"""R9: frame-exact cut check. diff(n) = mean |frame n - frame n-1| on 72x128 gray; at every expected cut frame f the diff must peak at f (not f-1 / f+1)."""
import subprocess, sys, json, numpy as np
v = sys.argv[1]
d = json.load(open("D:/Montage-02/Clients/Dusha/ريل 9/work/edl_R9.json"))
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", "scale=72:128,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
a = np.frombuffer(raw, np.uint8).reshape(-1, 128, 72).astype(np.float32)
df = np.r_[0, np.abs(np.diff(a, axis=0)).mean((1, 2))]
ok = 0
for s in d["shots"][1:]:
    f = s["f0"]; w = df[f - 2:f + 3]; pk = f - 2 + int(np.argmax(w))
    good = pk == f; ok += good
    print(f"{s['id']:5s} beat {s['b0']:5} frame {f:3d}  diffs {np.round(w, 1).tolist()}  peak {pk} {'OK' if good else 'OFF %+d' % (pk - f)}")
print(f"{ok}/{len(d['shots']) - 1} cuts on their beat frame")
