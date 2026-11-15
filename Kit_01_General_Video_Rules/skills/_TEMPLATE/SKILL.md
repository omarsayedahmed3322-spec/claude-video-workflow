---
name: style-<short-name>
description: <One or two sentences: what this style/technique produces and WHEN to use it. Include the words the user actually says, e.g. "ستايل الجريدة", "newspaper collage look", "كابشن كاريوكي". This line is all Claude sees until the skill is used — make it specific.>
---

# <Style / technique name>

> Copy this folder to `skills/<name>/`, fill it, run `tools/sync_skills.ps1`, test in a fresh session.
> Keep this file under ~150 lines. Anything long (measurements, code, frame lists) goes in `references/` and is linked below.

## What it looks like (the fingerprint)
- Pace: average shot length, cuts per second, where cuts land vs the VO.
- Motion: signature eases (in/out influence), speeds, what never moves.
- Type: fonts (PostScript names), sizes, weights, colours, where text sits, how it enters/exits.
- Colour / texture: palette (hex), grade or LUT, overlays (grain, paper…).
- Sound: what kind of SFX, how dense, music feel.

## Do / Don't
- Do: …
- Don't (what makes it look generic / "AI"): …

## How to build it
1. …
2. …
Reusable pieces: `references/<file>` (scripts, MOGRT/template names, presets).

## References
- `references/measurements.md` — numbers measured from the reference reels (and which reels).
- `references/examples.md` — frame grabs / timestamps of the moments that define the style.
- Source tutorials / screen recordings: <paths or links>.
