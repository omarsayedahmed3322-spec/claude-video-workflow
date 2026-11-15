"""Score speech-timing methods against a hand-checked captions.json (03 "Captions as a HyperFrames overlay", step 1).
usage: python -I -X utf8 timing_score.py <reference captions.json> <method.json> [<method.json> ...]
  reference = the reel's final captions.json after the word times were checked/fixed ([{"t", "w": [word starts], ...}])
  method    = whisper / stable-ts JSON ({"segments": [{"words": [{"word","start","end"}]}]}),
              or {"words": [{"w","s","e"}]}, or a plain list of {"word","start","end"} (Gemini/agy, faster-whisper...)
Words are matched by letters (tashkeel, punctuation and alef/ta-marbuta forms ignored), so spelling mistakes still map.
Prints per method: mean / median |error| of word starts, of chunk-first words (mostly phrase starts after a pause), worst word."""
import sys, json, re, difflib, os


def norm(s):
    s = re.sub("[ً-ْٰـ]", "", s)  # tashkeel, superscript alef, tatweel
    s = re.sub("[أإآ]", "ا", s).replace("ة", "ه").replace("ى", "ي")
    return re.sub("[^ء-ي]", "", s)  # Arabic letters only


def load_method(p):
    d = json.load(open(p, encoding="utf-8"))
    if isinstance(d, dict) and "segments" in d:
        d = [w for s in d["segments"] for w in s.get("words", [])]
    elif isinstance(d, dict) and "words" in d:
        d = d["words"]
    return [(w.get("word", w.get("w", "")), float(w.get("start", w.get("s"))), float(w.get("end", w.get("e", 0)))) for w in d]


def main(ref_path, methods):
    ref = json.load(open(ref_path, encoding="utf-8"))
    rw, first = [], set()  # (word, start)
    for c in ref:
        ws = c["t"].split()
        if len(ws) != len(c["w"]):
            sys.exit(f"reference chunk has {len(ws)} words but {len(c['w'])} starts: {c['t']}")
        first.add(len(rw))
        rw += list(zip(ws, c["w"]))
    sc = [(ch, i) for i, (w, _) in enumerate(rw) for ch in norm(w)]
    print(f"reference: {len(rw)} words, {len(first)} chunks ({os.path.basename(ref_path)})")
    for p in methods:
        tw = load_method(p)
        tc = [(ch, j) for j, (w, _, _) in enumerate(tw) for ch in norm(w)]
        sm = difflib.SequenceMatcher(None, [c for c, _ in sc], [c for c, _ in tc], autojunk=False)
        hit = {}
        for a, b, n in sm.get_matching_blocks():
            for k in range(n):
                hit.setdefault(sc[a + k][1], []).append(tc[b + k][1])
        errs = [((tw[min(hit[i])][1] - rw[i][1]) * 1000, i) for i in range(len(rw)) if i in hit]
        if not errs:
            print(f"\n{os.path.basename(p)}: no words matched"); continue
        def stats(xs):
            a = sorted(abs(x) for x in xs)
            return f"mean {sum(a) / len(a):.0f} ms, median {a[len(a) // 2]:.0f} ms (n={len(a)})" if a else "n=0"
        e_all = [e for e, _ in errs]; e_first = [e for e, i in errs if i in first]
        worst = max(errs, key=lambda x: abs(x[0]))
        print(f"\n{os.path.basename(p)}: matched {len(errs)}/{len(rw)} words")
        print(f"  all word starts : {stats(e_all)}")
        print(f"  chunk starts    : {stats(e_first)}, signed mean {sum(e_first) / max(1, len(e_first)):+.0f} ms")
        print(f"  worst           : «{rw[worst[1]][0]}» ref {rw[worst[1]][1]:.2f} {worst[0]:+.0f} ms")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
