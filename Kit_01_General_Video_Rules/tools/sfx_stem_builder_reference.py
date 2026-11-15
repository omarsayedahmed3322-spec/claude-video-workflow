"""REFERENCE COPY (AG1 reel). Framework is reusable; replace cues(), VO windows, GAP, LENGTH per project."""
"""AG1 Agency promo - SFX stem builder.

39.00 s @ 30 fps. Builds 6 stereo stems (48 kHz / 24-bit) from the 12 base
sounds in sources/. Every cue is aligned so its acoustic peak (smoothed
envelope max) lands on its target time, unless anchored to its start.

Levels are clip PEAK dBFS. Cue list is data (CUES); later sections append.
"""
import csv
import glob
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parent
SRC, DER, STEMS = ROOT / "sources", ROOT / "derived", ROOT / "stems"
SR, FPS, LENGTH = 48000, 30, 39.00
N = int(round(LENGTH * SR))
LAYERS = ["01_ambience", "02_motion", "03_texture", "04_emotional", "05_foley", "06_extras"]

# Default clip peak levels (dBFS) when a cue does not specify one.
LV = dict(whoosh=-12, swoosh=-12, pop=-14, click=-16, marker=-16,
          typing=-18, hit=-8, chime=-22)


# ---------------------------------------------------------------- DSP helpers
_cache = {}


def load(name):
    """Base sound as float32 stereo (n, 2) at 48 kHz."""
    if name not in _cache:
        path = SRC / name
        if name == "base_ambience_clean.mp3":
            # tile the raw 5.0 s seamless loop, not the 12 s render (its seam is mid-loop)
            path = Path(glob.glob(str(SRC / "_raw" / "01" / "*.mp3"))[0])
        y, _ = librosa.load(path, sr=SR, mono=False)
        y = np.atleast_2d(y).T
        if y.shape[1] == 1:
            y = np.repeat(y, 2, axis=1)
        _cache[name] = y.astype(np.float32)
    return _cache[name].copy()


def pitch(x, st):
    """Sampler-style varispeed: +st = higher and shorter (keeps transients clean)."""
    if st == 0:
        return x
    r = 2 ** (st / 12)
    return librosa.resample(x.T, orig_sr=SR * r, target_sr=SR).T


def _filt(x, kind, f, order=2):
    sos = butter(order, f, btype=kind, fs=SR, output="sos")
    return sosfilt(sos, x, axis=0).astype(np.float32)


def hpf(x, f):
    return _filt(x, "highpass", f)


def lpf(x, f):
    return _filt(x, "lowpass", f)


def fade(x, in_ms=2.0, out_ms=10.0):
    x = x.copy()
    ni, no = int(SR * in_ms / 1000), int(SR * out_ms / 1000)
    if ni:
        x[:ni] *= np.linspace(0, 1, ni)[:, None]
    if no:
        x[-no:] *= np.linspace(1, 0, no)[:, None]
    return x


def trim(x, dur, out_ms=60.0):
    return fade(x[: int(dur * SR)], 0, out_ms)


def gain_peak(x, db):
    return x * (10 ** (db / 20) / (np.abs(x).max() + 1e-12))


def pan(x, a, b=None):
    """Constant-power pan of the mono sum, -1 (L) .. +1 (R); a->b sweeps across the clip."""
    b = a if b is None else b
    m = x.mean(axis=1)
    th = (np.linspace(a, b, len(m)) + 1) * np.pi / 4
    return (np.stack([np.cos(th) * m, np.sin(th) * m], axis=1) * np.sqrt(2)).astype(np.float32)


def peak_idx(x, win_ms=10):
    w = max(1, int(SR * win_ms / 1000))
    env = np.convolve(np.abs(x).mean(axis=1), np.ones(w) / w, "same")
    return int(np.argmax(env))


# ------------------------------------------------------------ sound builders
def whoosh(st=0, dur=None, pan_ab=(0, 0), db=LV["whoosh"]):
    x = hpf(pitch(load("base_whoosh_fast.wav"), st), 120)
    if dur:
        x = trim(x, dur, 80)
    return gain_peak(pan(x, *pan_ab) if pan_ab != (0, 0) else x, db)


def swoosh(dur, db=LV["swoosh"]):
    return swoosh_p(0, dur, db)


def swoosh_p(st, dur, db=LV["swoosh"]):
    x = hpf(pitch(load("base_swoosh_smooth.wav"), st), 120)
    return gain_peak(trim(x, dur, 120), db)


def pop(st=0, p=None, db=LV["pop"], lp=None):
    x = hpf(pitch(load("base_pop_card.wav"), st), 200)
    if lp:
        x = lpf(x, lp)
    return gain_peak(pan(x, p) if p is not None else x, db)


def click(st=0, p=None, db=LV["click"], lp=None):
    x = hpf(pitch(load("base_click_ui.wav"), st), 800)
    if lp:
        x = lpf(x, lp)
    return gain_peak(pan(x, p) if p is not None else x, db)


def marker(st=0, pan_ab=None, lp=None, db=LV["marker"]):
    x = hpf(pitch(load("base_marker_strike.wav"), st), 300)
    if lp:
        x = lpf(x, lp)
    return gain_peak(pan(x, *pan_ab) if pan_ab else x, db)


def hit(dur=0.6, db=LV["hit"], mid=False):
    """Sub-heavy impact. mid=True adds a 200 Hz+ transient so it survives phone speakers."""
    x = trim(load("base_hit_impact.wav"), dur, 150)
    x = gain_peak(x, db)
    if mid:
        t = gain_peak(hpf(pitch(load("base_pop_card.wav"), -5), 250), db - 10)
        x[: len(t)] += t[: len(x)]
    return x


def punch(db=-12):
    """Tight low-mid punch: LPF'd hit + UI click on the same transient."""
    x = gain_peak(trim(lpf(load("base_hit_impact.wav"), 600), 0.35, 120), db)
    c = click(0, db=db - 4)
    shift = peak_idx(x, 5) - peak_idx(c, 5)  # click start offset inside x
    c = c[max(-shift, 0):]
    s = max(shift, 0)
    out = np.zeros((max(len(x), s + len(c)), 2), np.float32)
    out[: len(x)] += x
    out[s: s + len(c)] += c
    return out


def warm_punch(db=-10):
    """Warm low-mid punch: hit body (LPF 1.2 kHz) + pitched-down pop for 200 Hz+ presence."""
    x = gain_peak(trim(lpf(load("base_hit_impact.wav"), 1200), 0.5, 150), db)
    t = gain_peak(lpf(hpf(pitch(load("base_pop_card.wav"), -5), 200), 1500), db - 6)
    x[: len(t)] += t[: len(x)]
    return gain_peak(x, db)


def riser(max_len):
    """Riser cut hard at its own peak (5 ms fade); keeps the last max_len seconds."""
    x = load("base_riser_tonal.wav")
    x = x[: peak_idx(x, 10) + 1][-int(max_len * SR):]
    return gain_peak(fade(x, 20, 5), -10)


def vibrate(total=1.10, p=-0.30, db=-16):
    """Two buzz pulses (the 0.62 s buzz repeated), faded out at `total` seconds."""
    b = load("base_phone_vibrate.wav")[: int(0.62 * SR)]
    x = np.concatenate([b, np.zeros((int(0.03 * SR), 2), np.float32), b])
    x = hpf(trim(x, total, 120), 100)
    return gain_peak(pan(x, p), db)


def paper(db=-14):
    return gain_peak(hpf(load("base_paper_slide.wav"), 150), db)


def typing(dur=0.7, db=LV["typing"]):
    return gain_peak(trim(hpf(load("base_typing_burst.wav"), 300), dur, 60), db)


def chime(st=0, db=LV["chime"]):
    return gain_peak(hpf(pitch(load("base_chime_success.wav"), st), 400), db)


def ambience_bed():
    loop = load("base_ambience_clean.mp3")
    y = np.tile(loop, (int(np.ceil(N / len(loop))), 1))[:N]
    y = lpf(hpf(y, 100), 9000)
    y = gain_peak(y, -24)
    f0, f1 = int(38.0 * SR), N
    y[f0:f1] *= np.linspace(1, 0, f1 - f0)[:, None]
    return fade(y, 50, 0)


# --------------------------------------------------------------------- cues
# (id, layer, target_s, clip, anchor, win_ms, note)
# anchor "peak": clip's smoothed peak lands on target_s; "start": clip starts at target_s;
# "end": clip ends at target_s.
def cues():
    C = []

    def add(cid, layer, t, clip, note, anchor="peak", win=10):
        C.append((cid, layer, t, clip, anchor, win, note))

    # Section 1 - Hook & Brand Intro (0.00 - 7.80)
    add("S1-01a", "04_emotional", 0.08, hit(0.6), "hook hit: 'يا أخوي' + stop sign")
    add("S1-01b", "03_texture", 0.08, pop(+1), "hook pop layer", win=5)
    add("S1-02", "02_motion", 0.95, whoosh(0, pan_ab=(-0.7, 0)), "flip to white 'اسمعني' L->C", win=30)
    add("S1-03", "03_texture", 1.35, marker(+2, lp=6000), "underline draws under 'اسمعني'")
    add("S1-04", "03_texture", 2.00, pop(0), "search-bar UI pops", win=5)
    add("S1-05", "03_texture", 2.15, typing(0.7), "typing 'تدري من حنا؟' 2.15-2.85", anchor="start")
    add("S1-06a", "02_motion", 3.05, swoosh(0.6), "card slides up from bottom", anchor="start")
    add("S1-06b", "04_emotional", 3.45, hit(1.0, db=-10, mid=True), "logo snaps into focus")
    add("S1-07", "02_motion", 4.85, whoosh(-1, pan_ab=(0.7, 0)), "cut to 'واللي ورانا' R->C", win=30)
    add("S1-08", "02_motion", 5.85, whoosh(+1), "banner 'مو مجرد بوستات وتصاميم'", win=30)
    for i, (t, st, p) in enumerate(zip([6.55, 6.80, 7.05, 7.30], [-2, -1, 0, 1],
                                       [-0.40, -0.15, 0.15, 0.40])):
        add(f"S1-09{'abcd'[i]}", "03_texture", t, pop(st, p, db=-15), f"post frame {i + 1} pops", win=5)

    # Section 2 - Problem vs. Target Goal (7.80 - 13.80)
    add("S2-01", "02_motion", 7.85, whoosh(-2), "cut to red-border 'ما نبدأ بسؤال:'", win=30)
    add("S2-02", "03_texture", 8.85, pop(0), "card 'كم بوست تبغى؟' pops", win=5)
    add("S2-03", "05_foley", 9.30, marker(0, pan_ab=(-0.6, 0.6), db=-14), "red strike-through L->R")
    add("S2-04", "02_motion", 9.95, swoosh(0.5), "to blue grid, podium blocks", win=30)
    add("S2-05a", "03_texture", 10.60, pop(0), "top block + bullseye pops", win=5)
    add("S2-05b", "06_extras", 10.60, chime(), "subtle success chime", win=5)
    add("S2-06", "04_emotional", 11.35, punch(), "'وش الهدف' low-mid punch", win=5)
    add("S2-07", "03_texture", 12.30, click(-1), "bottom block unblurs", win=5)

    # Section 3 - Process & Campaign Management (13.80 - 20.80)
    add("S3-01a", "02_motion", 13.90, whoosh(0), "cut to white 'نفهم مشروعك'", win=30)
    add("S3-01b", "03_texture", 13.90, pop(0), "box snaps in", win=5)
    add("S3-02", "03_texture", 14.80, pop(-2), "'وعميلك' box drops in", win=5)
    for i, (t, st) in enumerate(zip([15.55, 15.95, 16.35], [-1, 0, 1])):
        add(f"S3-03{'abc'[i]}", "02_motion", t, whoosh(st, dur=0.35, db=-14), f"banner {i + 1} swish", win=30)
        add(f"S3-03{'abc'[i]}c", "03_texture", t, click(0), f"banner {i + 1} snap", win=5)
    add("S3-04", "02_motion", 17.05, whoosh(0, db=-14), "cut to white 'وندير'", win=30)
    steps = [(17.70, pop, 0, -0.25, "حملاتك"), (18.65, click, 1, 0.25, "من الاختبار"),
             (19.35, pop, 2, -0.25, "إلى التحليل"), (20.00, click, 3, 0.25, "والتحسين")]
    for i, (t, fn, st, p, txt) in enumerate(steps):
        add(f"S3-05{'abcd'[i]}", "03_texture", t, fn(st, p), f"step '{txt}'", win=5)

    # Section 4 - Attention, Conviction & Conversion (20.80 - 25.80)
    add("S4-01", "02_motion", 20.90, swoosh(0.5), "signboard 'نعرف وش يلفت'", win=30)
    add("S4-02a", "06_extras", 21.15, chime(-3), "red lamp glow pulse", win=5)
    add("S4-02b", "03_texture", 21.65, pop(0), "'انتباه عميلك' fills sign", win=5)
    add("S4-03", "02_motion", 22.55, swoosh(0.6), "diagonal bars + split panels", win=30)
    for i in range(3):
        add(f"S4-03{'abc'[i]}", "02_motion", 22.55 + 0.05 * i, click(i, db=-20), f"micro-click {i + 1}", win=2)
    add("S4-04", "03_texture", 23.05, chime(0, db=-14), "checkmark badge", win=5)
    add("S4-05", "02_motion", 23.85, whoosh(-1), "split-screen reveals phone", win=30)
    add("S4-06a", "05_foley", 24.00, vibrate(), "phone vibrates L30, 24.00-25.10", anchor="start")
    add("S4-06b", "03_texture", 25.15, click(0), "'ويشتري' lands", win=5)

    # Section 5 - The 3 Pillars & Final CTA (25.80 - 39.00)
    add("S5-01", "05_foley", 25.90, paper(), "envelope opens, 'كل رسالة' card slides", anchor="start")
    for i in range(6):
        add(f"S5-02{'abcdef'[i]}", "03_texture", 26.70 + 0.095 * i, click(0.5 * i, db=-18),
            f"avatar card {i + 1}", win=2)
    add("S5-03", "02_motion", 27.55, whoosh(0), "cut to white, design UI windows", win=30)
    for i, (t, p) in enumerate(zip([27.65, 27.80, 27.95], [-0.3, 0.0, 0.3])):
        add(f"S5-03{'abc'[i]}", "03_texture", t, pop(i, p, db=-15), f"UI window tap {i + 1}", win=5)
    add("S5-04a", "02_motion", 28.85, swoosh_p(-2, 0.55), "badge drops from top", anchor="start")
    add("S5-04b", "05_foley", 29.15, pop(-1, db=-14), "badge stops (tactile)", win=5)
    add("S5-05", "04_emotional", 29.85, warm_punch(-10), "'لها هدف' snaps in", win=5)
    add("S5-06", "04_emotional", 32.90, riser(2.05), "riser 30.85 -> hard cut 32.90", anchor="end")
    for i, t in enumerate([31.05, 31.45, 31.85, 32.25]):
        add(f"S5-06{'abcd'[i]}", "03_texture", t, click(0, db=-20, lp=4000), f"muffled word pulse {i + 1}", win=5)
    add("S5-07a", "04_emotional", 33.02, hit(1.48, db=-6, mid=True), "CTA burst: logo + 'تواصل معنا'")
    add("S5-07b", "02_motion", 33.02, chime(0, db=-14), "CTA chime", win=5)
    add("S5-08a", "02_motion", 34.10, swoosh_p(+2, 0.6, db=-16), "'فريق DIGITAL BUILD' unblurs", win=30)
    add("S5-08b", "03_texture", 35.15, pop(-1, db=-14, lp=6000), "'جاهز يبنيها معك' final pop", win=5)
    return C


# ------------------------------------------------------------ mix processing
# Active VO speech windows (s). Motion/texture/foley duck -5 dB inside them.
VO = [(0.05, 1.85), (2.00, 4.45), (4.85, 7.45), (7.85, 9.65), (10.05, 13.45),
      (13.90, 20.45), (20.90, 25.45), (25.90, 30.55), (30.95, 36.80)]
DUCK_DB, DUCK_LAYERS, DUCK_SMOOTH_MS = -5.0, ("02_motion", "03_texture", "05_foley"), 60
GAP = (32.90, 33.00)        # deliberate pre-CTA silence (all layers)
MASTER_CEIL_DB, MASTER_HPF = -1.5, 30


def duck_env():
    g = np.ones(N, np.float32)
    for a, b in VO:
        g[int(a * SR): int(b * SR)] = 10 ** (DUCK_DB / 20)
    w = int(SR * DUCK_SMOOTH_MS / 1000)
    return np.convolve(np.pad(g, w, mode="edge"), np.ones(w) / w, "same")[w:-w]


def gap_env(floor_db=-60, ramp_ms=8):
    """Gain dip to `floor_db` over GAP; ramps sit inside the gap so 33.00 is untouched."""
    g = np.ones(N, np.float32)
    a, b, r = int(GAP[0] * SR), int(GAP[1] * SR), int(SR * ramp_ms / 1000)
    lo = 10 ** (floor_db / 20)
    g[a:b] = lo
    g[a:a + r] = np.linspace(1, lo, r)
    g[b - r:b] = np.linspace(lo, 1, r)
    return g


def limit(x, ceil_db, look_ms=5):
    """Look-ahead peak limiter: min-filter then box-smooth (<= window) never overshoots."""
    from scipy.ndimage import minimum_filter1d
    c = 10 ** (ceil_db / 20)
    need = np.minimum(1.0, c / (np.abs(x).max(axis=1) + 1e-12))
    w = max(1, int(SR * look_ms / 1000))
    g = minimum_filter1d(need, w * 2 + 1)
    g = np.convolve(g, np.ones(w) / w, "same")
    return np.clip(x * g[:, None], -c, c).astype(np.float32)


# -------------------------------------------------------------------- build
def build():
    DER.mkdir(exist_ok=True)
    STEMS.mkdir(exist_ok=True)
    stems = {k: np.zeros((N, 2), np.float32) for k in LAYERS}
    stems["01_ambience"] += ambience_bed()

    rows = []
    for cid, layer, t, clip, anchor, win, note in cues():
        p = peak_idx(clip, win)
        off = {"peak": p, "start": 0, "end": len(clip)}[anchor]
        start = int(round(t * SR)) - off
        a, b = max(start, 0), min(start + len(clip), N)
        stems[layer][a:b] += clip[a - start: b - start]
        actual = (start + p) / SR
        target = t if anchor == "peak" else actual
        rows.append(dict(id=cid, layer=layer, anchor=anchor, target_s=f"{t:.3f}",
                         start_s=f"{start / SR:.3f}", end_s=f"{(start + len(clip)) / SR:.3f}",
                         peak_s=f"{actual:.4f}",
                         err_frames=f"{(actual - target) * FPS:+.3f}",
                         clip_dur_s=f"{len(clip) / SR:.3f}",
                         clip_peak_db=f"{20 * np.log10(np.abs(clip).max()):.1f}",
                         clipped_start=start < 0, note=note))

    duck, gap = duck_env(), gap_env()
    for k in LAYERS:
        if k in DUCK_LAYERS:
            stems[k] *= duck[:, None]
        # ambience dips 18 dB in the gap (bed keeps breathing); everything else goes silent
        stems[k] *= (gap[:, None] if k != "01_ambience" else (1 - (1 - gap[:, None]) * (1 - 10 ** (-18 / 20))))

    for k, y in stems.items():
        assert len(y) == N
        sf.write(STEMS / f"{k}.wav", y, SR, subtype="PCM_24")
    mix = hpf(sum(stems.values()), MASTER_HPF)
    pk = np.abs(mix).max()
    master = limit(mix, MASTER_CEIL_DB)
    sf.write(STEMS / "00_FULL_SFX_MASTER.wav", master, SR, subtype="PCM_24")
    old_preview = DER / "preview_mix.wav"
    if old_preview.exists():
        old_preview.unlink()

    with open(DER / "cue_log.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"{'id':8} {'layer':13} {'target':>7} {'peak':>8} {'err_fr':>7} {'dur':>6} {'dB':>6}")
    for r in rows:
        flag = "  <- starts before 0" if r["clipped_start"] else ""
        print(f"{r['id']:8} {r['layer']:13} {r['target_s']:>7} {r['peak_s']:>8} "
              f"{r['err_frames']:>7} {r['clip_dur_s']:>6} {r['clip_peak_db']:>6}{flag}")
    print("\nstem peaks (dBFS):")
    for k, y in stems.items():
        print(f"  {k:13} {20 * np.log10(np.abs(y).max() + 1e-12):6.1f}   len {len(y) / SR:.3f} s")
    print(f"  mix pre-limit  {20 * np.log10(pk):6.1f}")
    print(f"  MASTER         {20 * np.log10(np.abs(master).max()):6.1f}   len {len(master)} samples")


if __name__ == "__main__":
    build()
