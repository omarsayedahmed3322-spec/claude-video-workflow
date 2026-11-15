---
name: logo-on-object
description: Put a client logo on a real-looking object in an AI shot (van, car, door, product, sign, phone screen) so it looks printed on, stays in one place and one size across the campaign, and keeps its letters; also remove or move a logo in a finished clip. Use when Omar says «حط اللوجو على العربية», «لوجو على الباب», «اللوجو بيتنقل», «اللوجو مايل», «اللوجو باين لازق», «شيل اللوجو», «Veo كتب كلام», logo on van/product/sign.
---

# اللوجو على أي حاجة (Logo on an object)

> Moved here from `01_workflow.md` §D on 2026-11-11 (plan phase 2). Source reels: CLC R1 + R3 (CLC van campaign), Omar 2026-11-08.
> Prompts: `references/prompts.md`. Tool commands and their gotchas: `references/tools.md`.

## القاعدة الأساسية
- **A logo on any object (van, product, sign) goes in at the image step, never pasted on after** (Omar, 2026-11-08). CLC R1: our per-frame replacement (`logo_replace.py`) turned the logo with the disc's tilt, the client saw the stickers as «مايلة بشكل غريب»; 3 shots were remade at the image step.
- **Client asks for one small logo fix on an existing clip** («اللوجو بيتنقل»، «مايل»): try the smallest fix inside the edit first (move/turn the logo on the existing clip, `references/tools.md`). Regenerating is a proposal only (START-HERE §2).

## الخطوات (Codex pipeline, one step per request — CLC R1+R3 were rejected by the client)
1. **Flat logo, once.** Same artwork, no gloss/shadow, transparent PNG. Codex left a dark smudge in it (CLC), so check it zoomed, or build it in code from the master: one solid colour from the median of the circle, white from low-saturation/high-value pixels, alpha from a clean fitted circle. Attach only that file in every later request.
2. **Frame that already has a logo:** request A removes every logo/decal, request B adds the flat logo. A clean frame needs only B.
3. **One position for the whole campaign** (the client noticed the logo jumping front door ↔ sliding door): write it in words in request B (CLC: centred on the front door, below the window). Make one side-view frame first, then attach it as image 3 «position and size reference» to every other request. Pick a panel no shot opens (CLC: the sliding door opens in two shots, so the front door).
4. **Size and perspective in numbers, or each shot invents its own** (client: «moving forward and back, growing and shrinking»): give the physical size against a part every shot shows (CLC: ≈45 cm, ≈2.8× the door handle's length, ≈⅔ of the front door's width, «use the handle as your ruler»), and say it is printed on that surface. On an angled door it becomes an ellipse squeezed like the handle and door gaps; a flat circle facing the camera on an angled door is what reads as pasted.
5. **Parallel Codex requests are fine,** but check each output matches its source frame (mean-pixel diff against the inputs) before using it.
5b. **Omar judges tilt against the van's lower grey line, not the screen** `[ذوق عمر]` (CLC R4, 2026-11-14): Codex gave ~20° one way, then «NO TILT» the other way; both «مايل». What passed: placed in code on the clean frame, `tools/place_clean.py` (shear: text lines parallel to that line measured with Hough, verticals vertical, lit by the paint, `DARKCUT` keeps it off the tyre, `HANDLE` cuts round the handle). Size from the APPROVED shots only: width ≈ 95% of the front door, height ≈ 0.8 of the door (window bottom → grey line), centred on the door. Every new shot is measured against those, never against an earlier rejected version.
6. **Who makes the image:**
   - Omar in Flow: every shot with the logo in its prompt list says «ارفق اللوجو PNG مع البرومبت» (the flat logo file, with the printed-on wording in the prompt). That is how a logo lands in a realistic scene.
   - Claude: ChatGPT image, `free_llm.py image ... --ref <shot frame> --ref <flat logo>`. The flat file, not the glossy master object, or the shine comes along and it reads as a stuck-on sticker. Wording: `references/prompts.md`. A first pass that only asked for an upright decal still looked pasted (Omar: «مش شايف فرق»). With the full wording it comes out blended and spelled right.
7. **Animate from `First frame`:** Flow `Omni 1.2 Flash` (Veo did it in CLC, but Veo now only with Omar's OK, `01_workflow.md` §D table). Video models redraw the logo from frame 0: Omni kept it on the right door but turned the English into a plain sans and the Arabic «ق» into «ب» (CLC R1 L01/L06 close-ups).
   - Logo shots: **locked-off camera, no zoom** (a push-in enlarged the logo and its redrawn letters) and **one continuous shot, no cuts or angle change** (Omni jumped to a new angle mid-shot in a 4 s door-opening take).
   - **Kling slid the logo along the van** (CLC R4 S07: 116 px over 5 s while the camera drifted) → `patch_track.py` + inpaint the pink leftovers, then `tools/logo_track.py` (our logo, affine ECC on the van body, hidden behind anything passing in front). Or animate the clean frame and place the logo only in post.

## الفحص (every take)
- Letters on a native-resolution crop at **0, 2, 4 s**; worst in close-ups.
- Logo width/height should follow the door's angle (CLC: side view 0.99, three-quarter 0.6–0.84, steep close-up 0.45).
- Size **against the van, not the screen:** logo height / door-panel height (window bottom → body crease) must match across shots (CLC R3: 0.62 vs 0.78 read as «not the same size»; L05 scaled ×0.8).
- Removing text or a logo: check a frame from the middle and the end, not only the first (CLC R3 L05: «Qalviing» appeared after 1 s).

## إصلاح كليب خلصان (details in `references/tools.md`)
- **Remove** a logo or Veo's invented text: clean frame 0 with ChatGPT image, then `tools/patch_track.py` (or `self` when the text appears mid-clip).
- **Move** a logo to the right panel: `patch_track.py` to remove, then `tools/logo_place.py` to place it tracked.
- **Big close-up where the logo already sits right:** don't swap it for the flat one. A flat, upright, evenly lit disc filling half the frame read as «مش واقعي خالص» next to the original's shine and light, worse than its −1.4° tilt (CLC R3 L01, reverted). Fix a small tilt only by turning the existing logo, or leave it.
- **Never freeze part of an AI clip on frame 0** (logo or background) to hide a problem `[ذوق عمر]` (CLC R4 S04, 2026-11-14): the Kling take wobbles (van ±2 px, ground warping), the frozen part doesn't, and the shot read as «كل حاجة بترقص». Omar took the untouched take, even with a tiny man far back. Fix with a tracked patch, a still, or a new take.
- **Flat UI only** (chat avatar): `tools/logo_replace.py ... rigid`.
- **Text added onto a phone screen** reads as pasted unless it follows the screen with an affine track (move + zoom, not translation only), is softened like the footage (~1 px blur at 720p), lit by the screen around it and given grain (`CLC R1 scripts\chat_edit.py`). Check a crop of each clip after.

## قريب منها (stays in `01_workflow.md` §D)
- Typing / text on a phone screen (first + last frame, `Frames to Video`).
- Camera move across a real logo / sign from the client's 4K footage (no generated letters).
