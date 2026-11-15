r"""Install the Claude-Workflow system on this PC for the Claude account(s) that use this Windows user.
Run from anywhere:   python install.py            (the repo root = the folder this file is in)
Dry test:            python install.py --claude-dir <temp folder> --archive <temp folder> --no-env --no-plugins
Show only:           python install.py --dry-run   (prints every step, writes nothing)

What it does (each step is idempotent: running it twice changes nothing the second time):
 1. Backs up <claude-dir>\settings.json and CLAUDE.md to <archive>\<date>\claude-config\ (never deletes anything).
 2. settings.json: sets env.CLAUDE_WORKFLOW = the repo root and adds the 3 hooks (credit guard, kit review at Stop,
    kit review at SessionStart). A hook whose command already runs the same script is updated in place, so an old
    path is replaced, not duplicated. Every other key in settings.json stays as it was.
 3. Copies the Kit skills to <claude-dir>\skills (Kit_01_General_Video_Rules\tools\sync_skills.ps1).
 4. CLAUDE.md: adds the line @<root>/TALK-TO-ME.md if no @...TALK-TO-ME.md line is there (creates the file if needed).
 5. Windows user env var CLAUDE_WORKFLOW (for After Effects and terminals outside Claude Code). --no-env skips it.
 6. git config core.hooksPath .githooks (auto-push + skill sync after each commit), if the root is a git clone.
 7. Plugins in Kit_01_General_Video_Rules\tools\claude_plugins.json: `claude plugin marketplace add` + `claude plugin
    install -s user`. With --claude-dir the CLI gets CLAUDE_CONFIG_DIR=<claude-dir>. --no-plugins skips it.
Formats checked against the Claude Code docs on 13 Nov 2026 (settings / hooks / memory / plugins pages).
"""
import argparse, datetime, json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(ROOT, "Kit_01_General_Video_Rules", "tools")
FWD = ROOT.replace("\\", "/")

# (event, matcher or None, script file, extra args, python flags, timeout) - same as Omar's PC on 13 Nov 2026
HOOKS = [
    ("PreToolUse", "^mcp__.*([Ee]leven[Ll]abs|[Mm]agnific|[Hh]iggsfield)", "credit_guard_hook.py", "", "-I -X utf8 ", 10),
    ("Stop", None, "kit_review_hook.py", "", "", 20),
    ("SessionStart", "startup", "kit_review_hook.py", " --session-start", "-I -X utf8 ", 10),
]


def say(msg):
    print(msg, flush=True)


def backup(paths, archive, dry):
    dst = os.path.join(archive, datetime.date.today().isoformat(), "claude-config")
    for p in paths:
        if not os.path.exists(p):
            continue
        name = os.path.basename(p) + ".before-install-" + datetime.datetime.now().strftime("%H%M%S")
        say("backup: %s -> %s" % (p, os.path.join(dst, name)))
        if not dry:
            os.makedirs(dst, exist_ok=True)
            shutil.copy2(p, os.path.join(dst, name))
            with open(os.path.join(dst, "README.txt"), "a", encoding="utf-8") as f:
                f.write("%s came from %s (install.py, %s)\n" % (name, p, datetime.datetime.now().isoformat(" ", "seconds")))


def merge_settings(s):
    s.setdefault("env", {})["CLAUDE_WORKFLOW"] = ROOT
    hooks = s.setdefault("hooks", {})
    for event, matcher, script, args, flags, timeout in HOOKS:
        cmd = 'python %s"%s/Kit_01_General_Video_Rules/tools/%s"%s' % (flags, FWD, script, args)
        want = {"type": "command", "command": cmd, "timeout": timeout}
        groups = hooks.setdefault(event, [])
        done = False
        for g in groups:
            if g.get("matcher") != matcher:
                continue
            for h in g.get("hooks", []):
                if script in h.get("command", "") and (("--session-start" in h["command"]) == bool(args)):
                    h.update(want); done = True
        if not done:
            g = {"hooks": [want]}
            if matcher is not None:
                g = {"matcher": matcher, "hooks": [want]}
            groups.append(g)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claude-dir", default=os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude"))
    ap.add_argument("--archive", default=os.path.join(os.path.dirname(ROOT), "_Archive"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-env", action="store_true")
    ap.add_argument("--no-plugins", action="store_true")
    a = ap.parse_args()
    cd, dry = os.path.abspath(a.claude_dir), a.dry_run
    settings_p, claude_md = os.path.join(cd, "settings.json"), os.path.join(cd, "CLAUDE.md")
    say("root: %s\nclaude dir: %s%s" % (ROOT, cd, "  (dry run: nothing is written)" if dry else ""))

    backup([settings_p, claude_md], a.archive, dry)

    s = json.load(open(settings_p, encoding="utf-8")) if os.path.exists(settings_p) else {}
    before = json.dumps(s, sort_keys=True)
    s = merge_settings(s)
    if json.dumps(s, sort_keys=True) == before:
        say("settings.json: already up to date")
    else:
        say("settings.json: env.CLAUDE_WORKFLOW + hooks written")
        if not dry:
            os.makedirs(cd, exist_ok=True)
            with open(settings_p, "w", encoding="utf-8", newline="\n") as f:
                json.dump(s, f, indent=2, ensure_ascii=False); f.write("\n")

    sync = os.path.join(TOOLS, "sync_skills.ps1")
    ps = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", sync, "-Dst", os.path.join(cd, "skills")]
    say("skills: " + " ".join('"%s"' % x if " " in x else x for x in ps))
    if not dry:
        r = subprocess.run(ps, capture_output=True, text=True)
        say("  %d skills synced%s" % (r.stdout.count("synced:"), "" if r.returncode == 0 else " - ERROR: " + r.stderr[-300:]))

    line = "@%s/TALK-TO-ME.md" % FWD.replace(" ", "\\ ")   # CLAUDE.md imports: a space is written as "\ " (memory docs)
    text = open(claude_md, encoding="utf-8").read() if os.path.exists(claude_md) else ""
    if any(l.strip().startswith("@") and l.strip().endswith("TALK-TO-ME.md") for l in text.splitlines()):
        say("CLAUDE.md: an @...TALK-TO-ME.md line is already there")
    else:
        say("CLAUDE.md: add " + line)
        if not dry:
            with open(claude_md, "a", encoding="utf-8", newline="\n") as f:
                f.write(("\n" if text and not text.endswith("\n") else "") + "\n" + line + "\n")

    if not a.no_env:
        say("user env var: CLAUDE_WORKFLOW=" + ROOT)
        if not dry:
            subprocess.run(["setx", "CLAUDE_WORKFLOW", ROOT], capture_output=True)

    for repo in (ROOT, os.path.join(ROOT, "Kit_04_Clients")):   # the system repo + the private clients repo if cloned here
        if os.path.isdir(os.path.join(repo, ".git")) and os.path.isdir(os.path.join(repo, ".githooks")):
            say("git: core.hooksPath .githooks in " + repo)
            if not dry:
                subprocess.run(["git", "-C", repo, "config", "core.hooksPath", ".githooks"])

    if not a.no_plugins:
        cfg = json.load(open(os.path.join(TOOLS, "claude_plugins.json"), encoding="utf-8"))
        env = dict(os.environ)
        if a.claude_dir != ap.get_default("claude_dir"):
            env["CLAUDE_CONFIG_DIR"] = cd
        claude = shutil.which("claude") or "claude"
        cmds = [[claude, "plugin", "marketplace", "add", src] for src in cfg["marketplaces"].values()]
        cmds += [[claude, "plugin", "install", p, "-s", "user"] for p in cfg["plugins"]]
        for c in cmds:
            say("plugins: " + " ".join(c[1:]))
            if not dry:
                r = subprocess.run(c, capture_output=True, text=True, env=env)
                out = (r.stdout + r.stderr).strip().splitlines()
                say("  " + (out[-1] if out else "ok"))

    if not os.path.isdir(os.path.join(ROOT, "Kit_04_Clients")):
        say("note: no Kit_04_Clients here (client files are a separate private repo). The system works without it.")
    say("done. Open a NEW Claude Code session so it reads the new settings.")


if __name__ == "__main__":
    main()
