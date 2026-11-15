r"""footage_index.py - index a shoot folder once, so no session re-analyses the same clips (plan phase 8-c, 2026-11-14).

usage:
  python -I -X utf8 footage_index.py <shoot folder> [--out DIR] [--recursive] [--force] [--workers N]

Writes <out>\footage_index.json and <out>\footage_index_sheet_NN.png (3 frames per clip at 10/50/90 %,
200 px wide keeping the aspect, 5 clips per row, 35 clips per image: the 01 §C contact-sheet rule).
Default out: <shoot folder>\_index\ . A shoot folder inside Dropbox needs --out (Omar, 2026-11-14:
the index of a Dropbox shoot goes to the reel's work\footage_index\, so nothing new syncs to the client).

Per clip: duration, size AFTER the rotation flag (Sony FX30 portrait = 3840x2160 + rotation 90 -> 2160x3840),
rotation, fps, video codec, audio yes/no (from the audio stream's codec_name), creation time, mean luma and
% burnt pixels, camera motion (pan/tilt px/s at 1080 width, zoom %/s) in 3 windows around 10/50/90 %,
shake (a number only, never a flag: on the CLB 4-11 shoot the clips used in the approved R1 measured
1.1-32.5 px, as high as the unused ones, so it does not tell bad shake from a wanted handheld move), the 3
frame times, "flags" (no audio / short / dark / burnt: measured, every one is only a warning) and "notes"
(empty, for Omar / the eye review). Re-running keeps every "notes" and reuses a clip's numbers while its size and mtime are
unchanged (--force re-measures everything).

Motion: the optical-flow method and the static limits of reel-music-montage/references/motion_rough.py
(CLB R1), with one change: the pan/tilt is the move of the frame centre, not the affine tx/ty (those are
about the top-left corner, so a push-in also read as pan-right + tilt-down). Content moving left = the camera
pans right.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ============================ SETTINGS ============================
VIDEO_EXT = (".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".m4v", ".avi", ".mkv")
LONG_SIDE = 480                 # analysis frame: long side in px (portrait 270x480, as motion_rough.py)
WIN = 1.0                       # seconds analysed around each of 10/50/90 %
FLOW_FPS = 10                   # frames per second analysed in a window
POINTS = (0.10, 0.50, 0.90)     # frame positions (01 §C: 10/50/90 % of the duration)
ZOOM_MIN, PAN_MIN = 1.5, 25     # %/s and px/s (at 1080 width) below which a move reads static (motion_rough.py)
BURNT_LUMA = 250                # luma (0-255, full range) counted as burnt
THUMB_W = 200                   # contact-sheet frame width (01 §C)
CLIPS_PER_ROW, ROWS_PER_SHEET = 5, 7
FONT = r"C:\Windows\Fonts\arial.ttf"
# Flag limits: NOT approved numbers (no kit rule yet) -> every flag is a warning that prints the measured value.
FLAG_DARK = 20.0                # mean luma below this % (0-100) -> "dark"
FLAG_BURNT = 5.0                # burnt pixels above this % -> "burnt"
FLAG_SHORT = 2.0                # clips shorter than this (s) -> "short"
VERSION = 1
# ==================================================================


def run(cmd):
    return subprocess.run(cmd, capture_output=True)


def probe(path):
    p = run(["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height,avg_frame_rate,channels:stream_side_data=rotation"
             ":format=duration:format_tags=creation_time", "-of", "json", path])
    return json.loads(p.stdout.decode("utf-8", "replace") or "{}")


def fps_of(s):
    num, _, den = (s or "0/1").partition("/")
    try:
        return float(num) / float(den or 1) if float(den or 1) else 0.0
    except ValueError:
        return 0.0


def decode_window(path, t0, dur, w, h):
    """rgb24 frames at FLOW_FPS from t0 for dur seconds, scaled to w x h (ffmpeg applies the rotation flag)."""
    p = run(["ffmpeg", "-nostdin", "-v", "error", "-ss", "%.3f" % t0, "-t", "%.3f" % dur, "-i", path,
             "-an", "-vf", "fps=%d,scale=%d:%d" % (FLOW_FPS, w, h), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    n = len(p.stdout) // (w * h * 3)
    return np.frombuffer(p.stdout[: n * w * h * 3], np.uint8).reshape(n, h, w, 3)


def flow(frames, to1080):
    """motion_rough.py method: per frame pair, partial affine from tracked corners."""
    g = [cv2.cvtColor(f, cv2.COLOR_RGB2GRAY) for f in frames]
    cy, cx = g[0].shape[0] / 2.0, g[0].shape[1] / 2.0
    dxs, dys, zs = [], [], []
    for a, b in zip(g[:-1], g[1:]):
        p0 = cv2.goodFeaturesToTrack(a, 300, 0.01, 6)
        if p0 is None:
            continue
        p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None)
        ok = st.ravel() == 1
        if ok.sum() < 10:
            continue
        M, _ = cv2.estimateAffinePartial2D(p0[ok], p1[ok])
        if M is None:
            continue
        # move of the frame CENTRE (M's own tx/ty are about the top-left corner, so a push-in read as pan+tilt)
        dxs.append((M[0, 0] * cx + M[0, 1] * cy + M[0, 2] - cx) * to1080)
        dys.append((M[1, 0] * cx + M[1, 1] * cy + M[1, 2] - cy) * to1080)
        zs.append(np.sqrt(M[0, 0] ** 2 + M[1, 0] ** 2) - 1)
    if not dxs:
        return None
    dx, dy, z = np.array(dxs), np.array(dys), np.array(zs)
    # shake = what is left after a smooth (2nd-degree) fit of the per-frame move, as a robust sigma (median-based):
    # a deliberate ease in/out is not shake, and one tracking miss or whip does not decide it
    jitter = 0.0
    if len(dx) > 4:
        t = np.arange(len(dx))
        r = [np.median(np.abs(v - np.polyval(np.polyfit(t, v, 2), t))) * 1.4826 for v in (dx, dy)]
        jitter = float(np.hypot(r[0], r[1]))
    return dict(dx=round(float(dx.mean()) * FLOW_FPS, 1), dy=round(float(dy.mean()) * FLOW_FPS, 1),
                zoom=round(float(z.mean()) * FLOW_FPS * 100, 2), jitter=round(jitter, 1), pairs=len(dx))


def kind_of(m):
    if m is None:
        return "unknown"
    k = []
    if m["zoom"] > ZOOM_MIN:
        k.append("push-in")
    elif m["zoom"] < -ZOOM_MIN:
        k.append("pull-out")
    if abs(m["dx"]) > PAN_MIN:
        k.append("pan-right" if m["dx"] < 0 else "pan-left")
    if abs(m["dy"]) > PAN_MIN:
        k.append("tilt-down" if m["dy"] < 0 else "tilt-up")
    return "+".join(k) or "static"


def index_clip(path):
    info = probe(path)
    streams = info.get("streams", [])
    vs = [s for s in streams if s.get("codec_type") == "video"]
    au = [s for s in streams if s.get("codec_type") == "audio" and s.get("codec_name")]
    st = os.stat(path)
    c = dict(file=os.path.basename(path), rel=None, bytes=st.st_size, mtime=int(st.st_mtime))
    dur = float(info.get("format", {}).get("duration", 0) or 0)
    c["duration"] = round(dur, 3)
    c["created"] = info.get("format", {}).get("tags", {}).get("creation_time")
    c["audio"] = bool(au)
    c["audio_codec"] = au[0]["codec_name"] if au else None
    if not vs:
        c["flags"] = ["no video stream"]
        c["notes"] = ""
        return c
    v = vs[0]
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        rot = int(sd.get("rotation", 0) or 0)
    if abs(rot) in (90, 270):
        w, h = h, w
    c.update(width=w, height=h, rotation=rot, orientation="portrait" if h > w else "landscape" if w > h else "square",
             fps=round(fps_of(v.get("avg_frame_rate")), 3), codec=v.get("codec_name"))
    if w >= h:
        aw, ah = LONG_SIDE, max(2, round(LONG_SIDE * h / w / 2) * 2)
    else:
        aw, ah = max(2, round(LONG_SIDE * w / h / 2) * 2), LONG_SIDE
    to1080 = 1080.0 / aw
    wins, thumbs, lum, burnt = [], [], [], []
    for p in POINTS:
        t = p * dur
        t0 = max(0.0, min(t - WIN / 2, dur - WIN))
        fr = decode_window(path, t0, min(WIN, dur), aw, ah)
        if len(fr) == 0:
            wins.append(dict(at=round(t, 2), kind="unknown"))
            continue
        m = flow(fr, to1080)
        wins.append(dict(at=round(t, 2), kind=kind_of(m), **(m or {})))
        i = min(len(fr) - 1, max(0, int(round((t - t0) * FLOW_FPS))))
        thumbs.append((round(t, 2), fr[i]))
        y = fr.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32)   # Rec.709 luma, full range
        lum.append(float(y.mean()))
        burnt.append(float((y >= BURNT_LUMA).mean() * 100))
    c["frames_at"] = [t for t, _ in thumbs]
    c["luma_mean"] = round(np.mean(lum) / 255 * 100, 1) if lum else None
    c["burnt_pct"] = round(max(burnt), 2) if burnt else None
    c["motion"] = wins
    ks = [x["kind"] for x in wins]
    c["camera"] = ks[0] if len(set(ks)) == 1 else " -> ".join(ks)
    jit = [x.get("jitter", 0) for x in wins]
    c["shake"] = round(max(jit), 1) if jit else None
    flags = []
    if not c["audio"]:
        flags.append("no audio")
    if dur < FLAG_SHORT:
        flags.append("short %.2fs" % dur)
    if c["luma_mean"] is not None and c["luma_mean"] < FLAG_DARK:
        flags.append("dark (luma %.1f%%)" % c["luma_mean"])
    if c["burnt_pct"] is not None and c["burnt_pct"] > FLAG_BURNT:
        flags.append("burnt %.1f%%" % c["burnt_pct"])
    c["flags"] = flags
    c["notes"] = ""
    c["_thumbs"] = thumbs
    return c


def font(sz):
    try:
        return ImageFont.truetype(FONT, sz)
    except OSError:
        return ImageFont.load_default()


def make_sheets(clips, out_dir, thumbs_by_file):
    f1, f2 = font(18), font(14)
    per = CLIPS_PER_ROW * ROWS_PER_SHEET
    paths = []
    for s in range(0, len(clips), per):
        part = clips[s: s + per]
        th = max([round(THUMB_W * c.get("height", 1) / max(c.get("width", 1), 1)) for c in part] + [1])
        cell_w, cell_h, pad = 3 * THUMB_W + 2 * 2, th + 66, 10
        rows = (len(part) + CLIPS_PER_ROW - 1) // CLIPS_PER_ROW
        cols = min(CLIPS_PER_ROW, len(part))
        img = Image.new("RGB", (cols * (cell_w + pad) + pad, rows * (cell_h + pad) + pad), (20, 20, 20))
        d = ImageDraw.Draw(img)
        for i, c in enumerate(part):
            x = pad + (i % CLIPS_PER_ROW) * (cell_w + pad)
            y = pad + (i // CLIPS_PER_ROW) * (cell_h + pad)
            for j, (t, fr) in enumerate(thumbs_by_file.get(c["file"], [])):
                im = Image.fromarray(fr)
                im = im.resize((THUMB_W, max(1, round(THUMB_W * im.height / im.width))), Image.LANCZOS)
                img.paste(im, (x + j * (THUMB_W + 2), y))
            line1 = "%s  %.1fs  %s" % (c["file"], c.get("duration", 0), "" if c.get("audio") else "NO AUDIO")
            line2 = c.get("camera", "?")
            line3 = "luma %s%%  burnt %s%%  shake %s  %s" % (c.get("luma_mean"), c.get("burnt_pct"), c.get("shake"),
                                                          "; ".join(f for f in c.get("flags", []) if f != "no audio"))
            while line2 and d.textlength(line2, font=f2) > cell_w - 4:
                line2 = line2[:-2]
            while line3 and d.textlength(line3, font=f2) > cell_w - 4:
                line3 = line3[:-2]
            d.text((x + 2, y + th + 3), line1, fill=(255, 220, 90) if c.get("flags") else (235, 235, 235), font=f1)
            d.text((x + 2, y + th + 25), line2, fill=(190, 190, 190), font=f2)
            d.text((x + 2, y + th + 44), line3, fill=(190, 190, 190), font=f2)
        p = os.path.join(out_dir, "footage_index_sheet_%02d.png" % (s // per + 1))
        img.save(p)
        paths.append(p)
    return paths


def main():
    ap = argparse.ArgumentParser(description="Index a shoot folder (footage_index.json + contact sheets).")
    ap.add_argument("folder")
    ap.add_argument("--out", help="output folder (default <folder>\\_index; required for a Dropbox folder)")
    ap.add_argument("--recursive", action="store_true", help="also index sub-folders")
    ap.add_argument("--force", action="store_true", help="re-measure clips even if unchanged")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    folder = os.path.abspath(a.folder)
    if not os.path.isdir(folder):
        sys.exit("not a folder: %s" % folder)
    if a.out:
        out = os.path.abspath(a.out)
    elif "dropbox" in folder.lower():
        sys.exit("this shoot is inside Dropbox: pass --out <reel>\\work\\footage_index (nothing is written into Dropbox)")
    else:
        out = os.path.join(folder, "_index")
    files = []
    for root, dirs, names in os.walk(folder):
        dirs[:] = [x for x in dirs if x != "_index" and not x.startswith(".")]
        for n in sorted(names):
            if n.lower().endswith(VIDEO_EXT):
                files.append(os.path.join(root, n))
        if not a.recursive:
            break
    if not files:
        sys.exit("no video files in %s" % folder)
    os.makedirs(out, exist_ok=True)
    jpath = os.path.join(out, "footage_index.json")
    old = {}
    if os.path.exists(jpath):
        try:
            old = {c["rel"]: c for c in json.load(open(jpath, encoding="utf-8")).get("clips", [])}
        except (ValueError, KeyError):
            old = {}
    todo, clips = [], {}
    for f in files:
        rel = os.path.relpath(f, folder)
        o = old.get(rel)
        st = os.stat(f)
        if o and not a.force and o.get("bytes") == st.st_size and o.get("mtime") == int(st.st_mtime) \
                and o.get("frames_at") is not None:
            clips[rel] = o
        else:
            todo.append(f)
    print("%d clips, %d to measure, %d unchanged" % (len(files), len(todo), len(files) - len(todo)), flush=True)
    thumbs = {}
    with cf.ThreadPoolExecutor(max(1, a.workers)) as ex:
        for f, c in zip(todo, ex.map(index_clip, todo)):
            rel = os.path.relpath(f, folder)
            c["rel"] = rel
            if rel in old:
                c["notes"] = old[rel].get("notes", "")
            thumbs[c["file"]] = c.pop("_thumbs", [])
            clips[rel] = c
            print("  %-14s %6.1fs %4dx%-4d %5.1ffps %-8s luma %5s%% burnt %5s%%  %-22s %s" % (
                c["file"], c.get("duration", 0), c.get("width", 0), c.get("height", 0), c.get("fps", 0),
                "audio" if c["audio"] else "NO-AUDIO", c.get("luma_mean"), c.get("burnt_pct"),
                c.get("camera", "?"), "; ".join(c["flags"])), flush=True)
    # unchanged clips: their frames are needed again for the sheets (cheap: 3 single frames)
    for rel, c in clips.items():
        if c["file"] not in thumbs and c.get("frames_at"):
            fp = os.path.join(folder, rel)
            w, h = c.get("width", 0), c.get("height", 0)
            aw = THUMB_W
            ah = max(2, round(THUMB_W * h / max(w, 1) / 2) * 2)
            th = []
            for t in c["frames_at"]:
                p = run(["ffmpeg", "-nostdin", "-v", "error", "-ss", "%.3f" % t, "-i", fp, "-frames:v", "1",
                         "-vf", "scale=%d:%d" % (aw, ah), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
                if len(p.stdout) >= aw * ah * 3:
                    th.append((t, np.frombuffer(p.stdout[: aw * ah * 3], np.uint8).reshape(ah, aw, 3)))
            thumbs[c["file"]] = th
    ordered = [clips[os.path.relpath(f, folder)] for f in files]
    sheets = make_sheets(ordered, out, thumbs)
    doc = dict(folder=folder, created=dt.datetime.now().isoformat(timespec="seconds"), tool="footage_index.py",
               version=VERSION, clips_count=len(ordered),
               limits=dict(static_zoom_pct_s=ZOOM_MIN, static_pan_px_s=PAN_MIN, burnt_luma=BURNT_LUMA,
                           flag_dark_luma_pct=FLAG_DARK, flag_burnt_pct=FLAG_BURNT,
                           flag_short_s=FLAG_SHORT, note="flags are warnings only; limits are not approved kit numbers"),
               sheets=[os.path.basename(p) for p in sheets], clips=ordered)
    tmp = jpath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, jpath)
    print("wrote %s + %d sheet(s)" % (jpath, len(sheets)))


if __name__ == "__main__":
    main()
