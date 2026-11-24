# 02 — قوانين الحركة ومعايير البناء (Motion Laws & Build Standards)

> Style-neutral. Style-specific looks (paper strips, invert strobe, collage…) live in the style kit.

## 0. الافتراضي لكل نوع ريل (اتعتمد من عمر 11 نوفمبر 2026، من القواعد الموجودة بس)

| نوع الريل | الافتراضي | جاي منين |
|---|---|---|
| متكلم قاعد أو ريل فخم | قطع عادي. زوم بطيء لقطة آه ولقطة لأ (≈1.9 %/s، واللقطة الأقصر من 1.5 ثانية ثابتة). ترانزيشن مرة أو مرتين في الريل، ومش في أول ثواني. مفيش `bounce`. مفيش صوت على القطع العادي. | CLA R1: سكيل `reel-talking-head` (الكاميرا، والترانزيشن، والصوت) |
| مونتاج على مزيكا | قطع على الضربة. اتجاه حركة واحد لكل جملة موسيقية. مفيش ترانزيشن بيحط أكتر من لقطة على الشاشة. | CLB R1: سكيل `reel-music-montage` |
| موشن جرافيك `UI` | القوانين التلاتة في §1 كاملة، ومعاها «مفيش فيد شفافية» و«الدخول بحركة وبلور» (§4). | §1، §4 |
| وثائقي | سكيل `style-documentary-heritage`. | السكيل |

- النوع مش في الجدول؟ اسأل عمر، ومتعمّمش ذوق عميل على عميل تاني.

## 1. The 3 golden laws
> الافتراضي للموشن جرافيك السريع، مش لأي ريل (شوف §0). متتشالش.
- **A. Speed never hits zero.** Nothing is 100% static inside a scene — a Master Drift null (expression, no keys) keeps a micro-drift. Use a **bounded** push, not an endless one:
  `value + [Math.sin(time*1.2)*8, Math.cos(time*0.9)*8, 35*0.6*(1-Math.cos(time*0.8))]` (≤3% zoom). The unbounded `time*35` zoomed +12% in 4.6s and pushed content out of the safe zone.
- **B. Overlapping action.** Each animation starts at 60–75% of the previous one. Stagger 2–4 frames (0.06–0.12s @30fps) or `valueAtTime(time - delay)`.
- **C. Every cut = peak camera velocity.** The shot opens with the camera already fast at 0.0s and decelerates; exits whip out past the cut.

## 2. Keyframes & easing
- **Never LINEAR.** Use the `applySmoothEase` helper (`tools/ae_helpers.jsx`) — handles 1D/2D/3D without array-length errors.
- Signatures: **Snappy entry** in 85 / out 15 · **S-curve in-scene move** 80/80 · **Whip exit** 15/85 · camera cut beats 88/12.
- The general "85–90% influence" rule means the **strong side** of a move; the other side follows the signature above (e.g. 15 on a snappy entry's out). There is no case for a plain/linear key.
- **Always separate Position dimensions** (`dimensionsSeparated = true`) before keying X/Y/Z — combined position creates swimming spatial beziers.
- Audit after every build: count keys and LINEAR keys (target 0) and report them.
- `comp.motionBlur = true` + `layer.motionBlur = true` on moving layers. **Turn motion blur OFF on layers whose Source Text changes per frame** (kashida-grow, counters) — it smears.

## 3. Camera
- **Two-Null rig:** `Cam_Drift_Null` (expression only) → `Cam_Beat_Null` (separated X/Y/Z keys, 88/12) → `Scene_Camera` (one-node). Never key the camera itself.
- Hold the beat null before each internal cut, jump on the cut (keeps Law C).
- **Music montage (rapid crash-zoom burst, directional clusters by measured camera motion, no split screens / several shots on screen, cuts on the beat):** skill `reel-music-montage` (`skills\reel-music-montage\SKILL.md`, moved there 2026-11-13).
- **Real footage of a person talking (punch-ins, slow zoom per shot at ≈1.9 %/s, rare transitions, B-roll edges on the speaker's cuts, static → handheld):** skill `reel-talking-head` (moved there 2026-11-12 from §3 and §4).
- When 3D gets fragile (envelopes, folding parts), a **clean 2D build with a `PAN_Null` parent** (whip X + scale zoom + sin drift) is more robust than a 3D rig.

## 4. Entries / exits
- **No pure opacity fade** (الافتراضي للموشن جرافيك السريع، شوف §0)**.** Entry = motion (Y-offset or scale 85→100) + Gaussian Blur 45→0 over 0.35s (Repeat Edge Pixels ON, 80/20).
- Scene entry blur f0–10, exit blur 0→45 over the last 6–8 frames (15/85).
- **Masks and crops are feathered by default** `[ذوق عمر]`: anything that moves through a mask or crop window (rolling digits, wipes, reveals, chart lines and area fills) fades out over a wide band (about 15–35% of the window), never a hard edge. Feather 0 only when the mask isolates one complete element exactly, so no cut shows and no pixel is missing or extra (AG1 R5, 2026-11-16: «اخطاء مبتدئين مش اخطاء ستايل»).
- **Bounce only on icons / cards / badges / logos**, never on text (inertial bounce expression in `tools/ae_helpers.jsx`).
- **Caption bubbles / chat lines (CLE R2, Omar):** pop-in = scale 55→100 with the bounce overshoot (a bubble is a card) + Gaussian Blur 16→0 over the first ~4 frames + motion blur ON. **Dialogue = one line on screen at a time:** each line leaves right after its last word (lift 70px, scale 100→86, blur 0→22, opacity out over 0.2s, 15/85) — stacking two speakers' lines scattered the eye.
- Collage/sticker wobble: `posterizeTime(12)` for a tactile stop-motion feel; text/camera/UI stay smooth.

## 4b. تايبوجرافي كبير على فوتيج حقيقي (key-phrase type on real footage) `[ذوق عمر]`
> Omar on CLA R8 v3 (2026-11-23): «عجبني اوي اوي اوي… التايبوجرافي والموشن والبلور الي بيتعمل ف البدايه ونعومه حركه الموشن», then «ثبتهم لمهارات المونتاج عندك عموما». Default for the key phrases of any real-footage reel. Fonts and colours come from the client's identity; the motion numbers stay. Reference build: `D:\Montage-02\Clients\AG2\CLA\reel-08 - care\scripts\build_CLA_R8.jsx` (25 fps, 1080×1920).
- **Layout:** two lines per phrase: a small plain line (58–80 px, white ExtraBold) + the key word big and italic in the brand accent (140–156 px), 92–114 px between line centres, max width 900 (shrink if wider), inside the safe zone and never on the face. About 4 phrases per 30 s; the caption hides while big type is up and never repeats it.
- **Entry (this is the smoothness):** each line lands on its own spoken word: Y +44 → 0 in 12 f, opacity 0→100 in 7 f, Gaussian Blur 18→0 in 10 f (Repeat Edge Pixels ON), tracking 12→0 in 14 f. Ease: first key out 12 %, last key in 85 %, speed 0; opacity 60/60.
- **Exit:** 6 f, up 22 px, blur 0→14, opacity →0, ease out 40 / in 70; lines leave 1 f apart, first line first.
- **Lists and tags:** a word list rises word by word on its spoken words (+36 in 11 f, opacity 6 f, blur 16→0 in 9 f). A name tag rises letter by letter (+28, 5 f per letter, 0.5 f apart, cubic ease-out `1-(1-x)^3`).
- **Shadow:** 13 %, distance 3, softness 34, no box behind big type. **No motion blur on the type:** the smoothness is the ease + blur + tracking, not the shutter.
- **Line motif (optional, one per reel, taken from the reel's idea):** stroke 3, dash 14 / gap 10, round cap, drawn with Trim Paths 0→100 in 9–16 f, ease 10/80 (R8: a couture stitch under the key word).
- **Around it:** plain cuts wide ↔ close 128 %, slow zoom 1.9 %/s on wides only (33/33, speed 0 at both ends); the type carries the motion, the camera stays calm.

## 5. Timing readability (from user reviews)
- Anything that must be read on a beat must be **fully in and sharp before the word is spoken**, and fully settled before the next cut.
- Typewriter lines finish ≥0.5s before the cut.
- Strike-through / "wrong answer" reveals finish ≥10 frames before the cut.
- Pop grids (many cards/phones) must finish popping before the cut — check the MP4 at the cut frame.

## 6. Layout & safe zones (9:16 Reels / TikTok, 1080×1920)
- **Reels safe zone (newest, 2026-11-04 — supersedes the older y 250–1500 map and my-motion Rules 05/07/18):** nothing important above **y≈250** (status bar, tabs) or below **y≈1420** (caption, username, music bar); keep **x ≤ ~950** (like/comment/share column) and a **~60px** left margin. All text, logos, labels, cards, icons and CTAs live inside it **at every frame including camera push**. Only backgrounds / full-bleed decor may cross.
- **Captions never cover the product or logo in the shot.** The caption Y (≈1330) is a default, not a law: per shot, check where the logo/product sits and move that caption block above it (still inside the safe zone). Re-check after swapping any clip; a new take framed the van lower and the pill sat right on its logo (CLC R1 L06 → captions to y 840, 2026-11-08).
- **Karaoke captions centre around y≈1330**, not in the lower third the way references place them. Why: CLG R1 had captions at y 1655 and a label at 1795 — the user called it «خطأ شنيع».
- When a footage element sits outside the zone, its label moves to the nearest safe spot instead of following the element. Overlay the safe-zone guide on inspection frames before saying done.
- Lay out inside that zone from the start. Retro-fix for an existing piece: a `SAFE_Fit` null per content comp (created at identity, parent all content, then scale ~88.5%, pos ~470/957) — `tools/safe_fit.jsx`.
- Max text/element width ≈ 880–900px; measure with `sourceRectAtTime()` × scale after building and shrink if over.
- Stacked blocks are vertically balanced (real block height centered, slightly below geometric centre); never crowd the top half and leave the bottom third empty.
- A badge/icon on a text strip: its bottom ≥30px above the strip and never covers a letter; ascenders never touch strip edges.
- Elements entering near text slide from **behind** the text strip (layered under it), never across the text.
- No empty frames: dark beats get a base colour + radial glow + subtle grid/pattern; key words go huge.

## 7. 3D stacking & parenting (render-safe)
- Layers that sit ON another 3D layer never share its depth: put them in the same shape layer as extra groups (first group = on top), or pull them to `z = −4` (or further if the parent swings). Same-depth layers flicker/vanish in the final render.
- **Parent children BEFORE giving the parent scale/rotation keys** — otherwise AE compensates the child's scale.
- A layer that rotates toward camera (flaps, cards) can cover text: move text in front (z −300 with perspective-compensated scale) and to the top of the stack.

## 8. Idempotent script skeleton
```javascript
var resultFile = new File(SCR + "NN_result.txt"); var log = [];
app.beginUndoGroup("Claude_Motion_Build");
try {
  // 1) delete previous comps by name  2) build  3) audit keys  4) saveFrameToPng check frames
  log.push("OK");
} catch (err) { log.push("Error: " + err.toString() + " at line " + err.line); }
finally { app.endUndoGroup(); resultFile.encoding="UTF-8"; resultFile.open("w"); resultFile.write(log.join("\n")); resultFile.close(); }
```
Never `alert()` in a CLI-run script (it blocks AE); always log to file. Put all timings as named frame constants at the top (`CUT1 = 64`, `F(n) = n/FPS`), with the measured VO times in a comment.
