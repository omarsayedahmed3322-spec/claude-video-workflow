"""Find hidden control characters in the Kit's .md / .txt files.

Why: Windows paths written from a script as plain strings turned backslash-f, -a, -v, -r and
-01 into control characters (13 broken spots found on 10 Nov 2026). This tool catches them.

Usage (always with -I -X utf8 so Arabic prints):
    python -I -X utf8 check_text.py <folder or file> [<folder or file> ...]
    python -I -X utf8 check_text.py --staged      (only the files in the commit; run by .githooks/pre-commit)

Errors (exit 1): any byte 0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F, or a CR not followed by LF.
Warnings only (looks like a path or sentence that broke into two lines, e.g. a backslash-r
that became a real line break): a line that starts with a lowercase English letter while the
line before it does not end with '.' or '|' and leaves a backtick span open (odd number of
backticks). Lines inside ``` code fences are skipped. Without the backtick and fence
conditions the warning list was 3610 lines long and nobody would read it.
TAB and CRLF are normal and are not reported.
"""
import os
import sys

EXTS = (".md", ".txt")
BAD = set(range(0x00, 0x09)) | {0x0B, 0x0C} | set(range(0x0E, 0x20))
SKIP_DIRS = {".git", "node_modules", "__pycache__"}


def iter_files(args):
    for a in args:
        if os.path.isfile(a):
            if a.lower().endswith(EXTS):
                yield a
        elif os.path.isdir(a):
            for root, dirs, files in os.walk(a):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for f in files:
                    if f.lower().endswith(EXTS):
                        yield os.path.join(root, f)
        else:
            print(f"not found: {a}")


def show(s):
    out = []
    for c in s:
        if c == "\r":
            out.append("<CR>")
        elif c == "\n":
            out.append("<LF>")
        elif ord(c) < 0x20 and c != "\t":
            out.append(f"[0x{ord(c):02X}]")
        else:
            out.append(c)
    return "".join(out)


def check(path):
    errors, warns = [], []
    text = open(path, "rb").read().decode("utf-8", errors="replace")
    line = 1
    for i, ch in enumerate(text):
        o = ord(ch)
        if ch == "\n":
            line += 1
        elif ch == "\r":
            if i + 1 >= len(text) or text[i + 1] != "\n":
                errors.append((line, "CR without LF", show(text[max(0, i - 20): i + 20])))
        elif o in BAD:
            errors.append((line, f"control 0x{o:02X}", show(text[max(0, i - 20): i + 20])))
    lines = text.replace("\r\n", "\n").split("\n")
    fence = False
    for n, cur in enumerate(lines):
        if cur.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence or n == 0:
            continue
        prev = lines[n - 1].rstrip()
        if (cur[:1].isascii() and cur[:1].islower() and prev and not prev.endswith((".", "|"))
                and prev.count("`") % 2 == 1):
            warns.append((n + 1, "line starts lowercase after an unfinished line", show(cur[:40])))
    return errors, warns


def staged_files():
    """Files added/changed in the commit being made (used by .githooks/pre-commit)."""
    import subprocess
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"],
                         capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p and os.path.isfile(p)]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    targets = staged_files() if sys.argv[1] == "--staged" else sys.argv[1:]
    n_err = n_warn = n_files = 0
    for path in iter_files(targets):
        n_files += 1
        errors, warns = check(path)
        for ln, kind, ctx in errors:
            print(f"ERROR {path}:{ln}  {kind}  ...{ctx}...")
        for ln, kind, ctx in warns:
            print(f"warn  {path}:{ln}  {kind}  {ctx}")
        n_err += len(errors)
        n_warn += len(warns)
    print(f"checked {n_files} file(s): {n_err} error(s), {n_warn} warning(s)")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
