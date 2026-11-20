"""check_cuts.py — frame check at every planned cut of a render (from CLA R6, 2026-11-19).
The frame ON a cut must belong to the new shot (close to the next frame, far from the previous one), and neither the cut
frame nor the one before may be black. Catches what qc_reel's black-frame check misses: a single black frame or a
one-frame flash at a cut (CLA R6: a stretched layer started a frame late at 1.52 s and outlived its cut at 7.68 s).
Usage: python check_cuts.py <render.mp4> <edl.json> [--fps 25]
  edl.json: any EDL with "shots": [{"t0": ...}, ...] (plan_talking.py / plan_*.py) and optionally "outro".
Exit 1 if a cut is suspect."""
import argparse, json, subprocess, sys
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("mp4"); ap.add_argument("edl"); ap.add_argument("--fps", type=float, default=25)
a = ap.parse_args()
E = json.load(open(a.edl, encoding="utf-8"))
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.mp4, "-vf", "scale=108:192", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                     capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, 192, 108).astype(float)
cuts = [s["t0"] for s in E["shots"][1:]] + ([E["outro"]] if "outro" in E else [])
bad = 0
for t in cuts:
    n = int(round(t * a.fps))
    if n < 1 or n + 1 >= len(fr):
        continue
    prev_on = np.abs(fr[n] - fr[n - 1]).mean(); on_next = np.abs(fr[n + 1] - fr[n]).mean()
    flag = "OK" if on_next < prev_on else "FLASH?"
    if min(fr[n].mean(), fr[n - 1].mean()) < 12:
        flag = "BLACK"
    bad += flag != "OK"
    print("cut %7.2f (f%5d)  |f-1 -> f| %5.1f   |f -> f+1| %5.1f  %s" % (t, n, prev_on, on_next, flag))
print("cuts with a suspect frame:", bad)
sys.exit(1 if bad else 0)
