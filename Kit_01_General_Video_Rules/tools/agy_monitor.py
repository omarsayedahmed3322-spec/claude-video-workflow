"""agy_monitor.py - Local RTL Arabic web viewer & live monitor for Claude Code <-> Antigravity (agy) CLI reviews.

Zero external dependencies (Python stdlib only). Binds strictly to 127.0.0.1.

Usage:
  python -I -X utf8 agy_monitor.py              # start server on http://127.0.0.1:8765 and open browser
  python -I -X utf8 agy_monitor.py --no-open    # start server without opening browser
  python -I -X utf8 agy_monitor.py --port 8765  # custom port
"""
import argparse
import glob
import json
import mimetypes
import os
import re
import socket
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WF = os.environ.get("CLAUDE_WORKFLOW") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
STATE_DIR = os.path.dirname(WF)
LIVE_LOG = os.path.join(STATE_DIR, "_agy_live.log")
LIVE_STATE = os.path.join(STATE_DIR, "_agy_live_state.json")
META_FILE = os.path.join(STATE_DIR, "_agy_meta.json")
BRAIN_DIR = os.path.expanduser(r"~\.gemini\antigravity-cli\brain")
ID_RE = re.compile(r"^[a-fA-F0-9\-]{8,64}$")


def load_json_safe(path, default):
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _to_12h(dt, with_date=True, with_sec=False):
    h24 = dt.hour
    suffix = "ص" if h24 < 12 else "م"
    h12 = h24 % 12 or 12
    t_str = f"{h12:02d}:{dt.minute:02d}:{dt.second:02d} {suffix}" if with_sec else f"{h12:02d}:{dt.minute:02d} {suffix}"
    if with_date:
        return f"{dt.strftime('%Y-%m-%d')} · {t_str}"
    return t_str


def fmt_dt(ts_or_iso, with_date=True, with_sec=False):
    if isinstance(ts_or_iso, (int, float)):
        return _to_12h(datetime.fromtimestamp(ts_or_iso), with_date=with_date, with_sec=with_sec)
    if isinstance(ts_or_iso, str) and ts_or_iso.strip():
        s = ts_or_iso.strip()
        if " ص" in s or " م" in s:
            return s
        # HH:MM:SS only
        m_only = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", s)
        if m_only:
            h24, mi, sec = int(m_only.group(1)), int(m_only.group(2)), int(m_only.group(3) or 0)
            suffix = "ص" if h24 < 12 else "م"
            h12 = h24 % 12 or 12
            return f"{h12:02d}:{mi:02d}:{sec:02d} {suffix}" if m_only.group(3) else f"{h12:02d}:{mi:02d} {suffix}"
        try:
            iso = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso)
            if dt.tzinfo is not None:
                dt = dt.astimezone()
            return _to_12h(dt, with_date=with_date, with_sec=with_sec)
        except Exception:
            return s
    return ""


def clean_prompt(raw):
    """Strip the boilerplate view_file wrapper added by free_llm.py so the real prompt shows first."""
    if not raw:
        return ""
    m = re.match(
        r"^Open each of these files with your view_file tool so you see/hear them directly:.*?reply with the answer only\.\s*\n+",
        raw,
        flags=re.S,
    )
    if m:
        return raw[m.end():].strip()
    return raw.strip()


def transcript_path(conv_id):
    base = os.path.join(BRAIN_DIR, conv_id, ".system_generated", "logs")
    full = os.path.join(base, "transcript_full.jsonl")
    compact = os.path.join(base, "transcript.jsonl")
    if os.path.exists(full):
        return full
    if os.path.exists(compact):
        return compact
    return None


def read_steps(conv_id):
    p = transcript_path(conv_id)
    if not p:
        return []
    steps = []
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    steps.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return steps


def summarize_conversation(conv_id, meta_map):
    conv_dir = os.path.join(BRAIN_DIR, conv_id)
    p = transcript_path(conv_id)
    mtime = os.path.getmtime(p) if p and os.path.exists(p) else os.path.getmtime(conv_dir)
    meta = meta_map.get(conv_id) or {}
    steps = read_steps(conv_id)

    model = meta.get("model") or ""
    prompt_preview = meta.get("prompt_preview") or ""
    has_video = False
    has_audio = False
    has_image = False
    in_tok = 0
    out_tok = 0
    done = False
    created = ""

    for st in steps:
        if not created and st.get("created_at"):
            created = fmt_dt(st.get("created_at"))
        if st.get("model"):
            model = st["model"]
        if st.get("type") == "USER_INPUT" and not prompt_preview:
            prompt_preview = clean_prompt(st.get("content") or "")[:180]
        if st.get("input_tokens"):
            in_tok = max(in_tok, int(st["input_tokens"]))
        if st.get("output_tokens"):
            out_tok += int(st["output_tokens"])
        for med in st.get("media") or []:
            mt = med.get("mime_type") or ""
            if mt.startswith("video/"):
                has_video = True
            elif mt.startswith("audio/"):
                has_audio = True
            elif mt.startswith("image/"):
                has_image = True
        if st.get("type") == "PLANNER_RESPONSE" and (st.get("content") or "").strip():
            done = True

    media_dir = os.path.join(conv_dir, ".system_generated", "logs", "media")
    if os.path.isdir(media_dir):
        for fn in os.listdir(media_dir):
            ext = os.path.splitext(fn)[1].lower()
            if ext in (".mp4", ".mov", ".webm", ".mkv"):
                has_video = True
            elif ext in (".mp3", ".wav", ".m4a"):
                has_audio = True
            elif ext in (".png", ".jpg", ".jpeg", ".webp"):
                has_image = True

    files = meta.get("files") or []
    title = " + ".join(files) if files else (prompt_preview.splitlines()[0][:80] if prompt_preview else conv_id[:12])
    return {
        "id": conv_id,
        "title": title,
        "files": files,
        "model": model or "agy",
        "time": created or fmt_dt(mtime),
        "mtime": mtime,
        "prompt_preview": prompt_preview.replace("\n", " ")[:140],
        "has_video": has_video,
        "has_audio": has_audio,
        "has_image": has_image,
        "in_tokens": in_tok,
        "out_tokens": out_tok,
        "steps_count": len(steps),
        "done": done,
    }


def list_conversations(limit=80):
    if not os.path.isdir(BRAIN_DIR):
        return []
    meta_map = load_json_safe(META_FILE, {})
    dirs = []
    for name in os.listdir(BRAIN_DIR):
        if not ID_RE.match(name):
            continue
        full = os.path.join(BRAIN_DIR, name)
        if not os.path.isdir(full):
            continue
        tp = transcript_path(name)
        if not tp:
            continue
        dirs.append((os.path.getmtime(tp), name))
    dirs.sort(reverse=True)
    return [summarize_conversation(name, meta_map) for _, name in dirs[:limit]]


def get_conversation_detail(conv_id):
    if not ID_RE.match(conv_id):
        return None
    meta_map = load_json_safe(META_FILE, {})
    meta = meta_map.get(conv_id) or {}
    steps = read_steps(conv_id)
    if not steps:
        return None
    media_dir = os.path.join(BRAIN_DIR, conv_id, ".system_generated", "logs", "media")
    media_files = []
    if os.path.isdir(media_dir):
        for fn in sorted(os.listdir(media_dir)):
            fp = os.path.join(media_dir, fn)
            if os.path.isfile(fp):
                mt = mimetypes.guess_type(fp)[0] or "application/octet-stream"
                media_files.append({
                    "name": fn,
                    "mime": mt,
                    "size_mb": round(os.path.getsize(fp) / (1024 * 1024), 2),
                    "url": "/media/%s/%s" % (conv_id, urllib.parse.quote(fn)),
                })
    clean_steps = []
    model = meta.get("model") or ""
    for st in steps:
        if st.get("model"):
            model = st["model"]
        st_type = st.get("type") or ""
        raw_content = st.get("content") or ""
        display_content = clean_prompt(raw_content) if st_type == "USER_INPUT" else raw_content
        clean_steps.append({
            "index": st.get("step_index"),
            "source": st.get("source") or "",
            "type": st_type,
            "status": st.get("status") or "",
            "time": fmt_dt(st.get("created_at")),
            "model": st.get("model") or "",
            "content": display_content,
            "thinking": st.get("thinking") or "",
            "tool_calls": st.get("tool_calls") or [],
            "input_tokens": st.get("input_tokens") or 0,
            "output_tokens": st.get("output_tokens") or 0,
        })
    return {
        "id": conv_id,
        "model": model or "agy",
        "files": meta.get("files") or [],
        "file_paths": meta.get("file_paths") or [],
        "started_at": fmt_dt(meta.get("started_at")) if meta.get("started_at") else (clean_steps[0]["time"] if clean_steps else ""),
        "duration_seconds": meta.get("duration_seconds") or 0,
        "media": media_files,
        "steps": clean_steps,
    }


def get_live_payload():
    st = load_json_safe(LIVE_STATE, {})
    if isinstance(st, dict) and st:
        st = dict(st)
        if st.get("started_at"):
            st["started_at"] = fmt_dt(st["started_at"], with_date=True, with_sec=True)
        if st.get("updated_at"):
            st["updated_at_short"] = fmt_dt(st["updated_at"], with_date=False, with_sec=False)
            st["updated_at"] = fmt_dt(st["updated_at"], with_date=True, with_sec=True)
        if st.get("events"):
            st["events"] = [
                {"t": fmt_dt(e.get("t", ""), with_date=False, with_sec=True), "msg": e.get("msg", "")}
                for e in st["events"]
            ]
    tail = ""
    try:
        if os.path.exists(LIVE_LOG):
            with open(LIVE_LOG, "rb") as f:
                size = os.path.getsize(LIVE_LOG)
                f.seek(max(0, size - 24000))
                tail = f.read().decode("utf-8", errors="replace")
    except Exception:
        pass
    return {"state": st, "log_tail": tail}


HTML_PAGE = r"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>مراقب وسجل Antigravity (agy) — شات كلود وجيميناي</title>
<style>
  :root {
    --bg: #0E131B;
    --panel: #151C27;
    --panel-2: #1C2534;
    --border: #273245;
    --ink: #EDF2F7;
    --muted: #93A4BD;
    --acc: #38BDF8;
    --acc-bg: rgba(56, 189, 248, 0.12);
    --green: #34D399;
    --green-bg: rgba(52, 211, 153, 0.12);
    --red: #F87171;
    --red-bg: rgba(248, 113, 113, 0.14);
    --amber: #FBBF24;
    --amber-bg: rgba(251, 191, 36, 0.12);
    --purple: #A78BFA;
    --purple-bg: rgba(167, 139, 250, 0.12);
    --code: #0A0E14;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: "Cairo", "Segoe UI", Tahoma, sans-serif;
    line-height: 1.7;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  header {
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    padding: 10px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-shrink: 0;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .brand h1 {
    margin: 0;
    font-size: 16px;
    font-weight: 800;
  }
  .live-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-size: 12.5px;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--panel-2);
    cursor: pointer;
  }
  .live-pill.running {
    background: var(--red-bg);
    border-color: var(--red);
    color: #FECACA;
  }
  .live-pill.done {
    background: var(--green-bg);
    border-color: rgba(52, 211, 153, 0.45);
    color: #A7F3D0;
  }
  .dot {
    width: 9px; height: 9px; border-radius: 50%; background: var(--muted);
  }
  .live-pill.running .dot {
    background: var(--red);
    animation: pulse 1.1s infinite;
  }
  .live-pill.done .dot { background: var(--green); }
  @keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.4); opacity: 0.45; }
  }
  .hdr-actions { display: flex; gap: 8px; align-items: center; }
  button {
    font-family: inherit;
    background: var(--panel-2);
    color: var(--ink);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12.5px;
    font-weight: 700;
    cursor: pointer;
  }
  button:hover { border-color: var(--acc); color: #fff; }
  button.primary { background: var(--acc-bg); border-color: var(--acc); color: var(--acc); }

  .layout {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
  aside {
    width: 330px;
    min-width: 280px;
    background: var(--panel);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .search-box {
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
  }
  .search-box input {
    width: 100%;
    font-family: inherit;
    background: var(--bg);
    color: var(--ink);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 7px 11px;
    font-size: 13px;
    outline: none;
  }
  .search-box input:focus { border-color: var(--acc); }
  .conv-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }
  .conv-item {
    padding: 10px 11px;
    border-radius: 10px;
    border: 1px solid transparent;
    margin-bottom: 6px;
    cursor: pointer;
    background: rgba(255,255,255,0.02);
  }
  .conv-item:hover { background: var(--panel-2); border-color: var(--border); }
  .conv-item.active { background: var(--acc-bg); border-color: var(--acc); }
  .conv-item.live-card {
    background: linear-gradient(135deg, rgba(248,113,113,0.12), rgba(56,189,248,0.1));
    border-color: rgba(248,113,113,0.45);
  }
  .conv-title {
    font-size: 13.5px;
    font-weight: 800;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 3px;
  }
  .conv-preview {
    font-size: 12px;
    color: var(--muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 5px;
  }
  .conv-meta {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    font-size: 11px;
    color: var(--muted);
    align-items: center;
  }
  .badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 999px;
    font-size: 10.5px;
    font-weight: 700;
    background: var(--panel-2);
    border: 1px solid var(--border);
  }
  .b-vid { color: var(--acc); border-color: rgba(56,189,248,0.4); }
  .b-aud { color: var(--purple); border-color: rgba(167,139,250,0.4); }
  .b-mod { color: var(--green); border-color: rgba(52,211,153,0.4); direction: ltr; }

  main {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 18px 22px 50px;
  }
  .empty {
    text-align: center;
    color: var(--muted);
    margin-top: 80px;
    font-size: 15px;
  }
  .chat-header {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 13px 16px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    flex-wrap: wrap;
  }
  .chat-header h2 { margin: 0 0 4px 0; font-size: 16px; }
  .chat-sub { font-size: 12.5px; color: var(--muted); display: flex; gap: 10px; flex-wrap: wrap; }

  .media-strip {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    margin-bottom: 16px;
  }
  .media-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 11px;
    padding: 10px;
    max-width: 340px;
  }
  .media-card video {
    max-height: 300px;
    max-width: 100%;
    border-radius: 8px;
    background: #000;
    display: block;
  }
  .media-card audio { width: 280px; max-width: 100%; display: block; margin-top: 4px; }
  .media-cap { font-size: 11.5px; color: var(--muted); margin-top: 5px; direction: ltr; text-align: left; }

  .msg {
    border-radius: 12px;
    padding: 13px 16px;
    margin-bottom: 13px;
    border: 1px solid var(--border);
    background: var(--panel);
  }
  .msg-claude {
    border-right: 4px solid var(--amber);
    background: linear-gradient(180deg, rgba(251,191,36,0.06), var(--panel));
  }
  .msg-gemini {
    border-right: 4px solid var(--acc);
    background: linear-gradient(180deg, rgba(56,189,248,0.06), var(--panel));
  }
  .msg-tool {
    border-right: 4px solid var(--purple);
    background: var(--panel-2);
    padding: 9px 14px;
    font-size: 12.5px;
  }
  .msg-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 7px;
    font-size: 12.5px;
    font-weight: 800;
  }
  .msg-claude .msg-head { color: var(--amber); }
  .msg-gemini .msg-head { color: var(--acc); }
  .msg-tool .msg-head { color: var(--purple); margin-bottom: 4px; }
  .msg-time { color: var(--muted); font-weight: 500; font-size: 11.5px; direction: ltr; }

  .msg-body {
    font-size: 14px;
    white-space: pre-wrap;
    word-break: break-word;
    overflow-wrap: anywhere;
    unicode-bidi: plaintext;
    text-align: start;
  }
  .msg-body h1, .msg-body h2, .msg-body h3 { margin: 12px 0 6px; color: #fff; }
  .msg-body h2 { font-size: 16px; border-bottom: 1px solid var(--border); padding-bottom: 4px; }
  .msg-body h3 { font-size: 14.5px; color: var(--acc); }
  .msg-body code {
    background: var(--code);
    padding: 1px 6px;
    border-radius: 5px;
    font-family: Consolas, monospace;
    font-size: 12.5px;
    direction: ltr;
    unicode-bidi: isolate;
    display: inline-block;
  }
  .msg-body pre {
    background: var(--code);
    border: 1px solid var(--border);
    padding: 10px 12px;
    border-radius: 8px;
    overflow-x: auto;
    direction: ltr;
    text-align: left;
    font-family: Consolas, monospace;
    font-size: 12px;
  }

  details.think-box {
    background: var(--purple-bg);
    border: 1px solid rgba(167,139,250,0.3);
    border-radius: 9px;
    padding: 7px 12px;
    margin-bottom: 10px;
  }
  details.think-box summary {
    cursor: pointer;
    font-size: 12.5px;
    font-weight: 700;
    color: var(--purple);
  }
  .think-body {
    margin-top: 8px;
    font-size: 12.5px;
    color: #D8D2F0;
    white-space: pre-wrap;
    word-break: break-word;
    unicode-bidi: plaintext;
    text-align: start;
    border-top: 1px dashed rgba(167,139,250,0.3);
    padding-top: 7px;
  }
  .raw-log {
    background: var(--code);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px;
    font-family: Consolas, "Cairo", monospace;
    font-size: 12.5px;
    white-space: pre-wrap;
    word-break: break-word;
    unicode-bidi: plaintext;
    text-align: start;
    max-height: 360px;
    overflow-y: auto;
    color: #CBD5E1;
  }
  .toast {
    position: fixed; bottom: 18px; left: 18px;
    background: var(--green); color: #052E16;
    padding: 8px 14px; border-radius: 8px; font-weight: 800; font-size: 13px;
    display: none; z-index: 999;
  }
</style>
</head>
<body>
  <header>
    <div class="brand">
      <h1>مراقب وسجل محادثات كلود كود مع <code>agy</code> (Gemini)</h1>
      <span id="livePill" class="live-pill" onclick="selectLive()">
        <span class="dot"></span>
        <span id="livePillText">جاري الفحص...</span>
      </span>
    </div>
    <div class="hdr-actions">
      <button class="primary" onclick="selectLive()">شاشة اللايف</button>
      <button onclick="loadList(true)">تحديث السجل</button>
    </div>
  </header>

  <div class="layout">
    <aside>
      <div class="search-box">
        <input id="q" type="text" placeholder="ابحث باسم الفيديو أو كلام البرومبت أو الموديل..." oninput="renderList()">
      </div>
      <div id="convList" class="conv-list"></div>
    </aside>
    <main id="main">
      <div class="empty">اختار أي مراجعة من القائمة على اليمين أو اضغط «شاشة اللايف» لمتابعة الشغل الحالي.</div>
    </main>
  </div>

  <div id="toast" class="toast">تم النسخ!</div>

<script>
let allConvs = [];
let activeMode = "live"; // "live" or conv_id
let liveData = null;
let rawLogOpen = false;
let liveThinkOpen = null;
let lastLiveSig = "";

function esc(s) {
  return String(s || "").replace(/[&<>"]/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c]));
}

function renderMd(txt) {
  let s = esc(txt || "");
  s = s.replace(/```([\s\S]*?)```/g, (_, code) => `<pre>${code.trim()}</pre>`);
  s = s.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  s = s.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  s = s.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  s = s.replace(/^# (.+)$/gm, "<h1>$1</h1>");
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  return s;
}

function copyText(t) {
  navigator.clipboard.writeText(t).then(() => {
    const el = document.getElementById("toast");
    el.style.display = "block";
    setTimeout(() => { el.style.display = "none"; }, 1800);
  });
}

async function loadList(keepSelection) {
  const r = await fetch("/api/list");
  allConvs = await r.json();
  renderList();
  if (!keepSelection && allConvs.length && activeMode === "live" && (!liveData || !liveData.state || !liveData.state.status)) {
    selectConv(allConvs[0].id);
  }
}

function renderList() {
  const q = (document.getElementById("q").value || "").trim().toLowerCase();
  const box = document.getElementById("convList");
  let html = "";
  const st = (liveData && liveData.state) || {};
  const isRun = st.status === "running";
  html += `<div class="conv-item live-card ${activeMode === 'live' ? 'active' : ''}" onclick="selectLive()">
    <div class="conv-title">${isRun ? '🔴 شغال لايف دلوقتي!' : '⚡ شاشة اللايف (آخر بث)'}</div>
    <div class="conv-preview">${esc((st.files && st.files.length) ? st.files.join(" + ") : (st.prompt ? st.prompt.slice(0, 70) : "مستني أي مراجعة جديدة من كلود كود..."))}</div>
    <div class="conv-meta">
      <span class="badge b-mod">${esc(st.model || "agy")}</span>
      <span>${esc(st.updated_at || "")}</span>
    </div>
  </div>`;

  for (const c of allConvs) {
    const hay = (c.title + " " + c.prompt_preview + " " + c.model + " " + c.id).toLowerCase();
    if (q && !hay.includes(q)) continue;
    html += `<div class="conv-item ${activeMode === c.id ? 'active' : ''}" onclick="selectConv('${c.id}')">
      <div class="conv-title">${esc(c.title)}</div>
      <div class="conv-preview">${esc(c.prompt_preview || "(بدون نص برومبت)")}</div>
      <div class="conv-meta">
        <span class="badge b-mod">${esc(c.model)}</span>
        ${c.has_video ? '<span class="badge b-vid">فيديو</span>' : ''}
        ${c.has_audio ? '<span class="badge b-aud">صوت</span>' : ''}
        <span>${esc(c.time)}</span>
      </div>
    </div>`;
  }
  box.innerHTML = html;
}

function selectLive() {
  activeMode = "live";
  lastLiveSig = "";
  renderList();
  renderLive(true);
}

async function selectConv(id) {
  activeMode = id;
  renderList();
  const main = document.getElementById("main");
  main.innerHTML = '<div class="empty">جاري تحميل المحادثة...</div>';
  const r = await fetch("/api/conv/" + encodeURIComponent(id));
  if (!r.ok) {
    main.innerHTML = '<div class="empty">المحادثة مش موجودة أو لسه فاضية.</div>';
    return;
  }
  const d = await r.json();
  renderConv(d);
}

function renderConv(d) {
  const main = document.getElementById("main");
  const resumeCmd = `agy --conversation ${d.id}`;
  let html = `<div class="chat-header">
    <div>
      <h2>${esc((d.files && d.files.length) ? d.files.join(" + ") : ("محادثة " + d.id.slice(0, 12)))}</h2>
      <div class="chat-sub">
        <span>الوقت: ${esc(d.started_at)}</span>
        <span>الموديل: <code>${esc(d.model)}</code></span>
        ${d.duration_seconds ? `<span>المدة: ${d.duration_seconds} ث</span>` : ''}
        <span>المعرف: <code>${esc(d.id)}</code></span>
      </div>
    </div>
    <div>
      <button class="primary" onclick="copyText('${esc(resumeCmd)}')">انسخ أمر فتحها في agy</button>
    </div>
  </div>`;

  if (d.media && d.media.length) {
    html += `<div class="media-strip">`;
    for (const m of d.media) {
      if (m.mime.startsWith("video/")) {
        html += `<div class="media-card"><video controls preload="metadata" src="${m.url}"></video><div class="media-cap">${esc(m.name)} (${m.size_mb} MB)</div></div>`;
      } else if (m.mime.startsWith("audio/")) {
        html += `<div class="media-card"><audio controls preload="metadata" src="${m.url}"></audio><div class="media-cap">${esc(m.name)} (${m.size_mb} MB)</div></div>`;
      } else if (m.mime.startsWith("image/")) {
        html += `<div class="media-card"><img style="max-height:240px;max-width:100%;border-radius:8px;" src="${m.url}"><div class="media-cap">${esc(m.name)}</div></div>`;
      }
    }
    html += `</div>`;
  }

  for (const st of d.steps) {
    if (st.type === "USER_INPUT") {
      html += `<div class="msg msg-claude">
        <div class="msg-head"><span>طلب كلود كود إلى agy</span><span class="msg-time">${esc(st.time)}</span></div>
        <div class="msg-body" dir="auto">${renderMd(st.content)}</div>
      </div>`;
    } else if (st.type === "PLANNER_RESPONSE") {
      const hasTools = st.tool_calls && st.tool_calls.length;
      const hasText = (st.content || "").trim().length > 0;
      const hasThink = (st.thinking || "").trim().length > 0;
      if (!hasTools && !hasText && !hasThink) continue;
      html += `<div class="msg ${hasText ? 'msg-gemini' : 'msg-tool'}">
        <div class="msg-head">
          <span>${hasText ? 'تقرير ورد Gemini' : 'خطوة تنفيذ (فتح ملفات/أدوات)'} ${st.model ? '(' + esc(st.model) + ')' : ''}</span>
          <span class="msg-time">${esc(st.time)} ${st.input_tokens ? '· in:' + st.input_tokens + ' out:' + st.output_tokens : ''}</span>
        </div>`;
      if (hasThink) {
        html += `<details class="think-box"><summary>اضغط لعرض تفكير Gemini الداخلي (${st.thinking.length} حرف)</summary><div class="think-body" dir="auto">${esc(st.thinking)}</div></details>`;
      }
      if (hasTools) {
        const tlist = st.tool_calls.map(tc => `<code>${esc(tc.name)}</code>: ${esc(JSON.stringify(tc.args || {}))}`).join("<br>");
        html += `<div class="msg-body" dir="ltr" style="font-size:12.5px;margin-bottom:${hasText ? 8 : 0}px;">${tlist}</div>`;
      }
      if (hasText) {
        html += `<div class="msg-body" dir="auto">${renderMd(st.content)}</div>`;
      }
      html += `</div>`;
    }
  }
  main.innerHTML = html;
}

function renderLive(force) {
  if (activeMode !== "live") return;
  const sig = JSON.stringify(liveData || {});
  if (!force && sig === lastLiveSig) return;
  lastLiveSig = sig;
  const main = document.getElementById("main");
  const prevLog = document.getElementById("rawLogBody");
  const prevScrollTop = prevLog ? prevLog.scrollTop : null;
  const prevAtBottom = prevLog ? (prevLog.scrollHeight - prevLog.scrollTop - prevLog.clientHeight < 30) : true;

  const st = (liveData && liveData.state) || {};
  const tail = (liveData && liveData.log_tail) || "";
  if (!st.status && !tail) {
    main.innerHTML = `<div class="empty">مفيش مراجعة اتبعتت عن طريق التحديث الجديد لسه.<br>أول ما كلود كود يشغّل <code>free_llm.py</code> للمراجعة، هتظهر هنا لايف لحظة بلحظة! (وتقدر دلوقتي تتصفح كل محادثاتك القديمة من القائمة على اليمين).</div>`;
    return;
  }
  const statusLabel = st.status === "running" ? "🔴 شغال لايف دلوقتي..." : (st.status === "done" ? "✅ آخر مراجعة خلصت بنجاح" : "⚠️ آخر مراجعة وقفت بخطأ");
  let html = `<div class="chat-header">
    <div>
      <h2>${statusLabel} — ${esc((st.files && st.files.length) ? st.files.join(" + ") : "بدون ميديا")}</h2>
      <div class="chat-sub">
        <span>البداية: ${esc(st.started_at)}</span>
        <span>الموديل: <code>${esc(st.model)}</code></span>
        <span>المدة: ${st.duration_seconds || 0} ث</span>
        ${st.conversation_id ? `<span>المعرف: <code>${esc(st.conversation_id)}</code></span>` : ''}
      </div>
    </div>
    <div>
      ${st.conversation_id ? `<button class="primary" onclick="selectConv('${esc(st.conversation_id)}')">افتح السجل الكامل + الفيديو</button>` : ''}
    </div>
  </div>`;

  if (st.prompt) {
    html += `<div class="msg msg-claude">
      <div class="msg-head"><span>البرومبت اللي كلود بعته</span><span class="msg-time">${esc(st.started_at)}</span></div>
      <div class="msg-body" dir="auto">${renderMd(st.prompt)}</div>
    </div>`;
  }

  if (st.events && st.events.length) {
    html += `<div class="msg msg-tool">
      <div class="msg-head"><span>خطوات التنفيذ لايف</span><span></span></div>
      <div class="msg-body" style="font-size:12.5px;">${st.events.map(e => `[${esc(e.t)}] ${esc(e.msg)}`).join("\n")}</div>
    </div>`;
  }

  if (st.live_thinking) {
    const thinkShouldOpen = (liveThinkOpen !== null) ? liveThinkOpen : (st.status === "running");
    html += `<details class="think-box" ${thinkShouldOpen ? "open" : ""} ontoggle="liveThinkOpen = this.open"><summary>تفكير Gemini لايف (${st.live_thinking.length} حرف)</summary><div class="think-body" dir="auto">${esc(st.live_thinking)}</div></details>`;
  }

  if (st.live_text) {
    html += `<div class="msg msg-gemini">
      <div class="msg-head"><span>رد وتقرير Gemini ${st.status === "running" ? "(بيكتب دلوقتي...)" : "(النهائي)"}</span><span class="msg-time">${esc(st.updated_at)}</span></div>
      <div class="msg-body" dir="auto">${renderMd(st.live_text)}</div>
    </div>`;
  }

  if (st.error) {
    html += `<div class="msg" style="border-right:4px solid var(--red);color:#FECACA;">خطأ: ${esc(st.error)}</div>`;
  }

  if (tail) {
    html += `<details style="margin-top:14px;" ${rawLogOpen ? "open" : ""} ontoggle="rawLogOpen = this.open"><summary style="cursor:pointer;color:var(--muted);font-size:13px;">عرض السجل النصي الخام (<code>_agy_live.log</code>)</summary><div id="rawLogBody" class="raw-log" dir="auto" style="margin-top:8px;">${esc(tail)}</div></details>`;
  }
  main.innerHTML = html;
  const newLog = document.getElementById("rawLogBody");
  if (newLog && rawLogOpen) {
    if (prevAtBottom || prevScrollTop === null) newLog.scrollTop = newLog.scrollHeight;
    else newLog.scrollTop = prevScrollTop;
  }
}

let prevStatus = "";
async function pollLive() {
  try {
    const r = await fetch("/api/live");
    liveData = await r.json();
    const st = liveData.state || {};
    const pill = document.getElementById("livePill");
    const txt = document.getElementById("livePillText");
    pill.className = "live-pill " + (st.status === "running" ? "running" : (st.status === "done" ? "done" : ""));
    if (st.status === "running") {
      txt.textContent = "مراجعة شغالة لايف (" + (st.duration_seconds || 0) + " ث)";
    } else if (st.status === "done") {
      txt.textContent = "آخر مراجعة خلصت · " + (st.updated_at_short || st.updated_at || "");
    } else {
      txt.textContent = "جاهز للمتابعة اللايف";
    }
    if (prevStatus === "running" && st.status !== "running") {
      loadList(true);
    }
    prevStatus = st.status || "";
    renderList();
    if (activeMode === "live") renderLive();
  } catch (e) {}
}

loadList(false);
pollLive();
setInterval(pollLive, 1500);
setInterval(() => loadList(true), 12000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return  # quiet console

    def send_json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def serve_media(self, conv_id, filename):
        if not ID_RE.match(conv_id):
            self.send_error(400)
            return
        safe_name = os.path.basename(urllib.parse.unquote(filename))
        fp = os.path.join(BRAIN_DIR, conv_id, ".system_generated", "logs", "media", safe_name)
        if not os.path.isfile(fp):
            self.send_error(404)
            return
        size = os.path.getsize(fp)
        mime = mimetypes.guess_type(fp)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        code = 200
        if rng and rng.startswith("bytes="):
            parts = rng[6:].split("-", 1)
            try:
                if parts[0]:
                    start = int(parts[0])
                if parts[1]:
                    end = min(int(parts[1]), size - 1)
                if 0 <= start <= end < size:
                    code = 206
            except ValueError:
                pass
        length = end - start + 1
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        try:
            with open(fp, "rb") as f:
                f.seek(start)
                left = length
                while left > 0:
                    chunk = f.read(min(65536, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/" or path == "/index.html":
            data = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/ping":
            self.send_json({"app": "agy_monitor", "ok": True})
            return
        if path == "/api/list":
            self.send_json(list_conversations())
            return
        if path == "/api/live":
            self.send_json(get_live_payload())
            return
        if path.startswith("/api/conv/"):
            cid = urllib.parse.unquote(path[len("/api/conv/"):])
            detail = get_conversation_detail(cid)
            if not detail:
                self.send_json({"error": "not found"}, 404)
            else:
                self.send_json(detail)
            return
        if path.startswith("/media/"):
            rest = path[len("/media/"):].split("/", 1)
            if len(rest) == 2:
                self.serve_media(rest[0], rest[1])
                return
        self.send_error(404)


def is_our_monitor(host, port):
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://{host}:{port}/api/ping", timeout=0.6) as r:
            return json.loads(r.read().decode("utf-8")).get("app") == "agy_monitor"
    except Exception:
        return False


def main():
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="AGY CLI Live Monitor & Chat History Viewer")
    ap.add_argument("--port", type=int, default=48765)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    host = "127.0.0.1"
    port = a.port
    if is_our_monitor(host, port):
        url = f"http://{host}:{port}/"
        print(f"AGY Monitor is already running at {url}")
        if not a.no_open:
            webbrowser.open(url)
        return
    srv = None
    for candidate in range(port, port + 20):
        try:
            srv = ThreadingHTTPServer((host, candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if srv is None:
        sys.exit("Could not bind a free port")
    url = f"http://{host}:{port}/"
    print(f"AGY Monitor running at {url}  (Ctrl+C to stop)")
    if not a.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
