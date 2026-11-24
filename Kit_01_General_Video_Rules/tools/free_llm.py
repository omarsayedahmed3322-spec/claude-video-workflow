"""Send a task to a free LLM API (list: github.com/mnfst/awesome-free-llm-apis) so Claude saves its own limits.
Keys live OUTSIDE this repo: <parent of Claude-Workflow>\\keys\\free-llm.env (override with env FREE_LLM_ENV). Never commit keys.
Used by the skill free-llm-delegate. Prints only the answer on stdout (one "[provider/model]" line on stderr).

  python free_llm.py ask "prompt" [--task fast|long] [--provider groq] [--model ID] [--file a.txt ...] [--out res.md]
  python free_llm.py ask --prompt-file brief.md --file ref.mp4      # media: paid Gemini key if set, else agy
  python free_llm.py ask --prompt-file p.txt --file reel.mp4 --fps 10 --thinking medium [--start 12 --end 18]   # paid key
  python free_llm.py ask --prompt-file p.txt --file reel.mp4 --jpeg-sheets        # agy: frames as JPEG sheets + sound
  python free_llm.py budget                                         # paid key: month spend vs cap
  python free_llm.py check                                          # which providers answer right now
  python free_llm.py models groq                                    # model ids a provider serves
  python free_llm.py ask "..." --provider agy --workdir "D:\some\folder"   # agy works inside that folder only

- Falls through the task's provider order on missing key / 401 / 429 / 5xx / timeout.
- Text files passed with --file are appended to the prompt; video/audio/image files are uploaded to Gemini,
  used once, then deleted from Google's side.
"""
import argparse, glob, json, mimetypes, os, shutil, subprocess, sys, tempfile, threading, time
import requests

WF = os.environ.get("CLAUDE_WORKFLOW") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ENV_PATH = os.environ.get("FREE_LLM_ENV") or os.path.join(os.path.dirname(WF), "keys", "free-llm.env")   # next to <Claude-Workflow>: <parent>\keys
AGY_STATE_DIR = os.path.dirname(WF)
AGY_LIVE_LOG = os.path.join(AGY_STATE_DIR, "_agy_live.log")
AGY_LIVE_STATE = os.path.join(AGY_STATE_DIR, "_agy_live_state.json")
AGY_META_FILE = os.path.join(AGY_STATE_DIR, "_agy_meta.json")
GEMINI = "https://generativelanguage.googleapis.com"

# name: (base_url, key_env, default_models, works_without_key) — comma-separated models are tried in order (busy -> next)
PROVIDERS = {
    "codex":      ("codex", "", "", True),  # friend's ChatGPT Plus: --provider codex only (debate / hard jobs), capped by codex_gate()
    "agy":        ("antigravity", "", "gemini-4-hydrogen-high,gemini-4-hydrogen-xhigh,gemini-4-hydrogen-medium", True),  # Omar 2026-11-17: order high -> xhigh -> medium (last resort), never low; 2026-11-15: high is the default for every review; 2026-11-12: Gemini 4 Hydrogen replaced 3.8 Flash;  # Antigravity CLI, Omar's Google AI Pro login (Gemini CLI was closed to personal accounts 2026-11-06)
    "gemini":     (GEMINI + "/v1beta/openai", "GEMINI_API_KEY", "gemini-3.5-flash,gemini-flash-latest,gemini-flash-lite-latest", False),  # flash-latest hung 4/4 on 2026-11-06
    "groq":       ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b", False),
    "nvidia":     ("https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY", "nvidia/nemotron-3.5-lightning-30b-a3b,google/gemma-4-31b-it", False),
    "mistral":    ("https://api.mistral.ai/v1", "MISTRAL_API_KEY", "mistral-medium-latest", False),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "openrouter/free", False),
    "cloudflare": ("https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1",
                   "CLOUDFLARE_API_TOKEN", "@cf/meta/llama-3.3-70b-instruct-fp8-fast", False),
    "zai":        ("https://api.z.ai/api/paas/v4", "ZAI_API_KEY", "glm-4.7-flash", False),
    "gonka":      ("https://proxy.gonkabroker.com/v1", "GONKA_API_KEY", "deepseek-ai/DeepSeek-V4-Flash-0731,MiniMaxAI/MiniMax-M2.7", False),
    "llm7":     ("https://api.llm7.io/v1", "LLM7_API_KEY", "gpt-oss:20b", True),
    "kilo":       ("https://api.kilo.ai/api/gateway", "", "kilo-auto/free", True),
    "ovh":        ("https://oai.endpoints.kepler.ai.cloud.ovh.net/v1", "", "gpt-oss-120b", True),
}
# fast = short jobs in bulk (translate, split captions, prompt variants); long = big inputs (transcripts, logs)
ORDER = {
    "fast": ["groq", "nvidia", "mistral", "gemini", "cloudflare", "zai", "openrouter", "gonka", "llm7", "kilo", "ovh"],
    "long": ["gemini", "agy", "mistral", "nvidia", "groq", "zai", "gonka", "openrouter", "kilo", "llm7", "ovh"],
}
MEDIA_PREFIX = ("video/", "audio/", "image/")
# Video on agy starts with neon-high (Omar 2026-11-19). Audio-only jobs keep PROVIDERS["agy"] (hydrogen: Arabic dialect text).
AGY_VIDEO_MODELS = "gemini-4-neon-high,gemini-4-hydrogen-high"
# Sheets on agy: hydrogen-high first. Same reel, same prompt, 13 sheets: hydrogen 192 s; neon ran into the 7-minute stop (AG1 R7, 2026-11-22).
AGY_SHEETS_MODELS = "gemini-4-hydrogen-high,gemini-4-neon-high"
AGY_SHEETS_TIMEOUT = 600   # s. The 7-minute stop is our own --print-timeout (agy itself has none)
GEMINI_MEDIA_MODEL = "gemini-4-hydrogen"   # media on the Gemini API (the text list in PROVIDERS["gemini"] is separate)
# USD per 1M tokens (input, output incl. thinking): Google's pricing page, read 2026-11-22. Unknown model -> hydrogen's price.
GEMINI_PRICES = {"gemini-4-hydrogen": (1.50, 7.50), "gemini-4-neon": (3.00, 15.00), "gemini-4-argon": (2.00, 10.00),
                 "gemini-3.8-flash": (0.75, 3.75), "gemini-3.5-flash-lite": (0.30, 2.50)}
BUDGET_FILE = os.path.join(AGY_STATE_DIR, "_gemini_api_budget.json")
HISTORY_DIR = os.path.join(AGY_STATE_DIR, "_gemini_api_history")
BUDGET_DEFAULT_USD = 9.00   # safety cap per month when GEMINI_BUDGET_MONTHLY_USD is not set in free-llm.env
RETRYABLE = {401, 402, 403, 404, 408, 410, 429, 500, 502, 503, 504}


def load_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():  # real env vars win
        if k.endswith(("_API_KEY", "_API_TOKEN", "_ACCOUNT_ID", "_MODEL", "_BUDGET_MONTHLY_USD")):
            env[k] = v
    return env


def endpoint(name, env):
    if name == "codex":
        return ("codex", "", "") if shutil.which("codex") else None
    if name == "agy":
        exe = shutil.which("agy") or os.path.expanduser(r"~\.gemini\bin\agy.exe")
        return (exe, "", env.get("AGY_MODEL") or PROVIDERS["agy"][2]) if os.path.exists(exe) else None
    base, key_env, model, anon = PROVIDERS[name]
    key = env.get(key_env, "") if key_env else ""
    if not key and not anon:
        return None
    if "{CLOUDFLARE_ACCOUNT_ID}" in base:
        if not env.get("CLOUDFLARE_ACCOUNT_ID"):
            return None
        base = base.replace("{CLOUDFLARE_ACCOUNT_ID}", env["CLOUDFLARE_ACCOUNT_ID"])
    return base, key, env.get(name.upper() + "_MODEL") or model


class Skip(Exception):
    pass


def chat(name, env, prompt, system=None, model=None, max_tokens=4096, timeout=120, workdir=None):
    ep = endpoint(name, env)
    if not ep:
        raise Skip("no key")
    base, key, default_model = ep
    if name == "codex":
        return codex_run(prompt if not system else system + "\n\n" + prompt, workdir, timeout=max(timeout, 600), model=model)
    if name == "agy":
        return antigravity(base, prompt, system, model or default_model, timeout, workdir)
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    err = "no model"
    for m in (model or default_model).split(","):
        r = requests.post(base + "/chat/completions", headers=headers, timeout=timeout,
                          json={"model": m, "messages": msgs, "max_tokens": max_tokens})
        if r.status_code in RETRYABLE:
            err = "HTTP %d %s" % (r.status_code, r.text[:160].replace("\n", " "))
            continue
        r.raise_for_status()
        text = r.json()["choices"][0]["message"].get("content") or ""
        if text.strip():
            return text, m
        err = "empty answer"
    raise Skip(err)


def _t12(with_date=False):
    lt = time.localtime()
    suf = "ص" if lt.tm_hour < 12 else "م"
    h12 = lt.tm_hour % 12 or 12
    t = "%02d:%02d:%02d %s" % (h12, lt.tm_min, lt.tm_sec, suf)
    return ("%04d-%02d-%02d · %s" % (lt.tm_year, lt.tm_mon, lt.tm_mday, t)) if with_date else t


def _agy_write_log(text, reset_if_big=False):
    try:
        if reset_if_big and os.path.exists(AGY_LIVE_LOG) and os.path.getsize(AGY_LIVE_LOG) > 5 * 1024 * 1024:
            with open(AGY_LIVE_LOG, "rb") as f:
                f.seek(-512 * 1024, os.SEEK_END)
                tail = f.read()
            with open(AGY_LIVE_LOG, "wb") as f:
                f.write(tail)
        with open(AGY_LIVE_LOG, "a", encoding="utf-8") as f:
            f.write(text)
            f.flush()
    except Exception:
        pass


def _agy_save_state(state):
    try:
        state["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        tmp_p = "%s.%d.tmp" % (AGY_LIVE_STATE, os.getpid())
        with open(tmp_p, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_p, AGY_LIVE_STATE)
    except Exception:
        pass


def _agy_record_meta(conv_id, info):
    if not conv_id:
        return
    try:
        meta = {}
        if os.path.exists(AGY_META_FILE):
            with open(AGY_META_FILE, encoding="utf-8") as f:
                meta = json.load(f)
        meta[conv_id] = info
        if len(meta) > 300:
            keys = sorted(meta.keys(), key=lambda k: meta[k].get("started_at", ""))[-300:]
            meta = {k: meta[k] for k in keys}
        tmp_p = "%s.%d.tmp" % (AGY_META_FILE, os.getpid())
        with open(tmp_p, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        os.replace(tmp_p, AGY_META_FILE)
    except Exception:
        pass


def antigravity(exe, prompt, system=None, model="", timeout=120, workdir=None, attach=()):
    # Antigravity CLI (agy) on Omar's Google account, full permissions (Omar's call, 2026-11-06): it can run commands
    # and edit files, so it runs in a fresh temp folder unless --workdir names the one work folder it may touch.
    # Runs in a fresh temp folder; a long prompt is saved there as task.md (Windows caps a command line at ~32k chars).
    # Streams live progress via --output-format stream-json to _agy_live.log and _agy_live_state.json for Omar's monitor.
    text = ((system + "\n\n") if system else "") + prompt
    orig_files = [os.path.basename(f) for f in attach]
    orig_paths = [os.path.abspath(f) for f in attach]
    with tempfile.TemporaryDirectory(prefix="agy_", ignore_cleanup_errors=True) as tmp:   # agy can still hold the folder on exit (2026-11-13)
        d = workdir or tmp
        ask = text
        mentions = []
        for i, f in enumerate(attach):  # @file puts media straight into its context. Video comes in as frames only,
            f = light_proxy(f, tmp)  # so the soundtrack is also handed over as its own mp3
            ext = os.path.splitext(f)[1].lower()
            dst = os.path.join(tmp, "media%d%s" % (i, ext))
            shutil.copy(f, dst)
            mentions.append(dst)
            if mimetypes.guess_type(f)[0].startswith("video/") and shutil.which("ffmpeg"):
                mp3 = os.path.join(tmp, "media%d_audio.mp3" % i)
                if subprocess.run(["ffmpeg", "-loglevel", "error", "-i", dst, "-vn", "-c:a", "libmp3lame", "-y", mp3]).returncode == 0:
                    mentions.append(mp3)
        if mentions:
            d = tmp
        if len(text) > 20000:  # works since the datacloud_telemetry hook (broken on Windows) was disabled 2026-11-06
            with open(os.path.join(tmp, "task.md"), "w", encoding="utf-8") as f:
                f.write(text)
            ask = "Read %s and do exactly what it asks. Reply with the answer only." % os.path.join(tmp, "task.md")
        if mentions:  # "@file" in -p mode attaches nothing (media=0 in its log): the agent then ran ffmpeg/whisper itself
            # and hit the 7-min timeout. Naming view_file and banning commands makes it load the media itself (2026-11-06)
            ask = ("Open each of these files with your view_file tool so you see/hear them directly: %s. "
                   "The _audio.mp3 file, if any, is the video's soundtrack. Do NOT run any commands, scripts or other "
                   "tools. Then do the task below and reply with the answer only.\n\n" % ", ".join(mentions)) + ask
        err = "no model"
        for m in model.split(","):
            cmd = [exe, "-p", ask, "--output-format", "stream-json", "--dangerously-skip-permissions",
                   "--print-timeout", "%ds" % timeout] + (["--model", m] if m else [])
            started_str = time.strftime("%Y-%m-%d %H:%M:%S")
            t_start = time.time()
            live_state = {
                "status": "running",
                "started_at": started_str,
                "model": m or "auto",
                "conversation_id": "",
                "files": orig_files,
                "file_paths": orig_paths,
                "prompt": prompt[:8000],
                "events": [{"t": started_str, "msg": "بدء جلسة agy (%s)" % (m or "auto")}],
                "live_thinking": "",
                "live_text": "",
                "duration_seconds": 0,
                "usage": {},
                "error": "",
            }
            _agy_save_state(live_state)
            files_label = ", ".join(orig_files) if orig_files else "بدون ملفات ميديا"
            _agy_write_log(
                ("\n" + "=" * 72 + "\n"
                 "[%s] جلسة جديدة | الموديل: %s | الملفات: %s\n"
                 "البرومبت: %s\n"
                 + "-" * 72 + "\n")
                % (_t12(with_date=True), m or "auto", files_label, prompt[:600].replace("\n", " ")),
                reset_if_big=True,
            )
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace",
                    stdin=subprocess.DEVNULL, cwd=d,
                )
            except Exception as e:
                err = str(e)[:160]
                live_state["status"] = "error"
                live_state["error"] = err
                _agy_save_state(live_state)
                continue

            stderr_chunks = []
            def _read_err():
                try:
                    stderr_chunks.append(proc.stderr.read())
                except Exception:
                    pass
            t_err = threading.Thread(target=_read_err, daemon=True)
            t_err.start()

            timed_out = [False]
            def _kill_on_timeout():
                timed_out[0] = True
                try:
                    proc.kill()
                except Exception:
                    pass
            timer = threading.Timer(timeout + 30, _kill_on_timeout)
            timer.start()

            conv_id = ""
            used_model = m or "auto"
            final_response = ""
            text_deltas = []
            raw_lines = []
            streaming_text_started = False
            last_save = time.time()

            try:
                for line in proc.stdout:
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        ev = json.loads(s)
                    except Exception:
                        raw_lines.append(s)
                        continue
                    etype = ev.get("event", "")
                    if ev.get("conversation_id") and not conv_id:
                        conv_id = ev["conversation_id"]
                        live_state["conversation_id"] = conv_id
                    if etype == "init":
                        init_d = ev.get("init") or {}
                        if init_d.get("model"):
                            used_model = init_d["model"]
                            live_state["model"] = used_model
                        _agy_write_log("[%s] Conversation ID: %s | Model: %s\n" % (_t12(), conv_id, used_model))
                        _agy_record_meta(conv_id, {
                            "started_at": started_str, "model": used_model,
                            "files": orig_files, "file_paths": orig_paths,
                            "prompt_preview": prompt[:300],
                        })
                        _agy_save_state(live_state)
                    elif etype == "step_update":
                        su = ev.get("step_update") or {}
                        if su.get("conversation_id") and not conv_id:
                            conv_id = su["conversation_id"]
                            live_state["conversation_id"] = conv_id
                        st_type = su.get("step_type", "")
                        st_state = su.get("state", "")
                        st_idx = su.get("step_index", "")
                        td = su.get("text_delta") or ""
                        thd = su.get("thinking_delta") or su.get("thought_delta") or ""
                        if thd:
                            live_state["live_thinking"] += thd
                        if td:
                            if not streaming_text_started:
                                _agy_write_log("\n[%s] رد Gemini (لايف):\n" % _t12())
                                streaming_text_started = True
                            text_deltas.append(td)
                            live_state["live_text"] += td
                            _agy_write_log(td)
                        elif st_type:
                            msg = "خطوة %s: %s (%s)" % (st_idx, st_type, st_state)
                            if not live_state["events"] or live_state["events"][-1]["msg"] != msg:
                                live_state["events"].append({"t": _t12(), "msg": msg})
                                _agy_write_log("[%s] %s\n" % (_t12(), msg))
                        if su.get("usage"):
                            live_state["usage"] = su["usage"]
                        if time.time() - last_save >= 0.4:
                            live_state["duration_seconds"] = round(time.time() - t_start, 1)
                            _agy_save_state(live_state)
                            last_save = time.time()
                    elif etype == "result":
                        res = ev.get("result") or {}
                        if res.get("conversation_id"):
                            conv_id = res["conversation_id"]
                            live_state["conversation_id"] = conv_id
                        if res.get("response"):
                            final_response = res["response"]
                        if res.get("usage"):
                            live_state["usage"] = res["usage"]
                        if res.get("duration_seconds") is not None:
                            live_state["duration_seconds"] = round(float(res["duration_seconds"]), 1)
            finally:
                timer.cancel()
                proc.wait()
                t_err.join(timeout=2)

            if timed_out[0]:
                err = "timeout"
                live_state["status"] = "error"
                live_state["error"] = "timeout"
                live_state["duration_seconds"] = round(time.time() - t_start, 1)
                _agy_save_state(live_state)
                _agy_write_log("\n[%s] انتهى الوقت (timeout)\n" % _t12())
                continue

            answer = (final_response or "".join(text_deltas) or "\n".join(raw_lines)).strip()
            if proc.returncode == 0 and answer:
                live_state["status"] = "done"
                live_state["live_text"] = answer
                live_state["duration_seconds"] = live_state["duration_seconds"] or round(time.time() - t_start, 1)
                _agy_save_state(live_state)
                _agy_record_meta(conv_id, {
                    "started_at": started_str, "model": used_model,
                    "files": orig_files, "file_paths": orig_paths,
                    "prompt_preview": prompt[:300],
                    "duration_seconds": live_state["duration_seconds"],
                    "usage": live_state["usage"],
                })
                _agy_write_log(
                    "\n[%s] انتهت المراجعة بنجاح في %.1f ث | ID: %s\n"
                    % (_t12(), live_state["duration_seconds"], conv_id)
                )
                return answer, used_model
            out = ("".join(stderr_chunks) or "\n".join(raw_lines)).strip()
            err = out.splitlines()[-1][:160] if out else "exit %d" % proc.returncode
            live_state["status"] = "error"
            live_state["error"] = err
            live_state["duration_seconds"] = round(time.time() - t_start, 1)
            _agy_save_state(live_state)
            _agy_write_log("\n[%s] خطأ: %s\n" % (_t12(), err))
    raise Skip(err)


PROXY_OVER = 8e6      # bytes. Bigger videos are re-encoded before upload: Omar's upload runs ~0.3 MB/s (57 MB = 3 min)
PROCESS_CAP = 180     # s to wait for Google to finish processing an uploaded file
BUSY_WAITS = (10, 25)  # s between retries of the same model on 429/503 before moving to the next one
AGY_MEDIA_TIMEOUT = 420  # s for agy to watch/hear media (frames + mp3)
AGY_TEXT_TIMEOUT = 300   # s for an agy text job (only when Omar asks)
GEN_CAP = 150         # s per model answer; a busy model took 4.6 min on 2026-11-06 while the next one answers in ~40 s


def log(msg, t0=[time.time()]):  # progress on stderr, so a long media job never looks frozen
    print("[%5.0fs] %s" % (time.time() - t0[0], msg), file=sys.stderr, flush=True)


def _probe(p, *args):
    r = subprocess.run(["ffprobe", "-v", "error"] + list(args) + ["-of", "csv=p=0", p], capture_output=True, text=True)
    return r.stdout.strip()


def _src_fps(p):
    try:
        n, d = _probe(p, "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate").split(",")[0].split("/")
        return float(n) / float(d)
    except Exception:
        return 0.0


def light_proxy(p, tmp, target_fps=None):
    # agy (target_fps None): its reader takes 1 image per second, so 5 fps / crf 32 / 720 px loses nothing it uses.
    # Gemini API (target_fps = the fps asked in videoMetadata): the proxy must keep at least that many frames, or the
    # API is paid for duplicated frames (the old fps=5 proxy under an fps=10 request). crf 28 keeps small Arabic text.
    if not (mimetypes.guess_type(p)[0] or "").startswith("video/") or os.path.getsize(p) <= PROXY_OVER or not shutil.which("ffmpeg"):
        return p
    out = os.path.join(tmp, "proxy_" + os.path.splitext(os.path.basename(p))[0] + ".mp4")
    if target_fps:
        src = _src_fps(p)
        keep = min(target_fps, src) if src else target_fps
        vf, crf, abr = "fps=%g,scale='min(720,iw)':-2" % keep, "28", "64k"
    else:
        vf, crf, abr = "fps=5,scale='min(720,iw)':-2", "32", "48k"
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", p, "-vf", vf,
                        "-c:v", "libx264", "-crf", crf, "-preset", "veryfast", "-c:a", "aac", "-ac", "1", "-b:a", abr, out])
    if r.returncode != 0 or not os.path.exists(out):
        log("proxy failed, uploading the original")
        return p
    log("proxy %s: %.1f MB -> %.1f MB" % (os.path.basename(p), os.path.getsize(p) / 1e6, os.path.getsize(out) / 1e6))
    return out


def _budget_load():
    try:
        with open(BUDGET_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"months": {}}


def budget_cap(env):
    try:
        return float(env.get("GEMINI_BUDGET_MONTHLY_USD") or BUDGET_DEFAULT_USD)
    except ValueError:
        return BUDGET_DEFAULT_USD


def budget_month(month=None):
    m = _budget_load().get("months", {}).get(month or time.strftime("%Y-%m"), {})
    return float(m.get("usd", 0.0)), int(m.get("requests", 0))


def gemini_cost(model, in_tok, out_tok):
    pin, pout = next((v for k, v in GEMINI_PRICES.items() if model.startswith(k)), GEMINI_PRICES["gemini-4-hydrogen"])
    return (in_tok * pin + out_tok * pout) / 1e6


def budget_add(model, files, in_tok, out_tok, secs):
    cost = gemini_cost(model, in_tok, out_tok)
    b = _budget_load()
    m = b.setdefault("months", {}).setdefault(time.strftime("%Y-%m"), {"usd": 0.0, "requests": 0, "items": []})
    m["usd"] = round(m.get("usd", 0.0) + cost, 6)
    m["requests"] = m.get("requests", 0) + 1
    m.setdefault("items", []).append({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "model": model, "files": files,
                                      "in": in_tok, "out": out_tok, "sec": round(secs), "usd": round(cost, 6)})
    tmp_p = "%s.%d.tmp" % (BUDGET_FILE, os.getpid())
    with open(tmp_p, "w", encoding="utf-8") as f:
        json.dump(b, f, ensure_ascii=False, indent=1)
    os.replace(tmp_p, BUDGET_FILE)
    return cost, m["usd"]


def gemini_media(env, prompt, paths, system=None, model=None, timeout=None, fps=None, thinking="medium", media_res=None,
                 start=None, end=None, paid=False, over_budget=False):
    """Video/audio/image on the Gemini API: the model gets real video (videoMetadata.fps, up to 24) with its sound.
    paid=True uses GEMINI_PAID_API_KEY, counts every answer against the monthly cap and refuses once it is reached.
    paid=False is the free key: 20 requests a day on hydrogen, busy answers included, and Google may train on it."""
    key = env.get("GEMINI_PAID_API_KEY" if paid else "GEMINI_API_KEY")
    if not key:
        sys.exit("Media files need %s in %s" % ("GEMINI_PAID_API_KEY" if paid else "GEMINI_API_KEY", ENV_PATH))
    cap_usd = budget_cap(env)
    if paid and not over_budget and budget_month()[0] >= cap_usd:
        sys.exit("Monthly safety budget $%.2f reached ($%.2f spent) - pass --allow-over-budget only with Omar's OK"
                 % (cap_usd, budget_month()[0]))
    h = {"x-goog-api-key": key}
    model = model or env.get("GEMINI_MEDIA_MODEL") or GEMINI_MEDIA_MODEL
    timeout = timeout or (540 if thinking == "high" else 300)
    tier = "paid" if paid else "free"
    names = [os.path.basename(p) for p in paths]
    started = time.strftime("%Y-%m-%d %H:%M:%S")
    t0 = time.time()
    state = {"status": "running", "started_at": started, "model": "%s (API %s)" % (model, tier), "conversation_id": "",
             "files": names, "file_paths": [os.path.abspath(p) for p in paths], "prompt": prompt[:8000], "events": [],
             "live_thinking": "", "live_text": "", "duration_seconds": 0, "usage": {}, "error": ""}
    _agy_write_log("\n" + "=" * 72 + "\n[%s] جلسة Gemini API (%s) | الموديل: %s | الملفات: %s\nالبرومبت: %s\n%s\n"
                   % (_t12(True), tier, model, ", ".join(names), prompt[:600].replace("\n", " "), "-" * 72), reset_if_big=True)

    def step(msg):
        log(msg)
        state["events"].append({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "msg": msg})
        state["duration_seconds"] = round(time.time() - t0, 1)
        _agy_save_state(state)
        _agy_write_log("[%s] %s\n" % (_t12(), msg))

    def fail(msg):
        state["status"], state["error"] = "error", msg
        step("فشل: " + msg)
        sys.exit(msg)

    uploaded = []
    tmp = tempfile.mkdtemp(prefix="gem_")
    try:
        for p in paths:
            p = light_proxy(p, tmp, target_fps=fps or 1)
            mime = mimetypes.guess_type(p)[0] or "application/octet-stream"
            size = os.path.getsize(p)
            step("uploading %s (%.1f MB)" % (os.path.basename(p), size / 1e6))
            r = requests.post(GEMINI + "/upload/v1beta/files", timeout=60, json={"file": {"display_name": "media"}},
                              headers={**h, "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                                       "X-Goog-Upload-Header-Content-Length": str(size),
                                       "X-Goog-Upload-Header-Content-Type": mime})
            r.raise_for_status()
            with open(p, "rb") as f:
                r = requests.post(r.headers["X-Goog-Upload-URL"], data=f, timeout=600,
                                  headers={"Content-Length": str(size), "X-Goog-Upload-Offset": "0",
                                           "X-Goog-Upload-Command": "upload, finalize"})
            r.raise_for_status()
            info = r.json()["file"]
            uploaded.append(info)
            t = time.time()
            while info.get("state") == "PROCESSING":  # video needs a few seconds before it can be used
                if time.time() - t > PROCESS_CAP:
                    fail("Gemini still processing %s after %ds" % (p, PROCESS_CAP))
                time.sleep(3)
                info = requests.get(GEMINI + "/v1beta/" + info["name"], headers=h, timeout=30).json()
            if info.get("state") == "FAILED":
                fail("Gemini could not process " + p)
            info["mime"] = mime
            uploaded[-1] = info
        parts = []
        for u in uploaded:
            part = {"fileData": {"mimeType": u["mime"], "fileUri": u["uri"]}}
            if u["mime"].startswith("video/"):
                vm = {}
                if fps:
                    vm["fps"] = float(fps)
                if start is not None:
                    vm["startOffset"] = "%gs" % start
                if end is not None:
                    vm["endOffset"] = "%gs" % end
                if vm:
                    part["videoMetadata"] = vm
            parts.append(part)
        parts.append({"text": prompt})
        gen = {}
        if thinking:
            gen["thinkingConfig"] = {"thinkingLevel": thinking}
        if media_res:
            gen["mediaResolution"] = "MEDIA_RESOLUTION_" + media_res.upper()
        body = {"contents": [{"role": "user", "parts": parts}]}
        if gen:
            body["generationConfig"] = gen
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        r = None
        for m in model.split(","):
            waits = [15, 45, 90]
            while True:   # a busy answer is retried on the SAME uploaded file, never re-uploaded
                step("asking %s: fps=%s thinking=%s res=%s (up to %ds)" % (m, fps or "default", thinking, media_res or "default", timeout))
                try:
                    r = requests.post(GEMINI + "/v1beta/models/%s:generateContent" % m, headers=h, json=body, timeout=timeout)
                except requests.Timeout:
                    step("%s gave no answer in %ds" % (m, timeout))
                    r = None
                    break
                dropped = [k for k in ("mediaResolution", "thinkingConfig") if k in gen and k[:8].lower() in r.text.lower()]
                if r.status_code == 400 and dropped:
                    step("%s refused %s, asking again without it: %s" % (m, "+".join(dropped), r.text[:160].replace("\n", " ")))
                    for k in dropped:
                        gen.pop(k)
                    continue
                daily = r.status_code == 429 and "per day" in r.text.lower()
                if r.status_code not in (429, 500, 503) or daily or not waits:
                    break
                wait = waits.pop(0)
                step("%s busy (HTTP %d), same file again in %ds" % (m, r.status_code, wait))
                time.sleep(wait)
            if r is not None and (r.status_code == 200 or r.status_code not in RETRYABLE):
                model = m
                break
        if r is None:
            fail("Gemini gave no answer from " + model)
        if r.status_code != 200:
            fail("Gemini HTTP %d: %s" % (r.status_code, r.text[:400]))
        d = r.json()
        text = "".join(pt.get("text", "") for pt in (d.get("candidates") or [{}])[0].get("content", {}).get("parts", []))
        u = d.get("usageMetadata", {})
        in_tok = u.get("promptTokenCount", 0)
        out_tok = u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
        secs = time.time() - t0
        cost = gemini_cost(model, in_tok, out_tok)
        if paid:
            cost, month = budget_add(model, names, in_tok, out_tok, secs)
            line = "[gemini/paid] %.0fs | in=%.1fk out+think=%.1fk | $%.3f | month=$%.2f/$%.2f" % (
                secs, in_tok / 1e3, out_tok / 1e3, cost, month, cap_usd)
        else:
            line = "[gemini/free] %.0fs | in=%.1fk out+think=%.1fk | would cost $%.3f on the paid tier" % (
                secs, in_tok / 1e3, out_tok / 1e3, cost)
        state.update(status="done", live_text=text, usage={"input_tokens": in_tok, "output_tokens": out_tok,
                                                           "thinking_tokens": u.get("thoughtsTokenCount", 0), "usd": round(cost, 4)})
        step(line)
        _agy_write_log("\nرد Gemini:\n%s\n" % text)
        try:
            os.makedirs(HISTORY_DIR, exist_ok=True)
            hp = os.path.join(HISTORY_DIR, "%s_%s.json" % (time.strftime("%Y%m%d_%H%M%S"), os.path.splitext(names[0])[0][:40] if names else "text"))
            with open(hp, "w", encoding="utf-8") as f:
                json.dump({"started_at": started, "tier": tier, "model": model, "files": state["file_paths"], "fps": fps,
                           "thinking": thinking, "media_res": media_res, "start": start, "end": end, "seconds": round(secs),
                           "usage": u, "usd": round(cost, 6), "prompt": prompt, "answer": text}, f, ensure_ascii=False, indent=1)
        except Exception:
            pass
        return text, "%s/%s" % (tier, model)
    finally:
        for u in uploaded:
            try:
                requests.delete(GEMINI + "/v1beta/" + u["name"], headers=h, timeout=30)
            except Exception:
                pass
        shutil.rmtree(tmp, ignore_errors=True)


def sheets_review(exe, prompt, system, model, video, fps):
    """Interim eyes on agy (no paid key yet) and the fallback when the API is down. agy's reader hands the model ONE
    image per second of a video file (measured 2026-11-22: 10 of 250 frames), but reads still images in full: the
    reel goes as JPEG contact sheets, `fps` frames per second, 12 per sheet, real time stamped above every frame,
    plus the soundtrack. 250 of 250 frames read on the test clip."""
    try:
        dur = float(_probe(video, "-show_entries", "format=duration"))
    except ValueError:
        sys.exit("ffprobe could not read the length of %s" % video)
    font = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arialbd.ttf")   # no fontfile = ffmpeg segfault here (Fontconfig)
    fontarg = ("fontfile='%s':" % font.replace("\\", "/").replace(":", "\\:")) if os.path.exists(font) else ""
    tmp = tempfile.mkdtemp(prefix="sheets_")
    try:
        vf = ("fps=%g,scale=432:-2:flags=lanczos,pad=iw:ih+40:0:40:black," % fps
              + "drawtext=" + fontarg + "text='T %{pts\\:hms}':fontsize=28:fontcolor=yellow:x=8:y=6,tile=4x3:padding=6:color=white")
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", video, "-an", "-vf", vf, "-q:v", "3",
                            os.path.join(tmp, "sheet_%02d.jpg")])
        sheets = sorted(glob.glob(os.path.join(tmp, "sheet_*.jpg")))
        if r.returncode != 0 or not sheets:
            sys.exit("ffmpeg could not build the sheets")
        files = list(sheets)
        if _probe(video, "-select_streams", "a", "-show_entries", "stream=index"):
            au = os.path.join(tmp, "sound.mp3")
            if subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", video, "-vn", "-c:a", "libmp3lame", "-q:a", "5", au]).returncode == 0:
                files.append(au)
        log("sheets: %d images at %g fps, %.1f MB with sound, reel %.1f s" % (len(sheets), fps, sum(os.path.getsize(f) for f in files) / 1e6, dur))
        pre = ("HOW YOU SEE THIS REEL (set by the tool, always true):\n"
               "- The image files are contact sheets of CONSECUTIVE frames of the reel, %g frames per second, 12 per sheet, "
               "reading order left to right then top to bottom; the files are in order, the first one comes first.\n"
               "- The yellow \"T hh:mm:ss.mmm\" stamp in the black bar above each frame is that frame's REAL reel time. The "
               "bar is not part of the reel. Report every time from those stamps.\n" % fps)
        if len(files) > len(sheets):
            pre += "- The mp3 file is the reel's real soundtrack at normal speed. Times you give for sounds are approximate.\n"
        pre += ("- You cannot see what happens between two frames. Never state that something lasted, appeared or vanished "
                "at a time you have no stamped frame for; say \"not sure\" instead.\n\nTASK:\n")
        return antigravity(exe, pre + prompt, system, model, AGY_SHEETS_TIMEOUT, None, files)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- Codex (a friend's ChatGPT Plus, lent to Omar: use only for jobs that need it, never in ORDER) ----
CODEX_CAP = 80  # % of the 5-hour window. Week: 80% spread evenly over the week (+10% slack), so early in the week = less


def codex_limits():
    """Latest rate_limits Codex wrote in its own session logs (free to read, no request)."""
    root = os.path.expanduser(r"~\.codex\sessions")
    files = []
    for dp, _, fs in os.walk(root):
        files += [os.path.join(dp, f) for f in fs if f.endswith(".jsonl")]
    for f in sorted(files, key=os.path.getmtime, reverse=True)[:5]:
        with open(f, encoding="utf-8", errors="replace") as fh:
            lines = [l for l in fh if '"rate_limits"' in l]
        for line in reversed(lines):
            rl = json.loads(line).get("payload", {}).get("rate_limits") or {}
            if rl.get("primary"):
                return rl
    return None


def codex_gate():
    rl = codex_limits()
    if not rl:
        return True, "limits unknown (first run)"
    now = time.time()
    p, w = rl["primary"], rl.get("secondary") or {}
    if p["used_percent"] >= CODEX_CAP and p["resets_at"] > now:
        return False, "5h window at %d%% (cap %d%%), resets in %d min" % (p["used_percent"], CODEX_CAP, (p["resets_at"] - now) / 60)
    if w and w["resets_at"] > now:
        elapsed = 1 - (w["resets_at"] - now) / (w["window_minutes"] * 60)
        allowed = min(CODEX_CAP, CODEX_CAP * elapsed + 10)
        if w["used_percent"] >= allowed:
            return False, "week at %d%%, allowed %d%% by now, resets in %.1f days" % (w["used_percent"], allowed, (w["resets_at"] - now) / 86400)
    return True, "5h %d%% | week %s%%" % (p["used_percent"], w.get("used_percent", "?"))


def codex_run(prompt, workdir=None, images=(), timeout=600, model=None, effort=None):
    exe = shutil.which("codex")
    if not exe:
        raise Skip("codex not installed")
    ok, why = codex_gate()
    if not ok:
        raise Skip("codex paused: " + why)
    with tempfile.TemporaryDirectory(prefix="codex_") as tmp:
        last = os.path.join(tmp, "_answer.txt")
        cmd = [exe, "exec", "--skip-git-repo-check", "-s", "workspace-write", "-C", workdir or tmp, "-o", last]
        cmd += sum((["-i", i] for i in images), []) + (["-m", model] if model else []) + (["-c", "model_reasoning_effort=" + effort] if effort else []) + ["-"]
        try:
            r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        except subprocess.TimeoutExpired:
            raise Skip("codex timeout")
        text = open(last, encoding="utf-8").read().strip() if os.path.exists(last) else ""
        if not text:
            raise Skip("codex: " + ((r.stderr or r.stdout).strip().splitlines() or ["exit %d" % r.returncode])[-1][:160])
        return text, "codex"


def cmd_image(a, env):
    if a.prompt_file:
        with open(a.prompt_file, encoding="utf-8") as f:
            a.prompt = (a.prompt + "\n\n" + f.read()).strip()
    if not a.prompt:
        sys.exit("No prompt given")
    out = os.path.abspath(a.out)
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="codex_img_") as tmp:
        ask = ("Use your built-in image generation tool (image_gen, not code or SVG). %s\n"
               "Save the final image as out.png in the current folder. Reply with one short line." % a.prompt)
        try:
            text, _ = codex_run(ask, tmp, a.ref or (), model=a.model, effort=a.effort)
        except Skip as e:
            sys.exit(str(e))
        src = os.path.join(tmp, "out.png")
        if not os.path.exists(src):
            # a light driver sometimes makes the image but doesn't save it; image_gen keeps every picture here
            made = [g for g in glob.glob(os.path.join(os.path.expanduser("~"), ".codex", "generated_images", "*", "*.png"))
                    if os.path.getmtime(g) >= t0]
            if not made:
                sys.exit("codex made no image: " + text[:200])
            src = max(made, key=os.path.getmtime)
        shutil.copy(src, out)
    print("codex image -> %s | %s" % (out, codex_gate()[1]))


def cmd_budget(a, env):
    cap = budget_cap(env)
    usd, n = budget_month()
    avg = usd / n if n else 0.09   # 0.09 = one 31 s reel at 10 fps, thinking medium (measured 2026-11-22)
    print("Gemini paid key: %s | month %s: $%.2f of $%.2f in %d request(s)" % (
        "set" if env.get("GEMINI_PAID_API_KEY") else "NOT set (media goes to agy)", time.strftime("%Y-%m"), usd, cap, n))
    print("left: $%.2f = about %d review(s) at $%.3f each" % (max(0.0, cap - usd), int(max(0.0, cap - usd) / avg), avg))


def cmd_limits(a, env):
    print(codex_gate()[1] if codex_gate()[0] else "PAUSED: " + codex_gate()[1])


def is_media(p):
    return (mimetypes.guess_type(p)[0] or "").startswith(MEDIA_PREFIX)


def protected_workdir(path):
    """agy/codex run with full permissions inside --workdir. Client work and the kits themselves are refused unless
    --allow-protected-workdir is given (plan phase 9, 2026-11-20: until now this was a written rule only)."""
    p = os.path.normcase(os.path.realpath(path))
    wf = os.path.normcase(os.path.realpath(WF))
    if p == wf or p.startswith(wf + os.sep):
        return "Claude-Workflow"
    parts = [x.lower() for x in p.split(os.sep)]
    return "Clients" if "clients" in parts else None


def cmd_ask(a, env):
    if a.workdir:
        hit = protected_workdir(a.workdir)
        if hit and not a.allow_protected_workdir:
            sys.exit("Refused: --workdir %s is under %s\\ (agy/codex can edit and delete files there). Use an empty folder "
                     "or copy the files out; only if Omar asked for it, add --allow-protected-workdir." % (a.workdir, hit))
    prompt = a.prompt or ""
    if a.prompt_file:
        with open(a.prompt_file, encoding="utf-8") as f:
            prompt = (prompt + "\n\n" + f.read()).strip()
    if not prompt and not sys.stdin.isatty():
        prompt = sys.stdin.read()
    if not prompt:
        sys.exit("No prompt given")
    media = [p for p in a.file if is_media(p)]
    for p in a.file:
        if p not in media:
            with open(p, encoding="utf-8", errors="replace") as f:
                prompt += "\n\n--- %s ---\n%s" % (os.path.basename(p), f.read())
    # Omar, 2026-11-06: agy (Antigravity, gemini-3.8-flash-high on his Google AI Pro) is Claude's eyes and ears:
    # the default for every video/audio review. Text jobs (thinking, writing, summaries) go to no model unless Omar
    # asks (--provider <name> or --free). The Gemini API key runs out after a few requests. If agy fails, stop and
    # say so; never fall through silently.
    if media:
        is_video = lambda p: (mimetypes.guess_type(p)[0] or "").startswith("video/")
        paid = bool(env.get("GEMINI_PAID_API_KEY"))
        api = dict(fps=a.fps, thinking=a.thinking, media_res=a.media_res, start=a.start, end=a.end)
        if a.jpeg_sheets or a.provider == "agy" or not (paid or a.provider == "gemini" or a.allow_free_media):
            # agy: asked for by name, the sheets mode, or the interim route while no paid key is set
            ep = endpoint("agy", env)
            if not ep:
                sys.exit("agy not found, and no GEMINI_PAID_API_KEY in " + ENV_PATH)
            if not (a.jpeg_sheets or a.provider == "agy"):
                log("Paid Gemini key not configured yet -> using interim agy mode")
            agy_model = a.model or (AGY_VIDEO_MODELS if any(is_video(p) for p in media) else ep[2])
            log("agy is watching %d file(s)" % len(media))
            try:
                if a.jpeg_sheets:
                    if len(media) != 1 or not is_video(media[0]):
                        sys.exit("--jpeg-sheets takes exactly one video file (its sound is sent along by itself)")
                    text, used = sheets_review(ep[0], prompt, a.system, a.model or AGY_SHEETS_MODELS, media[0], a.fps or 5)
                else:
                    text, used = antigravity(ep[0], prompt, a.system, agy_model, AGY_MEDIA_TIMEOUT, a.workdir, media)
            except Skip as e:
                sys.exit("agy failed: %s" % e)
            route = "agy/" + used
        elif paid and not a.allow_free_media:
            text, used = gemini_media(env, prompt, media, a.system, a.model, paid=True, over_budget=a.allow_over_budget, **api)
            route = "gemini/" + used
        else:
            # the free key: 20 requests a day on hydrogen, busy answers included, and Google may train on what it gets
            if not a.allow_free_media:
                sys.exit("Refused: the free Gemini key is not for client media (Google may train on it). "
                         "Add --allow-free-media only for a non-secret test, or set GEMINI_PAID_API_KEY in " + ENV_PATH)
            text, used = gemini_media(env, prompt, media, a.system, a.model, paid=False, **api)
            route = "gemini/" + used
    else:
        if not a.provider and not a.free:
            sys.exit("Text jobs run only when Omar asks: add --provider <name> or --free")
        order = [a.provider] if a.provider else ORDER[a.task]
        fails = []
        for name in order:
            try:
                text, used = chat(name, env, prompt, a.system, a.model, a.max_tokens,
                                  timeout=AGY_TEXT_TIMEOUT if name == "agy" else 120, workdir=a.workdir)
                route = name + "/" + used
                break
            except (Skip, requests.RequestException) as e:
                fails.append("%s: %s" % (name, e))
        else:
            sys.exit("All providers failed:\n  " + "\n  ".join(fails))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("%s -> %s (%d chars)" % (route, a.out, len(text)))
    else:
        print("[%s]" % route, file=sys.stderr)
        print(text)


def cmd_check(a, env):
    for name in PROVIDERS:
        if name == "codex":
            print("%-11s -- %s" % (name, codex_gate()[1]))
            continue
        if not endpoint(name, env):
            print("%-11s -- no key" % name)
            continue
        t = time.time()
        try:
            text, used = chat(name, env, "Reply with the single word: OK", max_tokens=200, timeout=60)
            print("%-11s OK   %-40s %.1fs" % (name, used, time.time() - t))
        except (Skip, requests.RequestException) as e:
            print("%-11s FAIL %s" % (name, str(e)[:150]))


def cmd_models(a, env):
    ep = endpoint(a.name, env)
    if not ep or a.name in ("agy", "codex"):
        sys.exit("No key for " + a.name)
    base, key, _ = ep
    r = requests.get(base + "/models", headers={"Authorization": "Bearer " + key} if key else {}, timeout=60)
    r.raise_for_status()
    for m in r.json().get("data", []):
        print(m.get("id"))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ask")
    s.add_argument("prompt", nargs="?")
    s.add_argument("--prompt-file")
    s.add_argument("--file", action="append", default=[])
    s.add_argument("--task", choices=ORDER, default="fast", help="provider order used with --free")
    s.add_argument("--free", action="store_true", help="use the free providers (only when Omar asks); default is agy")
    s.add_argument("--provider", choices=PROVIDERS)
    s.add_argument("--model")
    s.add_argument("--system")
    s.add_argument("--max-tokens", type=int, default=4096)
    s.add_argument("--out")
    s.add_argument("--fps", type=float, help="Gemini API: frames per second the model gets (max 24). With --jpeg-sheets: frames per second on the sheets (default 5)")
    s.add_argument("--thinking", choices=["low", "medium", "high"], default="medium", help="Gemini API thinking level (high = final gate of class A/A+ only)")
    s.add_argument("--media-res", choices=["low", "medium", "high"], help="Gemini API: resolution of each frame (high for small Arabic text)")
    s.add_argument("--start", type=float, help="Gemini API: review from this second")
    s.add_argument("--end", type=float, help="Gemini API: review up to this second")
    s.add_argument("--jpeg-sheets", action="store_true", help="agy: send one video as JPEG contact sheets + its sound (interim / fallback)")
    s.add_argument("--allow-free-media", action="store_true", help="send media on the FREE Gemini key (non-secret tests only)")
    s.add_argument("--allow-over-budget", action="store_true", help="paid Gemini key past the monthly cap (only with Omar's OK)")
    s.add_argument("--workdir", help="agy only: the one folder it may work in (default: an empty temp folder)")
    s.add_argument("--allow-protected-workdir", action="store_true",
                   help="let --workdir point under Clients\\ or Claude-Workflow\\ (only when Omar asked)")
    s = sub.add_parser("image", help="generate an image with Codex (friend's ChatGPT Plus, capped)")
    s.add_argument("prompt", nargs="?", default="")
    s.add_argument("--prompt-file", help="long prompt kept in a file (appended to the prompt argument)")
    s.add_argument("--out", required=True)
    s.add_argument("--ref", action="append", help="reference image(s) to attach")
    # the picture comes from Codex's image_gen tool whatever drives it; a light driver only makes it faster
    s.add_argument("--model", default="gpt-6-luna", help="Codex model that drives image_gen (default fast)")
    s.add_argument("--effort", default="low", help="reasoning effort of that driver")
    sub.add_parser("limits", help="Codex usage vs Omar's caps (reads local logs, costs nothing)")
    sub.add_parser("budget", help="paid Gemini key: this month's spend against the safety cap (costs nothing)")
    sub.add_parser("check")
    s = sub.add_parser("models")
    s.add_argument("name", choices=PROVIDERS)
    a = ap.parse_args()
    env = load_env()
    {"ask": cmd_ask, "check": cmd_check, "models": cmd_models, "image": cmd_image, "limits": cmd_limits, "budget": cmd_budget}[a.cmd](a, env)


if __name__ == "__main__":
    main()
