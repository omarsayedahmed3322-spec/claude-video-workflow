"""Whisper word timings -> captions.json chunks (the format make_caption_overlay.py and the AE caption builds read).
1) With an approved script (better phrase starts, script spelling; CLF R2 test 2026-11-14):
     stable-ts VO.mp3 --align script.txt --language ar --model small -o <dir>/VO.json
   No script:
     whisper VO.mp3 --language ar --model small --word_timestamps True --output_format json --output_dir <dir>
2) python whisper_to_captions.py <dir>/VO.json captions.json [--max-words 4] [--gap 0.35]
A chunk breaks on punctuation (، . ! ? …), on a pause longer than --gap, or at --max-words.
Whisper's spelling can differ from the script: fix the "t" texts by hand against the approved script, keep the times.
"""
import argparse, json

ap = argparse.ArgumentParser()
ap.add_argument("whisper_json"); ap.add_argument("out")
ap.add_argument("--max-words", type=int, default=4)
ap.add_argument("--gap", type=float, default=0.35)
a = ap.parse_args()

words = [w for s in json.load(open(a.whisper_json, encoding="utf-8"))["segments"] for w in s.get("words", [])]
chunks, cur = [], []
for i, w in enumerate(words):
    cur.append(w)
    txt = w["word"].strip()
    nxt = words[i + 1] if i + 1 < len(words) else None
    if (txt[-1:] in "،,.!?؟…" or len(cur) >= a.max_words or nxt is None or nxt["start"] - w["end"] > a.gap):
        chunks.append(cur); cur = []
out = []
for i, c in enumerate(chunks):
    out.append({"t": " ".join(w["word"].strip() for w in c), "w": [round(w["start"], 3) for w in c],
                "in": round(max(0.0, c[0]["start"] - 0.05), 3)})
for i, c in enumerate(out):
    c["out"] = round(out[i + 1]["w"][0] - 0.05, 3) if i + 1 < len(out) else round(chunks[i][-1]["end"] + 0.4, 3)
json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
for c in out: print(c["in"], c["out"], c["t"])
