# Replace the AI-garbled logo disc on the van (or the chat avatar) with the real logo, frame by frame.
# Track: pink-disc ellipse per frame (searched near the last one), smoothed over time.
# Look: real logo warped onto the ellipse, colour-matched to the original disc, carrying the original's
#       light/shade, slightly softened + grain; only where the disc is visible (abayas in front stay on top).
# usage: python -I logo_replace.py <in.mp4> <out.mp4> <logo.png> <cx> <cy> [rigid [diameter [screen_angle]] | fixed w,h,angle]
#        (cx, cy = disc centre near frame 0)
import subprocess
import sys

import cv2
import numpy as np

src, dst, logo_path = sys.argv[1], sys.argv[2], sys.argv[3]
init = (float(sys.argv[4]), float(sys.argv[5]))

cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
cap.release()
H, W = frames[0].shape[:2]


def hsv_masks(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    pink = ((h >= 150) | (h <= 6)) & (s >= 70) & (v >= 60)
    white = (s < 70) & (v > 140)
    return pink, white


# ---------- 1. track ----------
ell = []
cx, cy, rad = init[0], init[1], 70.0
for f in frames:
    win = int(rad * 1.6 + 40)
    x0, y0 = max(0, int(cx - win)), max(0, int(cy - win))
    x1, y1 = min(W, int(cx + win)), min(H, int(cy + win))
    pink, _ = hsv_masks(f[y0:y1, x0:x1])
    m = cv2.morphologyEx(pink.astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    best = None
    for c in cs:
        if cv2.contourArea(c) < 150:
            continue
        mm = cv2.moments(c)
        d = np.hypot(mm["m10"] / mm["m00"] + x0 - cx, mm["m01"] / mm["m00"] + y0 - cy)
        score = cv2.contourArea(c) - 20 * d
        if best is None or score > best[0]:
            best = (score, c)
    if best is None or len(best[1]) < 5:
        ell.append(None)
        continue
    hull = cv2.convexHull(best[1]) + np.array([[x0, y0]])
    (ex, ey), (ew, eh), ea = cv2.fitEllipse(hull)
    ea = ((ea + 90) % 180) - 90  # same ellipse, upright logo
    if ea > 45:
        ea, ew, eh = ea - 90, eh, ew
    elif ea <= -45:
        ea, ew, eh = ea + 90, eh, ew
    if abs(ew - eh) / max(ew, eh) < 0.12:  # near-circle: the angle is noise, keep the logo upright
        ew = eh = (ew + eh) / 2
        ea = 0.0
    ell.append([ex, ey, ew, eh, ea])
    cx, cy, rad = ex, ey, max(ew, eh) / 2

# fill gaps + smooth (angle unwrapped; fitEllipse swaps axes near 0/180)
n = len(ell)
idx = [i for i in range(n) if ell[i] is not None]
P = np.array([ell[i] for i in idx], float)
for i in range(1, len(P)):
    while P[i, 4] - P[i - 1, 4] > 90:
        P[i, 4] -= 180
    while P[i, 4] - P[i - 1, 4] < -90:
        P[i, 4] += 180
A = np.stack([np.interp(range(n), idx, P[:, k]) for k in range(5)], 1)
k = 7
pad = np.pad(A, ((k // 2, k // 2), (0, 0)), mode="edge")
med = np.stack([np.median(pad[i:i + k], 0) for i in range(n)])
ker = np.ones(5) / 5
S = np.stack([np.convolve(np.pad(med[:, j], 2, mode="edge"), ker, "valid") for j in range(5)], 1)
# rigid mode (flat UI like a chat avatar): fixed size/angle, centre from template matching of the
# area around the disc (the disc outline alone is too small and noisy -> the logo shook, CLC R1 L05)
mode = sys.argv[6] if len(sys.argv) > 6 else ""
if mode in ("rigid", "fixed"):
    em = np.zeros((H, W), np.uint8)
    if mode == "fixed":
        # disc cut by the frame edge, so the hull fit lies: frame-0 ellipse given as "w,h,angle" around <cx> <cy>,
        # followed with ECC on the disc itself (a door moving next to it would pull a wider window, CLC R3 L01)
        w0, h0, a0 = (float(v) for v in sys.argv[7].split(","))
        S[:, 4] = a0
        cv2.ellipse(em, ((init[0], init[1]), (w0 * 1.15, h0 * 1.15), a0), 255, -1)
        tx, ty = init
    else:
        S[:, 2] = S[:, 3] = float(sys.argv[7]) if len(sys.argv) > 7 else np.median((S[:, 2] + S[:, 3]) / 2)  # optional diameter at frame 0
        # optional screen tilt at frame 0 (degrees, cv2 sign: up-to-the-right text = negative); the logo then turns with
        # the phone. Upright-to-the-frame read as crooked on a phone held at -5 deg (CLC R1 L05, Omar 2026-11-09)
        S[:, 4] = float(sys.argv[8]) if len(sys.argv) > 8 else 0.0
        w0 = h0 = S[0, 2]
        tx, ty = S[0, 0], S[0, 1]
        # follow the screen with an affine ECC (move + zoom; the phone drifted 22px and zoomed 4.6% in CLC R1 L05)
        r0 = int(max(S[0, 2], S[0, 3]) * 2.2)
        em[max(0, int(ty - r0)):int(ty + r0), max(0, int(tx - r0 * 1.6)):min(W, int(tx + r0 * 0.8))] = 255
    g0 = cv2.GaussianBlur(cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.2)
    wm = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
    for i in range(n):
        gi = cv2.GaussianBlur(cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.2)
        try:
            _, wm = cv2.findTransformECC(g0, gi, wm.copy(), cv2.MOTION_AFFINE, crit, em, 5)
        except cv2.error:
            pass
        S[i, 0], S[i, 1] = wm @ np.array([tx, ty, 1.0])
        z = np.sqrt(abs(np.linalg.det(wm[:, :2])))
        S[i, 2], S[i, 3] = w0 * z, h0 * z
        if mode == "rigid" and len(sys.argv) > 8:
            S[i, 4] = float(sys.argv[8]) + np.degrees(np.arctan2(wm[1, 0], wm[0, 0]))
    k3 = np.ones(3) / 3
    for j in (0, 1, 2, 3, 4):
        S[:, j] = np.convolve(np.pad(S[:, j], 1, mode="edge"), k3, "valid")
else:
    # a decal on a car body doesn't turn: one tilt for the whole clip (per-frame angles made it spin, CLC R1 L01)
    S[:, 4] = np.median(S[:, 4])
print("angle range before lock: %.1f..%.1f" % (A[:, 4].min(), A[:, 4].max()))
lo = np.stack([np.convolve(np.pad(S[:, j], 6, mode="edge"), np.ones(13) / 13, "valid") for j in (0, 1)], 1)
print("tracked %d/%d frames, size %.0fx%.0f, jitter %.2fpx" % (len(idx), n, S[:, 2].mean(), S[:, 3].mean(), np.abs(S[:, :2] - lo).mean()))

# ---------- 2. composite ----------
logo = cv2.imdecode(np.fromfile(logo_path, np.uint8), cv2.IMREAD_UNCHANGED).astype(np.float32)  # imread fails on Arabic paths
LH, LW = logo.shape[:2]
lrgb, la = logo[..., :3], logo[..., 3:] / 255.0
lp, _ = hsv_masks(logo[..., :3].astype(np.uint8))
logo_pink_mean = lrgb[lp & (la[..., 0] > 0.9)].mean(0)
lsat = cv2.cvtColor(logo[..., :3].astype(np.uint8), cv2.COLOR_BGR2HSV)[..., 1].astype(np.float32) / 255.0
rng = np.random.default_rng(7)

ff = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "%dx%d" % (W, H),
                       "-r", str(fps), "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "14",
                       "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "copy", dst], stdin=subprocess.PIPE)
for i, f in enumerate(frames):
    ex, ey, ew, eh, ea = S[i]
    t = np.deg2rad(ea)
    R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    Sc = np.diag([ew / LW, eh / LH])
    M = np.hstack([R @ Sc, (np.array([ex, ey]) - R @ Sc @ np.array([LW / 2, LH / 2]))[:, None]])
    wl = cv2.warpAffine(lrgb, M, (W, H), flags=cv2.INTER_AREA if ew < LW else cv2.INTER_LINEAR, borderValue=0)
    wa = cv2.warpAffine(la, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    ws = cv2.warpAffine(lsat, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    wl = cv2.GaussianBlur(wl, (0, 0), 0.7)
    wa = cv2.GaussianBlur(wa, (0, 0), 0.6)
    if wa.ndim == 3:
        wa = wa[..., 0]
    # work only in a box around the disc
    r = int(max(ew, eh) / 2 + 8)
    bx0, by0, bx1, by1 = max(0, int(ex - r)), max(0, int(ey - r)), min(W, int(ex + r)), min(H, int(ey + r))
    fo = f[by0:by1, bx0:bx1].astype(np.float32)
    pink, white = hsv_masks(f[by0:by1, bx0:bx1])
    inside = np.zeros(pink.shape, np.uint8)
    cv2.ellipse(inside, ((ex - bx0, ey - by0), (ew, eh), ea), 1, -1)
    inside = inside.astype(bool)
    # visible = disc pixels (pink or its white lettering); a dark abaya in front is not
    vis = ((pink | white) & inside).astype(np.uint8)
    vis = cv2.morphologyEx(vis, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    vis = cv2.GaussianBlur(vis.astype(np.float32), (0, 0), 0.8)
    # colour match + the original's light/shade (lettering smoothed away first)
    pk = pink & inside
    gain = np.clip(fo[pk].mean(0) / logo_pink_mean, 0.6, 1.4) if pk.sum() > 50 else np.ones(3)
    lum = cv2.cvtColor(fo.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    lum[~pk] = lum[pk].mean() if pk.sum() > 50 else lum.mean()
    shade = cv2.GaussianBlur(lum, (0, 0), max(3.0, r / 6))
    shade = np.clip(shade / shade[inside].mean(), 0.75, 1.25)[..., None]
    gl = float(np.mean(gain))
    sw = np.clip(ws[by0:by1, bx0:bx1] * 1.4, 0, 1)[..., None]  # tint only the pink, keep the white lettering neutral
    lg = wl[by0:by1, bx0:bx1] * (gl + (gain - gl) * sw) * shade
    lg += rng.normal(0, 2.2, lg.shape).astype(np.float32)  # grain like the footage
    a = (wa[by0:by1, bx0:bx1] * vis)[..., None]
    out = f.copy()
    out[by0:by1, bx0:bx1] = np.clip(fo * (1 - a) + lg * a, 0, 255).astype(np.uint8)
    ff.stdin.write(out.tobytes())
ff.stdin.close()
ff.wait()
print("wrote", dst.encode("ascii", "replace").decode())
