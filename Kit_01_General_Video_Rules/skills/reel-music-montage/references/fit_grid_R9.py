"""R9: refit the beat grid on the reel's stretch of the track from the kick onsets themselves (120 Hz low-pass, Hilbert envelope, onset =
20 % of the rise before each peak). beat_grid.py's kick onsets moved by ~40 ms with the analysis window (full track vs excerpt), so the
cut grid comes from this direct measure. Bar downbeats (every 4th beat) peak late (bass note on top) and are left out of the fit."""
import subprocess, numpy as np, scipy.signal as ss, json
sr = 44100
s = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", "D:/Montage-02/Clients/Dusha/ريل 9/R9_sfx/music_src_pixabay_cjkap_minimal-groove.mp3",
                                  "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout, np.float32).astype(np.float64)
b, a = ss.butter(4, 120, btype="low", fs=sr); env = np.abs(ss.hilbert(ss.filtfilt(b, a, s))); env = np.convolve(env, np.ones(44) / 44, "same")
def onset(t):
    i0 = int((t - 0.12) * sr); w = env[i0:int((t + 0.12) * sr)]; p = int(np.argmax(w))
    fl = np.percentile(w[:max(10, p - int(0.03 * sr))], 20); th = fl + 0.2 * (w[p] - fl); j = p
    while j > 0 and w[j] > th: j -= 1
    return (i0 + j) / sr
B, S0 = 0.49706, 17.125
for it in range(3):
    ks = np.arange(40); on = np.array([onset(S0 + k * B) for k in ks]); r = on - (S0 + ks * B)
    m = np.abs(r - np.median(r)) < 0.03
    B, S0 = np.polyfit(ks[m], on[m], 1)
    print(f"iter {it}: B {B:.5f} S0 {S0:.4f}  inliers {m.sum()}/40  resid ms {np.round((on[m] - (S0 + ks[m] * B)) * 1000).astype(int).tolist()}")
json.dump({"B": round(B, 5), "S0": round(S0, 4)}, open("D:/Montage-02/Clients/Dusha/ريل 9/work/grid_fit.json", "w"))
