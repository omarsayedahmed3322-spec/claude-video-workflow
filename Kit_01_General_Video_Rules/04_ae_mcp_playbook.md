# 04 — After Effects + MCP: أسرع وأرخص طريقة (Execution Playbook)

## 0. Which engine for which job (plan phase 7, 2026-11-13)
| Job | Engine |
|---|---|
| Cutting, prepping and grading footage | `ffmpeg` from the cut file (EDL: `plan_talking.py`, `edl_montage.py`) |
| Captions, cards, titles, end card, flat UI | a transparent `HyperFrames` layer (`03` last section) |
| A full motion-graphics reel with no footage | AE or `HyperFrames`: the same result in the test (SC02 of AG1 reel 1 rebuilt in ~11 min, text within 3 px of the approved AE render; Omar 2026-11-13: «الاتنين زي بعض… الاتنين حلوين»). In HyperFrames give Arabic text padding (~0.45em): `data-motion-blur` crops each mover to its box, and Palestine's ink runs past a `line-height: 1` box, so the word showed in halves [تقني] |
| Tracking, phone screen, effect on footage, 3D camera, anything Omar will tweak by hand | AE through the Runner (§2) |
| Omar's edits to the cut | `XML` in Premiere: `tools/edl_to_premiere_xml.py` out, `tools/xml_to_edl.py` back |

## 1. What each path can do (checked Nov 2026)
| Need | Best path | Notes |
|---|---|---|
| Everything in AE: small tweak, read values, full build, import | **`tools/ae_run.ps1 -Jsx <file>`** (Claude Runner, §2) | Arabic text straight in the script, saves + versions the project first, prints the result. |
| Runner not reachable (exit 2) | read its message: close the dialog / restart AE (Omar: «لو مش لاقي نبض اقفل الافتر وافتحه تاني»); then `AfterFX.exe -r`, then computer use → File › Scripts › Run Script File… | Old path, kept only as a fallback. |
| Emergency only: every runner attempt above failed | AfterEffectsMCP tools (`setLayerKeyframe`, `setLayerExpression`…) through the MCP Bridge panel | The Bridge panel stays **closed** otherwise; the runner heartbeat died twice on AE 2027 with it open (2026-11-21) `[ذوق عمر]`. Only a fixed list of predefined commands. |
| Render MP4 | **`tools/ae_render.ps1`** (aerender in the background, `-Preview` = half res draft) | No GUI, Arabic folders OK, checks the audio stream. Renders the **saved** project (any runner job saves it). `aerender ERROR An existing connection was forcibly closed` right after a runner build = transient; rerun once (CLC R3, 2026-11-08). **If it fails twice, or the mp4 comes out black from some point with «Unable to allocate N MB» in the log (ae_render still prints «rendered», black frames are only a QC warning): it is Windows commit memory, not the GPU** — compare `Get-Counter '\Memory\Committed Bytes','\Memory\Commit Limit'`; with the pagefile off the limit equals the RAM and Chrome/dwm crash too. Omar turns on the automatic pagefile (`sysdm.cpl`) and restarts; the next render passed first time `[تقني]` (CLA R5, 2026-11-21: 5 failed renders). **AE keeps the footage files of the open project locked:** a re-graded prep clip gets a new file name, never an overwrite `[تقني]` (CLA R5). Time remap: never delete all its keys (`while(numKeys) removeKey(1)`) → the property hides and the next `setValueAtTime` throws «property or a parent property is hidden»; set the new keys first, then remove the leftovers (CLC R3). Also check the runner log says `OK` before rendering: ae_render renders whatever was saved, even a half build. |
| Render QA stills / in-app render | Render Queue from a JSX (`tools/render_mp4_with_audio.jsx`) via the runner | Blocks AE while it renders. |
| Read user's manual edits | MCP read tools or a small read-only JSX that dumps keys to a txt | Never rebuild over them. |

## 2. Claude Runner — how scripts reach AE (since 2026-11-04)
- A Startup script (`tools/ae_runner/`, installed by `install_ae_runner.ps1`) starts a poller inside AE on every launch (~9 s after AE opens). It watches `OneDrive\Documents\claude-ae-queue\` (full path in `THIS-PC.md`; plain `C:\Users\PC\Documents` does not exist on this PC) and runs any `*.jsx` dropped there. No `-r`, no Bridge cycle, no computer use: it ran fine with the MCP Bridge window open.
- `tools/ae_run.ps1 -Jsx <file>` queues the script and prints `<id>.result.txt`: `STATUS` / `VERSION` / `RETURN` (the script's last expression) / the `clog()` lines. Exit 0 OK, 1 script error, 2 runner unreachable. If AE isn't running it starts it.
- Before each job the runner **saves the project and copies it to `<project folder>\_versions\<name>_<date>_<time>_<script>.aep`**. Add `-NoVersion` for read-only jobs. `_versions\` keeps the newest 10 copies + the newest copy of each older day; the rest are **moved** (never deleted) to `D:\AI\_Archive\aep_versions\<project>\` after every new copy — the user empties the archive. On a PC without that drive they go to `_versions\_old\`.
- Inside a job: `CLAUDE_JOB.dir` = the folder of the original script (write logs/frames there), `clog(x)` = a line in the result. The whole job is one undo step (Ctrl+Z undoes a build).
- **Arabic literals work as-is** (the job is sent as UTF-8 with BOM) — the `.src.jsx` → `\u` conversion is no longer needed.
- `#include` doesn't work in jobs → put `// claude-include: <path>` on its own line (absolute or relative to the script); `ae_run.ps1` pastes that file in. Example: `// claude-include: <Claude-Workflow>\Kit_01_General_Video_Rules\tools\ctrl_rig.jsx`.
- Never `alert()` and never leave an error uncaught in a script started with `-r`: the error dialog is modal and freezes the runner until someone clicks OK (happened 2026-11-04). Runner jobs are safe — their errors go to the result file.
- Status panel: Window › `Claude Runner.jsx` (dock it once; shows the last jobs, Pause checkbox). The runner works without it.
- Exit 2 "heartbeat stale": AE has a dialog open (error, save prompt, Home screen) or is rendering. If no one can click it, the dialog can be closed from PowerShell with `PostMessage(hwnd, WM_CLOSE)` on the `#32770` window of the AfterFX process. If the runner still says busy: Escape in AE (closes a hidden dialog), then `AfterFX.exe -r` a one-liner `$.global.CLAUDE_RUNNER.busy=false` `[تقني]` (CLA R4).
- **Computer Use on `After Effects` returns `user_denied` at once, with no window shown to Omar** → AE is marked «denied» in the Computer Use settings of the Claude app. Don't retry 3 times: tell Omar to remove the denial, or to close the AE window himself `[تقني]` (CLC R5, 2026-11-18: refused 3 times, Omar fixed it on his side).
- **Before closing or restarting AE, ask Omar whether another session is working on it** (CLI, CLJ…), so its work isn't lost `[تقني]` (CLC R5, 2026-11-18).
- **AE started with `-r` closes itself when the script finishes,** and the review frames the script writes in the background never get saved `[تقني]` (CLF R5, 2026-11-18). `aerender` isn't affected. Not tested yet: `app.exitAfterLaunchAndEval = false` at the top of the template.

## 3. Running a JSX from PowerShell (copy-paste)
```powershell
$reel = "<Clients>\<client>\ريل N"   # the client reel folder (Kit_04_Clients), never a side folder
powershell -ExecutionPolicy Bypass -File "<Claude-Workflow>\Kit_01_General_Video_Rules\tools\ae_run.ps1" -Jsx "$reel\scripts\build_<CODE>_R<N>.jsx"
```
- Long renders: run in the background and wait for the notification; don't poll in a loop.
- Before sending a big JSX, syntax-check it: copy to `.js` and `node --check file.js` (catches typos without touching AE). Node accepts things ExtendScript rejects — e.g. a `/` inside a regex character class (`/[\/]x/`) is a syntax error in ExtendScript; escape it `[\\/]` or avoid the regex.
- `run_and_sheet.ps1` (tools) = run through the runner + build a contact sheet from the PNGs the script saved.

## 4. Background renders — `ae_render.ps1`
```powershell
powershell -ExecutionPolicy Bypass -File "<Claude-Workflow>\Kit_01_General_Video_Rules\tools\ae_render.ps1" -Project "$reel\<CODE>_R<N>.aep" -Comp "00_Master_Reel" -Out "$reel\exports - <CODE> R<N>\previews\SC01_preview.mp4" -StartFrame 0 -EndFrame 120 -Preview
```
- **Check a render is alive on `AfterFX.com`'s CPU time**, not `aerender.exe` (that one stays at ~0 s the whole render; CLF R3). To stop a render kill `AfterFX.com` too (`taskkill aerender` alone leaves it rendering), and render the retry under a new file name `[تقني]` (CLA R4).
- `-Preview` = template «Claude Preview Half» (draft, half res, no motion blur): for timing reviews, ~2× faster. Without it: «Claude Final». Both use OM «Claude H264 Audio» (audio forced On). The templates are made once by `ae_runner/setup_render_templates.jsx` (run with `ae_run.ps1 -NoVersion`; redo on a new AE version).
- Arabic folder names are handled: the script makes ASCII junctions under `C:\ae_jx\` (a `.txt` next to each says where it points). The **file names** (`.aep`, output) must stay ASCII — they already are by the naming rules.
- It renders the **saved** file: run it after a runner job (which saves) or after the user saves.
- At the end it prints ffprobe and warns if the MP4 has no audio. Checked 2026-11-04: preview 540×960 + audio, final 1080×1920 + audio, from a folder named «اختبار ريل».

## 5. Rendering gotchas (AE 2026)
- MP4 = output template matching `/^H\.264/`. **Audio:** `om.setSettings({"Output Audio":"On"})` — the numeric value `1` means **Off** in AE 2026. Make sure the VO layer has `audioEnabled = true`.
- Verify the MP4 has audio: `ffprobe` or check the bytes contain `soun` / `mp4a`.
- **No PNG template in AE 2026** → still-frame QA via the `TIFF` template, 1-frame RQ items.
- Many outputs → queue them all and call `rq.render()` once.
- Remove old RQ items for the comp before adding new ones.
- Precomp audio for solo listening: put the VO in each scene precomp as a **guide** layer at `startTime = -sceneStart` (audible solo, never doubled in the master).
- When only the audio changes, don't re-render the picture: remux the new mix onto the same video with ffmpeg (seconds instead of a full render).

## 6. Verify (what actually catches bugs)
1. `comp.saveFrameToPng(t, file)` for quick checks + contact sheet.
2. **Render-Queue TIFFs** of key frames — `saveFrameToPng` can look fine while the final render drops 3D layers.
3. **The MP4 itself**: open it in the built-in browser, seek `<video>` to the exact seconds (words, cuts) and grab frames to a canvas. The user reviews the MP4, so this is the ground truth.
4. Overlay the safe-zone map on the check frames for 9:16.
5. Pull frames from the final MP4 with `ffmpeg -ss <t>` at the words and cuts that matter — not only project frames.
6. A **22-frame contact sheet** per review catches text off screen, fallback fonts and shifted highlights fast.
7. Don't say "fixed" until the log, timing and actual values confirm it: several times the frames came out unchanged because of a cache, not the fix.
8. **Check the MP4 has sound before sending it** (`volumedetect`, max must not be −91 dB). CLA R1 v12 came out of aerender silent although the comp had the MIX layer; Omar couldn't review it. Safe path: remux the mix onto the render (`-map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k`).
9. Any texture or overlay the user supplies is meant to be seen: never a Guide layer (even if a brief says "Guide"), and check it shows in the render (AG1 R1 paper: Multiply 25%; 15% was invisible).

## 7. Scripting gotchas learned
- **`child.parent = shape` from a script keeps the child's look at frame 0, so it divides by the parent's scale there:** parent keyed 70% at 0 → child 143% (CLC R7 badge text ran over its bars), keyed 0% → child gone (CLA R3 number in a pill). Set `child.transform.scale.setValue([100,100])` right after `parent =`; the child's position is in the parent's layer space (shape layer: origin = shape centre, not the anchor) `[تقني]` (CLC R7, 2026-11-22).
- **`saveFrameToPng` check PNGs showed a b-roll layer without its 158 % scale; the MP4 was right** (CLA R3). Check scale/crop on the rendered MP4, not on the check PNGs `[تقني]`.
- **The build template closes the open project with `SAVE_CHANGES`:** if another reel's project is open, it gets saved (and the runner versions it) before the new build. Close other reels first `[تقني]` (CLA R3: R2's `.aep` was saved). The same for a stem-swap script (`swap_stems`): it ran on the open CLA R4 project, didn't find its layers and just saved it (CLJ R4, 2026-11-16). Before any swap script, check `app.project.file.name` is this reel's and stop if not `[تقني]`.
- Convert Audio to Keyframes = `app.executeCommand(app.findMenuCommandId("Convert Audio to Keyframes"))` with only the audio layer selected in an opened temp comp; delete the temp comp after.
- `sourceRectAtTime(t,false)` is the only reliable text size; measure at a time when the layer is fully in.
- Effects by match name: Gaussian Blur `ADBE Gaussian Blur 2` (prop 3 = Repeat Edge Pixels), Drop Shadow `ADBE Drop Shadow` (2 opacity, 3 direction, 4 distance, 5 softness). Set effect values by the property match name (`"ADBE Unsharp Mask2-0001"` amount, `-0002` radius), not by index: `property(1)` on Unsharp Mask is a 0–1 control and threw «Value 30 out of range» (CLD R3).
- Shapes: `ADBE Root Vectors Group` → `ADBE Vector Group` → `ADBE Vectors Group` (+ Rect/Ellipse/Shape) ; Repeater `ADBE Vector Filter - Repeater` for grids.
- Font check: create a text layer, set the font, read it back — if it differs, the PostScript name is wrong. **A font that isn't installed reads back unchanged** (AE keeps the name and renders a fallback; the only sign is «Project has missing fonts» in the render log), so check the font files first (`ls %LOCALAPPDATA%\Microsoft\Windows\Fonts`). This PC has `Cairo`, `Raleway` and `Montserrat` in all weights (checked CLA R3, 2026-11-13; CLA R1 had only `Raleway-Bold`/`Black`).
- **`setTemporalEaseAtKey` array length:** spatial properties (Position, Anchor) take **one** `KeyframeEase` per side even though they are 2D/3D; `TwoD`/`ThreeD` non-spatial ones (Scale) take 2/3. Pick by `propertyValueType` (`TwoD_SPATIAL`/`ThreeD_SPATIAL` → 1), or it throws «Value array does not have 1 elements».
- **Camera MP4s with rotation metadata (`side_data rotation=±90`, 4K 50p event footage):** transcode them first with ffmpeg (it auto-rotates) to 1080×1920 at the comp fps (`scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=25`, `crf 14`), then import. Fast in AE and no rotation guesswork (CLA R1: 11 clips).
- Never `alert()` from a CLI script. Always try/catch + file log with `err.line`. The log goes next to the script in the reel's `scripts\` folder, never in a temp/scratchpad folder (it disappears).
- **Time Remap:** add the new keyframes first, then delete the old ones — deleting all keys hides the property and `setValue` fails after.
- **Expressions written from Python:** any `\n` inside the expression string must be written `\\n`, or the line breaks and AE throws «Unterminated string».
- **`+` on arrays is vector math in AE scripting:** `"pos=" + [0,-100]` throws «Object of type Error found where a Number, Array, or Property is needed». Log arrays with `.join(",")` or `.toString()`.
- **3D camera** threw «divide by zero» and wouldn't zoom on a flat page (AG1 R2) → a 2D two-null rig (Anchor = look-at point, Scale = zoom) is simpler and reliable for flat layouts.
- **Adding an effect invalidates the objects of the effects added before it** on that layer («Object is invalid»). Keep names, not objects: `ctrlRef()` only needs `{ name: "…" }`; `ctrl_rig.jsx` `ctrlAdd` returns just that since CLH R7 (2026-11-21) `[تقني]`.
- **CTRL restores saved slider values on rebuild, so a new default in the code never shows** (CLA R4: tint 16/18 stayed from v1 to v3). To change a default, rename the slider `[تقني]`.
- **Colour effects that don't take what you'd expect** `[تقني]` (CLA R4): Levels gamma (`ADBE Easy Levels2-0005`) takes no expression → drive the adjustment layer's Opacity from the slider; Vibrance's amount skips skin → use its Saturation (property 2) on a face; Hue/Saturation master saturation shifted the hue (magenta glint) → desaturate with a grey solid in `Saturation` blend mode.
- **Time remap freeze:** after `timeRemapEnabled = true`, `setValue()` fails («property or a parent property is hidden»); set both default keys with `setValueAtKey(k, t)` instead.
- **A build that crashes leaves an unsaved «Untitled Project» open; the next build's `app.newProject()` then opens a Save As dialog and the runner hangs** (CLA R1, Omar had to click it). Start every build script with `app.project.close(app.project.file ? CloseOptions.SAVE_CHANGES : CloseOptions.DO_NOT_SAVE_CHANGES)` — never `if (app.project.file)` alone. If a job sits in `.running` with AE CPU flat, look for a dialog before anything else.
- **`CLAUDE_JOB.dir` is a string** in runner jobs → `new Folder(String(CLAUDE_JOB.dir))` before `.parent` / `.fsName`.
- **Stacking order bites twice:** `layers.addShape()` / `addText()` put the new layer on top, so text made before its bubble ends up hidden under it → `tx.moveBefore(shape)`. Inside a shape layer the **first** group added is on top → add the small parts (buttons, icons) before the big background rect (CLE R2: bubble text and the «إرسال» pill were invisible).
- **Shape match names:** group position = `ADBE Vector Position`, group opacity = `ADBE Vector Group Opacity`, scale `ADBE Vector Scale`, rotation `ADBE Vector Rotation`. Noise effect: the colour checkbox is `Noise Type`.
- **`makeText(…, font)` skips RTL + the Universal composer** when a font is passed → set `FONT_AR` to the font and call it without the font argument.
- **`saveFrameToPng` is asynchronous** — check frames written by the same job can still be the previous build's, and it sometimes doesn't overwrite an existing PNG at all (the check images stayed old after a rebuild, CLA R3 v5, 2026-11-17) `[تقني]`. Judge from frames pulled out of the rendered MP4 (`ffmpeg -ss`).
- **Any video cropped and scaled in ffmpeg before AE must end with `setsar=1`** `[تقني]`: `crop` + `scale` gave a non-square pixel (1216:1215) and AE showed the shot narrow with black on its sides (CLA R3 v5, 2026-11-17).
- **Caches:** Omar said «لازم نمسح الكاشات قبل أي حاجة، هي اللي عامله المشكلة» (CLF R5, 2026-11-18). The session didn't say which cache.
- **Mixed clip sizes (720 and 1080 wide):** base scale = `150 * 720 / item.width`, never one constant.
- **Constant-speed cuts from long clips: use `layer.stretch = 100/speed` + `startTime = t0 - src*stretch/100`**, not time remap with `startTime = 0`: the remapped layer rendered black once `t0` was past the clip's own length (CLB R1, every shot after 9 s).
- **`layers.addSolid(..., duration)` ignores the duration** → a solid moved with `startTime` runs to the comp end and covers everything under it. Always set `inPoint`/`outPoint` after.
- **Time remap for slow-downs:** set the new keys first, then remove the old ones by time; ease only the last key; `frameBlendingType = FRAME_MIX` + `comp.frameBlending = true`.
- **Patching scripts that contain Arabic from bash:** a heredoc with Arabic + Python raw strings broke the shell. Write the patch `.py` with the Write tool and run it with the file path as an argument.
- **The runner saves the project that is open, not yours:** a CLD build first saved and versioned the open AG1 R3 project. Build scripts open their own `.aep` (`app.open`) and close it after if another reel is in progress. Before moving a reel folder, close its project (`app.project.close(CloseOptions.SAVE_CHANGES)`) so the runner doesn't re-save it at the old path.
- **A shape layer drawn with comp-pixel vertices** sits at the comp centre by default (`position [W/2,H/2]`), so everything lands offset by half a frame → `layer.transform.position.setValue([0,0])` `[تقني]` (CLC R4 corner brackets, 2026-11-14).
- **An unsaved «Untitled» project open in AE + a runner job = a Save As dialog that hangs the runner** (job sat «queued» past 600 s, CLC R4). Close it, or type the reel's `.aep` path in that dialog, then rerun `[تقني]`.
- **`app.open()` on a project whose footage moved** can raise a missing-files dialog that freezes the runner → `app.beginSuppressDialogs()` before it, then rebuild/relink.
- **`ffmpeg` inside a `while read` loop eats the loop's stdin** (file names came out cut: `c/مشهوره…`). Always `ffmpeg -nostdin` in loops. ffmpeg 9: `-vsync` is gone → `-fps_mode passthrough`.
- **AE locks every imported file:** re-rendering an overlay or mix over the same path fails («Permission denied»). Write each new render to a new name (`overlay_v2.mov`) and `item.replace()` it, keeping the project item name.
- **A PNG that already has alpha:** check it (`ffmpeg … format=rgba,crop=1:1:5:5`) before keying. `colorkey` on the AG1 logo turned its alpha-shaped blue fill into a solid square.

- **Stems that each carry the mix gain clip when AE sums them** (the limiter ran on the mix only: QC «clipping 0.2 dBTP», CLJ R4). Apply the limiter's per-sample gain to every stem (`gr = |limited| / |pre|`, min-filter 2 ms) so the stems add up to the limited mix `[تقني]` (`CLJ reel-04\scripts\build_audio.py`, 2026-11-15).
- **Windows paths inside a Python string written from a bash heredoc lose `\f` `\v` `\b`** (`reel-02\footage` became `reel-02` + form feed, `assets\vo` lost its `\v`). Build the path with `chr(92)` or forward slashes, and print the patched lines before running the JSX `[تقني]` (CLJ R2/R4, 2026-11-16).
- **A WAV rewritten on disk keeps playing the old audio in AE:** `importFile` finds the existing item, so call `item.mainSource.reload()` after it (CLB R2 mix).
- **Line breaks in AE text = `\r`.** When a Python generator writes the JSON, write the escape (`"\r"` in the .py source), never a raw CR: it broke the .py (CLB R2). Break captions by hand into balanced lines instead of letting a box auto-wrap (orphans like «size?» alone on line 2).
- **A re-rendered overlay/MOV keeps its old length in AE** even after removing the item, re-importing and `mainSource.reload()` (CLD R3: the file was 30.43 s, AE kept reading 30.00 s, so the end hold was lost). Import each new render under a new name (`_v2`, `_v3`) and check the logged `duration` against `ffprobe`. Same for any file AE has imported (the mix WAV too): AE keeps it open, so writing over it fails with «Permission denied» (CLD R5) → write the new version under a new name.
- **`ae_run.ps1` printed «NO RUNNER» (a dialog open in AE / the runner panel closed) and the chained `ae_render.ps1` still rendered the OLD project** — a preview that silently lacked the fix (CLB R2). Check the build's last line (`built …`) before rendering; never chain build → render blindly.
- **Removing every Time Remap key switches time remap off** → the next `setValueAtTime` fails with «property … is hidden». Set the new keys first, then delete the default end key (CLI R4) `[تقني]`.
- **AE locks imported footage:** `curl -o` onto a clip that is in the open project fails silently (the old file stays), even after closing the project. Download the new take as `V11b.mp4` and map it in the build script (`TAKE = { V11: "V11b" }`) (CLI R4) `[تقني]`.
- **Render "no output file"** right after a previous render of the same name → the old MP4 is open somewhere; render to a new name.
- **A stretched layer (`stretch` ≠ 100, e.g. 108.000004 %) lands one frame late on both edges** `[تقني]` (CLA R6 v2–v4): a black frame on its first cut and the layer still covering the next shot's first frame (a one-frame flash). AE also clamps `inPoint` to `startTime`. Fix: `startTime -= 0.5/fps; inPoint = t0 - 0.5/fps; outPoint = t1 - 0.5/fps`. `qc_reel`'s black-frame check misses a single frame: run `tools\check_cuts.py <mp4> <edl.json>` after every render.
- **Render only if the build printed its OK line** `[تقني]` (CLA R6 v5: the runner was stale after an «Untitled» AE, the chained render shipped the old project, byte-identical to v4): `if grep -q "OK layers" build.log; then ae_render…; fi`.
- **Comparing the render's audio to the mix:** AAC adds ≈21 ms of priming, so a plain correlation reads ≈0; cross-correlate a window first.

- **HyperFrames/GSAP** `[تقني]` (AG1 R5, 2026-11-16): `fromTo` draws its from-state at t=0, so a ring or particles meant for 1.6 s showed on frame 0: pass `immediateRender:false`. An SVG line drawn with `strokeDashoffset` and a round cap shows a dot before it draws: keep it at opacity 0 until the draw starts. A 54 s 1080×1920 reel renders in about 60 s. Entrances that still showed early were fixed the same way (AG1 R7). `data-start` rounded up put 5 cuts a frame late: write starts as exact multiples of 1/30 and check them with `check_cut_frames` (CLD R9, 2026-11-20).

- **Runner heartbeat stale with no dialog at all** `[تقني]` (CLB R3, 2026-11-17): AE sat on an empty «Untitled Project» left by another session; no `#32770` window, Escape did nothing, and even `AfterFX.exe -r` never ran. Check the Project panel is empty (title without `*`), then close AE normally (`CloseMainWindow`) and start it again: the runner beats ~10 s after launch. One screenshot to see the state is the only Computer Use it needs.
- **`layer.copyToComp()` does not always put the copy at index 1 in AE 2026** (it lands next to the selection) → deselect all, copy, find the new layer by `layer.id`, then `moveToBeginning()`. Use it to carry Omar's hand-made layers (shadow solid, veil, logo, CTRL, adjustment layer) into a new comp without touching the old one; copy `CTRL` before the layers whose expressions read it `[تقني]` (CLB R3).
- **24 fps AI clips in a 25 fps comp repeat one frame a second** → `item.mainSource.conformFrameRate = 25` on the new items only (an item already used in a comp Omar edited keeps its timing), and multiply every `src` second by 24/25. Speed ramp = time remap with two keys: `setValueAtKey(1, src0)`, `setValueAtTime(t1, src1)`, remove the default end key, then `KeyframeEase(speed, influence)` out of key 1 (fast) and into key 2 (≈0.9× so no frame repeats); slow-downs get `PIXEL_MOTION`, ramps `FRAME_MIX` `[تقني]` (CLB R3).
- **ffmpeg adds a `tmcd` data track when it transcodes AE's ProRes master** (the MP4 shows 3 streams) → `-map 0:v:0 -map 0:a:0 -write_tmcd 0` `[تقني]` (CLB R3).
- **A clip resized with ffmpeg `scale…,crop` can carry a non-square SAR (2889:2888) and AE shows it with black side bars** → end the filter with `setsar=1` and check `sample_aspect_ratio` with ffprobe before the build `[تقني]` (CLF R7, 2026-11-22: v1 went out with bars on 4 HyperFrames clips).
- **Job stuck on `.running`, heartbeat stale, AE CPU at 0 = a window is open inside AE** (CLF R7: «Adobe Genuine Service Alert», 23 min lost). List AE's window titles with `EnumWindows` from PowerShell, tell Omar the title and ask him to close it; don't wait for the 900 s timeout `[تقني]`.
- **AE locks footage that is in the open project**: overwriting `L04.mp4` failed with «Permission denied» → save the replacement under a new name and change the code in the shot table `[تقني]` (CLF R7).

## 8. Token-saving habits
- Read the handoff/state file instead of re-exploring the project.
- Never open media with Read; ls/ffprobe/AE metadata only.
- Prefer one parametrised script copied per scene (`NNa_vo_amplitude`, `NN_build`, `NNb_render`) over re-deriving code.
- Batch: one script that builds + audits + saves check frames; one render call for all outputs.
- Computer use only when no CLI/MCP path works, low-scale screenshots, batched actions.
- Never `find` over all of `D:\Montage-02\Clients\`: the AG2 downloads make it run past 120 s. Scope it to the company or client folder `[تقني]` (CLH R7, 2026-11-21).

## 9. Computer use (it takes over the user's screen)
- Only for a concrete step that needs it (running a JSX from the menu when `-r` fails, closing/reopening the Bridge). The user said «ماتشغلش الكمبيوتر يوز عالفاضي… شغله بسبب فقط».
- Batch the clicks into one short burst per run, take a screenshot right before each burst (the user may have moved the AE window — clicks once landed on the desktop), and release the screen right after.
- Never keep it engaged, take screenshots or hold the screen while waiting on renders, thinking or editing files — do edits and log checks via the shell.
