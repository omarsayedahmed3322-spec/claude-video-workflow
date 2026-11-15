r"""Build the public copy of Claude-Workflow (no clients, no keys, no personal paths) from this private one.

Run:      python -I -X utf8 export_public.py                 (writes to <parent of Claude-Workflow>\claude-workflow-public)
Check:    python -I -X utf8 export_public.py --check         (same checks, writes nothing)
Options:  --out <folder>   --archive <folder>   --settings <json>

One source, two repos: the public copy is generated, never edited by hand. Whatever the end-of-session review
changes in the kits reaches the public copy on the next run, so both evolve together.

What goes in: every file git tracks here (plus new files git does not ignore), then the files in public_overlay\
on top (README, .gitignore, the Kit_04 README without clients, ...).
What stays out: CHANGELOG.md, THIS-PC.md, Kit_04_Clients\, public_overlay\ itself, and the `exclude` list in the
private settings file (Kit_04_Clients\_public_export.json - it lives in the private clients repo because it names clients).
Text files are rewritten in this order:
  1. markers (.md only):  a line with <!--private--> is dropped;  <!--private:start--> ... <!--private:end--> is dropped;
     <!--public:start ... public:end--> is an HTML comment here (invisible) and becomes plain text in the public copy.
  2. lines containing any `drop_lines_containing` string are dropped.
  3. every client spelling in `aliases` becomes its alias (CLA, CLB, ...), in file names too.
Then the whole result is scanned. If a client spelling, an API key, a personal e-mail or a `forbidden_regex` hit is
still there, NOTHING is written and the hits are listed (exit 1).
A file that was in the public folder and is no longer exported is moved to <archive>\<date>\public-export-removed\
(never deleted). The .git folder of the public copy is left alone; committing and pushing it is a separate step
that waits for Omar's OK (START-HERE section 7).
"""
import argparse, datetime, fnmatch, json, os, re, shutil, subprocess, sys

ROOT = os.environ.get("CLAUDE_WORKFLOW") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ALWAYS_OUT = ["CHANGELOG.md", "THIS-PC.md", "Kit_04_Clients/", "public_overlay/", "*.pyc", "*/__pycache__/*"]
TEXT_EXT = {".md", ".py", ".jsx", ".js", ".mjs", ".ps1", ".json", ".txt", ".html", ".css", ".csv", ".tpl", ".example",
            ".sh", ".yml", ".yaml", ".toml", ".srt", ".xml", ".gitignore", ""}
SECRETS = [
    (r"sk-[A-Za-z0-9_\-]{24,}", "API key (sk-)"),
    (r"sk_[a-f0-9]{30,}", "API key (sk_)"),
    (r"AIza[0-9A-Za-z_\-]{30,}", "Google API key"),
    (r"gsk_[A-Za-z0-9]{24,}", "Groq key"),
    (r"nvapi-[A-Za-z0-9_\-]{20,}", "NVIDIA key"),
    (r"gh[pousr]_[A-Za-z0-9]{30,}", "GitHub token"),
    (r"[A-Za-z0-9._%+\-]+@(gmail|outlook|hotmail|yahoo|icloud)\.com", "personal e-mail"),
]


def term_regex(term):
    """ALL-CAPS codes (CLA, AG2) match only as a code: not inside a longer word. Anything else is used as written
    (a term may itself be a regex, e.g. a lookahead)."""
    if re.fullmatch(r"[A-Z]{2,5}", term):
        return r"(?<![A-Za-z])" + term + r"(?![a-z])"
    return term if re.search(r"[\\(\[]", term) else re.escape(term)


def load_settings(path):
    if not os.path.exists(path):
        sys.exit("export_public: settings file not found: %s\n(it lives in the private clients repo; without it "
                 "nothing can be checked for client names, so nothing is exported)" % path)
    cfg = json.load(open(path, encoding="utf-8"))
    pairs = [(t, alias) for alias, terms in cfg.get("aliases", {}).items() for t in terms]
    pairs.sort(key=lambda p: -len(p[0]))                       # longest spelling first
    cfg["_subs"] = [(re.compile(term_regex(t)), alias) for t, alias in pairs]
    cfg["_leaks"] = [(re.compile(term_regex(t)), "client name") for t, _ in pairs]
    cfg["_leaks"] += [(re.compile(rx), why) for rx, why in SECRETS]
    cfg["_leaks"] += [(re.compile(rx), "forbidden") for rx in cfg.get("forbidden_regex", [])]
    return cfg


def excluded(rel, patterns):
    for p in patterns:
        if p.endswith("/"):
            if rel.startswith(p):
                return True
        elif fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(os.path.basename(rel), p):
            return True
    return False


def is_text(rel, data):
    ext = os.path.splitext(rel)[1].lower()
    if os.path.basename(rel).startswith(".git"):
        ext = ".gitignore"
    if ext not in TEXT_EXT or b"\x00" in data[:4096]:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def markers(text):
    out, skip = [], False
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("<!--private:start"):
            skip = True; continue
        if s.startswith("<!--private:end"):
            skip = False; continue
        if skip or "<!--private-->" in line:
            continue
        if s.startswith("<!--public:start") or s.startswith("public:end-->"):
            continue
        out.append(line)
    return "\n".join(out)


def sub_all(text, cfg):
    n = 0
    for rx, alias in cfg["_subs"]:
        text, k = rx.subn(alias, text)
        n += k
    return text, n


def transform(rel, data, cfg):
    """-> (public rel path, public bytes, number of replacements)"""
    new_rel, n = sub_all(rel, cfg)
    if not is_text(rel, data):
        return new_rel, data, n
    text = data.decode("utf-8")
    if rel.lower().endswith(".md"):
        text = markers(text)
    drops = cfg.get("drop_lines_containing", [])
    if drops:
        text = "\n".join(l for l in text.split("\n") if not any(d in l for d in drops))
    text, k = sub_all(text, cfg)
    return new_rel, text.encode("utf-8"), n + k


def scan(rel, data, cfg):
    hits = []
    for rx, why in cfg["_leaks"]:
        m = rx.search(rel)
        if m:
            hits.append("%s  [file name]  %s: %s" % (rel, why, m.group(0)))
    if is_text(rel, data):
        for i, line in enumerate(data.decode("utf-8").split("\n"), 1):
            for rx, why in cfg["_leaks"]:
                m = rx.search(line)
                if m:
                    hits.append("%s:%d  %s: %s" % (rel, i, why, m.group(0)[:60]))
    return hits


def source_files():
    r = subprocess.run(["git", "-C", ROOT, "-c", "core.quotepath=off", "ls-files", "-co", "--exclude-standard"],
                       capture_output=True)
    if r.returncode != 0:
        sys.exit("export_public: git ls-files failed in %s" % ROOT)
    return [f for f in r.stdout.decode("utf-8").split("\n") if f and os.path.isfile(os.path.join(ROOT, f))]


def main():
    ap = argparse.ArgumentParser()
    parent = os.path.dirname(ROOT)
    ap.add_argument("--out", default=os.path.join(parent, "claude-workflow-public"))
    ap.add_argument("--archive", default=os.path.join(parent, "_Archive"))
    ap.add_argument("--settings", default=os.path.join(ROOT, "Kit_04_Clients", "_public_export.json"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    cfg = load_settings(a.settings)
    out_patterns = ALWAYS_OUT + cfg.get("exclude", [])

    result, replaced, hits = {}, 0, []                       # public rel -> (bytes or None, source path)
    jobs = [(f, os.path.join(ROOT, f)) for f in source_files() if not excluded(f, out_patterns)]
    overlay = os.path.join(ROOT, "public_overlay")
    for d, _, names in os.walk(overlay):
        for n in names:
            p = os.path.join(d, n)
            jobs.append((os.path.relpath(p, overlay).replace("\\", "/"), p))   # overlay wins: it comes last
    for rel, src in jobs:
        data = open(src, "rb").read()
        new_rel, new_data, n = transform(rel, data, cfg)
        replaced += n
        hits += scan(new_rel, new_data, cfg)
        result[new_rel] = (new_data, src)

    print("export_public: %d files, %d client spellings replaced, %d problems" % (len(result), replaced, len(hits)))
    if hits:
        for h in hits[:80]:
            print("  LEAK  " + h)
        if len(hits) > 80:
            print("  ... and %d more" % (len(hits) - 80))
        sys.exit("export_public: nothing written. Add the spelling to the aliases, or mark the line private.")
    if a.check:
        print("export_public: check only, nothing written")
        return

    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    stale = []
    for d, dirs, names in os.walk(out):
        if ".git" in dirs:
            dirs.remove(".git")
        for n in names:
            rel = os.path.relpath(os.path.join(d, n), out).replace("\\", "/")
            if rel not in result:
                stale.append(rel)
    if stale:
        dst = os.path.join(a.archive, datetime.date.today().isoformat(), "public-export-removed")
        for rel in stale:
            os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
            shutil.move(os.path.join(out, rel), os.path.join(dst, rel))
        print("export_public: %d files no longer exported, moved to %s" % (len(stale), dst))
    changed = 0
    for rel, (data, _) in result.items():
        p = os.path.join(out, rel)
        if os.path.exists(p) and open(p, "rb").read() == data:
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
        changed += 1
    print("export_public: %d files written or updated in %s" % (changed, out))


if __name__ == "__main__":
    main()
