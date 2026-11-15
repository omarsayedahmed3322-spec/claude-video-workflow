# Put a logo on a CLEAN clip (no logo on it) at a chosen spot, following the camera: the spot is an ellipse on
# frame 0 (the door seen at an angle), the area around it is tracked with an affine ECC, the logo is mapped onto the
# ellipse with its verticals kept vertical (shear, not rotation: a rotated logo read as «stuck on crooked», CLC R1),
# lit by the paint under it, softened like the footage, with grain.
# Used to move a logo to the same door in every shot when the AI put it on different doors (CLC R3, 2026-11-09).
# usage: python -I logo_place.py <clean.mp4> <out.mp4> <logo.png> <cx> <cy> <w> <h> <angle> [track_scale]
#        ellipse on frame 0 in source pixels (cv2.fitEllipse convention); track_scale = tracked window / ellipse (default 3),
#        0 = no tracking for a locked-off shot (plain white paint gave ECC nothing to hold and it ran away, CLC R3 L01)
import subprocess
import sys

import cv2
import numpy as np

src, dst, logo_p = sys.argv[1], sys.argv[2], sys.argv[3]
cx, cy, ew, eh, ea = (float(v) for v in sys.argv[4:9])
ts = float(sys.argv[9]) if len(sys.argv) > 9 else 3.0

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

logo = cv2.imdecode(np.fromfile(logo_p, np.uint8), cv2.IMREAD_UNCHANGED).astype(np.float32)
LH, LW = logo.shape[:2]
lrgb, la = logo[..., :3], logo[..., 3] / 255.0
t = np.deg2rad(ea)
R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
E = R @ np.diag([ew / 2, eh / 2])
A = np.linalg.cholesky(E @ E.T) @ np.diag([2 / LW, 2 / LH])  # same ellipse, upright verticals
M0 = np.vstack([np.hstack([A, (np.array([cx, cy]) - A @ np.array([LW / 2, LH / 2]))[:, None]]), [0, 0, 1]])

gray = lambda im: cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.2)
crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
r = max(ew, eh) * ts / 2
tm = np.zeros((H, W), np.uint8)
tm[max(0, int(cy - r)):min(H, int(cy + r)), max(0, int(cx - r * 1.5)):min(W, int(cx + r * 1.5))] = 255
g0 = gray(frames[0])
w = np.eye(2, 3, dtype=np.float32)
rng = np.random.default_rng(11)
ff = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "%dx%d" % (W, H),
                       "-r", str(fps), "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "14",
                       "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "copy", dst], stdin=subprocess.PIPE)
for i, f in enumerate(frames):
    try:
        if ts > 0:
            _, w = cv2.findTransformECC(g0, gray(f), w.copy(), cv2.MOTION_AFFINE, crit, tm, 5)
    except cv2.error:
        pass
    M = (np.vstack([w, [0, 0, 1]]) @ M0)[:2]
    wl = cv2.GaussianBlur(cv2.warpAffine(lrgb, M, (W, H), flags=cv2.INTER_AREA, borderValue=0), (0, 0), 0.7)
    wa = cv2.GaussianBlur(cv2.warpAffine(la, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0), (0, 0), 0.6)[..., None]
    fo = f.astype(np.float32)
    # the paint's own light and shade under the logo (white paint ≈ 1.0 → logo as designed)
    lum = cv2.GaussianBlur(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), max(3.0, max(ew, eh) / 8))
    m = wa[..., 0] > 0.5
    ref = np.percentile(lum[m], 90) if m.sum() > 50 else 255.0
    shade = np.clip(lum / max(ref, 1), 0.6, 1.1)[..., None]
    lg = wl * shade + rng.normal(0, 2.0, wl.shape).astype(np.float32)
    ff.stdin.write(np.clip(fo * (1 - wa) + lg * wa, 0, 255).astype(np.uint8).tobytes())
    if i % 48 == 0:
        print("frame %d  move %.1f,%.1f  zoom %.3f" % (i, w[0, 2], w[1, 2], np.sqrt(abs(np.linalg.det(w[:, :2])))))
ff.stdin.close()
ff.wait()
print("wrote", dst.encode("ascii", "replace").decode())
