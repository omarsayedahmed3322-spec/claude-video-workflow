# تجهيز أي جهاز جديد

> اقرا الملف ده لو مسارات `THIS-PC.md` مش موجودة على الجهاز اللي إنت عليه.
> دوّر الأول على الموجود. بعدين ابعتلي في رسالة واحدة: لقيت إيه، وناقص إيه، والمقترحات اللي تحت **الناقصة بس**.
> متعملش أي فولدر، ولا تنزّل أو تسطّب أي حاجة، قبل ما أوافق.
> الكلام اللي بين «» تحت ده بلسانك إنت ليا.

---

## 1. أول خطوة: الفولدر ده نفسه

- «الفولدر ده نازل من ريبو عمر على GitHub. تحديثاته بتيجي بـ `git pull` من جوه الفولدر، وقواعدك إنت مكانها `MY-RULES.md` (الشرح في `START-HERE.md` قسم 7).»
- «بعدها أشغّل سكريبت التسطيب مرة واحدة: `python install.py` من جوه الفولدر (محتاج Python و`claude` على الـ `PATH`). ده بيعمل كل اللي تحت لوحده: بياخد نسخة من `~\.claude\settings.json` و`CLAUDE.md` للأرشيف، وبيحط متغير `CLAUDE_WORKFLOW` بمسار الفولدر، وبيركّب الهوكس التلاتة (حماية الكريدت، ومراجعة آخر الجلسة، وتنبيه أول الجلسة)، وبينسخ السكيلز، وبيضيف سطر `@<الفولدر>/TALK-TO-ME.md` في `~\.claude\CLAUDE.md`، وبيشغّل `git config core.hooksPath .githooks`، وبيسطّب البلاجنز اللي في `Kit_01_General_Video_Rules\tools\claude_plugins.json`. لو اتشغّل مرتين مش بيكرر حاجة. عشان تشوف هيعمل إيه من غير ما يكتب حاجة: `python install.py --dry-run`.»
- «بعد التسطيب افتح جلسة Claude جديدة عشان تقرا الإعدادات الجديدة.»
- «وأقترح أعملك نفس الباك أب اليومي: مهمة ويندوز بتشغّل `Kit_01_General_Video_Rules\tools\daily_backup.ps1` كل يوم، عشان أي تعديل بإيدك يترفع.»
- «بعد كده أكتب نسخة جديدة من `THIS-PC.md` بمسارات الجهاز ده (وأحتفظ بالقديمة باسم `THIS-PC_<اسم الجهاز التاني>.md`).»
- «مكتبة الساوند `SFX_Library\` بقت جوه الريبو من 13 نوفمبر 2026، فبتنزل مع الفولدر.»
- «لو الفولدر مش متاح خالص، الصقلي `START-HERE.md` والكيت اللي محتاجينه في الشات، وأنا أشتغل منهم.»

---

## 2. الفولدرات

- **فولدر العملاء:** «أقترح عليك تعملّي فولدر `Clients\` بنظام العميل ← `ريل 1`…`ريل 10` ← `assets/footage/exports - <CODE> R<N>` (الشرح في `Kit_04_Clients\README.md`). أقدر أعمله لكل العملاء بسكريبت واحد لو وافقت.»
- **ملف `CLAUDE.md` لكل عميل:** «هعمل في فولدر كل عميل ملف `CLAUDE.md` من 3 سطور (الاسم والكود، وأمر يقرا ملفه من `Kit_04_Clients`، واكونت التوليد المسموح)، زي اللي على الجهاز الأساسي، وأي عميل جديد بيتعمله واحد. الشكل في `Kit_04_Clients\README.md`.»
- **مكتبة الساوند:** «لو `SFX_Library\` ماجتش مع الفولدر (ممكن تتشال عشان حجمها ~44 ميجا)، أقترح عليك تسيبلي فولدر ساوند إفكتس فيه الـ 12 صوت الأساسيين و`generations.json`، وجواه فولدر مكتبتك متقسم: `whoosh` و`risers and hits` و`textures` و`Flex UI SFX`. كده مش هولّد من ElevenLabs غير اللي ناقص.»
- **الريفرنسات:** «أقترح عليك تحط فيديو الريفرنس بتاع كل عميل في `Master Assets` بتاعه (زي ريفرنس CLG وريفرنس CLF).»
- **هوية كل عميل:** «حط لوجو كل عميل بجودة عالية (PNG شفاف) في `Master Assets` بتاعه. لو مفيش، هقص اللوجو من الريفرنس كحل مؤقت.»
- **الأرشيف:** «أقترح فولدر `_Archive` برا `Claude-Workflow`، أحط فيه أي نسخة مكررة بدل ما أمسحها.»

---

## 3. البرامج والأدوات

- **برنامج After Effects** (2026 لو ينفع)، ومعاه Premiere Pro وMedia Encoder لو موجودين.
- **برنامج بايثون 3** ومعاه: `numpy scipy soundfile librosa pyloudnorm opencv-python matplotlib`.
- **برنامج Node.js** عشان أفحص الـ JSX قبل ما أشغّله.
- **برنامجين `ffmpeg` و`ffprobe`** على الـ `PATH`.
- **برنامج `git`** عشان كل تعديل في الورك فلو يبقى ليه نسخة.
- **الخطوط:** `Palestine` و`Montserrat` (Black) و`Lalezar` و`Cairo` (Black) و`Lyon Arabic Display`. «اتأكد إنهم متركبين، وأنا هتأكد من أسمائهم الـ PostScript جوه AE.»

---

## 4. الـ MCP والسكيلز

- **أداة `AfterEffectsMCP`** + سكريبت البريدج `mcp-bridge-auto.jsx` في `Scripts\ScriptUI Panels` بتاع AE: «للتعديلات الصغيرة من غير ما أبني من الأول.»
- **بانل تشغيل السكريبتات (Claude Runner):** «هشغّل `Kit_01_General_Video_Rules\tools\ae_runner\install_ae_runner.ps1` وبعدين `setup_render_templates.jsx` مرة واحدة، عشان أشغّل السكريبتات في AE من غير `-r` ولا Computer Use.»
- **أداة `hyperframes`:** «`npm install -g hyperframes` (محتاجة Node 22 أو أحدث و`ffmpeg`)، للكابشن العربي كطبقة شفافة.»
- **أداة `ElevenLabs` MCP:** «للفويس والـ SFX اللي مش في المكتبة. هعمل `check_subscription` الأول عشان أعرف حدود الاكونت.»
- **حماية الكريدت (لازم على أي جهاز جديد، و`install.py` بيركّبها):** «هوك `PreToolUse` في `~\.claude\settings.json` بيشغّل `Kit_01_General_Video_Rules\tools\credit_guard_hook.py` على أي أداة من ElevenLabs أو Magnific أو Higgsfield، عشان يسألك قبل أي صرف كريدت. الـ matcher هو `^mcp__.*([Ee]leven[Ll]abs|[Mm]agnific|[Hh]iggsfield)`. هجرّبه بأداة صرف وانت ترفض.»
- **السكيلز (كلها في `Kit_01_General_Video_Rules\skills\`، ومعاها سكيلز التفويض `agy-delegate` و`claude-delegate` و`codex-delegate` و`opencode-delegate` و`delegate-setup` من 13 نوفمبر 2026):** «`install.py` بينسخها لـ `~\.claude\skills\` بسكريبت `sync_skills.ps1`.»
- **البلاجنز (`hyperframes` و`remotion`):** «`install.py` بيضيف الماركت بليس وبيسطّبهم، والقايمة في `Kit_01_General_Video_Rules\tools\claude_plugins.json`.»
- **الـ Computer Use:** «بس للخطوات اللي مفيش طريقة تانية ليها.»

---

## 5. بعد التجهيز

- «هكتب `THIS-PC.md` بمسارات الجهاز ده، وأضيف سطر في `CHANGELOG.md`.»
- «سطر `@<مسار الفولدر>/TALK-TO-ME.md` في `~\.claude\CLAUDE.md` بيحطه `install.py` (بيسحب قواعد الكلام في كل جلسة، اتجرب 11 نوفمبر 2026). هضيف تحته بإيدي سطر بيقول: اقرا `START-HERE.md` كله في شغل الفيديو. شكل الملف زي `~\.claude\CLAUDE.md` على الجهاز الأساسي.»
