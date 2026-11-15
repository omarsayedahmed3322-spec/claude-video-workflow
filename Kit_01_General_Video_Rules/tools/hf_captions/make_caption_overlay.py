"""Arabic word-by-word captions rendered by HyperFrames (Chrome) as a transparent ProRes 4444 .mov for AE / Premiere.
Chrome shapes Arabic natively (joined letters, RTL, kashida), so none of the AE Arabic workarounds are needed.

Input: captions.json in the CLF format  [{"t": "chunk text", "w": [word start s, ...], "in": s, "out": s}, ...]
       (make one from Whisper with whisper_to_captions.py, or by hand).
usage: python make_caption_overlay.py captions.json out.mov [--from 0 --to 8] [--font C:/.../Cairo-Black.ttf]
       [--size 76 --y 1330 --maxw 820 --color #FFFFFF --hl #FFD400 --fps 24 --w 1080 --h 1920] [--draft]
The overlay starts at --from: place it in AE at that time (layer In = from). Output frame 0 == reel time --from.
"""
import argparse, html, json, os, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # HF prints symbols the Windows console codepage can't

ap = argparse.ArgumentParser()
ap.add_argument("captions"); ap.add_argument("out")
ap.add_argument("--from", dest="t0", type=float, default=0.0)
ap.add_argument("--to", dest="t1", type=float, default=-1.0)
ap.add_argument("--font", default=os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts\Cairo-Black.ttf"))
ap.add_argument("--size", type=int, default=76)
ap.add_argument("--y", type=int, default=1330, help="vertical centre of the caption block (px)")
ap.add_argument("--maxw", type=int, default=820)
ap.add_argument("--color", default="#FFFFFF")
ap.add_argument("--hl", default="#FFD400", help="colour of the word being spoken")
ap.add_argument("--fps", type=int, default=24)
ap.add_argument("--w", type=int, default=1080); ap.add_argument("--h", type=int, default=1920)
ap.add_argument("--draft", action="store_true", help="fast low-quality render for timing checks")
ap.add_argument("--keep", action="store_true", help="keep the generated HyperFrames project (prints its path)")
a = ap.parse_args()

caps = json.load(open(a.captions, encoding="utf-8"))
t1 = a.t1 if a.t1 > 0 else max(c["out"] for c in caps)
caps = [c for c in caps if c["out"] > a.t0 and c["in"] < t1]
if not caps: sys.exit("no captions between %.2f and %.2f" % (a.t0, t1))
dur = round(t1 - a.t0, 3)

work = tempfile.mkdtemp(prefix="hf_caps_")          # ASCII temp path: the HF CLI never sees Arabic folder names
os.makedirs(os.path.join(work, "fonts"))
shutil.copy(a.font, os.path.join(work, "fonts", "cap" + os.path.splitext(a.font)[1]))
font_url = "fonts/cap" + os.path.splitext(a.font)[1]

clips, tweens = [], []
for i, c in enumerate(caps):
    s = max(c["in"], a.t0) - a.t0
    e = min(c["out"], t1) - a.t0
    words = c["t"].split(" ")
    ws = (c["w"] + [c["out"]] * len(words))[:len(words)]
    spans = "".join('<span class="w" id="w%d_%d">%s</span>' % (i, k, html.escape(w)) for k, w in enumerate(words))
    clips.append('<div class="clip cap" id="c%d" data-start="%.3f" data-duration="%.3f" data-track-index="1">'
                 '<div class="line" id="l%d">%s</div></div>' % (i, s, e - s, i, spans))
    for k in range(len(words)):
        wt = max(ws[k] - a.t0, s)
        nxt = (ws[k + 1] - a.t0) if k + 1 < len(words) else e
        tweens.append('tl.fromTo("#w%d_%d", {opacity: 0, y: 22, scale: 0.92}, {opacity: 1, y: 0, scale: 1, duration: 0.16, ease: "power3.out"}, %.3f);' % (i, k, wt))
        tweens.append('tl.fromTo("#w%d_%d", {color: "%s"}, {color: "%s", duration: 0.05, immediateRender: false}, %.3f);' % (i, k, a.color, a.hl, wt))
        tweens.append('tl.to("#w%d_%d", {color: "%s", duration: 0.08}, %.3f);' % (i, k, a.color, max(wt + 0.06, nxt - 0.02)))
    tweens.append('tl.to("#l%d", {opacity: 0, duration: 0.06}, %.3f);' % (i, max(s, e - 0.07)))

page = """<!doctype html>
<html lang="ar" dir="rtl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=%(w)d, height=%(h)d" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      @font-face { font-family: "CapFont"; src: url("%(font)s"); }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: %(w)dpx; height: %(h)dpx; overflow: hidden; background: transparent; }
      #root { position: relative; width: 100%%; height: 100%%; background: transparent; }
      .cap { position: absolute; left: 0; right: 0; top: %(top)dpx; display: flex; justify-content: center; }
      .line { width: %(maxw)dpx; display: flex; flex-wrap: wrap; justify-content: center; direction: rtl;
              gap: 0 0.28em; font-family: "CapFont"; font-size: %(size)dpx; line-height: 1.35; color: %(color)s;
              text-shadow: 0 4px 14px rgba(0,0,0,0.45); }
      .w { display: inline-block; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="%(dur).3f" data-width="%(w)d" data-height="%(h)d" data-fps="%(fps)d">
      %(clips)s
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
      %(tweens)s
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
""" % dict(w=a.w, h=a.h, font=font_url, top=a.y - int(a.size * 0.7), maxw=a.maxw, size=a.size, color=a.color,
           dur=dur, fps=a.fps, clips="\n      ".join(clips), tweens="\n      ".join(tweens))
open(os.path.join(work, "index.html"), "w", encoding="utf-8").write(page)
json.dump({"name": "caption-overlay"}, open(os.path.join(work, "hyperframes.json"), "w"))

def run(cmd):
    # HF prints ~100 progress lines per render; keep the chat short: last 3 lines on success, last 40 on failure
    print("$", " ".join(cmd)); sys.stdout.flush()
    r = subprocess.run(cmd, cwd=work, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.strip() and not l.startswith(("@hf-progress", "[INFO]"))]
    print("\n".join(lines[-40:] if r.returncode else lines[-3:]))
    if r.returncode: sys.exit("FAILED: %s (project kept in %s)" % (cmd[1], work))

hf = "hyperframes"
run([hf, "lint"])
tmp_out = os.path.join(work, "overlay.mov")
run([hf, "render", "--format", "mov", "--fps", str(a.fps), "--quality", "draft" if a.draft else "delivery", "--output", tmp_out])
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
shutil.copy(tmp_out, a.out)
probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=codec_name,pix_fmt,width,height,r_frame_rate:format=duration", "-of", "compact", a.out],
                       capture_output=True, text=True).stdout.strip()
print(probe)
if "yuva" not in probe and "rgba" not in probe: print("WARNING: no alpha channel in the output")
if a.keep: print("project:", work)
else: shutil.rmtree(work, ignore_errors=True)
print("OK ->", a.out, "| place at reel time %.3fs" % a.t0)
