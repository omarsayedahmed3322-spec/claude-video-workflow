"""edl_to_premiere_xml.py - turn a talking-head cut plan (EDL) into a Premiere timeline (FCP7 XML / xmeml).

usage:
  python -I -X utf8 edl_to_premiere_xml.py <edl.json> --root <reel folder> --jsx <build.jsx> --out <timeline.xml>
         [--files map.json] [--vo speech.wav] [--music music.mp3 --music-cut S --music-loop S --music-db DB]
         [--mix full_mix.wav] [--until SECONDS] [--fps 25] [--name SEQUENCE]

Omar opens the result in Premiere with File > Import (plan phase 6, 2026-11-12).

The EDL is what plan_talking.py writes (skills/reel-talking-head/references):
  doc   [{t0, t1, src}]                        speaker pieces on the timeline, src = source in (s)
  broll [{t0, t1, item, src, tin, tout, ...}]  item = key of FILES in the build .jsx
  shots [{t0, t1, zoom, k0, k1}]               zoom = scale k0 -> k1 over the shot
  caps  [{t0, t1, txt}]   outro = logo time    dur = reel length
All times are timeline seconds; the last speaker piece runs to dur (as in build_talking.jsx).

Tracks:  V1 speaker (FILES["doc"])   V2 b-roll   (no V3: captions/graphics are markers in v1)
         A1 speech (--vo, cut like V1)   A2 music (--music, A up to --music-cut, then B from --music-loop)
         A3 full mix (--mix), disabled, as a reference.
Not carried over in v1 (written as sequence markers instead): zoom moves, speed changes (b-roll
shorter than its slot), flash/zoom transitions, captions, the outro.
Paths are linked to the prepared clips the .jsx uses (footage/prep = rotated + graded), never raw.
--until cuts the sequence at that time (for a 3-clip test).
After writing, the file is re-read: XML valid, every path exists, V1 length = EDL length.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                         capture_output=True, stdin=subprocess.DEVNULL)
    if out.returncode != 0:
        sys.exit("ffprobe failed: " + path)
    j = json.loads(out.stdout.decode("utf-8"))
    v = next((s for s in j["streams"] if s["codec_type"] == "video" and s.get("codec_name") not in ("mjpeg", "png")), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    still = v is None and any(s["codec_type"] == "video" for s in j["streams"])
    return {"dur": float(j["format"].get("duration", 0) or 0), "v": v, "a": a, "still": still}


def pathurl(path):
    p = os.path.abspath(path).replace("\\", "/")
    drive, rest = p[0], p[2:]
    return "file://localhost/" + drive + "%3a" + urllib.parse.quote(rest, safe="/")


def url_to_path(u):
    p = urllib.parse.unquote(u[len("file://localhost/"):])
    return p.replace("/", os.sep)


class Timeline:
    def __init__(self, fps):
        self.fps = fps
        self.files = {}      # abs path -> (id, info)
        self.emitted = set() # file ids already written in full (later clips only reference the id)
        self.n = 0

    def f(self, t):
        return int(round(t * self.fps))

    def rate(self):
        return "<rate><timebase>%d</timebase><ntsc>FALSE</ntsc></rate>" % self.fps

    def info(self, path):
        path = os.path.abspath(path)
        if path not in self.files:
            self.files[path] = ("file-%d" % (len(self.files) + 1), probe(path))
        return self.files[path][1]

    def file_xml(self, path):
        info = self.info(path)
        path = os.path.abspath(path)
        fid = self.files[path][0]
        if fid in self.emitted:
            return '<file id="%s"/>' % fid, info
        self.emitted.add(fid)
        media = ""
        if info["v"]:
            media += ("<video><samplecharacteristics>%s<width>%s</width><height>%s</height>"
                      "<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio>"
                      "<fielddominance>none</fielddominance></samplecharacteristics></video>"
                      % (self.rate(), info["v"]["width"], info["v"]["height"]))
        if info["a"]:
            media += ("<audio><samplecharacteristics><depth>16</depth><samplerate>%s</samplerate>"
                      "</samplecharacteristics><channelcount>%s</channelcount></audio>"
                      % (info["a"].get("sample_rate", 48000), info["a"].get("channels", 2)))
        x = ("<file id=\"%s\"><name>%s</name><pathurl>%s</pathurl>%s<duration>%d</duration><media>%s</media></file>"
             % (fid, escape(os.path.basename(path)), pathurl(path), self.rate(), self.f(info["dur"]), media))
        return x, info

    def clip(self, path, start, end, src_in, kind, enabled=True, gain_db=None, speed=100.0):
        """start/end = timeline frames, src_in = source frame. kind = video|audio. speed in % (50 = half speed)."""
        fx, info = self.file_xml(path)
        self.n += 1
        dur = self.f(info["dur"])
        if abs(speed - 100) > 0.01:
            # Premiere's own export (Omar, 2026-11-12): in/out and duration are counted at the new speed
            src_in, dur = int(round(src_in * 100 / speed)), int(round(dur * 100 / speed))
        out = src_in + (end - start)
        x = ["<clipitem id=\"clipitem-%d\"><name>%s</name><enabled>%s</enabled><duration>%d</duration>%s"
             "<start>%d</start><end>%d</end><in>%d</in><out>%d</out>%s"
             % (self.n, escape(os.path.basename(path)), "TRUE" if enabled else "FALSE", dur, self.rate(),
                start, end, src_in, out, fx)]
        if kind == "audio":
            x.append("<sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack>")
        if abs(speed - 100) > 0.01:
            x.append("<filter><effect><name>Time Remap</name><effectid>timeremap</effectid>"
                     "<effectcategory>motion</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype>"
                     "<parameter><parameterid>variablespeed</parameterid><name>variablespeed</name><valuemin>0</valuemin>"
                     "<valuemax>1</valuemax><value>0</value></parameter>"
                     "<parameter><parameterid>speed</parameterid><name>speed</name><valuemin>-100000</valuemin>"
                     "<valuemax>100000</valuemax><value>%g</value></parameter>"
                     "<parameter><parameterid>reverse</parameterid><name>reverse</name><value>FALSE</value></parameter>"
                     "<parameter><parameterid>frameblending</parameterid><name>frameblending</name><value>FALSE</value>"
                     "</parameter></effect></filter>" % speed)
        if gain_db is not None:
            x.append("<filter><effect><name>Audio Levels</name><effectid>audiolevels</effectid>"
                     "<effectcategory>audiolevels</effectcategory><effecttype>audiolevels</effecttype>"
                     "<mediatype>audio</mediatype><parameter><parameterid>level</parameterid><name>Level</name>"
                     "<valuemin>0</valuemin><valuemax>3.98109</valuemax><value>%.5f</value></parameter>"
                     "</effect></filter>" % (10 ** (gain_db / 20)))
        x.append("</clipitem>")
        return "".join(x), info


def read_files_map(jsx):
    s = open(jsx, encoding="utf-8").read()
    m = re.search(r"var\s+FILES\s*=\s*\{(.*?)\};", s, re.S)
    if not m:
        sys.exit("no 'var FILES = {...};' in " + jsx)
    body = re.sub(r"//[^\n]*", "", m.group(1))
    return dict(re.findall(r"(\w+)\s*:\s*\"([^\"]+)\"", body))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--root", required=True, help="reel folder; FILES paths are relative to it")
    ap.add_argument("--jsx", help="build .jsx that holds var FILES = {...}")
    ap.add_argument("--files", help="JSON {item: relative path} instead of --jsx")
    ap.add_argument("--vo"); ap.add_argument("--music"); ap.add_argument("--mix")
    ap.add_argument("--music-cut", type=float); ap.add_argument("--music-loop", type=float)
    ap.add_argument("--music-db", type=float, default=-22.0)
    ap.add_argument("--until", type=float)
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--name")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    E = json.load(open(a.edl, encoding="utf-8"))
    files = json.load(open(a.files, encoding="utf-8")) if a.files else read_files_map(a.jsx)
    R = a.root
    T = Timeline(a.fps)
    f = T.f
    dur = E["dur"] if a.until is None else min(E["dur"], a.until)
    END = f(dur)
    markers = []   # (timeline frame in, frame out or -1, name, comment)
    warn = []

    def mk(t0, t1, name, comment=""):
        if f(t0) < END:
            markers.append((f(t0), min(f(t1), END) if t1 is not None else -1, name, comment))

    # ---- V1 speaker (+ A1 speech cut the same way) ----
    v1, a1, gap = [], [], []
    doc_path = os.path.join(R, files["doc"])
    for i, d in enumerate(E["doc"]):
        t1 = E["dur"] if i == len(E["doc"]) - 1 else d["t1"]
        s, e = f(d["t0"]), min(f(t1), END)
        if s >= END:
            break
        src = f(d["src"])
        left = f(T.info(doc_path)["dur"]) - src
        if e - s > left:   # the source ends first: AE leaves the rest empty too, so the gap is kept
            gap.append((s + left, e))
            mk((s + left) / a.fps, e / a.fps, "مفيش متكلم", "الفوتيج خلص هنا (زي AE)")
            e = s + left
        x = T.clip(doc_path, s, e, src, "video")[0]
        v1.append(x)
        if a.vo:
            a1.append(T.clip(a.vo, s, e, src, "audio")[0])

    # ---- V2 b-roll ----
    v2 = []
    for b in E["broll"]:
        s, e = f(b["t0"]), min(f(b["t1"]), END)
        if s >= END:
            continue
        p = os.path.join(R, files[b["item"]])
        info = T.info(p)
        if info["still"]:
            mk(b["t0"], b["t1"], "صورة ثابتة", os.path.basename(p) + " (مااتحطتش، ضيفها بإيدك)")
            continue
        src = f(b["src"])
        avail = f(info["dur"]) - src
        sp = float(b.get("speed", 100))
        if (e - s) * sp / 100 > avail:
            need = (b["t1"] - b["t0"]) / (avail / a.fps) * 100
            mk(b["t0"], b["t1"], "سرعة", "%s أقصر من مكانها: في AE اتمطّت %d%%. هنا متحطة %g%% لحد ما تخلص"
               % (b["item"], int(need + 0.999), sp))
            e = s + int(avail * 100 / sp)
        elif sp != 100:
            mk(b["t0"], b["t1"], "سرعة", "%s على %g%% (من القص بتاع عمر)" % (b["item"], sp))
        v2.append(T.clip(p, s, e, src, "video", speed=sp)[0])
        if b.get("tin", "cut") != "cut":
            mk(b["t0"], None, "ترانزيشن داخل: " + b["tin"])
        if b.get("tout", "cut") != "cut":
            mk(b["t1"], None, "ترانزيشن خارج: " + b["tout"])

    # ---- markers: zoom moves, captions, outro ----
    for sh in E.get("shots", []):
        if sh.get("zoom") and sh["k0"] != sh["k1"]:
            mk(sh["t0"], sh["t1"], "زوم", "Scale %g -> %g" % (sh["k0"], sh["k1"]))
    for c in E.get("caps", []):
        mk(c["t0"], c["t1"], "كابشن", c["txt"].replace("\r", " / ").replace("\n", " / "))
    if "outro" in E:
        mk(E["outro"], None, "القفلة", "طبقة بيضا واللوجو (من AE)")

    # ---- A2 music, A3 full mix (disabled) ----
    a2, a3 = [], []
    if a.music:
        cut = f(a.music_cut) if a.music_cut is not None else END
        a2.append(T.clip(a.music, 0, min(cut, END), 0, "audio", gain_db=a.music_db)[0])
        if cut < END and a.music_loop is not None:
            a2.append(T.clip(a.music, cut, END, f(a.music_loop), "audio", gain_db=a.music_db)[0])
        mk(0, None, "المزيكا", "متحطة %g dB ثابت. الميكس الأصلي فيه إنفلوب (أعلى على اللوجو)" % a.music_db)
    if a.mix:
        a3.append(T.clip(a.mix, 0, END, 0, "audio", enabled=False)[0])

    def track(items):
        return "<track>" + "".join(items) + "</track>"

    W, H = 1080, 1920
    name = a.name or os.path.splitext(os.path.basename(a.edl))[0]
    mxml = "".join("<marker><name>%s</name><comment>%s</comment><in>%d</in><out>%d</out></marker>"
                   % (escape(n), escape(c), i, o) for i, o, n, c in sorted(markers))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4">'
           '<sequence id="sequence-1"><name>%s</name><duration>%d</duration>%s'
           '<media><video><format><samplecharacteristics>%s<width>%d</width><height>%d</height>'
           '<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio>'
           '<fielddominance>none</fielddominance></samplecharacteristics></format>%s%s</video>'
           '<audio><numOutputChannels>2</numOutputChannels><format><samplecharacteristics><depth>16</depth>'
           '<samplerate>48000</samplerate></samplecharacteristics></format>%s%s%s</audio></media>%s'
           '</sequence></xmeml>\n'
           % (escape(name), END, T.rate(), T.rate(), W, H, track(v1), track(v2),
              track(a1), track(a2), track(a3), mxml))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w", encoding="utf-8", newline="\n").write(xml)

    # ---- check what was written ----
    root = ET.parse(a.out).getroot()
    urls = [u.text for u in root.iter("pathurl")]
    missing = [url_to_path(u) for u in urls if not os.path.exists(url_to_path(u))]
    vtracks = root.find("sequence/media/video").findall("track")
    v1len = sum(int(c.find("end").text) - int(c.find("start").text) for c in vtracks[0].findall("clipitem"))
    gaplen = sum(e - s for s, e in gap)
    ok = v1len + gaplen == END
    print("written:", a.out)
    print("XML valid: yes | files: %d | missing: %d | clips V1 %d, V2 %d, A1 %d, A2 %d, A3 %d | markers %d"
          % (len(urls), len(missing), len(v1), len(v2), len(a1), len(a2), len(a3), len(markers)))
    print("V1 %d frames + empty %d (source ended) = %d | EDL %d frames = %.2f s | %s"
          % (v1len, gaplen, v1len + gaplen, END, END / a.fps, "match" if ok else "MISMATCH"))
    for m in missing:
        print("MISSING:", m)
    for w in warn:
        print("WARN:", w)
    sys.exit(1 if missing or not ok else 0)


if __name__ == "__main__":
    main()
