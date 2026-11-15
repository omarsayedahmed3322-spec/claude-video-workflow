r"""Camera motion of every rough-cut shot, measured on the 4K original: pan dx, tilt dy (px/s at 1080 width) and zoom (%/s)
(skill reel-music-montage). Copied on 2026-11-13 from CLB R1 (AG2/CLB/Reel-01/scripts/motion_rough.py, 2026-11-07).
SETTINGS holds the reel's values; the logic is unchanged. Use it to group shots by direction: one direction per musical
phrase, change only on a music change (SKILL.md §الاتجاه). Adds "motion" to every shot of rough_map.json (written back).
Usage: python -I motion_rough.py [rough_map.json]   (the argument replaces MAP)"""
import os, json, subprocess, sys, numpy as np, cv2

# ============================ SETTINGS (CLB R1 values) ============================
FOOT = r"D:\Montage-02\Clients\AG2\AG2\Dropbox\4-11-2026"
MAP = r"D:\Montage-02\Clients\AG2\CLB\Reel-01\work\match\rough_map.json"   # from match_rough.py
EXT = ".MP4"
W, H = 270, 480                 # analysis size (x4 = 1080 wide)
FLOW_FPS = 10                   # frames per second analysed
TO_1080 = 4                     # 1080 / W
ZOOM_MIN, PAN_MIN = 1.5, 25     # %/s and px/s below which the shot reads static
# =====================================================================================
if len(sys.argv) > 1: MAP = sys.argv[1]
S = json.load(open(MAP))
for i, s in enumerate(S):
    t0 = s["src"][0][1]; t1 = s["src"][2][1]; dur = max(t1 - t0, 0.5)
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", "%.2f" % t0, "-t", "%.2f" % dur, "-i", os.path.join(FOOT, s["clip"] + EXT),
                          "-vf", "fps=%d,scale=%d:%d,format=gray" % (FLOW_FPS, W, H), "-f", "rawvideo", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W)
    dx = dy = zs = 0; n = 0
    for a, b in zip(fr[:-1], fr[1:]):
        p0 = cv2.goodFeaturesToTrack(a, 300, 0.01, 6)
        if p0 is None: continue
        p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None)
        ok = st.ravel() == 1
        if ok.sum() < 10: continue
        M, _ = cv2.estimateAffinePartial2D(p0[ok], p1[ok])
        if M is None: continue
        sc = np.sqrt(M[0, 0] ** 2 + M[1, 0] ** 2)
        dx += M[0, 2] + (sc - 1) * W / 2 * 0; dy += M[1, 2]; zs += sc - 1; n += 1
    k = FLOW_FPS * TO_1080 / max(n, 1)   # per second, scaled to 1080 px
    s["motion"] = dict(dx=round(dx * k, 1), dy=round(dy * k, 1), zoom=round(zs * FLOW_FPS / max(n, 1) * 100, 2))
    m = s["motion"]
    kind = "zoom-in" if m["zoom"] > ZOOM_MIN else "zoom-out" if m["zoom"] < -ZOOM_MIN else ""
    if abs(m["dx"]) > PAN_MIN: kind += (" content<-(cam right)" if m["dx"] < 0 else " content->(cam left)")
    if abs(m["dy"]) > PAN_MIN: kind += (" content-up(cam down)" if m["dy"] < 0 else " content-down(cam up)")
    print("%02d %s %.2f-%.2f  dx%6.1f dy%6.1f z%5.2f  %s" % (i, s["clip"], t0, t1, m["dx"], m["dy"], m["zoom"], kind or "static"))
json.dump(S, open(MAP, "w"), indent=1)
