r"""Scan the Claude-Workflow kits for clean-up candidates (plan phase 9, 2026-11-20). Read only: it never edits a kit.

Usage (from anywhere):
    python -I -X utf8 kit_scan.py [--root <Claude-Workflow>] [--out report.md]
<Claude-Workflow> = --root, else env CLAUDE_WORKFLOW, else four folders above this file (skills\kit-maintenance\references).

Checks, in the order of the report:
  1. broken characters: check_text.py errors + a TAB inside a word (a backslash-t that became a tab: «Video_Rules<TAB>ools»).
  2. Kit_01 files longer than FILE_MAX_LINES (the part for one reel type moves to that type's skill).
  3. items longer than LONG_ITEM_CHARS (rule format = two lines at most).
  4. near-duplicate items across files (word overlap >= DUP_MIN_SIM); a pair where only one side says no/never is
     marked «ممكن تعارض». Claude reads both lines before calling it a duplicate or a conflict.
  5. paths written in the kits that don't exist on this PC, and «temporary» lines with a date older than STALE_DAYS.
  6. Kit_01 lines that look like one client's rule: tagged [عميل], or naming exactly one client with no [تقني]/[ذوق عمر] tag.
  7. METRICS.csv trend: per month and per reel type, averages over the cells that are filled (n is printed).
Everything it prints is a candidate, not a verdict.
"""
import argparse, csv, glob, itertools, os, re, subprocess, sys
from collections import defaultdict
from datetime import date

SETTINGS = {
    "FILE_MAX_LINES": 150,      # Kit_01 0*.md files (START-HERE §7)
    "LONG_ITEM_CHARS": 420,     # about two lines in the chat
    "LONG_SHOW": 20,            # print only the longest ones; the total count is printed too
    "DUP_MIN_SIM": 0.55,        # Jaccard over normalised words
    "DUP_MIN_WORDS": 7,         # shorter items are too generic to compare
    "STALE_DAYS": 14,           # «لحد ما / مؤقت» lines older than this
    "TODAY": None,              # None = today; or "2026-11-20" to reproduce a report
}

HERE = os.path.dirname(os.path.abspath(__file__))
MONTHS = {"يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4, "مايو": 5, "يونيو": 6, "يوليو": 7,
          "أغسطس": 8, "اغسطس": 8, "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12}
TEMP_WORDS = re.compile(r"(مؤقت|لحين|for now|temporar)", re.I)   # «لحد ما» is everyday wording: too many false hits
NEG = re.compile(r"(^|\s)(مش|متـ|مت[ا-ي]+|ممنوع|ابدًا|أبدًا|never|don't|do not|no )", re.I)
STOP = set("""في من على عن مع لو او أو ولا اللي الي ده دي دا كده كدا بس كل يعني لما عشان علشان هو هي انت إنت مش لازم
ممكن بعد قبل الـ the and or of to in a an is be for with on at by it this that as from""".split())


def norm_words(s):
    s = re.sub(r"`[^`]*`", " ", s)                      # code spans are names, not wording
    s = re.sub(r"[ً-ْـ]", "", s)          # diacritics, tatweel
    s = s.translate(str.maketrans("أإآىة", "ااايه"))
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return {w for w in s.split() if len(w) > 2 and w not in STOP and not w.isdigit()}


def rule_files(root):
    k1 = os.path.join(root, "Kit_01_General_Video_Rules")
    files = [os.path.join(root, f) for f in ("TALK-TO-ME.md", "START-HERE.md", "NEW-PC-SETUP.md", "THIS-PC.md")]
    files += sorted(glob.glob(os.path.join(k1, "0*.md")))
    files += sorted(glob.glob(os.path.join(k1, "skills", "*", "SKILL.md")))
    files += sorted(glob.glob(os.path.join(root, "Kit_04_Clients", "*.md")))
    return [f for f in files if os.path.isfile(f)]


def items(path):
    """(line_no, text) of every bullet / numbered / table line outside code fences."""
    out, fence, public = [], False, False
    with open(path, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            s = line.rstrip("\r\n")
            if s.lstrip().startswith("```"):
                fence = not fence
                continue
            if "<!--public:start" in s:                  # the public copy's alternative lines repeat the private ones on purpose
                public = True
            if "public:end-->" in s:
                public = False
                continue
            if not fence and not public and re.match(r"\s*([-*]|\d+[.)]|\|)\s", s):
                out.append((i, s.strip()))
    return out


def rel(root, p):
    return os.path.relpath(p, root)


def find_dates(s):
    for m in re.finditer(r"(20\d\d)-(\d\d)-(\d\d)", s):
        yield date(int(m[1]), int(m[2]), int(m[3]))
    for m in re.finditer(r"(\d{1,2})\s+(%s)\s+(20\d\d)" % "|".join(MONTHS), s):
        yield date(int(m[3]), MONTHS[m[2]], int(m[1]))


def clients(root):
    """{alias: code} from Kit_04_Clients\\<CODE> - <name>.md"""
    out = {}
    for f in glob.glob(os.path.join(root, "Kit_04_Clients", "*.md")):
        m = re.match(r"([A-Z]{3}) - (.+)\.md$", os.path.basename(f))
        if m:
            out[m[1]] = m[1]
            out[m[2].strip()] = m[1]
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("CLAUDE_WORKFLOW") or os.path.abspath(os.path.join(HERE, "..", "..", "..", "..")))
    ap.add_argument("--out")
    a = ap.parse_args()
    root, S = a.root, SETTINGS
    today = date.fromisoformat(S["TODAY"]) if S["TODAY"] else date.today()
    files = rule_files(root)
    rep = []
    P = rep.append

    # 1. broken characters
    P("## 1. حروف بايظة")
    ct = os.path.join(root, "Kit_01_General_Video_Rules", "tools", "check_text.py")
    if os.path.isfile(ct):
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", ct, root], capture_output=True, text=True, encoding="utf-8")
        P("check_text.py: " + (r.stdout.strip().splitlines() or ["(no output)"])[-1])
        P("\n".join(l for l in r.stdout.splitlines() if "ERROR" in l.upper())[:3000])
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                if re.search(r"[A-Za-z_]\t[a-z]", line):
                    P("- TAB جوه كلمة: %s:%d  %s" % (rel(root, f), i, line.strip()[:90].replace("\t", "<TAB>")))

    # 2. long Kit_01 files
    P("\n## 2. ملفات Kit_01 أطول من %d سطر" % S["FILE_MAX_LINES"])
    for f in glob.glob(os.path.join(root, "Kit_01_General_Video_Rules", "0*.md")):
        n = sum(1 for _ in open(f, encoding="utf-8", errors="replace"))
        if n > S["FILE_MAX_LINES"]:
            P("- %s: %d سطر" % (rel(root, f), n))

    # 3. long items
    P("\n## 3. بنود أطول من %d حرف" % S["LONG_ITEM_CHARS"])
    all_items, long_ = [], []
    for f in files:
        for i, s in items(f):
            all_items.append((f, i, s))
            if len(s) > S["LONG_ITEM_CHARS"] and not s.startswith("|"):
                long_.append((len(s), f, i, s))
    long_.sort(reverse=True)
    P("%d بند، دول أطول %d:" % (len(long_), min(len(long_), S["LONG_SHOW"])))
    for n, f, i, s in long_[:S["LONG_SHOW"]]:
        P("- %s:%d (%d حرف)  %s…" % (rel(root, f), i, n, s[:70]))

    # 4. near duplicates / possible conflicts
    P("\n## 4. بنود شبه بعض (مكرر أو ممكن تعارض)")
    toks = [(f, i, s, norm_words(s)) for f, i, s in all_items if not s.startswith("|")]
    toks = [t for t in toks if len(t[3]) >= S["DUP_MIN_WORDS"]]
    index = defaultdict(set)
    for k, t in enumerate(toks):
        for w in t[3]:
            index[w].add(k)
    seen = set()
    for k, t in enumerate(toks):
        cand = defaultdict(int)
        for w in t[3]:
            if len(index[w]) < 40:                       # common words don't make a pair
                for j in index[w]:
                    if j > k:
                        cand[j] += 1
        for j, shared in cand.items():
            u = toks[j]
            sim = shared / len(t[3] | u[3])
            both_skills = t[0].endswith("SKILL.md") and u[0].endswith("SKILL.md")   # sibling skills share boilerplate
            if sim >= S["DUP_MIN_SIM"] and (k, j) not in seen and not both_skills:
                seen.add((k, j))
                tag = "ممكن تعارض" if bool(NEG.search(t[2])) != bool(NEG.search(u[2])) else "مكرر؟"
                P("- [%s %.2f] %s:%d  ↔  %s:%d\n    أ: %s\n    ب: %s" % (tag, sim, rel(root, t[0]), t[1], rel(root, u[0]), u[1],
                                                                  t[2][:110], u[2][:110]))

    # 5. missing paths and stale temporary lines
    P("\n## 5. مسارات مش موجودة على الجهاز، وسطور «مؤقتة» قديمة")
    missing = {}
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                for span in re.findall(r"`([^`]+)`", line):
                    p = span.strip().rstrip(".,،:;)")
                    if p.startswith("<Claude-Workflow>"):
                        p = root + p[len("<Claude-Workflow>"):]
                    if not re.match(r"^[A-Za-z]:\\", p) or re.search(r"[<>*?…|]|\.\.\.|%|\$|\{|\bN+\b", p):   # ريل N, reel-NN = placeholders
                        continue
                    p = os.path.expandvars(p)
                    if not os.path.exists(p):
                        missing.setdefault(p, "%s:%d" % (rel(root, f), i))
                if TEMP_WORDS.search(line):
                    old = [d for d in find_dates(line) if (today - d).days > S["STALE_DAYS"]]
                    if old:
                        P("- مؤقت من %s: %s:%d  %s" % (max(old), rel(root, f), i, line.strip()[:90]))
    for p, where in sorted(missing.items()):
        P("- مش موجود: %s  (%s)" % (p, where))

    # 6. one-client rules inside Kit_01
    P("\n## 6. سطور في Kit_01 شكلها قاعدة عميل واحد")
    cl = clients(root)
    pat = re.compile(r"(?<!\w)(%s)(?!\w)" % "|".join(sorted(map(re.escape, cl), key=len, reverse=True))) if cl else None
    for f in glob.glob(os.path.join(root, "Kit_01_General_Video_Rules", "0*.md")):
        for i, s in items(f):
            if "[عميل]" in s:
                P("- [عميل] %s:%d  %s" % (rel(root, f), i, s[:100]))
            elif pat and not s.startswith("|") and "[تقني]" not in s and "[ذوق عمر]" not in s:
                body = re.sub(r"\([^)]*\)", " ", s)            # (عمر، CLA R6، ...) is where it came from, not who it's for
                found = {cl[m] for m in pat.findall(body)}
                if len(found) == 1:
                    P("- %s %s:%d  %s" % (found.pop(), rel(root, f), i, s[:100]))

    # 7. METRICS trend
    P("\n## 7. اتجاه METRICS.csv")
    mp = os.path.join(root, "METRICS.csv")
    if not os.path.isfile(mp):
        P("- الملف مش موجود.")
    else:
        rows = list(csv.DictReader(open(mp, encoding="utf-8-sig")))
        P("- %d ريل في الملف." % len(rows))

        def num(r, k):
            try:
                return float(r.get(k) or "")
            except ValueError:
                return None

        for key, label in (("month", "الشهر"), ("type", "النوع")):
            groups = defaultdict(list)
            for r in rows:
                g = (r.get("date") or "")[:7] if key == "month" else (r.get("type") or "")
                groups[g or "؟"].append(r)
            P("\n| %s | ريلز | النسخ لحد الاعتماد (متوسط، n) | رفض العميل (متوسط، n) | جلسات (متوسط، n) |" % label)
            P("|---|---|---|---|---|")
            for g in sorted(groups):
                cells = []
                for k in ("versions_to_approval", "client_rejections", "sessions"):
                    v = [x for x in (num(r, k) for r in groups[g]) if x is not None]
                    cells.append("%.1f (%d)" % (sum(v) / len(v), len(v)) if v else "—")
                P("| %s | %d | %s |" % (g, len(groups[g]), " | ".join(cells)))
        spend = defaultdict(lambda: defaultdict(float))
        for r in rows:
            for part in (r.get("credits") or "").split(";"):
                m = re.match(r"\s*([\w-]+)\s*:\s*([\d.]+)", part)
                if m:
                    spend[(r.get("date") or "؟")[:7]][m[1]] += float(m[2])
        if spend:
            P("\nالكريدت لكل شهر (من الخانات المليانة بس):")
            for mo in sorted(spend):
                P("- %s: %s" % (mo, "، ".join("%s %g" % kv for kv in sorted(spend[mo].items()))))

    text = "\n".join(x for x in rep if x is not None)
    if a.out:
        open(a.out, "w", encoding="utf-8", newline="\n").write(text + "\n")
        print("wrote", a.out, "(%d lines)" % text.count("\n"))
    else:
        print(text)


if __name__ == "__main__":
    main()
