"""Send a task to a free LLM API (list: github.com/mnfst/awesome-free-llm-apis) so Claude saves its own limits.
Keys live OUTSIDE this repo: <parent of Claude-Workflow>\\keys\\free-llm.env (override with env FREE_LLM_ENV). Never commit keys.
Used by the skill free-llm-delegate. Prints only the answer on stdout (one "[provider/model]" line on stderr).

  python free_llm.py ask "prompt" [--task fast|long] [--provider groq] [--model ID] [--file a.txt ...] [--out res.md]
  python free_llm.py ask --prompt-file brief.md --file ref.mp4      # media files -> Gemini (native API) only
  python free_llm.py check                                          # which providers answer right now
  python free_llm.py models groq                                    # model ids a provider serves
  python free_llm.py ask "..." --provider agy --workdir "D:\some\folder"   # agy works inside that folder only

- Falls through the task's provider order on missing key / 401 / 429 / 5xx / timeout.
- Text files passed with --file are appended to the prompt; video/audio/image files are uploaded to Gemini,
  used once, then deleted from Google's side.
"""
import argparse, glob, json, mimetypes, os, shutil, subprocess, sys, tempfile, time
import requests

WF = os.environ.get("CLAUDE_WORKFLOW") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ENV_PATH = os.environ.get("FREE_LLM_ENV") or os.path.join(os.path.dirname(WF), "keys", "free-llm.env")   # next to <Claude-Workflow>: <parent>\keys
GEMINI = "https://generativelanguage.googleapis.com"

# name: (base_url, key_env, default_models, works_without_key) — comma-separated models are tried in order (busy -> next)
PROVIDERS = {
    "codex":      ("codex", "", "", True),  # friend's ChatGPT Plus: --provider codex only (debate / hard jobs), capped by codex_gate()
    "agy":        ("antigravity", "", "gemini-4-hydrogen-medium,gemini-4-hydrogen-high", True),  # Omar 2026-11-12: Gemini 4 Hydrogen replaced 3.8 Flash;  # Antigravity CLI, Omar's Google AI Pro login (Gemini CLI was closed to personal accounts 2026-11-06)
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
        if k.endswith(("_API_KEY", "_API_TOKEN", "_ACCOUNT_ID", "_MODEL")):
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


def antigravity(exe, prompt, system=None, model="", timeout=120, workdir=None, attach=()):
    # Antigravity CLI (agy) on Omar's Google account, full permissions (Omar's call, 2026-11-06): it can run commands
    # and edit files, so it runs in a fresh temp folder unless --workdir names the one work folder it may touch.
    # Runs in a fresh temp folder; a long prompt is saved there as task.md (Windows caps a command line at ~32k chars).
    text = ((system + "\n\n") if system else "") + prompt
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
            cmd = [exe, "-p", ask, "--dangerously-skip-permissions", "--print-timeout", "%ds" % timeout] + (["--model", m] if m else [])
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL,
                                   timeout=timeout + 30, cwd=d)
            except subprocess.TimeoutExpired:
                err = "timeout"
                continue
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip(), m or "auto"
            out = (r.stderr or r.stdout).strip()
            err = out.splitlines()[-1][:160] if out else "exit %d" % r.returncode
    raise Skip(err)


PROXY_OVER = 8e6      # bytes. Bigger videos are re-encoded before upload: Omar's upload runs ~0.3 MB/s (57 MB = 3 min)
PROCESS_CAP = 180     # s to wait for Google to finish processing an uploaded file
BUSY_WAITS = (10, 25)  # s between retries of the same model on 429/503 before moving to the next one
AGY_MEDIA_TIMEOUT = 420  # s for agy to watch/hear media (frames + mp3)
AGY_TEXT_TIMEOUT = 300   # s for an agy text job (only when Omar asks)
GEN_CAP = 150         # s per model answer; a busy model took 4.6 min on 2026-11-06 while the next one answers in ~40 s


def log(msg, t0=[time.time()]):  # progress on stderr, so a long media job never looks frozen
    print("[%5.0fs] %s" % (time.time() - t0[0], msg), file=sys.stderr, flush=True)


def light_proxy(p, tmp):
    # Gemini samples video at ~1 fps, so 5 fps / crf 32 / 720 px wide loses nothing it uses. Audio stays (mono 48k)
    # for VO and recitation jobs. 57 MB -> 3 MB on a 5-min phone clip.
    if not (mimetypes.guess_type(p)[0] or "").startswith("video/") or os.path.getsize(p) <= PROXY_OVER or not shutil.which("ffmpeg"):
        return p
    out = os.path.join(tmp, "proxy_" + os.path.splitext(os.path.basename(p))[0] + ".mp4")
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", p, "-vf", "fps=5,scale='min(720,iw)':-2",
                        "-c:v", "libx264", "-crf", "32", "-preset", "veryfast", "-c:a", "aac", "-ac", "1", "-b:a", "48k", out])
    if r.returncode != 0 or not os.path.exists(out):
        log("proxy failed, uploading the original")
        return p
    log("proxy %s: %.1f MB -> %.1f MB" % (os.path.basename(p), os.path.getsize(p) / 1e6, os.path.getsize(out) / 1e6))
    return out


def gemini_media(env, prompt, paths, system=None, model=None, timeout=600):
    key = env.get("GEMINI_API_KEY")
    if not key:
        sys.exit("Media files need GEMINI_API_KEY in " + ENV_PATH)
    h = {"x-goog-api-key": key}
    model = model or env.get("GEMINI_MODEL") or PROVIDERS["gemini"][2]
    uploaded = []
    tmp = tempfile.mkdtemp(prefix="gem_")
    try:
        for p in paths:
            p = light_proxy(p, tmp)
            mime = mimetypes.guess_type(p)[0] or "application/octet-stream"
            size = os.path.getsize(p)
            log("uploading %s (%.1f MB)" % (os.path.basename(p), size / 1e6))
            r = requests.post(GEMINI + "/upload/v1beta/files", timeout=60, json={"file": {"display_name": os.path.basename(p)}},
                              headers={**h, "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                                       "X-Goog-Upload-Header-Content-Length": str(size),
                                       "X-Goog-Upload-Header-Content-Type": mime})
            r.raise_for_status()
            with open(p, "rb") as f:
                r = requests.post(r.headers["X-Goog-Upload-URL"], data=f, timeout=timeout,
                                  headers={"Content-Length": str(size), "X-Goog-Upload-Offset": "0",
                                           "X-Goog-Upload-Command": "upload, finalize"})
            r.raise_for_status()
            info = r.json()["file"]
            uploaded.append(info)
            log("uploaded, Google is processing it")
            t = time.time()
            while info.get("state") == "PROCESSING":  # video needs a few seconds before it can be used
                if time.time() - t > PROCESS_CAP:
                    sys.exit("Gemini still processing %s after %ds" % (p, PROCESS_CAP))
                time.sleep(3)
                info = requests.get(GEMINI + "/v1beta/" + info["name"], headers=h, timeout=30).json()
            if info.get("state") == "FAILED":
                sys.exit("Gemini could not process " + p)
            info["mime"] = mime
            uploaded[-1] = info
        parts = [{"file_data": {"mime_type": u["mime"], "file_uri": u["uri"]}} for u in uploaded] + [{"text": prompt}]
        body = {"contents": [{"role": "user", "parts": parts}]}
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}
        models = model.split(",")
        for i, m in enumerate(models):
            cap = timeout if i == len(models) - 1 else min(timeout, GEN_CAP)  # the last model gets the full timeout
            r = None
            for wait in BUSY_WAITS + (None,):
                log("asking %s (up to %ds)" % (m, cap))
                try:
                    r = requests.post(GEMINI + "/v1beta/models/%s:generateContent" % m, headers=h, json=body, timeout=cap)
                except requests.Timeout:
                    log("%s gave no answer in %ds" % (m, cap))
                    break
                if r.status_code not in (429, 503) or wait is None:
                    break
                log("%s busy (HTTP %d), retrying in %ds" % (m, r.status_code, wait))
                time.sleep(wait)
            if r is not None and r.status_code not in RETRYABLE:
                break
        if r is None:
            sys.exit("Gemini gave no answer from " + model)
        if r.status_code != 200:
            sys.exit("Gemini HTTP %d: %s" % (r.status_code, r.text[:300]))
        model = m
        cand = r.json().get("candidates") or [{}]
        text = "".join(pt.get("text", "") for pt in cand[0].get("content", {}).get("parts", []))
        return text, model
    finally:
        for u in uploaded:
            try:
                requests.delete(GEMINI + "/v1beta/" + u["name"], headers=h, timeout=30)
            except Exception:
                pass
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


def cmd_limits(a, env):
    print(codex_gate()[1] if codex_gate()[0] else "PAUSED: " + codex_gate()[1])


def is_media(p):
    return (mimetypes.guess_type(p)[0] or "").startswith(MEDIA_PREFIX)


def cmd_ask(a, env):
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
        if a.provider == "gemini":
            text, used = gemini_media(env, prompt, media, a.system, a.model)
            route = "gemini/" + used
        else:
            ep = endpoint("agy", env)
            if not ep:
                sys.exit("agy not found. Use --provider gemini (API key, few requests) only if Omar asks")
            log("agy is watching %d file(s)" % len(media))
            try:
                text, used = antigravity(ep[0], prompt, a.system, a.model or ep[2], AGY_MEDIA_TIMEOUT, a.workdir, media)
            except Skip as e:
                sys.exit("agy failed: %s" % e)
            route = "agy/" + used
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
    s.add_argument("--workdir", help="agy only: the one folder it may work in (default: an empty temp folder)")
    s = sub.add_parser("image", help="generate an image with Codex (friend's ChatGPT Plus, capped)")
    s.add_argument("prompt", nargs="?", default="")
    s.add_argument("--prompt-file", help="long prompt kept in a file (appended to the prompt argument)")
    s.add_argument("--out", required=True)
    s.add_argument("--ref", action="append", help="reference image(s) to attach")
    # the picture comes from Codex's image_gen tool whatever drives it; a light driver only makes it faster
    s.add_argument("--model", default="gpt-6-luna", help="Codex model that drives image_gen (default fast)")
    s.add_argument("--effort", default="low", help="reasoning effort of that driver")
    sub.add_parser("limits", help="Codex usage vs Omar's caps (reads local logs, costs nothing)")
    sub.add_parser("check")
    s = sub.add_parser("models")
    s.add_argument("name", choices=PROVIDERS)
    a = ap.parse_args()
    env = load_env()
    {"ask": cmd_ask, "check": cmd_check, "models": cmd_models, "image": cmd_image, "limits": cmd_limits}[a.cmd](a, env)


if __name__ == "__main__":
    main()
