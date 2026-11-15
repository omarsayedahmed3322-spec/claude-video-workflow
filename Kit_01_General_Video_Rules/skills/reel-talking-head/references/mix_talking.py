"""Talking-head mix (skill reel-talking-head). Copied on 2026-11-12 from CLA R1
(AG2/CLA/reel-01/scripts/mix_CLA_R1.py, the mix_v17 used by v17–v19). Everything that belongs to one reel sits in
SETTINGS; the logic under it is the CLA logic unchanged (only the names of the constants changed, and two sound
lists that were loaded but never used are gone).
Speech (Adobe Podcast enhanced, full source length) cut to the EDL's kept intervals + music ~20 dB under the voice +
sounds only on real transitions + brand-moment sounds. No caption taps (Omar, CLA v4 and v17).
Usage: python -I mix_talking.py <speech.wav> <out.wav> [work_dir] [edl.json]   (work_dir/edl replace WORK/EDL, e.g. for a test)"""
import json, os, re, subprocess, sys, wave
import numpy as np
WF = (os.environ.get("CLAUDE_WORKFLOW") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))).replace("\\", "/")   # <Claude-Workflow>: env CLAUDE_WORKFLOW (install.ps1), else the repo this file sits in

# ============================ SETTINGS (CLA R1 mix_v17 values) ============================
R = "D:/Montage-02/Clients/AG2/CLA/reel-01/"
EDL = R + "scripts/edl_CLA_R1.json"          # written by plan_talking.py
WORK = R + "assets/audio/"                    # temp files: _meas.wav, _vo.wav, _premaster.wav
LIB = WF + "/SFX_Library/"
OMAR = LIB + "more-sfx-added-by-omar/"
SR = 48000
SPEECH_END = 75.30                            # source second where the last speaker layer's audio stops
SPEECH_CHAIN = ("highpass=f=70,acompressor=threshold=-30dB:ratio=4:attack=5:release=120:knee=4,"
                "acompressor=threshold=-18dB:ratio=4:attack=2:release=60,alimiter=limit=0.7:level=false")
SPEECH_MEDIAN = -8.5                          # median 400 ms phrase peak, dBFS (Omar: phrase peaks between -10 and -6)
SPEECH_LIMIT = 0.5                            # limiter after the gain: nothing above -6 dBFS
MUSIC = R + "assets/music/CLA_music_v1.mp3"
MUSIC_EQ = "equalizer=f=2600:t=o:w=1.4:g=-5,equalizer=f=350:t=o:w=1:g=-2"
MUSIC_CUT, MUSIC_LOOP, MUSIC_XF = 56.76, 20.22, 0.5   # play A up to CUT, then B from LOOP (same beat phase), 0.5 s crossfade
MUSIC_UNDER, MUSIC_LOGO = -22, -6             # music gain under the speech / on the logo, dB
INTRO_CUTS = [2.40, 4.76, 7.12, 9.44]          # only when the EDL has an intro (t0 > 0): CLA v9 and before
FLASH_LEVEL, WHIP_LEVEL = -17, -18             # transition sounds; plain cuts and the zoom-through stay silent
SIGNATURE_SRC = 38.12                          # first time the brand name is said («CLA»), source second
SIGNATURE = [(OMAR + "risers and hits/ES_Bass, Sharp Detail Riser - Epidemic Sound.mp3", None, -15, 0.15, 0.1),
             (OMAR + "risers and hits/hit.mp3", 2.0, -14, 0.0, 1.2)]   # (file, seconds to keep, peak dBFS, fade in, out)
NAMES_SRC = [45.10, 50.61, 56.30]              # each product name (word starts from the silence ends)
NAME_SOUND = (OMAR + "textures/clicks/ES_Select, Soft Round Pluck, Short, Reverb - Epidemic Sound.mp3", 1.4, -12, 0.0, 0.5)
FINAL_LIMIT = 0.85
# ============================================================================================

if len(sys.argv) > 3:
    WORK = sys.argv[3].rstrip("/\\") + "/"
if len(sys.argv) > 4:
    EDL = sys.argv[4]
E = json.load(open(EDL, encoding="utf-8"))
DUR, T0, T = E["dur"], E.get("t0", 11.76), E["outro"]
N = int(SR * DUR)


def load(path, af=None):
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-ac", "2", "-ar", str(SR)] + (["-af", af] if af else []) + ["-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).reshape(-1, 2).copy()


db = lambda x: 10 ** (x / 20)


def put(bus, a, t, g=1.0):
    i = int(round(t * SR))
    if i < 0:
        a, i = a[-i:], 0
    n = min(len(a), N - i)
    if n > 0:
        bus[i:i + n] += a[:n] * g


def fade(a, fin=0.0, fout=0.0):
    a = a.copy()
    if fin:
        k = max(1, int(fin * SR)); a[:k] *= np.linspace(0, 1, k)[:, None]
    if fout:
        k = max(1, int(fout * SR)); a[-k:] *= np.linspace(1, 0, k)[:, None]
    return a


peak_to = lambda a, d: a * db(d) / (np.abs(a).max() or 1)


def env(points):
    xs, ys = zip(*points)
    return np.interp(np.arange(N) / SR, xs, [db(y) for y in ys])[:, None]


def lufs(a):
    p = WORK + "_meas.wav"; write(p, a)
    out = subprocess.run(["ffmpeg", "-nostdin", "-i", p, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])


def write(path, a):
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


vo, mus, sfx = (np.zeros((N, 2), np.float32) for _ in range(3))

# speech: each kept interval at its speaker-layer time, 8 ms fades so the joins don't click
src = load(sys.argv[1], SPEECH_CHAIN)
for d in E["doc"]:
    t1 = d["t1"] if d is not E["doc"][-1] else d["t0"] + (SPEECH_END - d["src"])
    seg = src[int(d["src"] * SR):int((d["src"] + t1 - d["t0"]) * SR)]
    put(vo, fade(seg, 0.008, 0.008), d["t0"])

# music: A from 0, B from the same beat phase further in, loud on the intro and the logo, low under the voice
m = load(MUSIC, MUSIC_EQ)
xf = int(MUSIC_XF * SR); cut = MUSIC_CUT
A = m[:int(cut * SR) + xf].copy(); A[-xf:] *= np.linspace(1, 0, xf)[:, None]
B = m[int(MUSIC_LOOP * SR) - xf:].copy(); B[:xf] *= np.linspace(0, 1, xf)[:, None]
put(mus, A, 0); put(mus, B, cut - MUSIC_XF)
head = [(0, -2), (T0 - 0.45, -2), (T0 + 0.3, MUSIC_UNDER)] if T0 > 0 else [(0, -40), (0.3, MUSIC_UNDER)]   # no intro
mus *= env(head + [(T - 0.5, MUSIC_UNDER), (T + 0.5, MUSIC_LOGO), (DUR - 2.2, MUSIC_LOGO), (DUR, -45)])


# speech peaks between -10 and -6 dBFS (Omar): median phrase peak at SPEECH_MEDIAN, then a limiter at -6
def wpeaks(a, sec=0.4):                 # word/phrase peaks like a meter's peak hold
    w = int(sec * SR); p = np.abs(a[:len(a) // w * w]).max(1).reshape(-1, w).max(1)
    return 20 * np.log10(p[p > db(-35)])


vo *= db(SPEECH_MEDIAN - np.median(wpeaks(vo)))
tv = WORK + "_vo.wav"; write(tv, vo)
vo = load(tv, "alimiter=limit=%g:attack=3:release=60:level=false" % SPEECH_LIMIT)[:N]
pk = wpeaks(vo)
print("VO 400ms peaks dBFS: median %.1f, p10 %.1f, max %.1f" % (np.median(pk), np.percentile(pk, 10), pk.max()))
bed = vo + mus

# SFX at absolute levels (added after the loudness gain, so their peaks stay where they are set)
swoosh = load(LIB + "base_swoosh_smooth.wav")
wind = load(OMAR + "whoosh/ES_Organic, Wind, Soft, Normal 02 - Epidemic Sound.mp3")
hollow = load(OMAR + "whoosh/ES_Classic, Hollow, Low, Long - Epidemic Sound.mp3")
riser = load(LIB + "base_riser_tonal.wav")
drum = load(OMAR + "risers and hits/ES_Low Drum Hit, Simple - Epidemic Sound.mp3")
chime = load(LIB + "base_chime_success.wav")


def whoosh_at(t, k, level):
    s = fade(peak_to([swoosh, wind][k % 2][:int(1.2 * SR)], level), 0.0, 0.25)
    put(sfx, s, t - int(np.argmax(np.abs(s).max(1))) / SR)


if T0 > 0:                        # CLA v9 and before: beat-cut intro whooshes + riser/drum into the speaker
    for k, t in enumerate(INTRO_CUTS):
        whoosh_at(t, k, -10)
    r = fade(peak_to(riser, -14), 0.4, 0.05); put(sfx, r, T0 - len(r) / SR)
    put(sfx, fade(peak_to(drum, -9), 0, 0.6), T0)
# CLA v11 (Omar: «whooshes كتير، متعلقش على صوت واحد»): each transition kind has its own sound, rotating inside it
UI = OMAR + "Flex UI SFX/"
shimmer = [load(UI + "jingle-steel-0%d.wav" % k) for k in (1, 2, 4, 5, 6)]


def hit(s, t, level, lead=True):      # lead: place the sound's peak on the cut
    s = fade(peak_to(s[:int(1.2 * SR)], level), 0.0, 0.25)
    put(sfx, s, t - (int(np.argmax(np.abs(s).max(1))) / SR if lead else 0))


# the sound follows the transition (build_talking.jsx trans()): flash = steel shimmer starting with the light,
# whip = whoosh peaking on the cut, zoom = silent
br, n = E["broll"], {"flash": 0, "whip": 0, "zoom": 0}


def tsound(kind, t):
    if kind == "cut":                 # v15: plain cuts carry no transition sound (Omar: not every cut is a transition)
        return
    k = n[kind]; n[kind] += 1
    if kind == "flash":
        hit(shimmer[k % 5], t - 0.24, FLASH_LEVEL, lead=False)
    elif kind == "whip":
        whoosh_at(t, k, WHIP_LEVEL)
    else:                             # v17: zoom-through stays silent (Omar: the soft switch read as a camera fault)
        pass


for i, b in enumerate(br):
    tsound(b["tin"], b["t0"])
    if not (i < len(br) - 1 and abs(br[i + 1]["t0"] - b["t1"]) < 0.01):
        tsound(b["tout"], b["t1"])


def tl(src):                      # source second -> timeline second (same mapping as plan_talking.py)
    t = T0
    for a, b in E["keep"]:
        if src <= a:
            return t
        if src <= b:
            return t + src - a
        t += b - a
    return t


def on_word(s, t, level, fin=0.0, fout=0.3):     # the sound's loudest point lands on the word
    s = fade(peak_to(s, level), fin, fout)
    put(sfx, s, t - int(np.argmax(np.abs(s).max(1))) / SR)


def clipped(path, sec):
    a = load(path)
    return a[:int(sec * SR)] if sec else a


# CLA v16 (Omar): a signature sound the first time the brand name is said, and one other sound repeated on each
# product name.
cel = tl(SIGNATURE_SRC)
for path, sec, level, fin, fout in SIGNATURE:
    on_word(clipped(path, sec), cel, level, fin, fout)
pluck = clipped(NAME_SOUND[0], NAME_SOUND[1])
names = [tl(x) for x in NAMES_SRC]
for nm in names:
    on_word(pluck, nm, NAME_SOUND[2], NAME_SOUND[3], NAME_SOUND[4])
print("CLA", round(cel, 2), "names", [round(n, 2) for n in names])
# logo: a low hollow whoosh into the white, a soft drum under the logo, a quiet chime
put(sfx, fade(peak_to(hollow, -13), 0.05, 0.6), T - 0.5)
put(sfx, fade(peak_to(drum, -8), 0, 0.8), T + 0.44)
put(sfx, fade(peak_to(chime, -20), 0, 0.8), T + 0.5)
# no caption tap — soft-click «مكتوم… كأن فيه عيب تصوير» (Omar, CLA v4 and v17)

tmp = WORK + "_premaster.wav"
write(tmp, bed + sfx)
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", tmp, "-af", "alimiter=limit=%g:level=false" % FINAL_LIMIT,
                "-c:a", "pcm_s16le", sys.argv[2]], check=True)
print("written", sys.argv[2], "dur", DUR)
