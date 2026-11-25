---
name: reel-motion-graphics-hf
description: Omar's current look and checks for a full motion-graphics reel built in HyperFrames with no footage (business explainers, app or service ads, offers) - flat light design, fixed zones for title / stage / caption, minimum text sizes, words entering just before they are spoken, solid colours instead of transparency, and the frame-by-frame QC. Use when Omar says «موشن جرافيك», «ريل موشن», «موشن احترافي», «ستايل ماي بارت», «فلات وفاتح», motion graphics reel, HyperFrames explainer.
---

# Motion-graphics reel in HyperFrames (flat and light)

> Settled across 3 clients in 24–25 Nov 2026: `MYP` R1 (the reference Omar points to), `CLJ` R12, `AG1` R8–R10.
> Omar on the old navy / grid / glass look: «مش شغل موشن جرافيكس احترافي… ستايل قديم» `[ذوق عمر]`.
> Build with the HyperFrames skills (`hyperframes`, `hyperframes-cli`); Arabic text rules stay in `03_arabic_typography.md`.

## What it looks like (the fingerprint)
- **Flat and light:** light backgrounds, solid shapes, the client's colours; no glass cards, no glow, no dark navy grid.
- **Zones (1080×1920):** title y 280–640, stage (the illustration / UI / object) y 660–1240, caption y 1290–1400.
  Everything that matters inside x 60–950, y 250–1420.
- **Sizes:** body text ≥ 40 px, titles 76–96 px; anything that must read on a phone ≥ 640 px wide.
- **No empty space taller than ~250 px, and no empty frame inside a transition.**

## Timing
- Each word or element enters 2–5 frames **before** it is spoken (measured VO, `05` §1).
- The old caption leaves fully (0.12 s) before the new one enters; never two captions on screen.
- An «icon opens into the next scene» transition: 12 frames with `sine.in` (`power3.in` sits still for its first 4 frames).

## Do / Don't
- Do: dim or «not yet spoken» text = a **solid lighter colour**.
- Don't: `opacity` or `text-shadow` on text — in `AG1` R9 v3 a faded copy read as «two versions» of the text `[ذوق عمر]`.
- Don't: a first state set with `tl.set(...)` at t = 0 — use `fromTo` (and `immediateRender:false` where it must wait, `04` gotchas).
- Don't: photoreal human faces in business reels (`AG1` R8–R10, «متطلعش وشوش حقيقية»).

## Checks before sending to Omar
1. A contact sheet at 1 frame per second of the whole reel.
2. 5 fps strips around every transition (no empty frame, no early element).
3. A table: word / spoken at / appears at (each appears 2–5 frames before).
4. `tools\qc_reel.py --type mg` (via `ae_render.ps1 -Type mg` or directly on the MP4).
5. Mentor review in class `A+`: big mistakes only; ≤ 4 frames off the plan is accepted and written down (`TALK-TO-ME`).

## References
- `MYP` R1: `<Clients>\AG1\ماي بارت - عميل جديد\reel-01\` (`PROJECT_STATE.md` + the HyperFrames project).
- `CLJ` R12 and `AG1` R8–R10 `PROJECT_STATE.md` files for the same numbers in other palettes.
