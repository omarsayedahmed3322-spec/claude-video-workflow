# 05 — الصوت: الفويس والقطع والـ SFX (Audio, VO & SFX)

> الشغل الكامل للـ sound design (تحليل، cue sheet، توليد، QC، ستيمز) في السكيل
> `skills/reel-sound-design/SKILL.md` (متركّب كمان في `~/.claude/skills/reel-sound-design`).
> الملف ده = الأرقام المقاسة والمعتمدة (المستويات مكتوبة هنا بس، في §6). السكيل = الخطوات.

## 1. Cuts come from the VO, never from the brief
- Before every Beats Plan: run `tools/vo_amplitude.jsx` for the scene range (per-frame Audio Amplitude), find phrase starts/ends and the silence gaps.
- Cut **1 frame inside the real silence gap**; move the master scene markers to match; flag every difference from the brief (briefs were off by 0.1–0.5s, and once gave frame numbers that didn't match their own seconds).
- Record the measurement in the state file: `«phrase» 7.90–8.93 · gap 8.95–9.12 · …`.
- Word dips inside a phrase = sub-beats for text reveals; reveal text ~2–5 frames **before** the word.
- Outside AE, `ffmpeg -af silencedetect` on the VO file gives the same pauses in seconds.
- **Always measure, even when timecodes are given.** Timecodes from the user or another model are a guide that gets checked by measurement (Gemini's drifted up to 2.3s by the end; the real VO was 23.21s, not 21). An older AG1 R2 note said "ask the user for timecodes instead of detecting them" — superseded.
- **Music-only reels (beat grid and drop measured from the file, never agy/Gemini timings; render cut frames checked against the beats):** skill `reel-music-montage` (`skills\reel-music-montage\SKILL.md`, moved there 2026-11-13).
- **Silence gaps don't tell you which words are where.** A VO can run two phrases together with no pause (CLF R2: «وتجميد تناسب مشروعك؟» had only a 0.15s dip, and the 0.37s gap came before «مع CLF»), so mapping phrases to gaps + spreading words by letter count put two captions ~1s late. Verify: cut the VO into short pieces around each doubtful spot and run `speech_to_text` on each piece (file must sit under `C:\Users\PC\Desktop`); then place word starts on the envelope dips.
- **Tighten the VO before building (Omar, CLE R2: «متخليش الفيديو ممل وفيه سكوت كتير»).** Map the quiet gaps at 10 ms (below peak−30 dB), confirm doubtful bits (sigh or word?) with ElevenLabs STT on short cuts, then rebuild the VO from speech pieces: breaths/sighs out, pauses inside a line 0.08–0.22s, 0.08s between dialogue turns. Pad pieces 0.03s in / 0.07s out and re-check word endings with STT (the soft final «ت» of «تلفت» and «ج» of «الخليج» got clipped at 0.05s). The assemble script writes the **word map after the cut** (`vo_timing.json` for the build + `VO_MAP.md` for reading), so every timing downstream follows the edit (`assemble_vo.py` in CLE R2 `scripts\`).
- **Gemini word timecodes by ear drift** (CLE R2: up to 0.9s, wrong file lengths) → whisper `--word_timestamps True` + the gap map rule; report where Gemini differed. **Whisper's first word after a pause starts where the previous word ended** (CLF R3: «والمنتجات» 7.30 vs the real 7.70 after the gap): take each phrase start from the silencedetect gap end, and only the words inside a phrase from whisper. This is for raw whisper: with an approved script, `stable-ts --align` lands phrase starts by itself (CLF R2, 2026-11-14: 64 ms vs 288 ms), see `03` «Captions as a HyperFrames overlay» step 1 [تقني].
- **A caption line leaves 0.12s after its last word ends**, not when the next line starts — otherwise it sits on screen through the silence and reads as late (Omar, CLF R2).

## 2. Source order: the user's library first
- **Library first:** `..\SFX_Library\` (12 bases + `more-sfx-added-by-omar\`: highlighter, gears, low drum hit, whooshes, UI…). The user said plainly not to generate from ElevenLabs when the library has it.
- **`more-sfx-added-by-omar\Flex UI SFX\*.wav` are corrupted** (header bytes replaced, «Format not recognised»). Their headers hold UTF-8 replacement bytes (`EF BF BD`): the files went through a text conversion. Use the Epidemic files in `textures\clicks` / `textures\UI` (`soft-click-0x`, `tick-0x`) or the 12 bases until they're replaced from the original download.
- Then derive from a sound already picked (pitch, reverse, EQ, trim). Generate only what is still missing.


## 3. ElevenLabs (via MCP) — account limits (free tier, Nov 2026)
- No API key, ever — MCP tools only. Run `check_subscription` once at intake: limits may have changed.
- TTS with library/professional voices (e.g. "Mansour - Saudi") → 402. Premade voices work (Laura, Roger, Sarah, Lily…); `eleven_v3` and `eleven_v4` work (`list_models`, 2026-11-07). Premade + v4 + the Saudi text read as white Saudi dialect (Roger, judged by agy); older models came out MSA-ish → tashkeel on mispronounced words. A full ~50s script ≈ 700 characters per take out of 10,000/month.
- **ElevenLabs out (both MCP accounts at quota) or its site sign-in blocked in the built-in browser (the Google popup is refused):** Magnific `audio_tts` with `model: eleven_v4` has Saudi catalog voices (`audio_voices_list` search `Saudi`): Yusuf Haddad `1407` (agy 9/10, used), Saad Al-Qahtani `783`, Nabil Khalil `972`. About 152 credits per 53 s take `[تقني]` (AG1 R5, 2026-11-16).
- MCP saves TTS as `tts_[<first tag>_<timestamp>.mp3` → rename at once to `VO_take<N>_<voice>_<model>.mp3` in `assets\VO_takes\`.
- **The voice an old reel was generated with isn't in the WhatsApp file or the clip.** The moment Omar says the voice name, write it in the client file in the same round; if it isn't written, ask him or have him look in `History` on ElevenLabs. Never guess `[تقني]` (CLM R2, 2026-11-14: guessed `Hanafito`, then `Magdy`; Omar: «لا مكنش ده، كان اسمه تامر»).
- **Music is never generated unless the reel invents something that has no music** `[ذوق عمر]` (CLA R3, 2026-11-13). Source: `pixabay.com/music` (free). Skip tracks tagged «AI generated» on their page; the mp3 link (`cdn.pixabay.com/download/audio/...`) is in the track page HTML, no login. Show Omar 3 options (name, link, length) unless he says «اختار انت». Start the bed on the first beat, not on the soft intro (CLA R3: `Chill Reel` beat starts at 16.05 s).
- **`compose_music` returns 402 on the free tier** (checked again CLD R2, 2026-11-08). Music bed, in order: (1) the client's own music from their footage — a music-only edit or a clip with music and no voice (CLD R2: `غاله\مستند`, 27 s, extended to 33 s with `acrossfade` d=2 onto a copy starting at 6 s); (2) a 4–5 s seamless loop from `text_to_sound_effects` (`loop: true`) looped with ffmpeg `-stream_loop`.
- `text_to_sound_effects` max ≈5s; `prompt_influence` not exposed by the MCP tool.
- `speech_to_text` only reads files under `C:\Users\PC\Desktop`.
- Log every generation (file, prompt, duration, status) in `generations.json`; reject silent takes: measure the peak before using it `[تقني]` (CLC R4 clapperboard came back at −49 dBFS, inaudible in the mix).
- **Credits ran out on 2026-11-14** (10,000/month quota, `quota_exceeded`). Fallback for one-shots: earshot's shipped bank (`sfx_list` / `sfx_render`); a clapperboard = `fit/hit/bamboo_tok` + `cut_hit/kick` (dur 0.2, −8 dB) + short `aecho` (CLC R4 `sfx/clap_slate.wav`).

## 3b. VO script ready for ElevenLabs (Omar, 2026-11-04)
- When the VO is to be made, Claude writes it **ready to paste** into the ElevenLabs website, model `Eleven v4` only, for every reel; `v3` is no longer used anywhere `[ذوق عمر]` (CLH R7, 2026-11-21; the same tags work): one code block, nothing else inside it (no titles, no timecodes, no notes).
- Audio tags in English square brackets before the phrase they act on: `[confident]`, `[warm]`, `[curious]`, `[excited]`, `[serious]`, `[whispers]`, `[sighs]`, `[short pause]`. 1–2 tags per sentence at most — too many and the read sounds acted.
- Pauses: `...` for a hesitation, `—` for a short break, a new line for a breath. No SSML `<break>` (v3 ignored it; not rechecked on v4).
- Saudi dialect in the text itself (Kit_02 §6) + tashkeel only on words that get mispronounced. Phone numbers written in Arabic words (`صفر خمسة تسعة…`), brand as «AG1». Gulf/Hijazi voices say ق as g, even in the brand («جوافل الرشد», CLC R3): full tashkeel on the brand (`قَوَافِلُ`), else `Eleven Multilingual v2`, else Speech to Speech from a take that says it right. Whisper usually writes the dictionary word either way, so check the brand by ear (agy); when `small` does write ج («نجاء», «جطرة») take it as a flag (CLH R7, 2026-11-21: Mansour on v4 said the brand «نگاء» and «رابغ» as «رابِق» with light tashkeel).
- Under the block: the target length in seconds, the voice to pick (male Saudi from the library if the account allows it, else the closest premade + tashkeel), `Stability: Natural`, and "generate 3 takes, send the best one". The measured VO then rules as always (§1).
- **Omar may ask Claude to generate it instead** («ولّده إنت»; Dr. Saud reel, 2026-11-07: the ElevenLabs site was too confusing, condition: v4 only). Then: `list_models` to confirm the model he named exists (stop and say so if not), the same tagged text via MCP `text_to_speech` (`language: ar`), 2 takes on two premade male voices, agy listens to both (dialect, mispronounced words, tags read aloud, emotion) and Claude picks; the chosen take → `assets\VO.mp3`, sent to Omar with SendUserFile.
- Generate the whole script in one go, never line by line (v3 was unstable on very short texts; not rechecked on v4).
- **One sentence mispronounced → redo that sentence only** `[تقني]` (CLE R5, 2026-11-15; CLI R5, 2026-11-18): Omar generates that one sentence with the same voice, settings and model; Claude splices it in place of the old one at a natural pause, speeds it up by up to 5% to get close to the length, and moves everything after it (cards, end card, SFX) by the length difference (CLE R5: +0.33 s). The caption changes to the same words. The picture doesn't change, remix only. After the splice `agy` listens to the seam (CLI R5: «باينة شوية لو الصوت لوحده، ومقبولة لإعلان موبايل»; the end card's whoosh and hit covered it). Claude hasn't heard it, so tell Omar the second of that sentence so he listens before delivery.
- **If the model keeps missing an MSA word, swap it for plain Saudi colloquial** («نافذتك» → «شبّاكك»، «تتفصّل» → «نفصّلها») instead of piling on tashkeel, which didn't work `[تقني]` (CLE R5, 2026-11-15).
- **Free ElevenLabs accounts can't use library voices through the API** (402 `paid_plan_required`), so the MCP gives only English premades. On the website the free account can use library voices with the yellow badge (Mansour, Fahad, Ali calm & Deep, Ziyad); black-badge voices (Raed Alotaibi, Saleh) ask for an upgrade. Claude can drive the site in Claude in Chrome on Omar's «omar (work)» Chrome profile (the personal-Gmail profile is a different browser in `list_connected_browsers`); each generation gives 2 takes `[تقني]` (CLJ R9, 2026-11-15).
- **Magnific TTS (`audio_tts`, `eleven_v4`) when both free ElevenLabs accounts are empty** `[تقني]` (CLI R4, 2026-11-17): Magnific renames the library voices, so «Mansour» isn't there by name; pick the closest Saudi male by description (`Yusuf Haddad`, id 1407) and generate the whole script in one take so the voice doesn't change mid-reel. 40 s = 112 credits (`simulate_cost` first). The ElevenLabs API never returns an account's email.
- **A take whose voice doesn't fit the character's age or look:** ElevenLabs `Voice Changer` (Speech to Speech) on that same take keeps the read and most of the timing, so cuts and captions barely move; clean it like the others and re-measure the word times `[تقني]` (CLM R1, 2026-11-11).
- **Dialogue (2 speakers): the whole conversation in one generation, both voices, `eleven_v4` with tags** `[ذوق عمر]` (CLC R7, 2026-11-22: «ولد التيكات بتاعت كل شخصيه مع بعض في برومبت واحد»), not a take per voice spliced together. Magnific `audio_tts` `speakers: [{voiceId, speakerName}]` + one line per turn `Name: [tag] text`; no label or tag was read aloud, 18 s = 86 credits `[تقني]`. Split turns only to add a gap for a cut.
- **Don't wait for the final VO to build:** make a scratch VO with premade voices via MCP (`eleven_multilingual_v2`, `language: ar`, stable on short lines), build and preview the whole structure on it, then swap in the user's takes and re-measure (CLE R2).

## 3c. Vocals, Veo audio and alternate mixes (AG1 R3, 2026-11-05)
- `text_to_sound_effects` can make a short sung or hummed vocal line (≤5s).
- **Pick generated vocals without listening:** `speech_to_text` (are there words? which?) + a pitch contour (numpy autocorrelation per 50ms on a 16 kHz mono dump): sustained steps that move = sung; one flat pitch = a drone. Say plainly that the take was chosen by measurement.
- A sung line **with words** over the opening was rejected («مش حلوة»); a wordless hum was offered next to a no-vocal version.
- **Veo clip audio is free synced foley** (wings, pouring, kids, majlis murmur): cut it per shot with the picture. **Its level is absolute: peaks between −15 and −10 dBFS in the master** (Omar, CLE R2 — he meant the clip level itself, not a gap under the VO), a few dB lower inside speech.
- **Firefly and MiniMax clips carry sound inside them:** mute the clips before combining with the music, or the peak crosses the limit on the first render (CLB R6 needed two renders) `[تقني]` (CLB R6, 2026-11-18).
- **Taste decisions on sound → deliver versions side by side**, never overwrite the previous one: one mix script with env switches (`R3_VOCAL`, `R3_MIX`), remux each onto the same picture (no re-render).

## 4. SFX prompt recipe that worked
`<what> , <texture/material>, clean modern, isolated one-shot, dry, high-quality` — e.g. "short crisp UI card pop, soft wooden and plastic tactile click, clean modern interface appearance, very close, isolated one-shot, dry". Trim leading silence after generation.

## 5. SFX stem builder (Python) — `tools/sfx_stem_builder_reference.py`
- 12 base sounds → 6 stereo stems 48k/24-bit: `01_ambience 02_motion 03_texture 04_emotional 05_foley 06_extras` + `00_FULL_SFX_MASTER.wav`.
- Each cue is aligned so its **acoustic peak** lands on the target time (anchor `peak` / `start` / `end`); variations by varispeed pitch, HPF/LPF, pan, trim.
- Default clip peaks (dBFS): whoosh/swoosh −12, pop −14, click/marker −16, typing −18, hit −8, chime −22, ambience bed −24.
- Motion/texture/foley duck −5 dB inside VO speech windows (60 ms smoothing); deliberate silence gaps before a CTA (all layers to −60, ambience only −18).
- Master: HPF 30 Hz, look-ahead limiter ceiling −1.5 dBFS. Writes `cue_log.csv` with timing error in frames (target ±0).
- For phone speakers, layer a 200 Hz+ transient on sub hits.
- The cue list and VO windows are per project — copy the file and replace `cues()` and `VO`.

## 5b. Speech recorded on set (presenter, interview)
- **Any recorded voice of a real person: Omar cleans it in Adobe Podcast «Enhance Speech» before anything else, and its phrase peaks sit at −10…−6 dBFS (§6)** `[ذوق عمر]`. How to send it (and why the Adobe connector doesn't work), the compression chain, caption taps (none), transition SFX, brand moments, cutting inside a sentence and per-clip leveling of phone takes: skill `reel-talking-head` §الصوت (moved there 2026-11-12 from here and §1).

## 6. Mix levels the user approved (AG1 R2, 2026-11-03)

| نوع الريل | الكلام | المزيكا | الماستر | جاي منين |
|---|---|---|---|---|
| فويس مسجّل لوحده (VO) | −18 LUFS قبل الماستر؛ لو صوت شخص حقيقي: قمم −10…−6 dBFS | قمم −18…−22 dBFS (−20 تحت الكلام) | ≈ −14 LUFS، peak −1 dBFS | AG1 R2، CLG R1، CLF R2–R3، CLB R2 (المزيكا)، عمر 11 نوفمبر 2026 (القمم) |
| متكلم قاعد (صوته من التصوير) | قمم −10…−6 dBFS، ويتنضف في Adobe Podcast الأول (§5b) | ≈ 20 dB تحت الكلام | مفيش رقم LUFS مستهدف. CLA اتقاس ≈ −19 LUFS، ومتعلّيش الكلام فوق −6 | CLA R1، عمر 11 نوفمبر 2026 |
| كليب عميل بصوته (UGC، تليفون) | كل كليب `loudnorm=I=-20` قبل اللزق؛ قمم −10…−6 dBFS | 26 dB تحت الكلام (≈ −44 LUFS) | مفيش قرار | CLD R5، CLH R1، عمر 11 نوفمبر 2026 (القمم) |
| مزيكا بس | — | مفيش قرار | مفيش قرار | — |

Details and the story behind each number are in the bullets below and in §5b.

- **VO:** −18 LUFS before the master.
- **`loudnorm` بمرة واحدة بيقف تحت الهدف لو القمة ماسكاه** (طلع −16.3 بدل −14 مع `TP=-1.5`): بعده `volume=+XdB,alimiter=limit=0.83:level=false` وقيس تاني بـ `qc_reel.py` `[تقني]` (CLC R7، 23 نوفمبر 2026).
- **Music (Omar, CLB R2 — latest, wins over the older numbers here): peaks between −18 and −22 dBFS in the final master** (−20 under speech, ≈ −18.5 on a silent ending). Make room for the voice with a parametric EQ on the music, not just level: HPF 40 Hz, a wide dip ≈ −4.5 dB around 2.5 kHz (1.6 oct) and −2 dB at 350 Hz; duck ≈ −7 dB from the voice envelope (60 ms attack / 450 ms release); voice HPF 80 Hz + light compression (2.5:1). Mix and measure in code (pyloudnorm), import one WAV into AE, and keep stems. Reference: `CLB\reel-02\scripts\edl_CLB_R2.py mix`. Older rule (AG1 R2): 15 LU under the VO, a further −6 dB while someone speaks, −10 dB more under the final whisper.
- **SFX:** calibration levels above **+5 dB** (they were too quiet at first), ducked −5 dB inside speech.
  - Calibration #1 (AG1 reel, Nov 2026, approved; moved here from `reel-sound-design` on 2026-11-11): clip peaks whoosh/swoosh −12 · pop −14 · click/marker −16 · typing −18 · hit −8 · chime −22 · ambience bed −24 dBFS. Motion/texture/foley ducked −5 dB inside VO speech windows (60 ms smoothing), ambience not ducked; −5 dB for clean corporate reels with dense VO, 6–10 dB for busier styles. Pre-CTA: all layers −60 dB for 0.10 s (ambience only −18 dB). Master: HPF 30 Hz + look-ahead peak limiter at −1.5 dBFS ceiling.
  - Starting defaults from research, **not approved by Omar yet** (moved from `reel-sound-design` §8 on 2026-11-11), relative to the VO: ambience bed 20–28 dB under, texture 14–18, motion 10–14, emotional hits up to 4–8 dB under the VO peak (louder only where no VO plays); duck all SFX 6–10 dB while VO speaks (except planned accents in gaps); music (second pass) 12–20 dB under VO while talking, EQ dip in the 1–4 kHz voice range. Preview master −14 LUFS integrated, true peak ≤ −1 dBTP.
- **Master:** about −14 LUFS (−14.5 on R2, −14 on CLG R1), peak −1 dBFS. **Write the master WAV as stereo and measure the MP4 itself:** a mono WAV comes out of AE as dual-mono stereo, +3 LU (CLF R2 and R3 rendered at −11.4 LUFS from a −14.4 mono mix). Fix: stereo × −3 dB per channel, then remux onto the same picture.
- **The whisper at the end of a VO:** don't cut it and don't raise it — only duck the music under it.
- Check by measurement that the VO is louder than the music in **every sentence**, not only on average.
- **Talking-head promo, her own clip audio (CLH R1, 2026-11-05):** a bed at 19 dB under the VO was «عالية اوي ومزعجة». Approved: **26 dB under the VO** (≈ −44 LUFS), HPF 150 Hz + **4th-order LPF 4.5 kHz** to take the edge off glockenspiel/claps, −10 dB dips just before the water/logo moments.
- If the user doesn't answer the music question, build a calm bed (CLF R1: `make_music_bed.py`).
- Reference mix script: `AG1 R2 → R2_sfx\build_r2_audio.py` (library-only stems + VO/music mix).

## 7. User taste (so far)
- Calm, soothing music beds; no beat-synced shake.
- **Minor-key beds read as «موسيقى رعب»** (CLH R1 bed_A, C minor pads). Before using a generated bed, estimate its key (librosa chroma vs. Krumhansl profiles) and keep major-key, bright ones.
- **Thematic SFX = a light touch:** the water drops/splashes were «اوفر شوية» at first; 5–8 dB lower and no riser was right. Price reveals get a cash-register «ka-ching» (Omar asked for it on CLH R2).
- Slightly slower VO pace, few long silences.
