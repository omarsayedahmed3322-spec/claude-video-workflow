"""Kit review hooks for the Claude-Workflow kits.

Stop mode (default, hooks.Stop): at the END of a session, ask Claude to evolve the kits with everything it learned,
in one pass and one commit.
SessionStart mode (`--session-start`, hooks.SessionStart, matcher startup): if the previous session in the same project
folder did real work and was never reviewed, print one line (plain stdout goes into Claude's context).

Wired in ~\\.claude\\settings.json by install.ps1. Reads the hook JSON on stdin.
Edits land in <Claude-Workflow> itself (the PC copy); .githooks\\post-commit then syncs skills and pushes.
<Claude-Workflow> = env CLAUDE_WORKFLOW, else the folder two levels above this file.
- Omar (CLA R1, 2026-11-10): «التحديث يكون آخر كل جلسة، مش ع الفاضي وع المليان، وكذلك الـ commit». A Stop hook fires after
  every turn and can't see the session ending, so it only fires when Omar's last message closes the session (CLOSE_WORDS,
  short messages only) or asks for the review itself (REVIEW_WORDS, any length), and only if real work happened since the
  last review.
- Plan phase 2 (2026-11-11): closing words count only in a short message (< SHORT_MSG chars), so «شكرا، دلوقتي اعمل كذا»
  doesn't trigger it. Omar chose: the 5-line Arabic summary is shown BEFORE the commit and waits for his OK.
- Never loops: skips when stop_hook_active is true. The per-session marker stores the tool counts at the last review.
"""
import glob, json, os, re, sys

ROOT = os.environ.get("CLAUDE_WORKFLOW") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MIN_EDITS, MIN_BASH = 3, 12
SHORT_MSG = 40
MARKS = os.path.join(os.path.expanduser("~"), ".claude", "state", "kit_review")
# closing phrases (Egyptian Arabic + English): only in a short last message
CLOSE_WORDS = re.compile(
    r"(خلصنا|خلاص كده|كده تمام|تمام كده|كفاية كده|هنقفل|اقفل الجلسة|نقفل|سلام|شكرا|شكراً|تسلم|يعطيك العافية|"
    r"\bdone\b|\bthanks\b|\bbye\b|wrap ?up)", re.I)
# explicit review requests: any length
REVIEW_WORDS = re.compile(
    r"(حدّ?ث الكيتس|راجع الكيتس|مراجعة الكيتس|حدّ?ث الورك ?فلو|اعمل المراجعة|update the kits)", re.I)


def last_user_text(path):
    """Text of the last message Omar typed (tool results and system notices don't count)."""
    last = ""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"type":"user"' not in line and '"type": "user"' not in line:
                continue
            try:
                m = json.loads(line).get("message", {})
            except Exception:
                continue
            c = m.get("content")
            if isinstance(c, str):
                txt = c
            elif isinstance(c, list):
                txt = " ".join(p.get("text", "") for p in c if isinstance(p, dict) and p.get("type") == "text")
            else:
                txt = ""
            txt = txt.strip()
            if txt and not txt.startswith("<"):          # skip <task-notification>, <system-reminder>, hook echoes
                last = txt
    return last


def wants_review(txt):
    if REVIEW_WORDS.search(txt):
        return True
    return len(txt) < SHORT_MSG and bool(CLOSE_WORDS.search(txt))


def count_tools(path):
    """Counts only (never loads the transcript into context): (edits, shells)."""
    edits = shells = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"tool_use"' not in line:
                continue
            edits += line.count('"name":"Write"') + line.count('"name":"Edit"')
            shells += line.count('"name":"Bash"') + line.count('"name":"PowerShell"')
    return edits, shells


def read_mark(sid):
    mark = os.path.join(MARKS, sid + ".done")
    if os.path.exists(mark):
        try:
            e, s = (int(x) for x in open(mark).read().split())
            return e, s
        except Exception:
            pass
    return 0, 0


def unreviewed(edits, shells, last_e, last_s):
    return edits - last_e >= MIN_EDITS or shells - last_s >= MIN_BASH


def session_start(d):
    if d.get("source", "startup") != "startup":
        return
    cur = d.get("transcript_path", "")
    folder = os.path.dirname(cur) if cur else ""
    if not folder or not os.path.isdir(folder):
        return
    cur_id = d.get("session_id") or os.path.splitext(os.path.basename(cur))[0]
    others = [p for p in glob.glob(os.path.join(folder, "*.jsonl"))
              if os.path.splitext(os.path.basename(p))[0] != cur_id]
    if not others:
        return
    prev = max(others, key=os.path.getmtime)
    sid = os.path.splitext(os.path.basename(prev))[0]
    try:
        edits, shells = count_tools(prev)
    except Exception:
        return
    if unreviewed(edits, shells, *read_mark(sid)):
        print("مراجعة الكيتس: الجلسة اللي فاتت في نفس الفولدر اتقفلت من غير مراجعة (%d Edit/Write، %d Bash). "
              "الترانسكريبت: %s . قول لعمر في سطر واسأله يراجعها ولا لأ، ومتقراش الترانسكريبت كله." % (edits, shells, prev))


def stop(d):
    if d.get("stop_hook_active"):
        return
    path = d.get("transcript_path", "")
    try:
        if not wants_review(last_user_text(path)):
            return
    except Exception:
        return
    sid = d.get("session_id") or "unknown"
    last_e, last_s = read_mark(sid)
    try:
        edits, shells = count_tools(path)
    except Exception:
        return
    if not unreviewed(edits, shells, last_e, last_s):
        return
    os.makedirs(MARKS, exist_ok=True)
    open(os.path.join(MARKS, sid + ".done"), "w").write("%d %d" % (edits, shells))
    reason = (
        "مراجعة آخر الجلسة: الجلسة بتقفل، فراجع كل اللي اتعلمته فيها مرة واحدة، وعدّي على القايمة دي بند بند "
        "(الأماكن وسلّم الترقية وشكل القاعدة في {R}\\START-HERE.md قسم 7، واقرا القسم قبل ما تعدّل):\n"
        "سلّم الترقية: ملاحظة على نسخة شغالة = PROJECT_STATE.md بتاع الريل بس. بعد اعتماد الريل، اللي ثبت يتنقل لملف العميل في Kit_04. "
        "تدخل Kit_01 في حالتين بس: حقيقة تقنية (خطأ أداة وحله)، أو ذوق اتكرر عند عميلين أو عمر قال صريح «دي في كل الريلز».\n"
        "شكل القاعدة: سطرين بالكتير: إيه + الرقم + النوع ([تقني] أو [ذوق عمر] أو [عميل]) + الريل والتاريخ. الحكاية وكلام العميل مكانهم CHANGELOG.md.\n"
        "1) تصحيحات وتفضيلات المستخدم: القاعدة في مكانها الواحد حسب السلّم (Kit_01 من 01 لـ 05، أو {R}\\TALK-TO-ME.md لطريقة الكلام والتعامل).\n"
        "2) أخطاء وقعت فيها وحلها (سكريبت، رندر، أداة، أمر علّق): قسم الـ gotchas في الملف المناسب (غالبًا Kit_01\\04_ae_mcp_playbook.md).\n"
        "3) ترتيب الشغل والخطوات، أو طريقة أحسن لحاجة: Kit_01\\01_workflow.md.\n"
        "4) السكيلز: أي سكيل استخدمتها أو اتعلمت حاجة تخصها (free-llm-delegate، reel-sound-design، logo-on-object، style-...): عدّل SKILL.md "
        "أو references جواها في Kit_01_General_Video_Rules\\skills\\. ولو تكنيك جديد اتكرر واتعتمد، اقترح سكيل جديدة.\n"
        "5) العميل: لو الشغل ريل لعميل، أي ملاحظة أو قرار ستايل يخصه (ترانزيشنز، صوت، كادر، ألوان، فوتيج، شكل النسخة المعتمدة) "
        "يروح لـ Kit_04_Clients\\<الكود> - <الاسم>.md. اقراه كله، وشيل أو صلّح أي كلام فيه بقى قديم أو بيعارض الجديد "
        "(CLA R1: الملف فضل يقول «ووش مع كل ترانزيشن» بعد ما عمر رفضه).\n"
        "6) الريل نفسه: PROJECT_STATE.md (وHANDOFF.md لو موجود) بالحالة وآخر نسخة، عشان أي اكونت يكمّل.\n"
        "7) مسارات أو أدوات جديدة على الجهاز: THIS-PC.md.\n"
        "8) لو الجلسة كانت شغل في ريل: حدّث صف الريل في {R}\\METRICS.csv (أو ضيف صف لو مش موجود): النسخ لحد الاعتماد، "
        "ومرات رفض العميل، والكريدت لكل خدمة، وعدد الجلسات (زوّد 1)، والحالة. الرقم اللي مش متأكد منه سيبه فاضي، متخمّنش. "
        "الأعمدة في أول سطر في الملف، وشكل الكريدت (magnific:320;higgsfield:45) في START-HERE.md قسم 7.\n"
        "القواعد: لو في قاعدة قديمة أضعف استبدلها، ولو مكررة ادمجها، ولو جديدة حطها في مكانها المنطقي مش في آخر الملف، "
        "ومتكتبش نفس القاعدة في مكانين. عدّل في {R} نفسه على الجهاز (مش worktree ولا clone تاني)، على فرع master.\n"
        "قبل الحفظ (قرار عمر 11 نوفمبر 2026): اعرض على عمر ملخص عربي 5 سطور بالتعديلات (إيه اتغير وفين)، واستنى موافقته. "
        "متعملش commit قبل ما يوافق.\n"
        "بعد موافقته: سطر واحد في CHANGELOG.md للجلسة كلها، وcommit واحد؛ هوك الـ commit بينسخ السكيلز لـ ~\\.claude\\skills لوحده "
        "لو اتغيرت، وبيرفع على GitHub. لو بند مالوش جديد عدّيه، ولو مفيش جديد خالص قول كده في سطر واحد بس."
    ).replace("{R}", ROOT)
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=True))


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return
    if "--session-start" in sys.argv:
        session_start(d)
    else:
        stop(d)

main()
