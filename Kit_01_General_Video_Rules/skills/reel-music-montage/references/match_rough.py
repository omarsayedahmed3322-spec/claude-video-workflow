r"""Match every shot of Omar's rough cut to its source clip + second in the 4K originals (tiny-frame correlation)
(skill reel-music-montage). Copied on 2026-11-13 from CLB R1 (AG2/CLB/Reel-01/scripts/match_rough.py, 2026-11-07:
33/33 shots matched, scores 0.87-0.99). Everything that belongs to one reel sits in SETTINGS; the logic is unchanged.
The rough cut is his shot SELECTION, not the material: build from the originals, and still drop a shot whose light or
quality is weak (Omar). Next: motion_rough.py (camera motion per shot) and grade.py (colour), both read the same map.
Usage: python -I match_rough.py [out_dir]   -> <out_dir>/rough_map.json (out_dir replaces OUT, e.g. a temp folder for a test;
the decoded-frames cache <out_dir>/orig_4fps.npz is reused when it is there)."""
import os, json, subprocess, sys, numpy as np, glob
from concurrent.futures import ThreadPoolExecutor

# ============================ SETTINGS (CLB R1 values) ============================
FOOT = r"D:\Montage-02\Clients\AG2\AG2\Dropbox\4-11-2026"                     # the 4K originals
ROUGH = r"D:\Montage-02\Clients\AG2\CLB\Reel-01\assets\Omar's-Rough-Cut.mp4"  # Omar's rough cut
OUT = r"D:\Montage-02\Clients\AG2\CLB\Reel-01\work\match"
CLIP_GLOB = "C0*.MP4"           # originals to search (Sony FX30 names)
KEY_LEN = 5                     # clip key = first 5 letters of the file name (C0376)
LIB_FPS = 4                     # originals sampled at 4 fps
ROUGH_FPS = 30                  # frame rate of the rough-cut file (shot times = frame / ROUGH_FPS)
W, H = 36, 64                   # tiny grey frames compared
CUT_DIFF, CUT_RATIO, CUT_WIN = 18, 2.5, 15   # a cut = frame difference > 18 and > 2.5x the median of +-15 frames
# =====================================================================================
if len(sys.argv) > 1: OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

def frames(path, fps=None, extra=()):
    vf = ("fps=%s," % fps if fps else "") + "scale=%d:%d,format=gray" % (W, H)
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", *extra, "-i", path, "-vf", vf, "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)

def norm(a):
    a = a.reshape(len(a), -1); a = a - a.mean(1, keepdims=True)
    return a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-6)

cache = os.path.join(OUT, "orig_4fps.npz")
if os.path.exists(cache):
    z = np.load(cache, allow_pickle=True); lib = z["lib"].item()
else:
    clips = sorted(glob.glob(os.path.join(FOOT, CLIP_GLOB)))
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda p: frames(p, LIB_FPS), clips))
    lib = {os.path.basename(p)[:KEY_LEN]: r for p, r in zip(clips, res)}
    np.savez(cache, lib=np.array(lib, dtype=object))
names, idx, mats = [], [], []
for k, v in lib.items():
    names += [k] * len(v); idx += list(range(len(v))); mats.append(v)
LIB = norm(np.concatenate(mats))
R = frames(ROUGH); RN = norm(R)
# cuts: big frame difference
d = np.abs(np.diff(R.reshape(len(R), -1), axis=0)).mean(1)
cuts = [0] + [i + 1 for i in range(len(d)) if d[i] > CUT_DIFF and (i == 0 or d[i] > CUT_RATIO * np.median(d[max(0, i - CUT_WIN):i + CUT_WIN]))] + [len(R)]
shots = []
for a, b in zip(cuts[:-1], cuts[1:]):
    if b - a < 2: continue
    pts = []
    for f in (a + min(2, (b - a) // 3), (a + b) // 2, b - 1 - min(2, (b - a) // 3)):
        sc = LIB @ RN[f]; j = int(sc.argmax())
        pts.append((f, names[j], idx[j] / LIB_FPS, float(sc[j])))
    shots.append(dict(r0=a / ROUGH_FPS, r1=b / ROUGH_FPS, clip=pts[1][1], score=round(pts[1][3], 3),
                      src=[[p[1], p[2], round(p[3], 3)] for p in pts]))
json.dump(shots, open(os.path.join(OUT, "rough_map.json"), "w"), indent=1)
for s in shots:
    print("%5.2f-%5.2f %s %.2f | %s" % (s["r0"], s["r1"], s["clip"], s["score"], " ".join("%s@%.2f" % (c, t) for c, t, _ in s["src"])))
