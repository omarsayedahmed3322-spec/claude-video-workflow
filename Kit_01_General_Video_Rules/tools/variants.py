"""variants.py - put 2-3 renders of the same moment one after another in ONE video,
each labelled A / B / C, so Omar picks a taste option in one watch (plan phase 8-a).

usage:
  python -I -X utf8 variants.py A.mp4 B.mp4 [C.mp4] -o choices.mp4
         [--start S] [--dur D] [--labels A,B,C] [--gap 1.0] [--size 1080x1920] [--fps 25]

  --start/--dur  cut the same moment out of every input (use when the inputs are full
                 renders; skip when they are already the 3-5 s moment).
  --gap          seconds of black + silence between options (default 1.0).
  --size/--fps   output canvas (default 1080x1920; fps defaults to the first input's).

Each option keeps its own picture and sound at full size (Omar, 2026-11-14: «ورا بعض»).
The letter sits top-left inside the safe zone (x 60, y 250) for the whole option.
An input with no audio gets silence, so the options line up. Output: H.264 CRF 18,
AAC 192k, +faststart. After writing, the file is probed and its duration is checked
against the sum of the options + gaps.
Variant renders themselves come from the build/mix script with the option name in an
env var (like R3_VOCAL in mix_R3.py); this tool only joins them.
"""
import argparse
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

FONT = "C\\:/Windows/Fonts/arial.ttf"   # drawtext needs an explicit fontfile on this PC
SAFE_X, SAFE_Y = 60, 250                 # top-left of the safe zone on 1080x1920


def probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json",
                        "-show_streams", "-show_format", path], capture_output=True)
    if p.returncode != 0:
        sys.exit("ffprobe failed on %s:\n%s" % (path, p.stderr.decode("utf-8", "replace")))
    return json.loads(p.stdout.decode("utf-8", "replace"))


def fps_of(info):
    for s in info["streams"]:
        if s.get("codec_type") == "video":
            n, d = s.get("avg_frame_rate", "0/1").split("/")
            if float(d) and float(n):
                return float(n) / float(d)
    return 25.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--start", type=float, default=None)
    ap.add_argument("--dur", type=float, default=None)
    ap.add_argument("--labels", default=None)
    ap.add_argument("--gap", type=float, default=1.0)
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--fps", type=float, default=None)
    a = ap.parse_args()

    if len(a.inputs) < 2:
        sys.exit("need at least 2 renders to compare")
    labels = a.labels.split(",") if a.labels else [chr(65 + i) for i in range(len(a.inputs))]
    if len(labels) != len(a.inputs):
        sys.exit("--labels count (%d) != inputs (%d)" % (len(labels), len(a.inputs)))
    W, H = (int(v) for v in a.size.lower().split("x"))
    scale = W / 1080.0

    infos = []
    for path in a.inputs:
        if not os.path.isfile(path):
            sys.exit("missing: %s" % path)
        infos.append(probe(path))
    fps = a.fps or fps_of(infos[0])

    # duration of every option after the optional cut
    durs = []
    for info in infos:
        full = float(info["format"]["duration"])
        start = a.start or 0.0
        d = full - start
        if a.dur is not None:
            d = min(d, a.dur)
        if d <= 0:
            sys.exit("--start is past the end of an input (%.2f s)" % full)
        durs.append(d)

    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-y"]
    for path in a.inputs:
        if a.start is not None:
            cmd += ["-ss", "%.3f" % a.start]
        if a.dur is not None:
            cmd += ["-t", "%.3f" % a.dur]
        cmd += ["-i", path]

    fs = int(round(150 * scale))
    pad = int(round(18 * scale))
    parts, chains = [], []
    for i, (info, label, d) in enumerate(zip(infos, labels, durs)):
        has_audio = any(s.get("codec_type") == "audio" for s in info["streams"])
        chains.append(
            "[%d:v]scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,fps=%s,format=yuv420p,"
            "drawtext=fontfile='%s':text='%s':x=%d:y=%d:fontsize=%d:fontcolor=white:"
            "box=1:boxcolor=black@0.65:boxborderw=%d[v%d]"
            % (i, W, H, W, H, repr(fps), FONT, label, int(SAFE_X * scale), int(SAFE_Y * scale), fs, pad, i))
        if has_audio:
            chains.append("[%d:a]aresample=48000,aformat=channel_layouts=stereo,"
                          "apad,atrim=0:%.3f,asetpts=PTS-STARTPTS[a%d]" % (i, d, i))
        else:
            chains.append("anullsrc=r=48000:cl=stereo,atrim=0:%.3f,asetpts=PTS-STARTPTS[a%d]" % (d, i))
        parts.append("[v%d][a%d]" % (i, i))
        if a.gap > 0 and i < len(a.inputs) - 1:
            chains.append("color=c=black:s=%dx%d:r=%s:d=%.3f,format=yuv420p,setsar=1[gv%d]"
                          % (W, H, repr(fps), a.gap, i))
            chains.append("anullsrc=r=48000:cl=stereo,atrim=0:%.3f,asetpts=PTS-STARTPTS[ga%d]" % (a.gap, i))
            parts.append("[gv%d][ga%d]" % (i, i))
    n = len(parts)
    chains.append("%sconcat=n=%d:v=1:a=1[v][a]" % ("".join(parts), n))

    cmd += ["-filter_complex", ";".join(chains), "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        err = p.stderr.decode("utf-8", "replace").strip().splitlines()
        sys.exit("ffmpeg failed:\n" + "\n".join(err[-15:]))

    expect = sum(durs) + a.gap * (len(a.inputs) - 1)
    got = float(probe(a.out)["format"]["duration"])
    t = 0.0
    print("options (%s, %dx%d, %.3g fps):" % (os.path.basename(a.out), W, H, fps))
    for label, path, d in zip(labels, a.inputs, durs):
        print("  %s  %6.2f-%6.2f s  %s" % (label, t, t + d, os.path.basename(path)))
        t += d + a.gap
    ok = abs(got - expect) <= 2.0 / fps + 0.05
    print("duration %.2f s (expected %.2f) %s" % (got, expect, "OK" if ok else "MISMATCH"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
