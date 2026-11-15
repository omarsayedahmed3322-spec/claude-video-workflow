"""qc_reel.py - automatic QC of a rendered reel before it reaches Omar.

usage:
  python -I -X utf8 qc_reel.py <video.mp4> [--type talking|montage|mg|ai-film|ugc]
         [--edl edl.json|cuts.txt] [--expect-dur SECONDS] [--max-dur SECONDS] [--out-dir DIR]

Prints a table (نجح / تحذير / سقط), writes <video>.qc.json and <video>.qc_sheet.png
(one frame from the middle of every shot, with the safe zone drawn) next to the video,
or into --out-dir. Exit 1 if anything is «سقط».

Limits come from the kits (Kit_01 05 §6 loudness table, 01/00 safe zone). A check with
no approved number is only «تحذير», never «سقط» (plan phase 4, 2026-11-11):
  سقط  = no video, no audio, silent audio (max < -60 dB), not 9:16, longer than --max-dur,
         true peak above 0 dBTP (clipping).
  تحذير = everything else (loudness vs the table, dual mono, abrupt ending, black/frozen
         frames, shots under 3 frames, cuts off the EDL, look-alike shots).
--type -> row of the 05 §6 table:
  ai-film, mg -> recorded VO (master ≈ -14 LUFS, peak -1 dBFS; ±1 LU before warning)
  talking     -> seated talking head (no LUFS target; peak above -6 dBFS warns)
  ugc         -> client clip with its own sound (no master decision; peak above -6 warns)
  montage     -> music only (no decision: numbers are printed, no verdict)
  (none)      -> numbers printed, no verdict on loudness
"""
import argparse
import json
import math
import os
import re
import struct
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

FONT = "C\\:/Windows/Fonts/arial.ttf"   # drawtext needs an explicit fontfile on this PC
SAFE = (60, 250, 950, 1420)              # x0, y0, x1, y1 on 1080x1920
PASS, WARN, FAIL = "نجح", "تحذير", "سقط"


def run(cmd, binary=False):
    p = subprocess.run(cmd, capture_output=True)
    if binary:
        return p.stdout, p.stderr.decode("utf-8", "replace")
    return p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def ff(*args, binary=False):
    return run(["ffmpeg", "-nostdin", "-hide_banner", *args], binary=binary)


def probe(path):
    out, _ = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path])
    return json.loads(out or "{}")


def fnum(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


class Report:
    def __init__(self):
        self.rows = []

    def add(self, group, name, status, detail):
        self.rows.append({"group": group, "check": name, "status": status, "detail": detail})

    def worst(self):
        st = [r["status"] for r in self.rows]
        return FAIL if FAIL in st else WARN if WARN in st else PASS


def analyse_av(path, has_audio):
    """One pass: blackdetect + freezedetect + scdet on video, ebur128 + volumedetect on audio."""
    vf = "scale=270:-2,blackdetect=d=0.08:pix_th=0.10,freezedetect=n=-60dB:d=2,scdet=t=3"
    args = ["-loglevel", "info", "-i", path, "-vf", vf]
    if has_audio:
        args += ["-af", "ebur128=peak=true:framelog=quiet,volumedetect"]
    else:
        args += ["-an"]
    args += ["-f", "null", "-"]
    _, err = ff(*args)
    res = {"black": [], "freeze": [], "scd": []}
    for m in re.finditer(r"black_start:\s*([\d.]+)\s+black_end:\s*([\d.]+)", err):
        res["black"].append((float(m.group(1)), float(m.group(2))))
    fs = None
    for line in err.splitlines():
        m = re.search(r"freeze_start:\s*([\d.]+)", line)
        if m:
            fs = float(m.group(1))
        m = re.search(r"freeze_end:\s*([\d.]+)", line)
        if m and fs is not None:
            res["freeze"].append((fs, float(m.group(1))))
            fs = None
        m = re.search(r"lavfi\.scd\.score:\s*([\d.]+),\s*lavfi\.scd\.time:\s*([\d.]+)", line)
        if m:
            res["scd"].append((float(m.group(2)), float(m.group(1))))
    if fs is not None:
        res["freeze"].append((fs, None))
    m = re.search(r"Integrated loudness:\s*I:\s*(-?[\d.]+|-inf)\s*LUFS", err)
    res["lufs"] = fnum(m.group(1)) if m else None
    m = re.search(r"True peak:\s*Peak:\s*(-?[\d.]+|-inf)\s*dBFS", err)
    res["tp"] = fnum(m.group(1)) if m else None
    m = re.search(r"max_volume:\s*(-?[\d.]+|-inf)\s*dB", err)
    res["max_vol"] = fnum(m.group(1)) if m else None
    if res["max_vol"] is None and m and m.group(1) == "-inf":
        res["max_vol"] = -math.inf
    return res


def cuts_from_scores(scd, ftime):
    """Hard cut = one frame scoring >= 10. A short transition (blur, whip, dissolve) spreads the
    change over 2-4 frames of 3-9 each, so neighbouring frames are summed (YUGEN_R1: b-roll in/out
    at 35, 48.3, 62.6 s scored 4-6 per frame and a plain threshold of 10 missed them)."""
    cuts, cl = [], []
    for t, sc in sorted(scd) + [(1e9, 0.0)]:
        if cl and t - cl[-1][0] > 1.5 * ftime:
            if sum(x[1] for x in cl) >= 10:
                cuts.append(max(cl, key=lambda x: x[1])[0])
            cl = []
        cl.append((t, sc))
    return cuts


def lr_identical(path):
    _, err = ff("-i", path, "-vn", "-af", "pan=mono|c0=c0-c1,volumedetect", "-f", "null", "-")
    m = re.search(r"max_volume:\s*(-?[\d.]+|-inf)\s*dB", err)
    if not m:
        return None, None
    v = -math.inf if m.group(1) == "-inf" else float(m.group(1))
    return v <= -90, v


def tail_shape(path):
    """Last 0.3 s as mono float PCM: RMS of the final 20 ms vs the whole window."""
    raw, _ = ff("-sseof", "-0.3", "-i", path, "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "-", binary=True)
    n = len(raw) // 4
    if n < 2000:
        return None
    s = struct.unpack("<%df" % n, raw[: n * 4])

    def rms_db(x):
        if not x:
            return -math.inf
        r = math.sqrt(sum(v * v for v in x) / len(x))
        return 20 * math.log10(r) if r > 0 else -math.inf

    return {"window_db": rms_db(s), "last20ms_db": rms_db(s[-960:])}


def frame_raw(path, t, vf, w, h, pix="gray"):
    raw, _ = ff("-ss", "%.3f" % t, "-i", path, "-frames:v", "1", "-vf", vf + ",format=" + pix,
                "-f", "rawvideo", "-", binary=True)
    return raw if len(raw) >= w * h else None


def dhash(path, t):
    raw = frame_raw(path, t, "scale=9:8:flags=area", 9, 8)
    if not raw:
        return None
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (raw[y * 9 + x] > raw[y * 9 + x + 1])
    return bits


def make_sheet(path, shots, vw, out_png, tmp):
    k = 216 / vw if vw else 0.2
    x0, y0, x1, y1 = [round(v * (vw / 1080) * k) for v in SAFE]
    for i, (a, b) in enumerate(shots):
        mid = (a + b) / 2
        vf = ("scale=216:384,"
              "drawbox=x=%d:y=%d:w=%d:h=%d:color=yellow@0.8:t=1,"
              "drawtext=fontfile='%s':text='%d  %.2fs':x=6:y=366:fontsize=14:fontcolor=white:box=1:boxcolor=black@0.6"
              % (x0, y0, x1 - x0, y1 - y0, FONT, i + 1, a))
        ff("-y", "-ss", "%.3f" % mid, "-i", path, "-frames:v", "1", "-vf", vf,
           os.path.join(tmp, "s_%03d.png" % i))
    n = len(shots)
    cols = min(8, max(1, n))
    rows = math.ceil(n / cols)
    ff("-y", "-i", os.path.join(tmp, "s_%03d.png"), "-vf",
       "tile=%dx%d:padding=4:color=black" % (cols, rows), "-frames:v", "1", out_png)
    return os.path.exists(out_png)


def load_edl(p):
    txt = open(p, encoding="utf-8").read()
    try:
        d = json.loads(txt)
    except ValueError:
        return sorted({float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", txt)})
    if isinstance(d, dict) and "shots" in d:
        return sorted({float(s["t0"]) for s in d["shots"] if float(s["t0"]) > 0})
    if isinstance(d, list):
        return sorted({float(x["t0"] if isinstance(x, dict) else x) for x in d})
    raise SystemExit("EDL not understood: give {'shots':[{'t0':..}]} or a list of cut times")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--type", choices=["talking", "montage", "mg", "ai-film", "ugc"])
    ap.add_argument("--edl")
    ap.add_argument("--expect-dur", type=float)
    ap.add_argument("--max-dur", type=float)
    ap.add_argument("--out-dir")
    a = ap.parse_args()
    vid = os.path.abspath(a.video)
    if not os.path.exists(vid):
        raise SystemExit("not found: " + vid)
    base = os.path.splitext(os.path.basename(vid))[0]
    out_dir = a.out_dir or os.path.dirname(vid)
    os.makedirs(out_dir, exist_ok=True)
    R = Report()

    info = probe(vid)
    vs = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    au = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    dur = fnum(info.get("format", {}).get("duration")) or 0.0

    # ---- file
    R.add("ملف", "video stream", PASS if vs else FAIL, "%d" % len(vs))
    R.add("ملف", "audio stream", PASS if au else FAIL, "%d" % len(au) if au else "مفيش صوت")
    fps = 0.0
    vw = vh = 0
    if vs:
        v = vs[0]
        vw, vh = int(v.get("width", 0)), int(v.get("height", 0))
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            rot = int(sd.get("rotation", 0) or 0)
        if abs(rot) in (90, 270):
            vw, vh = vh, vw
        if (vw, vh) == (1080, 1920):
            R.add("ملف", "size", PASS, "1080x1920")
        elif vw * 16 == vh * 9:
            R.add("ملف", "size", WARN, "%dx%d (9:16 بس مش 1080x1920، بريفيو؟)" % (vw, vh))
        else:
            R.add("ملف", "size", FAIL, "%dx%d مش 9:16" % (vw, vh))
        num, _, den = (v.get("avg_frame_rate") or "0/1").partition("/")
        fps = float(num) / float(den or 1) if float(den or 1) else 0.0
        R.add("ملف", "fps", PASS, "%.3f" % fps)
    ftime = 1.0 / fps if fps else 0.04
    if a.expect_dur is not None:
        d = abs(dur - a.expect_dur)
        R.add("ملف", "duration vs expected", PASS if d <= ftime + 1e-3 else WARN,
              "%.3fs (المتوقع %.3fs، الفرق %.3fs)" % (dur, a.expect_dur, d))
    else:
        R.add("ملف", "duration", PASS, "%.3fs" % dur)
    if a.max_dur is not None:
        R.add("ملف", "max duration", PASS if dur <= a.max_dur + ftime else FAIL,
              "%.3fs (الحد %.1fs)" % (dur, a.max_dur))

    av = analyse_av(vid, bool(au)) if vs else {"black": [], "freeze": [], "scd": [], "lufs": None, "tp": None, "max_vol": None}

    # ---- audio
    if au:
        mv, lufs, tp = av["max_vol"], av["lufs"], av["tp"]
        silent = mv is None or mv < -60
        if silent:
            R.add("صوت", "not silent", FAIL, "max %s dB (تحت -60 = ساكت)" % mv)
        else:
            R.add("صوت", "not silent", PASS, "max %.1f dB" % mv)
        if tp is not None and tp > 0.0:
            R.add("صوت", "clipping (true peak)", FAIL, "%.1f dBTP فوق 0" % tp)
        typ = "silent" if silent else a.type
        detail = "I %s LUFS · TP %s dBTP · max %s dB" % (lufs, tp, mv)
        if typ in ("ai-film", "mg"):
            ok_i = lufs is not None and abs(lufs - (-14.0)) <= 1.0
            R.add("صوت", "loudness (VO row)", PASS if ok_i else WARN, detail + " · المعتمد ≈ -14 LUFS")
            if tp is not None and tp <= 0.0:
                R.add("صوت", "peak (VO row)", PASS if tp <= -1.0 else WARN, "%.1f dBTP · المعتمد -1" % tp)
        elif typ in ("talking", "ugc"):
            row = "talking row" if typ == "talking" else "ugc row"
            ok = mv is not None and mv <= -6.0
            R.add("صوت", "speech peak (%s)" % row, PASS if ok else WARN,
                  detail + " · الكلام متعلّاش فوق -6 dBFS")
        elif not silent:
            R.add("صوت", "loudness", PASS, detail + " · مفيش حكم (%s)" % (typ or "من غير نوع"))
        if silent:
            pass
        elif int(au[0].get("channels", 0)) == 2:
            same, dv = lr_identical(vid)
            if same is None:
                R.add("صوت", "L/R", WARN, "ماتقاسش")
            elif same:
                R.add("صوت", "L/R", WARN, "يمين = شمال بالظبط (مونو متكرر، بيعلّي +3 LU)")
            else:
                R.add("صوت", "L/R", PASS, "مختلفين (فرق max %.1f dB)" % dv)
        elif au:
            R.add("صوت", "L/R", WARN, "%s قناة" % au[0].get("channels"))
        ts = None if silent else tail_shape(vid)
        if silent:
            pass
        elif ts is None:
            R.add("صوت", "ending", WARN, "ماتقاسش")
        elif ts["last20ms_db"] > -40:
            R.add("صوت", "ending", WARN, "آخر 20ms على %.1f dB: الصوت مقطوع فجأة مش فيد" % ts["last20ms_db"])
        else:
            R.add("صوت", "ending", PASS, "آخر 20ms %.1f dB (آخر 0.3s %.1f dB)" % (ts["last20ms_db"], ts["window_db"]))

    # ---- picture
    shots = []
    if vs:
        if av["black"]:
            R.add("صورة", "black frames", WARN, ", ".join("%.2f–%.2f" % b for b in av["black"]))
        else:
            R.add("صورة", "black frames", PASS, "مفيش")
        if av["freeze"]:
            R.add("صورة", "frozen ≥2s", WARN, ", ".join("%.2f–%s" % (f[0], "%.2f" % f[1] if f[1] else "end")
                                                        for f in av["freeze"]) + " (ممكن مقصود)")
        else:
            R.add("صورة", "frozen ≥2s", PASS, "مفيش")
        cuts = sorted(c for c in cuts_from_scores(av["scd"], ftime) if ftime < c < dur - ftime)
        av["cuts"] = cuts
        edges = [0.0] + cuts + [dur]
        shots = [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]
        short = [(s, e) for s, e in shots if (e - s) < 3 * ftime - 1e-3]
        R.add("صورة", "cuts", PASS, "%d قطع، %d لقطة: %s" % (len(cuts), len(shots), " ".join("%.2f" % c for c in cuts)))
        R.add("صورة", "shots < 3 frames", WARN if short else PASS,
              ", ".join("%.2f (%d فريم)" % (s, round((e - s) / ftime)) for s, e in short) or "مفيش")
        if a.edl:
            exp = load_edl(a.edl)
            bad = []
            for t in exp:
                near = min(cuts, key=lambda c: abs(c - t)) if cuts else None
                off = round((near - t) / ftime) if near is not None else None
                if off is None or abs(off) > 1:
                    bad.append("%.2f→%s" % (t, "مش موجود" if off is None or abs(off) > 12 else "%+d فريم" % off))
            R.add("صورة", "cuts vs EDL", WARN if bad else PASS,
                  ("%d من %d في مكانهم ±1 فريم" % (len(exp) - len(bad), len(exp))) + ("؛ " + ", ".join(bad) if bad else ""))
        hashes = [dhash(vid, (s + e) / 2) for s, e in shots]
        sim = []
        for i in range(len(shots)):
            for j in range(i + 2, len(shots)):   # i+1 is the neighbour across the cut
                if hashes[i] is not None and hashes[j] is not None and bin(hashes[i] ^ hashes[j]).count("1") <= 5:
                    sim.append("%d≈%d" % (i + 1, j + 1))
        R.add("صورة", "look-alike shots", WARN if sim else PASS,
              (", ".join(sim) + " (اتفرّج عليهم في الشيت)") if sim else "مفيش")

    sheet = os.path.join(out_dir, base + ".qc_sheet.png")
    if shots:
        with tempfile.TemporaryDirectory() as tmp:
            ok = make_sheet(vid, shots, vw, sheet, tmp)
        R.add("للعين", "contact sheet + safe zone", PASS if ok else WARN,
              sheet if ok else "الشيت مااتعملش")

    # ---- output
    verdict = R.worst()
    w = max(len(r["check"]) for r in R.rows)
    print("QC  %s  (%s)" % (os.path.basename(vid), a.type or "من غير نوع"))
    for r in R.rows:
        print("  %-6s %-5s %-*s  %s" % (r["status"], r["group"], w, r["check"], r["detail"]))
    print("النتيجة: " + verdict)
    out = {"video": vid, "type": a.type, "verdict": verdict, "duration": dur, "fps": fps,
           "size": [vw, vh], "lufs": av.get("lufs"), "true_peak": av.get("tp"), "max_volume": av.get("max_vol"),
           "cuts": av.get("cuts"), "checks": R.rows}
    jp = os.path.join(out_dir, base + ".qc.json")
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print("json: " + jp)
    sys.exit(1 if verdict == FAIL else 0)


if __name__ == "__main__":
    main()
