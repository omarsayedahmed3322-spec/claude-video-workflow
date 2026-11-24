"""One command for the eyes-and-ears pass on a render: local QC -> Gemini -> a small sheet for Claude to verify.

  python -I review_reel.py reel.mp4 --type mg [--class A] [--final] [--start 12 --end 18] [--context ctx.txt]

1. <video>.qc.json (made by qc_reel.py; run here if missing). «سقط» stops everything: exit 2, nothing is sent.
2. free_llm.py reviews the reel: the paid Gemini key if it is set (real video + sound), else agy with JPEG sheets.
   fps / frame resolution / thinking come from the reel type; thinking is high only with --final on class A / A+.
3. Writes <video>.review.md and <video>.verify_sheet.jpg (the frames at the times PART 3 names, 8 at most), and
   prints a 5-line summary. Claude looks at that one sheet, not at the whole reel.
"""
import argparse, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import free_llm

PROMPT = os.path.join(HERE, "..", "skills", "free-llm-delegate", "references", "review_prompt.md")
# type: (fps, frame resolution). Slow talking shots need sharp captions, fast motion graphics need more frames.
PRESETS = {"talking": (4, "high"), "ugc": (4, "high"), "ai-film": (5, "medium"), "montage": (5, "medium"), "mg": (10, "medium")}
SHEETS_FPS_CAP = 5   # on agy sheets 10 fps of a 31 s reel is 26 images: too slow, and agy has no per-frame price to save


def measured_block(qc):
    lines = ["[MEASURED BY FFMPEG - TRUE, DO NOT GUESS OR CONTRADICT]",
             "- Length: %.3f s, %s fps, %sx%s." % (qc.get("duration") or 0, qc.get("fps"), *(qc.get("size") or ["?", "?"]))]
    cuts = [c for c in (qc.get("cuts") or []) if isinstance(c, (int, float))]
    if cuts:
        lines.append("- Cuts measured at (s): " + ", ".join("%.2f" % c for c in cuts) + ".")
    if qc.get("lufs") is not None:
        lines.append("- Loudness %s LUFS, true peak %s dBTP." % (qc.get("lufs"), qc.get("true_peak")))
    for r in qc.get("checks") or []:
        if r.get("status") != "نجح" and r.get("group") != "للعين":
            lines.append("- Local check «%s»: %s (%s)." % (r.get("check"), r.get("status"), r.get("detail")))
    return "\n".join(lines) + "\n"


def times_in(line):
    out = []
    for m in re.finditer(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2}(?:\.\d+)?)", line):
        h, mi, s = m.group(1), m.group(2), m.group(3)
        out.append((int(h) * 3600 if h else 0) + int(mi) * 60 + float(s))
    return out


def verify_sheet(video, review, out_jpg, dur):
    part3 = review.split("PART 3", 1)[1] if "PART 3" in review else ""
    picks = []
    for line in part3.splitlines():
        m = re.match(r"\s*\**(\d{1,2})[.)]", line)
        ts = times_in(line)
        if m and ts:
            picks.append((int(m.group(1)), min(max(ts[0], 0.0), max(dur - 0.05, 0.0))))
    picks = picks[:8]
    if not picks:
        return 0
    font = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arialbd.ttf")
    fontarg = ("fontfile='%s':" % font.replace("\\", "/").replace(":", "\\:")) if os.path.exists(font) else ""
    with tempfile.TemporaryDirectory() as tmp:
        cells = []
        for i, (n, t) in enumerate(picks):
            cell = os.path.join(tmp, "c%d.png" % i)
            vf = ("scale=540:-2:flags=lanczos,pad=iw:ih+44:0:44:black,drawtext=" + fontarg
                  + "text='#%d  %.2f s':fontsize=30:fontcolor=yellow:x=8:y=7" % (n, t))
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1", "-vf", vf, cell])
            if os.path.exists(cell):
                cells.append(cell)
        if not cells:
            return 0
        cols = min(4, len(cells))
        args = ["ffmpeg", "-nostdin", "-v", "error", "-y"]
        for c in cells:
            args += ["-i", c]
        if len(cells) == 1:
            args += ["-q:v", "3", out_jpg]
        else:
            layout = "|".join("%s_%s" % ("+".join(["w0"] * (i % cols)) or "0", "+".join(["h0"] * (i // cols)) or "0") for i in range(len(cells)))
            args += ["-filter_complex", "xstack=inputs=%d:layout=%s:fill=black" % (len(cells), layout), "-q:v", "3", out_jpg]
        subprocess.run(args)
    return len(cells) if os.path.exists(out_jpg) else 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video")
    ap.add_argument("--type", choices=sorted(PRESETS), required=True)
    ap.add_argument("--class", dest="cls", choices=["A+", "A", "B", "C", "D"], default="B")
    ap.add_argument("--final", action="store_true", help="the version that will be delivered (thinking high on class A / A+)")
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--context", help="text file: expected on-screen text, real logos or signs, the client's must-haves")
    ap.add_argument("--sheets", action="store_true", help="force the agy JPEG-sheets route even when the paid key is set")
    ap.add_argument("--no-send", action="store_true", help="stop after QC and print the prompt (dry run, no model is called)")
    a = ap.parse_args()
    video = os.path.abspath(a.video)
    if not os.path.exists(video):
        sys.exit("not found: " + video)
    stem = os.path.splitext(video)[0]

    qcp = stem + ".qc.json"
    if not os.path.exists(qcp):
        subprocess.run([sys.executable, "-I", os.path.join(HERE, "qc_reel.py"), video, "--type", a.type],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    qc = {}
    if os.path.exists(qcp):
        with open(qcp, encoding="utf-8") as f:
            qc = json.load(f)
    if qc.get("verdict") == "سقط":
        bad = ["%s: %s" % (r.get("check"), r.get("detail")) for r in qc.get("checks", []) if r.get("status") == "سقط"]
        print("QC سقط، مفيش حاجة اتبعتت: " + " | ".join(bad))
        sys.exit(2)

    env = free_llm.load_env()
    paid = bool(env.get("GEMINI_PAID_API_KEY")) and not a.sheets
    fps, res = PRESETS[a.type]
    thinking = "high" if (a.final and a.cls in ("A", "A+")) else "medium"
    if paid:
        how = ("The video is the finished reel, sampled at %g frames per second, each frame with its own timestamp, and "
               "it carries its own soundtrack. Report every time from the frame timestamps." % fps)
        if a.start is not None or a.end is not None:
            how += " You are given only the part from %s s to %s s; report on that part only." % (a.start or 0, a.end if a.end is not None else "the end")
    else:
        fps = min(fps, SHEETS_FPS_CAP)
        how = "(How you see the reel is described above by the tool.)"
    with open(PROMPT, encoding="utf-8") as f:
        prompt = f.read()
    ctx = ""
    if a.context:
        with open(a.context, encoding="utf-8") as f:
            ctx = "CONTEXT FOR THIS REEL (do not report these as problems):\n" + f.read().strip() + "\n"
    prompt = prompt.replace("{HOW_YOU_SEE}", how).replace("{MEASURED}", measured_block(qc) if qc else "").replace("{CONTEXT}", ctx)
    if a.no_send:
        print(prompt)
        print("--- route: %s | fps=%g res=%s thinking=%s" % ("gemini paid" if paid else "agy jpeg sheets", fps, res, thinking))
        return

    out_md = stem + ".review.md"
    with tempfile.TemporaryDirectory() as tmp:
        pf = os.path.join(tmp, "prompt.txt")
        with open(pf, "w", encoding="utf-8") as f:
            f.write(prompt)
        cmd = [sys.executable, "-I", os.path.join(HERE, "free_llm.py"), "ask", "--prompt-file", pf, "--file", video,
               "--out", out_md, "--fps", "%g" % fps]
        if paid:
            cmd += ["--thinking", thinking, "--media-res", res]
            if a.start is not None:
                cmd += ["--start", "%g" % a.start]
            if a.end is not None:
                cmd += ["--end", "%g" % a.end]
        else:
            cmd += ["--jpeg-sheets"]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = [l for l in (r.stderr or "").splitlines() if l.strip()]
    if r.returncode != 0 or not os.path.exists(out_md):
        print("المراجعة فشلت: " + (tail[-1] if tail else "من غير رسالة"))
        sys.exit(1)
    with open(out_md, encoding="utf-8") as f:
        review = f.read()
    n_obs = len(re.findall(r"(?m)^\s*\**\d{1,2}[.)]", review.split("PART 3", 1)[1])) if "PART 3" in review else 0
    sheet = stem + ".verify_sheet.jpg"
    n = verify_sheet(video, review, sheet, float(qc.get("duration") or 9e9))
    cost = next((l for l in reversed(tail) if "[gemini/" in l), "")
    print("QC: %s | الطريق: %s | fps=%g thinking=%s" % (qc.get("verdict", "متعملش"), (r.stdout or "").split(" -> ")[0].strip() or "?", fps, thinking if paid else "agy"))
    print("التقرير: " + out_md)
    print("ملاحظات PART 3: %d" % n_obs)
    print("شيت التحقق: " + (("%s (%d فريم)" % (sheet, n)) if n else "متعملش (مفيش ملاحظات بوقت)"))
    if cost:
        print(cost.strip())


if __name__ == "__main__":
    main()
