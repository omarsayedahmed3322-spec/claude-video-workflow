r"""Beat grid of a music track for a cut-on-the-beat montage (skill reel-music-montage). Written 2026-11-13 (plan phase 5-ب)
from the method in Kit_01 05_audio_sfx.md §1 that measured CLB R1 v11-v14 (the R1 measuring code itself was not saved;
only its result: grid 0.6457 s = 92.9 BPM, reel beat 0 = song 0.110 s).
Steps: librosa beat_track -> period folded into 70-140 BPM (librosa doubled the R1 tempo) -> kick onsets from the percussive
part band-passed 40-110 Hz (onset = steepest rise of a 5 ms RMS envelope before each peak) -> the grid phase is nudged so the
kicks sit on it (librosa's own grid was 0.07 s late on R1 = cuts 2 frames after the kick). With --near the nudge uses only the
kicks of the first NUDGE_BEATS beats of the reel: R1's kicks shift against one constant grid after the track's break (≈ +0.09 s
at reel beats 24-32), and R1 was aligned on its opening kicks. The kick list prints every offset so a drift shows.
Optional --drop: the first jump of the 150 Hz low-pass envelope (the drop in a track whose bass enters with the kick).
Times are never taken from agy/Gemini (05 §1); check the render after the build (cut frames vs beat frames).
Usage: python -I -X utf8 beat_grid.py <track> [--near SEC] [--drop] [--json out.json]
  --near SEC  print S0 = the grid line closest to SEC (the song second you want at reel beat 0; EDL setting S0)."""
import argparse
import json

import librosa
import numpy as np
import scipy.signal as ss

# ============================ SETTINGS ============================
SR = 22050
BPM_RANGE = (70, 140)           # fold the period into this range (halve / double)
KICK_BAND = (40, 110)           # Hz, band-pass on the percussive part
RMS_MS = 5                      # envelope window
KICK_HEIGHT = 0.3               # a kick peak is at least this fraction of the loudest one
KICK_GAP = 0.30                 # s, two kicks are at least this far apart
ON_BEAT = 0.125                 # a kick within this fraction of a beat from a grid line counts as on the beat
NUDGE_BEATS = 12                # with --near: phase from the kicks of the reel's first 12 beats only
DROP_LP = 150                   # Hz, low-pass for --drop
DROP_JUMP = 4.0                 # --drop: envelope jumps above this many times its median over the previous 2 s
# ==================================================================


def envelope(y, hop):
    return np.sqrt(np.convolve(y ** 2, np.ones(hop) / hop, "same"))[::hop]


def kick_onsets(y, sr):
    yp = librosa.effects.hpss(y)[1]
    b, a = ss.butter(4, list(KICK_BAND), btype="band", fs=sr)
    hop = int(sr * RMS_MS / 1000)
    env = envelope(ss.filtfilt(b, a, yp), hop)
    pk, _ = ss.find_peaks(env, height=env.max() * KICK_HEIGHT, distance=int(KICK_GAP * 1000 / RMS_MS))
    back = int(150 / RMS_MS)
    out = []
    for p in pk:
        lo = max(0, p - back)
        out.append((lo + int(np.argmax(np.diff(env[lo:p + 1])))) * RMS_MS / 1000)
    return np.array(out)


def grid(y, sr, near=None):
    _, bt = librosa.beat.beat_track(y=y, sr=sr, units="time")
    bt = np.asarray(bt)
    k, c = np.linalg.lstsq(np.vstack([np.arange(len(bt)), np.ones(len(bt))]).T, bt, rcond=None)[0]
    while 60 / k > BPM_RANGE[1]: k *= 2
    while 60 / k < BPM_RANGE[0]: k /= 2
    kicks = kick_onsets(y, sr)
    use = kicks if near is None else kicks[(kicks >= near - k / 2) & (kicks < near + NUDGE_BEATS * k)]
    best = None
    for ph in (c, c + k / 2):                     # librosa's beats may sit on the off-beat once the tempo is halved
        off = (use - ph) / k - np.round((use - ph) / k)
        on = np.abs(off) < ON_BEAT
        if best is None or on.sum() > best[0]: best = (on.sum(), ph, off[on])
    n_on, ph, off = best
    ph += float(np.median(off)) * k if len(off) else 0.0
    return float(k), float(ph % k), kicks, int(n_on)


def drop(y, sr):
    b, a = ss.butter(4, DROP_LP, btype="low", fs=sr)
    hop = int(sr * RMS_MS / 1000)
    env = envelope(ss.filtfilt(b, a, y), hop)
    w = int(2000 / RMS_MS)
    for i in range(w, len(env)):
        if env[i] > DROP_JUMP * (np.median(env[i - w:i]) + 1e-6): return i * RMS_MS / 1000
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("track"); ap.add_argument("--near", type=float); ap.add_argument("--drop", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    y, sr = librosa.load(a.track, sr=SR, mono=True)
    B, P, kicks, n_on = grid(y, sr, a.near)
    res = dict(period=round(B, 4), bpm=round(60 / B, 2), phase=round(P, 3), kicks_for_phase=n_on, kicks=len(kicks),
               kick_onsets=[round(float(t), 3) for t in kicks])
    print("grid %.4f s = %.2f BPM, first grid line %.3f s, %d kicks used for the phase, %d in the track" % (B, 60 / B, P, n_on, len(kicks)))
    if a.near is not None:
        n = round((a.near - P) / B); res["S0"] = round(P + n * B, 3)
        print("S0 (grid line nearest %.3f) = %.3f s (beat %d of the track)" % (a.near, res["S0"], n))
    if a.drop:
        res["drop"] = drop(y, sr); print("drop (first 150 Hz jump) =", res["drop"])
    for t in kicks:
        o = (t - P) / B; print("  kick %7.3f  beat %6.2f  off %+4d ms" % (t, o, round((o - round(o)) * B * 1000)))
    if a.json: json.dump(res, open(a.json, "w"), indent=1)
