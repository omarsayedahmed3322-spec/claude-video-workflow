# 00 — القواعد السريعة (اقرا ده بس في أول أي فيديو)

> صفحة واحدة بدل ما تقرا `01`–`05` كاملين في أول الجلسة. افتح الملف الكامل **في المرحلة اللي محتاجاه بس**، والقسم المطلوب بس (الجدول تحت).
> لو قاعدة هنا عكس الملف الكامل، الملف الكامل هو الأصل — صلّح هنا.

## Every video
- Kick-off: class `A/B/C/D` + client + reel + format/fps/length + VO + reference (`START-HERE` §3). Brief vs kit conflict → ask once.
- Work goes in the client's reel folder (`Kit_04_Clients\README.md`). `PROJECT_STATE.md` there = handoff; read it instead of re-exploring.
- One scene per session on long projects. Beats Plan second-by-second → **stop for approval** (A/B).
- Cuts come from the **measured VO**, never from brief timecodes. Cut 1 frame inside the silence gap. Caption line leaves 0.12s after its last word.
- Nothing is built before references + assets are in: kick-off asks for references + existing files; after the Beats Plan, one request for everything to be made, each with tool + prompt (code block) + settings + save path (`01` §A, sources table `01` §D). Check every AI clip end to end; never start at its first frame. A gesture or payoff near a clip's end (thumbs up, handshake) stays in: trim the start, not the end (Omar, CLI R3 2026-11-12). **Before any paid generation (Higgsfield, Flow, Codex image) read the credits rules in `01` (Higgsfield MCP / Flow bullets) first:** cheap models at 720p, one shot at a time, `get_cost` first, ask above ~30 credits (CLA R1 burned ≈358 credits on Seedance because that section wasn't read).
- VO to be made → Claude writes it ready to paste in ElevenLabs v3 with audio tags (`05` §3b).
- Client footage (UGC/ready edits): check for burned-in titles before captioning and hide captions over them (`01` §D). Whisper on Windows needs `PYTHONIOENCODING=utf-8` (`03`) and the `small` model only: `medium` isn't cached and silently starts a 1.4 GB download (CLE R3 edit, 2026-11-12: 6 min lost on a 33 s voice note); with `python -I` that variable is ignored, so call `sys.stdout.reconfigure(encoding='utf-8')`. Don't force `--language ar` before knowing the language: CLA's doctor spoke English and `ar` returned a garbled translation. ffmpeg `drawtext` needs `fontfile='C\:/Windows/Fonts/arial.ttf'` or it segfaults on Fontconfig `[تقني]`.
- B-roll from event shoots / client sites: skip frames with crew, rigs or script notes in hand, and web banners with baked-in buttons («ORDER NOW») or callouts — agy flagged both as amateur (CLA R1). Use the clean product render or an AI shot made from it.
- Review = **MP4 with VO**. Never say "done/fixed" before seeing it in the MP4.
- Every render → `tools\qc_reel.py` (`ae_render.ps1 -Type` runs it). **No version goes to Omar with a «سقط»** (`01` §E).

## Building in AE
- Which engine (ffmpeg / HyperFrames / AE / Premiere XML) for which job: the table in `04` §0.
- Run scripts: `tools/ae_run.ps1 -Jsx <file>` (runner saves + versions first). Render: `tools/ae_render.ps1` (`-Preview` for timing). No `alert()`.
- Every scene comp: `CTRL` null via `// claude-include: ...\tools\ctrl_rig.jsx`; user tweaks live there.
- Motion: never LINEAR; snappy in 85/15, S-curve 80/80, whip 15/85; overlap 2–4 frames; bounce only on icons/cards/logos. Default per reel type (talking head, music montage, UI motion, documentary): the table in `02` §0. "Nothing fully static" and "no plain opacity fades (motion + blur)" are the fast motion-graphics default, not every reel.
- Safe zone 1080×1920: y 250–1420, x 60–950; captions centred y≈1330; max text width ~880.
- No emoji in on-screen text, in any client video, unless Omar asks (`03`).
- Arabic in AE: PostScript font name, no stroke on Arabic, no RLM, kashida only between joined letters. Word-by-word captions can be a HyperFrames overlay (`03` last section).

## Sound
- Library first (`SFX_Library`), ElevenLabs only for what's missing, via MCP. Levels per reel type (VO, seated talking head, client clip, music only): the table in `05` §6. Any recorded voice of a person: peaks −10…−6 dBFS, cleaned in Adobe Podcast by Omar first (`05` §5b).

## Open the full file only when
| When | Open |
|---|---|
| Planning phases, assets, AI clips, deliverable names | `01_workflow.md` (§A–E — only the section in play) |
| Writing motion / camera / layout code | `02_motion_laws.md` (§0 = default per reel type) |
| Logo on a van / product / sign, or removing / moving a logo in a clip | skill `logo-on-object` |
| A reel of a real person talking (seated speaker, presenter, doctor, interview) | skill `reel-talking-head` |
| A reel cut to music with no VO (showcase, cut on the beat, rough cut, colour, crash-zoom burst) | skill `reel-music-montage` |
| Arabic text in AE (kashida, alignment, typewriter) or HF captions | `03_arabic_typography.md` |
| Running / rendering / debugging AE, a script error | `04_ae_mcp_playbook.md` (§5–7 gotchas) |
| VO measuring, SFX, mix | `05_audio_sfx.md` + skill `reel-sound-design` |
