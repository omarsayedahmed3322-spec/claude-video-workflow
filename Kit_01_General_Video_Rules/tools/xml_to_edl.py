"""xml_to_edl.py - read Omar's cut back from Premiere (FCP7 XML) into a talking-head EDL.

The way back of edl_to_premiere_xml.py (plan phase 6, 2026-11-12):
  1. edl_to_premiere_xml.py writes the first assembly, Omar opens it in Premiere.
  2. Omar cuts on V1 (speaker) and V2 (b-roll) only, then File > Export > Final Cut Pro XML.
  3. this tool turns that XML + the old EDL into a new EDL, and build_talking.jsx / mix_talking.py rebuild
     the reel in AE with his cut (captions, zooms, transitions and the outro are carried over).

usage:
  python -I -X utf8 xml_to_edl.py <premiere.xml> --edl <old edl.json> --root <reel folder> --jsx <build.jsx>
         --out <new edl.json> [--files map.json] [--sequence NAME]

What is read from the XML: V1 = speaker pieces (the FILES["doc"] clip), V2 = b-roll (any FILES item; a file
that is not in FILES gets a new key «new1, new2 ...» and is printed so it can be added to FILES).
Disabled clips are skipped. Everything else comes from the old EDL, moved by the SOURCE time of the speech:
  caps    a caption follows its words; a caption whose words were cut out is dropped (printed).
  outro   follows the last word; dur = outro + the old outro length.
  keep    speech kept = the new V1 source ranges inside the old keep ranges (what mix_talking.py cuts).
  broll   tin/tout/hard come from the old clip with the same item (else plain cut); oncut is recomputed.
  shots   rebuilt from the b-roll edges like plan_talking.py; zoom k0/k1 copied from the old shot that showed
          the same b-roll item or the same spoken moment (else static 100).
  topics, t0   copied as they are.
Markers whose name is not one of edl_to_premiere_xml's own (كابشن، زوم، سرعة، ترانزيشن، القفلة، المزيكا،
مفيش متكلم) are Omar's notes: printed with their time and saved in the EDL as "notes" (the build ignores them).
Speed: a constant speed on a V2 clip (Premiere Speed/Duration) is saved as broll "speed" (%, 50 = half speed)
and build_talking.jsx stretches the layer. Speed on V1 stops the tool (the speech would leave the lips).
Not read: speed ramps, reverse, Premiere transitions, effects, audio edits (the mix is rebuilt from the speech).
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

OWN_MARKERS = ("كابشن", "زوم", "سرعة", "ترانزيشن", "القفلة", "المزيكا", "مفيش متكلم", "صورة ثابتة")


def norm(p):
    return os.path.normcase(os.path.abspath(p))


def url_to_path(u):
    u = u.strip()
    for pre in ("file://localhost/", "file:///", "file://"):
        if u.startswith(pre):
            u = u[len(pre):]
            break
    return urllib.parse.unquote(u).replace("/", os.sep)


def read_files_map(jsx):
    s = open(jsx, encoding="utf-8").read()
    m = re.search(r"var\s+FILES\s*=\s*\{(.*?)\};", s, re.S)
    if not m:
        sys.exit("no 'var FILES = {...};' in " + jsx)
    return dict(re.findall(r"(\w+)\s*:\s*\"([^\"]+)\"", re.sub(r"//[^\n]*", "", m.group(1))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xml")
    ap.add_argument("--edl", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--jsx"); ap.add_argument("--files")
    ap.add_argument("--sequence")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    old = json.load(open(a.edl, encoding="utf-8"))
    files = json.load(open(a.files, encoding="utf-8")) if a.files else read_files_map(a.jsx)
    by_path = {norm(os.path.join(a.root, p)): k for k, p in files.items()}
    doc_path = norm(os.path.join(a.root, files["doc"]))

    root = ET.parse(a.xml).getroot()
    seqs = root.findall(".//sequence")
    seq = next((s for s in seqs if a.sequence is None or (s.findtext("name") or "") == a.sequence), None)
    if seq is None or seq.find("media/video") is None:
        sys.exit("no sequence%s in the XML" % ("" if a.sequence is None else " named " + a.sequence))
    fps = int(seq.findtext("rate/timebase"))
    urls = {f.get("id"): f.findtext("pathurl") for f in root.iter("file") if f.findtext("pathurl")}
    fdur = {f.get("id"): int(f.findtext("duration")) for f in root.iter("file") if f.findtext("duration")}

    def clips(track):
        out = []
        for c in track.findall("clipitem"):
            if (c.findtext("enabled") or "TRUE").upper() == "FALSE":
                continue
            st, en = int(c.findtext("start")), int(c.findtext("end"))
            if st < 0 or en < 0:
                sys.exit("clip «%s» touches a Premiere transition (start/end = -1): remove the transition and export again"
                         % c.findtext("name"))
            f = c.find("file")
            u = urls.get(f.get("id")) if f is not None else None
            if not u:
                sys.exit("clip «%s» has no file path in the XML" % c.findtext("name"))
            cr = int(c.findtext("rate/timebase") or fps)
            cin, cout = int(c.findtext("in")), int(c.findtext("out"))
            speed = 100.0
            for e in c.iter("effect"):
                if (e.findtext("effectid") or "") != "timeremap":
                    continue
                prm = {(p.findtext("parameterid") or ""): (p.findtext("value") or "") for p in e.findall("parameter")}
                if prm.get("reverse", "FALSE").upper() == "TRUE":
                    print("WARN: «%s» plays backwards in Premiere: not carried over" % c.findtext("name"))
                if prm.get("variablespeed", "0") not in ("0", "FALSE"):
                    print("WARN: «%s» has a speed ramp (Time Remapping) in Premiere: only constant speed is read"
                          % c.findtext("name"))
                try:
                    speed = abs(float(prm.get("speed", "100"))) or 100.0
                except ValueError:
                    pass
            src = cin / cr
            if abs(speed - 100) > 0.01:
                n = en - st
                # in/out are source frames when out-in = length x speed; if out-in = length they are speed-scaled
                if abs((cout - cin) - n * speed / 100) > 1.5 and abs((cout - cin) - n) <= 1.5:
                    src = cin * speed / 100 / cr
            fd = fdur.get(f.get("id"))
            out.append({"t0": st / fps, "t1": en / fps, "src": src, "speed": round(speed, 2),
                        "path": norm(url_to_path(u)), "name": c.findtext("name"),
                        "at_end": fd is not None and cout >= fd - 1})
        return sorted(out, key=lambda x: x["t0"])

    def keep_exact(src, olds):
        # the XML holds whole frames: a source in-point within one frame of the old one is the same in-point
        for o in olds:
            if abs(o - src) < 1.0 / fps:
                return o
        return src

    vt = seq.find("media/video").findall("track")
    if not vt:
        sys.exit("the sequence has no video track")
    v1 = clips(vt[0])
    v2 = clips(vt[1]) if len(vt) > 1 else []
    for c in v1:
        if c["path"] != doc_path:
            sys.exit("V1 has «%s», which is not the speaker clip %s: b-roll goes on V2" % (c["name"], files["doc"]))
        if c["speed"] != 100:
            sys.exit("V1 piece at %.2f s has speed %g%% in Premiere: the speech would drift off the lips. "
                     "Keep the speaker at 100%% (speed is for b-roll on V2)" % (c["t0"], c["speed"]))
    r3 = lambda x: round(x, 3)
    doc = [{"t0": r3(c["t0"]), "t1": r3(c["t1"]), "src": keep_exact(r3(c["src"]), [d["src"] for d in old["doc"]])}
           for c in v1]
    if not doc:
        sys.exit("V1 is empty")

    # ---- source <-> timeline through the speaker pieces ----
    def to_src(t, pieces):
        for i, d in enumerate(pieces):
            last = i == len(pieces) - 1
            if d["t0"] - 1e-6 <= t < d["t1"] + 1e-6 or (last and t >= d["t0"]):
                return d["src"] + t - d["t0"]
        return None

    def to_tl(s, pieces):
        for d in pieces:
            if d["src"] - 1e-6 <= s <= d["src"] + d["t1"] - d["t0"] + 1e-6:
                return d["t0"] + s - d["src"]
        return None

    def span_tl(s0, s1, pieces):   # timeline range showing source [s0, s1], or None if all of it was cut
        hits = []
        for d in pieces:
            a0, a1 = max(s0, d["src"]), min(s1, d["src"] + d["t1"] - d["t0"])
            if a1 > a0 + 1e-6:
                hits.append((d["t0"] + a0 - d["src"], d["t0"] + a1 - d["src"]))
        return (min(h[0] for h in hits), max(h[1] for h in hits)) if hits else None

    od = old["doc"]
    report = []

    # ---- captions ----
    caps = []
    for c in old.get("caps", []):
        s0, s1 = to_src(c["t0"], od), to_src(c["t1"], od)
        sp = span_tl(s0, s1, doc) if s0 is not None and s1 is not None else None
        if sp is None:
            report.append("caption dropped (its words were cut): " + c["txt"].replace("\r", " / "))
            continue
        caps.append({"t0": r3(sp[0]), "t1": r3(sp[1]), "txt": c["txt"]})

    # ---- outro / dur ----
    tail = old["dur"] - old["outro"]
    s_out = to_src(old["outro"], od)
    outro = to_tl(s_out, doc) if s_out is not None else None
    if outro is None:
        outro = doc[-1]["t1"]
        report.append("outro: its moment was cut, put at the end of V1 (%.2f s)" % outro)
    outro = round(round(outro * fps) / fps, 3)
    dur = round(round((outro + tail) * fps) / fps, 3)

    # ---- speech kept (mix_talking.py places word sounds with it: source -> timeline, one range per piece) ----
    # an untouched piece keeps its old range (exact speech edges); a trimmed or new piece = its own source range
    keep, paired = [], len(old["keep"]) == len(od)
    speech_end = old["keep"][-1][1] if old["keep"] else None
    for i, d in enumerate(doc):
        n = d["t1"] - d["t0"]
        j = next((j for j, o in enumerate(od) if o["src"] == d["src"]), None)
        if paired and j is not None and (j == len(od) - 1 or abs((od[j]["t1"] - od[j]["t0"]) - n) < 1.0 / fps):
            keep.append(old["keep"][j])
            continue
        a1 = d["src"] + n
        if i == len(doc) - 1 and speech_end is not None:
            a1 = min(a1, max(speech_end, d["src"]))
        keep.append([d["src"], r3(a1)])

    # ---- b-roll ----
    new_items, broll = {}, []
    for c in v2:
        item = by_path.get(c["path"])
        if item is None:
            item = new_items.setdefault(c["path"], "new%d" % (len(new_items) + 1))
        prev = [b for b in old["broll"] if b["item"] == item]
        p = min(prev, key=lambda b: abs(b["t0"] - c["t0"])) if prev else {}
        t1 = c["t1"]
        if p and c["speed"] == 100 and c["at_end"] and abs(p["t0"] - c["t0"]) < 1.0 / fps and p["t1"] > t1:
            t1 = p["t1"]   # edl_to_premiere_xml shortened it (AE stretches it to fill): give the slot back
            report.append("b-roll %s at %.2f: source too short, back to %.2f (AE stretches it)" % (item, c["t0"], t1))
        broll.append({"t0": r3(c["t0"]), "t1": r3(t1), "item": item,
                      "src": keep_exact(r3(c["src"]), [b["src"] for b in prev]),
                      "hard": p.get("hard", False), "tin": p.get("tin", "cut"), "tout": p.get("tout", "cut")})
        if c["speed"] != 100:
            broll[-1]["speed"] = c["speed"]   # build_talking.jsx: AE stretch = 10000 / speed
            report.append("b-roll %s at %.2f: speed %g%%" % (item, c["t0"], c["speed"]))
    for b in broll:
        b["oncut"] = any(abs(d["t0"] - b["t1"]) < 0.01 for d in doc[1:])

    # ---- shots (same rule as plan_talking.py), zoom copied from the old shot showing the same thing ----
    edges = sorted({0.0, outro} | {b["t0"] for b in broll} | {b["t1"] for b in broll})
    edges = [e for e in edges if e <= outro + 1e-6]
    shots = []
    for s, z in zip(edges, edges[1:]):
        bi = next((i for i, b in enumerate(broll) if b["t0"] <= s + 0.01 and b["t1"] >= z - 0.01), None)
        sh = {"t0": r3(s), "t1": r3(z), "br": bi, "zoom": False, "k0": 100, "k1": 100}
        src = None
        if bi is not None:
            src = next((o for o in old["shots"] if o["br"] is not None
                        and old["broll"][o["br"]]["item"] == broll[bi]["item"]), None)
        else:
            m = to_src((s + z) / 2, doc)
            ot = to_tl(m, od) if m is not None else None
            if ot is not None:
                src = next((o for o in old["shots"] if o["br"] is None and o["t0"] <= ot <= o["t1"]), None)
        if src:
            sh.update(zoom=src["zoom"], k0=src["k0"], k1=src["k1"])
        shots.append(sh)

    # ---- Omar's markers ----
    notes = []
    for mk in seq.iter("marker"):
        name, com = mk.findtext("name") or "", mk.findtext("comment") or ""
        if name.startswith(OWN_MARKERS):
            continue
        notes.append({"t": r3(int(mk.findtext("in")) / fps), "name": name, "comment": com})

    new = dict(old)
    new.update(doc=doc, broll=broll, caps=caps, shots=shots, keep=keep, outro=outro, dur=dur)
    if notes:
        new["notes"] = notes
    json.dump(new, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("written:", a.out)
    print("speaker pieces %d (was %d) | b-roll %d (was %d) | captions %d (was %d) | outro %.2f (was %.2f) | dur %.2f (was %.2f)"
          % (len(doc), len(od), len(broll), len(old["broll"]), len(caps), len(old.get("caps", [])),
             outro, old["outro"], dur, old["dur"]))
    for p, k in new_items.items():
        print("NEW FILE -> add to FILES in the build .jsx:  %s: \"%s\"" % (k, os.path.relpath(p, a.root).replace(os.sep, "/")))
    for r in report:
        print("NOTE:", r)
    for n in notes:
        print("OMAR @ %.2f s: %s %s" % (n["t"], n["name"], n["comment"]))


if __name__ == "__main__":
    main()
