"""Word timecodes on the GPU (RTX 5060 Ti): faster-whisper large-v3-turbo, float16.
Writes the same JSON shape as `whisper --output_format json` (segments[].words[]), so
whisper_to_captions.py and timing_score.py read it as is.

  python -X utf8 whisper_gpu.py VO.mp3 VO.json [--language ar] [--model large-v3-turbo]

Timecodes only: the spoken text comes from Gemini/agy (free-llm-delegate), fix the words by hand.
Why this file exists (2026-11-24): torch here is the CPU build, so `whisper` and `stable-ts` never
see the GPU, and faster-whisper on `cuda` died on "cublas64_12.dll is not found". The fix was
`pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`; their DLL folders are not on PATH, so this
script adds them before ctranslate2 loads. If the GPU fails it says why and falls back to CPU int8.
Measured: 91 s of English speech in 10.4 s (model load 4.6 s).
"""
import argparse, glob, json, os, site, sys, time

sys.stdout.reconfigure(encoding="utf-8")
for sp in site.getsitepackages() + [site.getusersitepackages()]:
    for d in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
        os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
        os.add_dll_directory(d)

from faster_whisper import WhisperModel

ap = argparse.ArgumentParser()
ap.add_argument("audio"); ap.add_argument("out")
ap.add_argument("--language", default=None, help="leave empty until you know it (00_quick_rules)")
ap.add_argument("--model", default="large-v3-turbo")
a = ap.parse_args()


def run(device, compute):
    t0 = time.time()
    m = WhisperModel(a.model, device=device, compute_type=compute)
    segs, info = m.transcribe(a.audio, language=a.language, word_timestamps=True)
    out = []
    for i, s in enumerate(segs):
        out.append({"id": i, "start": round(s.start, 3), "end": round(s.end, 3), "text": s.text,
                    "words": [{"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3),
                               "probability": round(w.probability, 3)} for w in (s.words or [])]})
        print("%.2f-%.2f %s" % (s.start, s.end, s.text), flush=True)
    return out, info, time.time() - t0


try:
    segments, info, took = run("cuda", "float16")
    device = "cuda"
except Exception as e:  # missing DLL, driver, out of memory
    print("GPU failed (%s: %s) -> CPU int8" % (type(e).__name__, str(e)[:200]), flush=True)
    segments, info, took = run("cpu", "int8")
    device = "cpu"

json.dump({"text": "".join(s["text"] for s in segments), "segments": segments, "language": info.language},
          open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("OK device=%s model=%s lang=%s words=%d audio=%.1fs took=%.1fs -> %s" % (
    device, a.model, info.language, sum(len(s["words"]) for s in segments), info.duration, took, a.out))
