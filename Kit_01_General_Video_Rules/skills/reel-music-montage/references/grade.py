r"""Colour for real footage (skill reel-music-montage): per-shot correction (white balance + exposure/levels, measured) + one
shared look, baked into one .cube per shot. Copied on 2026-11-13 from CLB R1 (AG2/CLB/Reel-01/scripts/grade.py, 2026-11-07).
- The CORRECTION block is the general method (numbers measured on R1's 8-bit Rec.709 h264, not log -> gentle moves only).
- The LOOK block is CLB's look («quiet luxury»: charcoal / ivory / gold, editorial, low saturation) and belongs to CLB only.
  Another client: ask Omar what look he wants (Omar, 2026-11-13); set LOOK = None for correction only.
The logic is the R1 logic unchanged (only the constants moved up here).
Usage: python -I grade.py [--out DIR] sheet [shot#...]  -> DIR\before_after.jpg + zoom_pairs.jpg + params.json
       python -I grade.py [--out DIR] cube <shot#>...   -> DIR\luts\shotNN.cube
Shot numbers = indexes in rough_map.json (match_rough.py). The EDL script imports this file to render graded intermediates."""
import os, sys, json, subprocess, numpy as np
from PIL import Image, ImageDraw

# ============================ SETTINGS (CLB R1 values) ============================
FOOT = r"D:\Montage-02\Clients\AG2\AG2\Dropbox\4-11-2026"
EXT = ".MP4"
OUT = r"D:\Montage-02\Clients\AG2\CLB\Reel-01\work\grade"
MAP = r"D:\Montage-02\Clients\AG2\CLB\Reel-01\work\match\rough_map.json"
SW, SH = 270, 480                       # analysis frame size (3 frames per shot: start / mid / end of the rough-cut shot)
NIGHT = {"C0402", "C0404", "C0405"}     # night shots: target mid 0.33 and never darkened
# --- CORRECTION (general, measured per shot) ---
NEUTRAL_SAT, NEUTRAL_L = 0.14, (0.30, 0.93)   # pixels that count as neutral surfaces
NEUTRAL_MIN_PX = 500
WB_CLIP = (0.90, 1.10)
WB_AMOUNT = 0.6                         # 60 % of the way to grey: the room keeps its warmth (R1 v7 read cold)
PCT = [0.7, 50, 99.3]                   # black / mid / white percentiles
BP_MAX, BP_PULL = 0.06, 0.85            # black point: only a small pull
WP_MIN = 0.80                           # stretch whites to 1 (max 25 %)
MID_TARGET, MID_TARGET_NIGHT = 0.44, 0.33
GAMMA_MIN, GAMMA_MIN_NIGHT, GAMMA_MAX = 0.72, 1.0, 1.30
# --- LOOK (CLB only) ---
LOOK = dict(
    sh_end=0.35, hi_start=0.55, hi_span=0.45,                       # tonal split weights
    tint_sh=[-0.010, 0.000, 0.012], tint_mid=[0.020, 0.007, -0.018], tint_hi=[0.024, 0.011, -0.022],
    sat=0.86,                                                       # saturation base, then by hue band (centre, width, add)
    sat_bands=[(35, 30, 0.08),        # orange/gold/wood/skin: 0.94
               (215, 45, -0.08),      # blues: 0.78
               (320, 40, -0.14), (0, 20, -0.06),   # pinks/magenta ties: 0.72
               (110, 45, -0.14)],     # greens: 0.72
    toe=0.032, shoulder=0.955, contrast=1.06, roll_at=0.75, roll_k=2.2, knee=0.18, knee_pow=1.04, norm=0.97)
CUBE_TITLE, CUBE_N = "CLB R1", 33
SHEET_COLS, SHEET_TILE = 8, (135, 240)
SHEET_PICK = [5, 10, 14, 21, 26, 12]    # shots shown big on zoom_pairs.jpg
# =====================================================================================
if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[1] == "--out":
    OUT = sys.argv[2]; del sys.argv[1:3]
os.makedirs(os.path.join(OUT, "luts"), exist_ok=True)
SHOTS = json.load(open(MAP))

def grab(clip, t, w=SW, h=SH):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", "%.2f" % t, "-i", os.path.join(FOOT, clip + EXT),
                          "-frames:v", "1", "-vf", "scale=%d:%d" % (w, h), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32) / 255

def lum(x): return x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722

# ---------- per-shot correction (measured) ----------
def analyse(frames, night=False):
    x = np.concatenate([f.reshape(-1, 3) for f in frames])
    L = lum(x); mx = x.max(1); mn = x.min(1); sat = (mx - mn) / (mx + 1e-4)
    neutral = (sat < NEUTRAL_SAT) & (L > NEUTRAL_L[0]) & (L < NEUTRAL_L[1])
    gains = np.ones(3)
    if neutral.sum() > NEUTRAL_MIN_PX:
        m = x[neutral].mean(0); gains = m[1] / m           # neutral surfaces -> grey
        gains = np.clip(gains, WB_CLIP[0], WB_CLIP[1])
        gains = 1 + (gains - 1) * WB_AMOUNT
    xc = np.clip(x * gains, 0, 1); Lc = lum(xc)
    p1, p50, p99 = np.percentile(Lc, PCT)
    bp = min(p1, BP_MAX) * BP_PULL
    wp = max(min(p99, 1.0), WP_MIN)
    mid = (p50 - bp) / (wp - bp)
    target = MID_TARGET_NIGHT if night else MID_TARGET
    gamma = np.clip(np.log(target) / np.log(max(mid, 1e-3)), GAMMA_MIN_NIGHT if night else GAMMA_MIN, GAMMA_MAX)   # mid-grey -> target (never darken night)
    return dict(gains=[round(float(g), 4) for g in gains], bp=round(float(bp), 4), wp=round(float(wp), 4),
                gamma=round(float(gamma), 3), med_before=round(float(np.median(L)), 3))

def correct(x, p):
    x = np.clip(x * np.array(p["gains"]), 0, 1)
    x = np.clip((x - p["bp"]) / (p["wp"] - p["bp"]), 0, 1)
    return x ** (1 / p["gamma"])

# ---------- the shared look (LOOK) ----------
def curve(x):                    # soft filmic S: deep but not crushed blacks, rolled-off highlights
    c = LOOK; toe, sh = c["toe"], c["shoulder"]
    s = 0.5 + (x - 0.5) * c["contrast"]                       # a bit more contrast through the mids
    s = np.where(s > c["roll_at"], c["roll_at"] + (s - c["roll_at"]) / (1 + (s - c["roll_at"]) * c["roll_k"]), s)   # roll the highlights off
    s = np.where(s < c["knee"], c["knee"] * (np.clip(s, 0, None) / c["knee"]) ** c["knee_pow"], s)  # deeper toe
    s = np.clip(s / c["norm"], 0, 1)
    return toe + (sh - toe) * s

def grade(x):
    if LOOK is None: return x
    c = LOOK
    L = lum(x)[..., None]
    # tonal split: shadows neutral-cool, mids a touch warm, highlights warm ivory
    w_sh = np.clip(1 - L / c["sh_end"], 0, 1); w_hi = np.clip((L - c["hi_start"]) / c["hi_span"], 0, 1); w_mid = 1 - w_sh - w_hi
    tint = (w_sh * np.array(c["tint_sh"]) + w_mid * np.array(c["tint_mid"])
            + w_hi * np.array(c["tint_hi"]))
    x = np.clip(x + tint, 0, 1)
    # saturation by hue band
    mx = x.max(-1, keepdims=True); mn = x.min(-1, keepdims=True); d = mx - mn + 1e-6
    r, g, b = x[..., 0:1], x[..., 1:2], x[..., 2:3]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    def band(cc, wdt): return np.clip(1 - np.abs(((h - cc + 180) % 360) - 180) / wdt, 0, 1)
    satk = c["sat"]
    for cc, wdt, add in c["sat_bands"]:
        satk = satk + add * band(cc, wdt)
    Ly = lum(x)[..., None]
    x = Ly + (x - Ly) * satk
    x = np.clip(x, 0, 1)
    out = np.stack([curve(x[..., i]) for i in range(3)], -1)
    return np.clip(out, 0, 1)

def full(x, p): return grade(correct(x, p))

def params(i):
    s = SHOTS[i]; fr = [grab(c, t) for c, t, _ in s["src"]]
    return analyse(fr, s["clip"] in NIGHT), fr

def write_cube(path, p, n=CUBE_N):
    g = np.linspace(0, 1, n); b, gg, r = np.meshgrid(g, g, g, indexing="ij")
    x = np.stack([r, gg, b], -1).reshape(-1, 3)
    y = full(x[None], p)[0]
    with open(path, "w") as f:
        f.write("TITLE \"%s\"\nLUT_3D_SIZE %d\n" % (CUBE_TITLE, n))
        for v in y: f.write("%.6f %.6f %.6f\n" % tuple(v))

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sheet":
        cols = SHEET_COLS; tw, th = SHEET_TILE
        o = Image.new("RGB", (cols * tw * 2 + cols * 6, ((len(SHOTS) + cols - 1) // cols) * (th + 4)), (30, 30, 30))
        dr = ImageDraw.Draw(o); allp = {}
        for i, s in enumerate(SHOTS):
            p, fr = params(i); allp[i] = dict(clip=s["clip"], **p)
            f = fr[1]; a = Image.fromarray((f * 255).astype(np.uint8)).resize((tw, th))
            bimg = Image.fromarray((full(f, p) * 255).astype(np.uint8)).resize((tw, th))
            x0 = (i % cols) * (2 * tw + 6); y0 = (i // cols) * (th + 4)
            o.paste(a, (x0, y0)); o.paste(bimg, (x0 + tw, y0))
            dr.rectangle([x0, y0, x0 + 64, y0 + 12], fill=(0, 0, 0)); dr.text((x0 + 2, y0), "%02d %s" % (i, s["clip"]), fill=(255, 255, 0))
        o.save(os.path.join(OUT, "before_after.jpg"), quality=85)
        pick = [int(a) for a in sys.argv[2:]] or SHEET_PICK
        z = Image.new("RGB", (len(pick) * 2 * SW // 1, SH))
        for k, i in enumerate(pick):
            p = allp[i]; f = params(i)[1][1]
            z.paste(Image.fromarray((f * 255).astype(np.uint8)), (k * 2 * SW, 0))
            z.paste(Image.fromarray((full(f, p) * 255).astype(np.uint8)), (k * 2 * SW + SW, 0))
        z.save(os.path.join(OUT, "zoom_pairs.jpg"), quality=88)
        json.dump(allp, open(os.path.join(OUT, "params.json"), "w"), indent=1); print(o.size)
    elif cmd == "cube":
        for a in sys.argv[2:]:
            i = int(a); p, _ = params(i); write_cube(os.path.join(OUT, "luts", "shot%02d.cube" % i), p); print("cube", i, p)
