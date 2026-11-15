---
name: "reel-sound-design"
description: Sound-design a promo/ad reel end to end - analyze the video, build a layered SFX cue sheet, source or generate sounds (library first, ElevenLabs second), QC them, and deliver per-layer stems aligned to 00:00 for Premiere.
---

# Reel Sound Design (Omar's workflow)

Talk to the user in Egyptian Arabic. Every paragraph, bullet and heading starts with an Arabic word; English terms, file names and numbers-with-units go in `backticks` mid-line or at the end, never first on a line (the chat flips a line to LTR when it starts in English). Keep English to the minimum. Prompts to ElevenLabs are always English.

Shared rules for any video (workflow, VO-measured cuts, AE execution) live in `<Claude-Workflow>\Kit_01_General_Video_Rules\` — read `05_audio_sfx.md` there before starting.

Purpose: given a finished picture edit of a short vertical promo/ad reel (usually with VO, often no music yet), produce professional, layered sound effects that follow the picture and the style of the video, and deliver them as stems Omar drops straight into Premiere Pro.

Core truths to keep in mind:
- You cannot hear. You measure (timing, peaks, spectrum, loudness) and look (frames, spectrograms). Omar's ears are the final judge; build every step so he can approve or reject quickly.
- Picture and style decide WHERE and WHAT. Music (when it exists) only adjusts HOW MUCH and HOW LOUD in a second pass.
- Restraint beats quantity. An accent on every cut buries the one that matters.


## 0. Prerequisites (check silently, install what is missing)

- `ffmpeg` / `ffprobe`
- Python: `numpy scipy soundfile librosa pyloudnorm opencv-python matplotlib` (+ `scenedetect` if available)
- ElevenLabs: **use the ElevenLabs MCP tools first** (`text_to_sound_effects`, `text_to_speech`, `check_subscription` — load via ToolSearch "elevenlabs"). That is how the AG1 reel was done; **no API key is used — never ask for one, never write one into a file, script or env var.** If the MCP is not connected: do everything up to the approved cue sheet, then stop and tell Omar to reconnect the ElevenLabs MCP.
- Run `check_subscription` once at intake: the account was **free tier** (Nov 2026) — see "MCP / free-tier facts" in section 5.
- Reusable base library from earlier reels: `<Claude-Workflow>\SFX_Library\` (12 clean corporate bases + `generations.json` with the prompts that passed). Check it before generating anything.
- Stem builder that already works end to end (peak alignment, ducking, gap, limiter, cue log): `<Claude-Workflow>\Kit_01_General_Video_Rules\tools\sfx_stem_builder_reference.py` — copy it and replace `cues()`, `VO`, `GAP`, `LENGTH`.
- Omar's own SFX library: `<Claude-Workflow>\SFX_Library\more-sfx-added-by-omar\` (folders `whoosh`, `risers and hits`, `textures`, `Flex UI SFX`). On another PC, find it via `THIS-PC.md` / `NEW-PC-SETUP.md` in the Claude-Workflow folder. If another library is given, index it once (file name, duration, folder = category) into `library_index.json`.

Working folder layout (create next to the video): `<reel>_sfx/` with `analysis/` (frames, contact sheets, cuts.json, motion.json, vo.json), `sources/` (raw library picks + raw ElevenLabs generations), `derived/` (processed variants: pitched, reversed, trimmed, EQ'd), `stems/` (final per-layer WAVs), and `cue_sheet.md`, `cue_sheet.csv`, `preview.mp4`, `feedback_log.md`.


## 1. Intake (one short message, then work)

Ask only what you cannot detect, in one message:
1. Style: luxury/calm, corporate/clean, energetic/hype - or "you choose".
2. Intensity 1-5 (default 3).
3. Platform (default Instagram Reels) and whether music will be added later.

If Omar says "you choose" or doesn't answer, detect it (step 2) and state the choice in one line.


## 2. Analyze the video

Get fps and duration with ffprobe. Work in frames, convert to ms with fps. Keep everything in `analysis/`.

**Shortcut when we built the picture ourselves in AE:** skip steps 1–4. The cuts, whips, pops and reveals are already known exactly from the build scripts' frame constants and `PROJECT_STATE.md` (scene ranges, per-beat frames), and the VO windows from the measured Audio Amplitude. Read those instead of running optical flow — cheaper and exact. Only look at frames for cues marked `uncertain`.

1. **Cuts**: PySceneDetect (ContentDetector) or `ffmpeg -vf "select='gt(scene,0.3)',showinfo"`. Record frame + seconds. Cuts are reliable.
2. **Motion**: optical flow (OpenCV Farneback on downscaled frames) -> per-frame motion magnitude + dominant horizontal direction. Find motion peaks (camera moves, zooms, whips, slides) and their start/peak/end. Direction feeds panning.
3. **Graphics/text appearance**: frame difference inside regions with low motion elsewhere + edge-density jumps. Treat as CANDIDATES.
4. **Visual confirmation**: build contact sheets (e.g. 4-6 fps around every candidate, labeled with timecode) and LOOK at them to confirm text pops, logo reveals, product reveals, CTA, impacts (object hits, camera shake). Mark anything unsure as `uncertain` in the cue sheet.
5. **VO**: extract audio; detect speech segments by energy (VAD). Gaps between phrases are where accents can live. If a transcript is available, note key/emphasis words.
6. **Hook window**: 0-1.5 s. Identify the first visual reveal or headline.
7. **Sections**: split the reel into 3-5 sections (hook / build / body / climax-reveal / CTA) from cuts, VO and visual content.


## 3. Style profile + emotion map

Classify by: cuts per second, mean motion, VO pace (words/s), content type (real estate, tourism, product, service, corporate). Then choose a profile; intensity shifts it ±1 step.

| Profile | SFX events / 10 s | Big hits per reel | Transition SFX | Palette |
|---|---|---|---|---|
| Luxury / calm | 2-4 | 1 | rarely, soft airy only | air, soft whooshes, glassy textures, warm low swells |
| Corporate / clean | 4-6 | 1-2 | sometimes | clean whooshes, UI clicks, light risers |
| Energetic / hype | 8-12 | 2-3 | often | punchy whooshes, snaps, glitches, sub drops |

These numbers are starting defaults. Once Omar's own project data (XML) is analyzed, replace them in `references/calibration.md` and use those instead.

Emotion map: write ONE target feeling per section (e.g. trust -> curiosity -> excitement -> confidence). Every cue must serve its section's feeling. Plan a contrast arc: early sections mids/highs and airy, lows (impacts, sub drops) introduced as it builds toward the reveal/CTA.


## 4. Build the cue sheet (then STOP for approval)

Layers (one stem each):
1. **Ambience** - bed for place/feeling.
2. **Motion** - whooshes/swishes on movement and visible transitions.
3. **Texture** - clicks, pops, UI, mechanical ticks, glitches on text/graphics.
4. **Emotional** - risers, hits, sub drops, reverse swells, braams.
5. **Foley** - "what does this shot sound like?": cloth, door, cup, footsteps, keys. Sparse.
6. **Extras** - the bolder optional cues. Muting this stem = calm version A; on = bold version B. Two versions, zero extra cost.

Cue fields: `id, layer, start_frame, start_s, sync_point (cut/peak/text/reveal), target_peak_s, duration_s, description, intensity 1-5, pan (L/C/R or keyframes), source plan (library file / generate / derive from #id), status (sure/uncertain)`.


### Placement rules
Read `references/cue_rules.md` before writing cues: motion/whoosh timing, texture, risers and hits, ambience, hook, sound-off rule.

Present the cue sheet as a markdown table in chat (grouped by section) with the profile, emotion map and counts per layer. Wait for Omar's approval or edits before spending any ElevenLabs credits.

## 5. Source the sounds (library first, generate second, derive always)

Order for every cue:
1. Omar's library (match by category folder + name keywords + duration).
2. Derive from an already-sourced sound (pitch, speed, reverse, EQ, trim, layer) - prefer this; it keeps the palette consistent.
3. Generate with ElevenLabs only for what is still missing.

Plan BASE sounds, not one sound per cue: e.g. 3 whoosh bases, 2 click bases, 1 riser, 1 hit set (transient + body + sub), 1-2 ambiences. Derive all cue variants locally.


### ElevenLabs
Read `references/elevenlabs_api.md` before the first generation: MCP / free-tier facts (they override the API facts), cost rule, prompting rules, settings table per use, generation workflow and `generations.json` log. Show Omar the planned number of calls and credits before generating.

## 6. Process each cue (SHAPE)

- **Source** - chosen file.
- **Hone** - trim leading/trailing silence; pitch/speed (slowing a whoosh without pitch correction = longer + lower); reverse when needed; fades (2-10 ms in to avoid clicks).
- **Amplify** - layer components across bands (hit = transient + body + sub).
- **Place** - find the sound's own peak (max of smoothed envelope or onset strength) and shift the clip so that peak lands on `target_peak_s`. This is sample-accurate (finer than a frame).
- **Environment** - ambience/foley under it.

Band slots per layer and phone translation: `references/cue_rules.md`.

## 7. Automatic QC (before Omar hears anything)

Run per cue and reject + fix (max 2 regenerations, then mark for Omar):
- Timing: |actual peak - target peak| <= 1 frame (transitions/clicks) or <= 2 frames (whooshes on moves).
- Duration within ±25% of planned.
- Spectral fit: spectral centroid and band energy match the layer slot (e.g. a click with strong energy < 300 Hz fails).
- No clipping (sample peak < -1 dBFS), no DC offset, no leading noise/silence > 30 ms.
- Variation: no two consecutive same-layer cues with identical source + pitch.
- Density: events per 10 s within profile range; flag if over.
- VO collision: no motion/texture cue peaking within 80 ms of a stressed VO syllable unless intentional.
- Save a spectrogram PNG per base sound and LOOK at it: smeared noise, artifacts, weak transient, or an unwanted tail = regenerate.

## 8. Mix and deliver

Levels: `<Claude-Workflow>\Kit_01_General_Video_Rules\05_audio_sfx.md` §6 (loudness per reel type, SFX layer levels and ducking). They are written there only. Check the preview in mono too; meaning must survive.

Deliverables in `stems/`, all WAV 48 kHz 24-bit, exactly the reel's length, starting at 00:00:00:00:
`01_ambience.wav 02_motion.wav 03_texture.wav 04_emotional.wav 05_foley.wav 06_extras.wav`
Plus `preview.mp4` (picture + VO + SFX), `cue_sheet.md/.csv`, and the sources.

Tell Omar: drag the stems onto separate audio tracks at 00:00 in Premiere; nothing needs moving. Mute `06_extras` for the calm version. To nudge by less than a frame: timeline menu -> Show Audio Time Units.

Recorded speech (presenter, interview): ask Omar to clean it in Adobe Podcast before anything (`05_audio_sfx.md` §5b).
Optional VO polish (only if asked or if VO is clearly noisy/uneven): light denoise -> HPF 80 Hz, LPF 12-16 kHz -> warmth EQ -> compression 2:1 -> de-esser -> limiter. Deliver as a separate `00_vo_polished.wav`, never overwrite his VO.

## 9. Second pass when music arrives
Steps in `references/cue_rules.md` (beats/downbeats, hits that double the music, EQ carve, rebalance, ~20% of cues change).

## 10. Feedback loop (how this skill gets better)

After Omar listens, log every note in `feedback_log.md` as: date, reel, cue id, his words, rule changed. When a note generalizes ("whooshes too loud in calm reels", "no clicks on Arabic captions"), update the matching rule, `05_audio_sfx.md` §6, or `references/calibration.md` and tell him which rule changed. Never argue taste; ask one clarifying question only if the note is ambiguous.

## Calibration
Omar's measured project data and the sources behind these rules: `references/calibration.md`.
