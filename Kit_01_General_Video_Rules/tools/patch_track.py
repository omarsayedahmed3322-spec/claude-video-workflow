# Remove something from an AI clip (a logo, invented text) with ONE cleaned frame: clean frame 0 with ChatGPT
# image («remove X, keep everything else identical»), then lay only the changed pixels over every frame,
# following the camera with an affine ECC around the area, matching the frame's light, with grain.
# usage: python -I patch_track.py <in.mp4> <out.mp4> <clean_frame0.png | self> <x0> <y0> <x1> <y1> [track_margin]
#        `self` = frame 0 is already clean and the thing shows up later (Veo invented text mid-clip, CLC R3 L05):
#        the whole box (feathered) is taken from frame 0
#        box = where the change is on frame 0 (source pixels); track_margin = how far around it to track (default 1.0 = box size)
import subprocess
import sys

import cv2
import numpy as np

src, dst, clean_p = sys.argv[1], sys.argv[2], sys.argv[3]
x0, y0, x1, y1 = (int(v) for v in sys.argv[4:8])
margin = float(sys.argv[8]) if len(sys.argv) > 8 else 1.0

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
f0 = frames[0]
gray = lambda im: cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.2)
crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)

SELF = clean_p == "self"
# 1. the clean frame comes back resized/shifted: align it to frame 0 on everything outside the box
clean = f0.copy() if SELF else cv2.resize(cv2.imdecode(np.fromfile(clean_p, np.uint8), 1), (W, H), interpolation=cv2.INTER_AREA)
out_m = np.full((H, W), 255, np.uint8)
cv2.rectangle(out_m, (x0 - 20, y0 - 20), (x1 + 20, y1 + 20), 0, -1)
wa = np.eye(2, 3, dtype=np.float32)
if not SELF:
  try:
    _, wa = cv2.findTransformECC(gray(f0), gray(clean), wa, cv2.MOTION_AFFINE, crit, out_m, 5)
  except cv2.error:
    pass
if not SELF:
    clean = cv2.warpAffine(clean, wa, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)

# 2. patch = pixels that really changed inside the box, grown and feathered
diff = np.abs(clean.astype(np.float32) - f0.astype(np.float32)).max(2)
pm = np.zeros((H, W), np.uint8)
pm[y0:y1, x0:x1] = 1 if SELF else (diff[y0:y1, x0:x1] > 18).astype(np.uint8)
pm = cv2.morphologyEx(pm, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
pm = cv2.dilate(pm, np.ones((13, 13), np.uint8))
pm = cv2.GaussianBlur(pm.astype(np.float32), (0, 0), 4)
ring = (cv2.dilate((pm > 0.05).astype(np.uint8), np.ones((31, 31), np.uint8)) > 0) & (pm < 0.02)
print("patch %.0f px, ring %d px" % (pm.sum(), ring.sum()))

# 3. follow the area: affine ECC on a window around the box (the patch itself excluded: it changes)
mx, my = int((x1 - x0) * margin), int((y1 - y0) * margin)
tm = np.zeros((H, W), np.uint8)
tm[max(0, y0 - my):min(H, y1 + my), max(0, x0 - mx):min(W, x1 + mx)] = 255
tm[pm > 0.02] = 0
g0 = gray(f0)
w = np.eye(2, 3, dtype=np.float32)
rng = np.random.default_rng(5)
ff = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "%dx%d" % (W, H),
                       "-r", str(fps), "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "14",
                       "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "copy", dst], stdin=subprocess.PIPE)
for i, f in enumerate(frames):
    try:
        _, w = cv2.findTransformECC(g0, gray(f), w.copy(), cv2.MOTION_AFFINE, crit, tm, 5)
    except cv2.error:
        pass
    c = cv2.warpAffine(clean, w, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    m = cv2.warpAffine(pm, w, (W, H), flags=cv2.INTER_LINEAR)[..., None]
    r = cv2.warpAffine(ring.astype(np.uint8), w, (W, H), flags=cv2.INTER_NEAREST) > 0
    fo = f.astype(np.float32)
    if r.sum() > 100:  # the light changes over the clip (door opens, sun): match the patch to the ring around it
        c *= np.clip(fo[r].mean(0) / np.maximum(c[r].mean(0), 1), 0.8, 1.25)
    c += rng.normal(0, 1.8, c.shape).astype(np.float32)
    ff.stdin.write(np.clip(fo * (1 - m) + c * m, 0, 255).astype(np.uint8).tobytes())
    if i % 40 == 0:
        print("frame %d  move %.1f,%.1f  zoom %.3f" % (i, w[0, 2], w[1, 2], np.sqrt(abs(np.linalg.det(w[:, :2])))))
ff.stdin.close()
ff.wait()
print("wrote", dst.encode("ascii", "replace").decode())
