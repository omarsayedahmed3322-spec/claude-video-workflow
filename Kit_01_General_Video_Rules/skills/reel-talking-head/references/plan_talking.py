"""Talking-head cut plan (skill reel-talking-head). Copied on 2026-11-12 from CLA R1
(AG2/CLA/reel-01/scripts/plan_CLA_R1.py, the v19 build of 2026-11-10). Everything that belongs to one reel sits in
SETTINGS; the logic under it is the CLA logic unchanged (only the names of the constants changed).
Silences: ffmpeg silencedetect=noise=-38dB:d=0.28 on the raw speech. Word times: whisper small --word_timestamps
(a phrase start = the end of the silence before it, never whisper's first word).
Writes <OUT>/<NAME>.json (read by mix_talking.py) and <OUT>/<NAME>.jsx (included by build_talking.jsx).
Usage: python -I plan_talking.py [out_dir]      (out_dir replaces OUT, e.g. a temp folder for a test)"""
import json
import sys

# ============================ SETTINGS (CLA R1 v19 values) ============================
OUT = "D:/Montage-02/Clients/AG2/CLA/reel-01/scripts/"
NAME = "edl_CLA_R1"
FPS = 25
T0 = 0.0                        # timeline second where the speaker starts (CLA v10: no intro, the reel opens on him)
SRC0, SRC1 = 3.70, 75.13        # source in/out: 0.10 s before his first word (3.80) / end of the last speech
LAST_WORD = 74.98               # source end of the last word (the outro starts OUTRO_PAD after it)
# silences to remove (source seconds). The first one is not a silence: the client's own re-cut joins
# «At CLA, | we believed…» (keeps 3.70–4.56, resumes 7.86 in the breath before «We» at 8.10)
SIL = [(4.50, 7.96), (13.949937, 14.384313), (20.562646, 21.342396), (24.718229, 25.374125), (26.883729, 27.18575),
       (28.417292, 29.111125), (31.602125, 32.489937), (35.489771, 36.204417), (37.560146, 38.118979),
       (38.711854, 39.414979), (44.428729, 45.102688), (45.639417, 46.217917), (49.742979, 50.61225),
       (51.346125, 51.637375), (55.431, 56.166438), (56.926812, 57.270667), (60.406729, 60.886625),
       (61.752792, 62.461042), (71.88025, 72.308437)]
PRE, POST = 0.10, 0.06          # keep 0.06 s after the last word and 0.10 s before the next
DOC_TAIL = 0.4                  # the last speaker layer runs this long past the last speech
# framing per topic: (src from, src to, mode, scale from, scale to[, src where it becomes visible]).
# push = slow eased zoom, hold = static. CLA v16: every framing is the full wide shot (100), no punch-ins.
TOPICS = [(SRC0, 12.75, "push", 100, 105), (12.75, 20.6, "hold", 100, 100), (20.6, 28.4, "push", 106, 100),
          (28.4, 44.43, "push", 100, 105, 38.6), (44.43, 71.9, "hold", 100, 100), (71.9, SRC1, "push", 100, 103)]
# b-roll: (src from, src to, item key in build_talking.jsx FILES, clip in-point[, True = hard cut on a sentence join])
# product shots cut in on the spoken name (word starts from the silence ends: 45.10 / 50.61 / 56.17)
BROLL = [(7.86, 10.40, "e27s", 3.0, True), (17.42, 20.56, "perf", 0.2), (25.0, 28.34, "e25", 2.0),
         (28.34, 31.66, "e46", 4.0), (31.66, 36.0, "e43", 0.4), (36.0, 38.6, "trio", 2.4),
         (44.43, 50.51, "aClar", 0.3), (50.51, 56.07, "aPerf", 0.0), (56.07, 61.75, "aBeau", 0.0),
         (65.40, 68.58, "trio", 0.0), (68.58, 71.95, "beauty", 1.0)]
SNAP_EDGE = 0.4                 # a b-roll edge this close to a speaker cut moves onto the cut
FLASH_IN = "trio"               # the one light sweep: into this item («That idea became CLA»)
ZOOM_OUT = "aBeau"              # the zoom-through: back to the speaker after this item (after the three products)
FIRST_CUT_ON_JOIN = True        # v19: the first b-roll starts exactly where the first speaker layer ends (plain cut)
CAPS = [(3.80, 12.62, "في يوغن، آمنّا أن الاهتمام بنفسك\rيجب أن يكون شيئًا تستمتع به"),
        (13.12, 16.48, "وفي يوم، بدأنا نسأل أنفسنا"),
        (17.42, 20.36, "لماذا لا تكون الشوكولاتة\rجزءًا من هذه التجربة؟"),
        (21.14, 24.48, "لم نُرِد أن نصنع\rمجرد شوكولاتة أخرى"),
        (25.12, 28.30, "أردنا أن نجمع بين عالمين"),
        (28.34, 31.62, "متعة تناول ما تحبّه"),
        (31.66, 35.26, "ومكوّنات اخترناها بعناية"),
        (36.08, 38.56, "ومن هذه الفكرة وُلدت CLA"),
        (39.26, 41.76, "ابتكرنا ثلاثة أنواع من الشوكولاتة"),
        (41.80, 44.34, "كلٌّ منها مستوحى\rمن جانب مختلف من حياتنا"),
        (45.00, 49.74, "Clarity، لتلك اللحظات\rالتي تشعر فيها أن الحياة أكبر منك"),
        (50.51, 55.43, "Performance، مستوحاة من الحركة\rوالرغبة في التطوّر باستمرار"),
        (56.07, 61.68, "و Beauty، مستوحاة من طريقة\rاهتمامنا بأنفسنا، من الداخل"),
        (62.38, 65.02, "بدأت CLA من قناعة بسيطة"),
        (65.56, 68.56, "أن العناية بنفسك\rوالاستمتاع بالحياة"),
        (68.60, 71.76, "لا يجب أن يكونا\rشيئين مختلفين"),
        (72.20, 74.98, "وهذا ما أردنا أن نشاركه معكم")]
CAP_TAIL, CAP_GAP = 0.12, 0.04  # a line leaves 0.12 s after its last word, and 0.04 s before the next line at the latest
OUTRO_PAD, OUTRO_LEN = 0.45, 4.6
MIN_ZOOM_SHOT = 1.5             # shots shorter than this stay static
RATE = 6 / 3.16                 # approved slow-zoom speed, % per second (106→100 over 3.16 s ≈ 1.9 %/s)
ZOOM_LONGEST = True             # the longest speaker stretch zooms in at RATE
FORCE_BROLL = [("trio", 40, (106, 100))]   # (item, only after this timeline second, (scale from, to)): kept zoom-out
# ========================================================================================

if len(sys.argv) > 1:
    OUT = sys.argv[1].rstrip("/\\") + "/"

keep, a = [], SRC0
for s, e in SIL:
    keep.append([round(a, 3), round(s + POST, 3)])
    a = e - PRE
keep.append([round(a, 3), SRC1])


def tl(src):
    """source time -> timeline time (inside a removed gap = the cut point)"""
    t = T0
    for a, b in keep:
        if src <= a:
            return round(t, 3)
        if src <= b:
            return round(t + src - a, 3)
        t += b - a
    return round(t, 3)


# speaker layers: one per kept interval, frames snapped to FPS
F = 1 / float(FPS)
snap = lambda x: round(round(x / F) * F, 3)
doc = []
for a, b in keep:
    t0, t1 = snap(tl(a)), snap(tl(b))
    doc.append({"t0": t0, "t1": t1, "src": round(a - (tl(a) - t0), 3)})
doc[-1]["t1"] = snap(tl(SRC1) + DOC_TAIL)

# framing per topic (source ranges). Topics that start under b-roll begin where the b-roll begins,
# so the new framing is already set when the b-roll leaves.
tp = []
for t in TOPICS:
    vis = t[5] if len(t) > 5 else t[0]
    tp.append({"a": tl(t[0]), "b": tl(t[1]), "mode": t[2], "k0": t[3], "k1": t[4], "va": tl(vis)})

# Times inside a removed gap map to the cut point.
br = [{"t0": snap(tl(b[0])), "t1": snap(tl(b[1])), "item": b[2], "src": b[3], "hard": len(b) > 4} for b in BROLL]
# a b-roll edge a few frames off a speaker cut flashes the old framing for 1–5 frames (Omar, CLA v10): move the edge onto the cut
for b in br:
    for d in doc[1:]:
        for k in ("t0", "t1"):
            if 0 < abs(d["t0"] - b[k]) <= SNAP_EDGE:
                b[k] = d["t0"]
    b["oncut"] = any(abs(d["t0"] - b["t1"]) < 0.01 for d in doc[1:])   # build fades it out over the new framing

# CLA v15 (Omar on v14): not every cut is a transition. zoom = zoom-through (scale + blur), flash = warm light
# sweep, once. Every other edge is a plain cut. (tin = into the b-roll, tout = back to the speaker)
for b in br:
    b["tin"], b["tout"] = "cut", "cut"
# v17 (Omar): no transition on the first cut — a transition one second in hurts the eye
next(b for b in br if b["item"] == FLASH_IN)["tin"] = "flash"
next(b for b in br if b["item"] == ZOOM_OUT)["tout"] = "zoom"
# v19 (Omar: «اعمل كات عادي خالص كلاسيك»): a plain cut to the b-roll right on the speech join — no freeze, no dissolve
if FIRST_CUT_ON_JOIN:
    br[0]["t0"] = doc[0]["t1"]

cp = []
for i, (a, b, txt) in enumerate(CAPS):
    t0, t1 = tl(a), tl(b) + CAP_TAIL
    if i < len(CAPS) - 1:
        t1 = min(t1, tl(CAPS[i + 1][0]) - CAP_GAP)
    cp.append({"t0": round(t0, 3), "t1": round(t1, 3), "txt": txt})

# v15 shots (Omar): a slow zoom runs exactly from the start to the end of the shot on screen, and two shots in a row
# never both zoom. A shot = a b-roll clip, or a speaker stretch between b-rolls.
end_speech = tl(LAST_WORD)
outro0 = snap(end_speech + OUTRO_PAD)
edges = sorted({0.0, outro0} | {b["t0"] for b in br} | {b["t1"] for b in br})
shots = []
for a, z in zip(edges, edges[1:]):
    bi = next((i for i, b in enumerate(br) if b["t0"] <= a + 0.01 and b["t1"] >= z - 0.01), None)
    if bi is not None:
        shots.append({"t0": a, "t1": z, "br": bi})
        continue
    cuts = [a, z]          # v16: no punch-ins any more, so a speaker stretch is one shot even across a topic change
    for c0, c1 in zip(cuts, cuts[1:]):
        shots.append({"t0": c0, "t1": c1, "br": None})
# Omar (v15→v16): keep the slow zoom-out on the trio near the end, and give the longest speaker stretch a zoom-in at
# that same speed. Forced shots win; the rest alternate around them.
force = {}
if ZOOM_LONGEST:
    longest = max((s for s in shots if s["br"] is None), key=lambda s: s["t1"] - s["t0"])
    force[id(longest)] = (100, round(100 + RATE * (longest["t1"] - longest["t0"]), 1))
for s in shots:
    for item, after, ks in FORCE_BROLL:
        if s["br"] is not None and br[s["br"]]["item"] == item and s["t0"] > after:
            force[id(s)] = ks
prev, flip = False, False
for i, s in enumerate(shots):
    nxt = shots[i + 1] if i + 1 < len(shots) else None
    s["zoom"] = id(s) in force or ((s["t1"] - s["t0"] >= MIN_ZOOM_SHOT) and not prev and not (nxt and id(nxt) in force))
    prev = s["zoom"]
    if id(s) in force:
        s["k0"], s["k1"] = force[id(s)]
        continue
    if s["br"] is None:                                  # speaker: the topic's framing; push topics keep their direction
        t = [x for x in tp if x["a"] <= s["t0"] + 0.01][-1]
        if t["mode"] == "push":
            s["k0"], s["k1"] = (t["k0"], t["k1"]) if s["zoom"] else (100, 100)   # static = full wide shot
            if s["zoom"] and abs(t["k1"] - t["k0"]) < 4:
                s["k1"] = t["k0"] + (5 if t["k1"] >= t["k0"] else -5)
        else:
            s["k0"], s["k1"] = t["k0"], (t["k0"] + 5 if s["zoom"] else t["k0"])
    else:                                                # b-roll: % of its cover scale, in and out alternate
        flip = not flip if s["zoom"] else flip
        s["k0"], s["k1"] = (100, 106) if not s["zoom"] else ((100, 106) if flip else (106, 100))
        if not s["zoom"]:
            s["k1"] = 100

outro = snap(end_speech + OUTRO_PAD)
edl = {"t0": T0, "shots": shots, "keep": keep, "doc": doc, "topics": tp, "broll": br, "caps": cp, "outro": outro,
       "dur": snap(outro + OUTRO_LEN)}
json.dump(edl, open(OUT + NAME + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
with open(OUT + NAME + ".jsx", "w", encoding="utf-8") as f:
    f.write("var EDL = " + json.dumps(edl, ensure_ascii=False) + ";\n")
print("doc layers", len(doc), "outro", outro, "dur", edl["dur"], "removed", round((SRC1 - SRC0) - sum(b - a for a, b in keep), 2))
