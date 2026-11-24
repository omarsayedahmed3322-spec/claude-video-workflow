# 03 — الكتابة العربي في After Effects (Arabic Typography)

## Text document setup (scripted)
```javascript
td.resetCharStyle(); td.resetParagraphStyle();
td.font = "<PostScriptName>";            // check it exists first (font check script) — wrong name silently falls back
td.composerEngine = ComposerEngine.UNIVERSAL_TYPE_ENGINE;   // in try/catch
td.direction = ParagraphDirection.DIRECTION_RIGHT_TO_LEFT;  // in try/catch
td.justification = ParagraphJustification.CENTER_JUSTIFY;
td.applyStroke = false;
```
Fit after creation: `fit(layer, maxW, maxH)` with `sourceRectAtTime` (scale down only), then anchor at the ink-box centre.

## Fonts & characters (learned on AG1 R2)
- **No emoji in any on-screen text** (hook, captions, cards, end card) in every client video `[ذوق عمر]`: an emoji in the plan's hook belongs to the post caption only. Only exception: Omar asks for it in that reel (AG1 account manager via Omar, CLJ R9, 2026-11-15: «متبقاش تحط ايموشن في الفيديو»).
- Use the **PostScript name**, not the Windows display name (e.g. `Lyon-Arabic-Display-Black`). Print `app.fonts.allFonts` once to find it.
- **No RLM (`‏`) at the start of the text** — it makes AE fall back to Times. `DIRECTION_RIGHT_TO_LEFT` is enough.
- Symbols like ✓ are missing from the fonts and stop the script with «invalid character» → icons are Shape Layers.
- **No shadda on dotted letters in on-screen text** (`ب ت ث ن ي`): in Cairo at caption/card size the shadda reads as an extra dot — «تيبّس» was read as «تينس» (Dr. Saud reel, 2026-11-07). Keep tashkeel for the VO text only.

## Alignment with RTL (learned on AG1 R2)
- Right/left alignment on **Point Text** doesn't work properly with RTL (text ran off screen).
- In **Paragraph Text** the alignment is flipped (`LASTLINE_LEFT` renders on the right).
- What works: centred text = Point Text; right/left text = a Paragraph Box whose edge sits on the target point, all computed **before** the layer is created — moving it afterwards breaks the position.
- `ParagraphJustification` values aren't comparable numbers in ExtendScript → pass alignment around as a letter (`"R" / "L" / "C"`).
- `sourceRectAtTime` returns stale cached values after an edit → measure on a temporary layer and delete it.
- **Numbered cards or options in a row run right to left:** ١ on the right, the last number on the left `[تقني]` (CLE R3, 2026-11-11: with ١ on the left, the bedroom «3» sat where the eye reads «1»).

## Stroke (faux-bold)
- **Arabic text: never a stroke.** It clogs counters and dots.
- English display text or a genuinely thin font: `applyStroke=true, strokeColor=fillColor, strokeWidth=5, strokeOverFill=true`. Small UI labels (≤50px) no stroke.
- Heavy fonts (e.g. Palestine Regular) — no stroke at all.

## Kashida (ـ tatweel) rules
1. Kashida goes **between two joined letters inside the word**, before the last letter — never after the final letter («واللـــــي» ✅ «والليـــــ» ❌). Before building, check every string with `ـ`: the `ـ` must be followed by a letter of the same word.
2. Briefs often place it wrongly — fix it and tell the user.
3. Font-specific breaks: in Palestine, a kashida next to a **medial ه** breaks visually → **no kashida in any word containing a medial ه** («لها», «جمهور», «يبنيها», «الهدف» plain). Test other fonts for similar breaks on first use.
4. **Long-kashida lines shrink:** a line with 2+ kashida runs gets width-limited to tiny type → split into two stacked lines.
5. Some kashida words report an inflated `sourceRectAtTime` height with ink at the top: size them like the sibling line and offset down by (boxH − visualH)/2.
6. Animated kashida grow (1→5 tatweels) = Source Text expression joining parts with a growing run; motion blur OFF on that layer (see `tools/ae_helpers.jsx` `kashidaGrow`).

## Typewriter RTL
Use a Range Selector / Source Text expression; anchor around the ink box (e.g. 62% for lines with descenders like «ي») so descenders stay inside strips; char blur ~12 on reveal; finish ≥0.5s before the cut.

## Mixed Arabic + English in one line
Keep them as separate layers (Arabic font + English font) placed side by side — one text layer with mixed scripts reorders unpredictably.

## What goes in a caption
- **Key words only, never words already on screen** `[ذوق عمر]` (Omar, CLC R7, 2026-11-22, «قاعدة عامة لكل الريلز»): a phrase shown in a card, title or hook gets no caption (the eye would read it twice), and a word a striking visual already says can go too. Captions don't have to be the VO word for word.

## Captions as a HyperFrames overlay (option, since 2026-11-04)
Word-by-word Arabic captions can be rendered outside AE: Chrome shapes Arabic itself (joined letters, RTL, no Times fallback, no Universal Type Engine tricks), and the result is a transparent ProRes 4444 `.mov` laid over the AE comp.
1. Timing: `captions.json` (`[{"t": text, "w": [word starts], "in", "out"}]`, same format as CLF R1). From the VO **with an approved script**: `stable-ts VO.mp3 --align script.txt --language ar --model small -o VO.json` (`script.txt` = the approved text, UTF-8), then `tools/hf_captions/whisper_to_captions.py VO.json captions.json`. The words come out in the script's spelling and phrase starts after a pause land right [تقني] (CLF R2 test, 2026-11-14: phrase starts 64 ms off vs 288 ms for `whisper small`, inside a phrase both ≈150 ms; 8 s run). **No script:** `python -X utf8 tools/hf_captions/whisper_gpu.py VO.mp3 VO.json` (GPU, `large-v3-turbo`; never `whisper --model small` unless the GPU run fails), then the same tool; fix the words, keep the times. Check word timing as in `05_audio_sfx.md`.
   - **Run Whisper with `PYTHONIOENCODING=utf-8`** (bash: `export PYTHONIOENCODING=utf-8 PYTHONUTF8=1`). Without it the Windows console crashes on the first Arabic line and writes no JSON (CLD R1). `python -I` ignores that variable (`-I` implies `-E`): use `python -I -X utf8` for any script that prints Arabic (CLD R2).
   - **Check `~\.cache\whisper` before picking a model; never call `--model medium`.** On 2026-11-08 only `tiny`, `base`, `small` are good there (`large-v3-turbo.pt.corrupt` failed its checksum on 11-07), so `small` is the model (2026-11-14: the broken `large-v3-turbo.pt.corrupt` and `medium.pt*` files were deleted with Omar's OK; the `medium.pt` from 11-12 had failed its checksum too). `faster-whisper` `large-v3-turbo` int8 is in `~\.cache\huggingface` (11-14): same timing as `small`, fewer spelling mistakes (CLF R2: «وننفذ», «فترة», «فريزرات» where `small` wrote «والنفذ», «فتغط», «فريزارات»), 9.7 s on 35 s [تقني]. `medium` isn't cached: it starts a 1.4 GB download and can sit on a 0-byte `medium.pt` with no CPU rise (CLD R2, renamed to `medium.pt.empty-broken`). `torch` here has no CUDA, so `--fp16 False`. Whisper may still re-download it (10 min) if the checksum fails. **A background run can hang silently:** if the process CPU time doesn't rise over 5 s (`(Get-Process -Id N).CPU`), kill it and rerun through the Python API (`whisper.load_model` + `transcribe` per file, `print(..., flush=True)` after each), only on the clips you need (CLB R2: the CLI on 5 files sat at 11 s CPU for minutes).
   - **Whisper can drop the last line when music runs under it** (CLD R3: the spoken CTA at 27.4–29.8 s was missing from the JSON, the music bed stayed at −10…−14 dB). Always check the tail: `volumedetect` on the last 3 s, and if it's loud with no words, cut the tail out (`-ss <last word end>`) and transcribe it on its own.
   - **Never pass `initial_prompt`** with the script's opening lines: Whisper treated them as already said and returned no words for the first 8 s (CLG R3). Run without it and fix the text against the script.
   - **Word times on the GPU first: `python -X utf8 tools/hf_captions/whisper_gpu.py VO.mp3 VO.json`** (`faster-whisper` `large-v3-turbo` float16 on the RTX 5060 Ti: 91 s of speech in 6 s, same JSON as `whisper`) [تقني] (2026-11-24). `whisper` and `stable-ts` stay on the CPU (`torch` is the `+cpu` build), so there `small` is the model: `medium` is a 1.4 GB download and ran >10 min on 43 s without finishing. Whisper garbles Saudi dialect either way (`small` heard «دخلت حد مع بنته» for «دخلت تحدي مع بنتي»), so the text is fixed by hand anyway, and lines you can't be sure of go to the user to confirm by ear.
   - **No approved script (client UGC):** write the corrected text one line per Whisper segment and map the words onto the segment's word times by position, like `CLD R1 scripts\make_CLD_captions.py`.
   - **Score the methods every time [ذوق عمر] (Omar, 2026-11-14):** no single winner yet, all four stay in use depending on the job. In every session that times speech, run the methods you can on that VO, fix the final `captions.json` by ear/gaps, then `python -I -X utf8 tools/hf_captions/timing_score.py captions.json <method>.json ...` and add a row to the table below. Use what the rows say is most accurate for that kind of VO.
     | Date, reel | VO | `stable-ts --align` (script) | `whisper small` | `faster-whisper` `large-v3-turbo` int8 | Gemini 4 Hydrogen on `agy` |
     |---|---|---|---|---|---|
     | 2026-11-14, CLF R2 | ElevenLabs Saudi, 35 s, script | starts 111 ms / chunk starts 76 ms, 4 s | 167 / 245 ms (early after pauses), 12.5 s | 174 / 273 ms, best spelling, 9.7 s | not run (Pro off) |
     | CLE R2 (05 §1) | — | — | — | — | Gemini by ear: drifted up to 0.9 s |
     Gemini/agy: ask through `free-llm-delegate` (`free_llm.py ask --file VO.mp3`) for word starts as JSON `[{"word","start","end"}]`, save it, score it like the rest; never use its times unscored.
2. Render: `python -I tools/hf_captions/make_caption_overlay.py captions.json "<reel>\assets - <CODE> R<N>\captions.mov" --from 0 --to <sec> [--font --size --y --maxw --color --hl]`. 8 s took 16 s. Output is `yuva444p12le` (alpha checked); frame 0 = reel time `--from`.
3. In AE: import, put it on top of the master at `--from`, label it `CAPS_HF`. Checked in AE 26.5: `hasAlpha = true`, composites over footage, renders with aerender.
- Use it when the captions are plain word-by-word lines (the CLF look) or a styled card per chunk. **The reel's flat graphics can ride in the same overlay** (chips struck through, list cards with ✕/✓, a stamp, a title card, a CTA pill, the end card with a base64 logo): one HTML, one render, Arabic shaped by Chrome (Dr. Saud reel `scripts\make_overlay.py`: 59.5 s in ~2 min). Captions that interact with the scene (kashida grow, typewriter strips, 3D) stay in AE.
- **A styled caption = copy the generator into the reel's `scripts\` and change the CSS there**, don't grow the kit tool per client. The fullest version is `Dusha\ريل 1\scripts\make_CLD_captions.py`: two fonts (keywords marked `*word` in the script get their own font/colour + an underline sweep), unspoken words at 40 % opacity, `|` forces a card break, `--hide S:E` for burned-in titles, `--min-dur`, and a CTA pill.
- **A caption container with `height:0` renders blank frames** (absolutely positioned card inside it). Give it a real height and centre the card with flex. Check one frame with `hyperframes snapshot --at <sec> --no-end` before the full render. The lint warning `nested_structure_needs_subcomposition` is harmless here.
- **Glass card behind the caption (real blur, CLD R1):** in AE, a copy of the footage with Gaussian Blur 55 (repeat edges) + Brightness +25, matted by a second, disabled copy of the overlay: `glass.setTrackMatte(matte, TrackMatteType.ALPHA); matte.enabled = false;`. The card in the HTML stays ~70–80 % opaque so the blur shows through.
- The style (font file, size, position, colours) is per client — pass it on the command line and note it in the client's file in `Kit_04_Clients`.
- **Arabic in HTML/HyperFrames, three traps** `[تقني]` (AG1 R5, 2026-11-16):
  - `Palestine` has no comma glyph: «229,000» showed as «229 000». Wrap every number inside Arabic text in a Montserrat span.
  - A signed number (`+84`) inside an RTL line moves its sign: give the number `direction:ltr; unicode-bidi:isolate`. Guillemets «» at the start or end of an RTL display line flip to the wrong side: drop them there (mid-line «نمو» is fine).
