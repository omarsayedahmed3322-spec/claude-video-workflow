---
name: style-documentary-heritage
description: Cinematic documentary / heritage film look for AI footage (Veo) — old-film rounded frame with black borders, warm muted grade, grain, fast montage cuts on the VO, slowed-and-blurred last shot with the logo. Use for «ستايل وثائقي»، «فيلم تراثي»، «إعلان وطني / اليوم الوطني / يوم التأسيس»، «فريم مقصوص بحواف»، «زي ريل السعودية»، heritage, nostalgic, national-day films.
---

# Documentary heritage film (AG1 R3 «السعودية»، Nov 2026 — Omar: «الشكل الوثائقي ده ممتاز»)

> Built and approved on AG1 R3. Full working code: `references/build_AG1_R3.jsx` (AE runner job) and
> `references/mix_R3.py` (ffmpeg mix). Copy them into the new reel's `scripts\`, then change only the tables at the top.
> AG1 R3's clips were made with Veo; that is history. New clips: `Omni 1.2 Flash` in Flow by default, and Veo only after asking Omar (it burns credits; `Kit_01\01_workflow.md` §D, Omar 2026-11-11).

## What it looks like (the fingerprint)
- **Frame:** the picture sits inside a rounded "film gate" on black — matte rect `W-40 × H-72`, roundness 46 — so a thin
  black border shows on every side. Omar's favourite part: «الفريم المقصوص عليه بوردرز… طابع وثائقي قديم».
- **Grade (on the picture precomp):** Hue/Sat master saturation −18 · Brightness & Contrast: contrast −10, brightness
  `wiggle(9,1.5)` (projector flicker) · Noise 6% mono (`Noise Type` 0) · warm-brown solid `[0.10,0.075,0.05]` in
  Lighten = lifted blacks · black vignette, inverted elliptical mask, feather 420, opacity 55% · gate weave on position
  `wiggle(3,1.6)` + a 3px sin drift. Order: everything precomposed into `02_Look`, then the gate matte cuts it.
- **Pace:** shots of 1–2s; each Veo clip gives 1–2 shots. Cut 1 frame inside the VO silence gaps. Inside one clip, a
  **jump-cut punch-in** (+15% scale at the cut) reads like the reference's handheld coverage. Every shot pushes in
  ~4–6% (85/15: leaves the cut fast, settles).
- **Fast montage right after the last VO line:** 5 cuts × 0.30s from earlier clips (falcon, mortar, kids, eye…), with an
  old film-projector clatter under it. Omar: «القطعات السريعة ممتازة».
- **Title on the last landscape shot:** `ArefRuqaa-Bold` cream `#F3E5C8`, two lines (170 / 104 px) in the sky, drop-in
  with blur; exits with blur + rise + fade (15/85) before the ending.
- **Captions:** one per VO sentence, `Palestine-Regular` 74px cream, y≈1330, drop shadow (opacity 190/255, dist 3,
  soft 16); in 0.12s before the first word (blur 18→0 + 22px rise + fade), out 0.12s after the last word.
  Write what the VO **says** (STT it): the VO said «هذه» where the script said «هذي».

## The ending that was approved (after 4 rejected versions)
1. Last shot (sunset) keeps playing: time remap ~0.8× until the title leaves, then ~0.35× (frame mix), blur 0→38 and
   brightness 0→−28 over 0.7s (80/80).
2. **Logo appears only here**, without its white background (PNG with alpha), with a soft dark drop shadow (opacity
   150, dist 0, soft 30), blur + scale 82→100% + 40px rise, then a slow 4% push to the last frame.
3. A **sketched heart** around logo + flag: parametric heart path (k=30), two cream strokes (4px 60% / 2px 30%,
   the second scaled 102.5% and rotated 1.5°), Roughen Edges, trim-path draw-on 1.1s, glow copy (blur 14), 9% fill.
   «قلب كأنه رسمة أو ظل، مش قلب واضح».
4. Flag (user's PNG, white bg flood-filled away) under the logo **inside** the heart, Wave Warp (height 12, width 240,
   speed 1.1) + Simple Choker 1.5. Shine: blurred white bar, Add, alpha-matted by a logo copy, sweeps across.
5. Music keeps going and is at its loudest under the logo, swoosh into it, daf hit on the landing, fade at the end.
Rejected: hard cut to a black «SOON»-style card with a plain logo · logo on a white rounded card · rings · the logo
as a small top bug during the whole film («الأزرق مش لايق فوق»).

## Sound
- Veo clip audio = free, synced foley (wings, pour, kids, majlis murmur): cut it per shot with the picture (`AMB` table).
- Music bed under the VO 15 LU down, up after the VO, swell under the logo. Daf hits on the big cuts.
- Opening vocal over the welcoming elder: a sung line with words was rejected («مش حلوة»); wordless humming
  (`text_to_sound_effects`, "humming… no lyrics") was offered with a no-vocal version — Omar's manager picks.

## Do / Don't
- Do pick the cleanest 1–2s of every clip after a frame strip of the whole clip — Veo breaks or burns text mid-clip.
- Do keep every Veo prompt in the target ratio **written in the prompt** («Vertical 9:16.») and with no dialogue.
- Don't use a plain opacity fade anywhere; don't end on a hard cut to black for this style.
- Don't let a VO line and the opening vocal overlap — shift the whole cut instead (`SH` in both scripts).

## How to build it
1. Brief + reference → shot list per VO sentence → asset request (prompts in `01_workflow.md` §D style).
2. Copy both reference scripts; edit `SHOTS`, `CAPS`, timing constants, `CLIPS`, `AMB`, then run the build via
   `ae_run.ps1`, render with `ae_render.ps1`, mix with `python -I mix_R3.py`, remux (audio-only changes never re-render).
3. Alternate audio versions: `R3_VOCAL=<file|none> R3_MIX=<name>.wav python -I mix_R3.py`, then remux each.
