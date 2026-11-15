---
name: reel-music-montage
description: Edit a reel cut to music from real footage with no voice-over (shop or product showcase, fashion, a place, an event recap) - beat grid from the track, Omar's rough cut matched to the 4K originals, camera-motion clusters, per-shot colour, the rapid crash-zoom burst, cuts on every beat, outro, QC of cut frames against the beats. Use when Omar says «مونتاج على مزيكا», «ريل على المزيكا», «قطع على البيت», «مع كل ضربة قطعة», «استعراض للمحل», «راف كات», «الهوك السريع», «كراش زوم», music montage, cut on the beat, showcase reel.
---

# ريل مونتاج على مزيكا (Music montage)

> Moved here on 2026-11-13 (plan phase 5-ب) from `02_motion_laws.md` §3 (rapid-zoom hook, directional clusters, no split
> screens), `01_workflow.md` §D (the rough cut, colour) and `05_audio_sfx.md` §1 (music-only beat grid + render check).
> Source reel: CLB R1 (AG2, `D:\Montage-02\Clients\AG2\CLB\Reel-01\`), approved `exports\CLB_R1_vFinal.mp4`
> (22.6 s, 2026-11-09, after the client's round) = `scripts\edl_CLB_R1_v14.py`.
> Scripts in `references/` (copies; the originals stay in the reel's `scripts\`): `beat_grid.py`, `match_rough.py`,
> `motion_rough.py`, `grade.py`, `edl_montage.py` + `build_montage.tpl.jsx`. Each has a SETTINGS block at the top with
> CLB's values: copy them to the new reel's `scripts\` and fill it.

## أول حاجة: الافتراضي وذوق العميل
- **Default for this reel type** (`02` §0, approved by Omar 2026-11-11): cut on the beat; one motion direction per musical
  phrase; no transition that puts more than one shot on screen.
- **Client taste stays under the client's name** — never the default for another client:
  - CLB: «مع كل ضربة قطعة»: no shot longer than one beat except one shot holding the break, plus half-beat bursts on the
    strong hits; no repeated shot at all, not even another second of the same clip (client, R1 round 2026-11-09). Captions
    only when the brief has text (Gotham Light, `CLB` file). Outro: ivory veil + gold logo (mandatory instructions).
  - CLB's shared colour look (`grade.py` LOOK) is CLB's. **Another client: ask Omar for the look** (Omar, 2026-11-13);
    the per-shot correction is the general part.
- Read the client file and its «قايمة فحص قبل التسليم» before the plan; the checklist is reviewed before every send.

## الخطوات بالترتيب
1. **Footage + references:** probe every clip (`01` §D; FX30 vertical = `3840×2160` with `rotation=90`, 50p → clean 50 % slow-mo).
   Analyse the client's references before the beats plan (`CLB` file: they show the taste for every video).
2. **Beat grid from the file, never from agy/Gemini** `[تقني]` (§شبكة الضربات): `beat_grid.py <track> --near <song sec>`.
3. **Omar's rough cut, if he made one** = his shot selection (§الراف كات): `match_rough.py` → `motion_rough.py`.
4. **Beats plan** (class A/B: stop for approval): which shot on which beats, the direction clusters, the burst(s), the break, the outro.
5. **Colour:** `grade.py sheet` (before/after) → OK → `edl_montage.py grade` (graded intermediates, §اللون).
6. **Build:** fill THE CUT in `edl_montage.py` → `edl_montage.py jsx` → `tools\ae_run.ps1 -Jsx <build>.jsx` → `ae_render.ps1 -Type montage`.
7. **QC** (§الفحص) + the client checklist as a table, every «نعم» with a second or frame (`01` §E).

## شبكة الضربات (`05` §1 before 2026-11-13)
- **The drop = the first kick in the bass band.** Low-pass the track at 150 Hz and find the first jump of its envelope
  (`scipy.signal.butter` + RMS at ~5 ms); beat period = distance between two such drops / beat count (`beat_grid.py --drop`).
- **Busy bassline** (the low-pass catches every bass note): take the kick from the percussive part instead (`librosa.effects.hpss`
  → band-pass 40–110 Hz → `find_peaks`), lay the librosa beat grid over it and nudge the grid so the kicks sit on it (CLB R1
  v11: the grid was 0.07 s late → cuts 2 frames after the kick). librosa `beat_track` / onset peaks put the drop 1.3 beats late
  in CLB R1 (snare, not kick), and doubled the tempo (184.6 for 92.9 BPM). `beat_grid.py` does all of this.
- **Music timing in seconds is never taken from agy/Gemini** (Omar, 2026-11-09: «بيجيبه بالتقريب»): agy may describe the
  structure (intro, build, drop) in words only; every cut time comes from measuring the file.
- Read the kick list `beat_grid.py` prints: on CLB R1's track the kicks shift against one constant grid after the break
  (≈ +0.09 s at reel beats 24–32). Aligned on the opening kicks, R1 was approved like that.
- In the EDL: `B` = period, `S0` = song second at reel beat 0 (the music layer starts at −S0), `bf(beat)` = reel frame.

## الراف كات (`01` §D before 2026-11-13)
- **Omar's rough cut = his shot selection, not the material.** Match every shot to the 4K original + source second (tiny-frame
  correlation, `match_rough.py`: 33/33 shots matched on CLB R1, scores 0.87–0.99) and build from the originals.
- Still drop any shot whose lighting or quality is weak even if it is in the rough cut (Omar).
- Set `ROUGH_FPS` to the rough-cut file's frame rate (R1: 30).

## الاتجاه والحركة (`02` §3 before 2026-11-13)
- **Directional clusters:** group shots by measured camera motion (zoom-in / pull-out / truck left / truck right, `motion_rough.py`)
  and keep one direction per musical phrase; change direction only on a music change (drop, break). Mixed directions inside a
  phrase read as shaking.
- **No transitions that put several shots on screen at once** (split rows, stacked/pop-up frames) unless Omar asks: he rejected
  the 3-row split in CLB R1 («سئ جدا»). Clean cuts on the beat.
- Every shot carries a small scale move (`s0`→`s1`, R1 beats: 1.00→1.06 at speed 1.2); a second beat on the same clip = a static
  punch-in 1.22→1.25 (R1 C0390, C0401).

## الهوك السريع (rapid crash-zoom burst)
- **What** (Omar, CLB R1, was `02` §3): 4–6 shots of 1–1.5 beats (v14: 8 shots of half a beat), all pushing forward (scale
  1.0→1.3 + the clip's own push at 2× speed). Ease: **first shot** eases in (slow start → fastest at the cut), **last shot** is
  the reverse (fast start → settles, `land`), **shots in between** keep the crash graph (in 85 / out 3). Motion blur visible:
  comp shutter **360**, phase **−180**; 240 read as no blur.
- **When** `[ذوق عمر]` (Omar, 2026-11-13): not mandatory, but one of the nice techniques: use it in every reel where it fits,
  not necessarily at the start (R1 v14: b0–4 and again on the strongest hit b27–29).
- A whoosh on every burst cut (`base_whoosh_fast` −14…−13 dB, the one on the landing −9), as in the R1 SFX list.

## اللون (`01` §D before 2026-11-13)
- **Per-shot correction + one shared look, baked into one `.cube` per shot** (`grade.py`): neutral surfaces → 60 % of the way to
  grey so the room keeps its warmth, levels + gamma to a target mid, then the shared look; night shots are never darkened.
- Check on a before/after sheet, then render graded intermediates with ffmpeg `lut3d` (1620×2880 for zoom headroom up to 1.5×;
  **native 2160×3840 when punch-ins go past 1.5×**, CLB R2; 4 in parallel). Footage was 8-bit Rec.709 → gentle moves only.
- If AE holds the old intermediates open, render the new ones into a new folder instead of deleting (ffmpeg fails with
  «Permission denied» on every file otherwise — CLB R2, again): name the folder per version from the start (`GR` in SETTINGS).
- Clips not in the rough cut get their grade measured from 3 frames of the clip itself (`ri_of()`).

## التكرار
- Repeats count by what the viewer sees, not by clip name (`01` §D): an AI clip whose first frame is a real shot repeats it;
  the same shelf from another angle is a repeat (CLB R1 v11–v13). Check the strip for look-alike neighbours.

## القفلة والصوت
- Outro: the client's (CLB: the filmed L'UOMO sign pulling back, ivory veil 88 % + gold logo 700 px riding the sign, R1 v13–v14).
  Add 2 beats of logo hold so the music fades out instead of stopping (R1 v15).
- Levels: `05` §6 row «مزيكا بس» (no decision yet) and the music rule in `05` §6 (CLB R2). SFX library first (`05` §2).

## الفحص
- `tools\qc_reel.py <mp4> --type montage --edl <cuts>` (or `ae_render.ps1 -Type montage`).
- **Check the render against the music** `[تقني]` (was `05` §1): measure the first kick in the MP4 and compare with the cut frame,
  and list every cut frame of the MP4 (ffmpeg `select='gt(scene,0.2)',showinfo`) against the expected beat frames from the
  EDL; they should match exactly (CLB R1 v14: 31/31).

## اللي اترفض (متعملوش)
- Split screens / 3 rows / stacked frames (CLB R1 «سئ جدا»); the 3-shots-together transition (R1 v10).
- Cut times from agy/Gemini; librosa's raw grid without the kick nudge.
- A repeated shot, or two look-alike neighbours (CLB client, R1 v11–v13).
- Motion blur at shutter 240 (read as none).

## المراجع
- `references/beat_grid.py` — period, phase, kicks, `S0`, drop. Written 2026-11-13 from the method above (R1's measuring code
  wasn't saved). Tested on R1's track: 0.6450 s / S0 0.120 against R1's 0.6457 / 0.110 → at most 0.015 s (0.36 frame) apart over the 35 beats.
- `references/match_rough.py`, `references/motion_rough.py` — tested 2026-11-13: with R1's SETTINGS they rewrite R1's
  `work\match\rough_map.json` byte for byte.
- `references/grade.py` — tested 2026-11-13: R1 shots 0, 5, 9, 12, 25 give R1's `.cube` files byte for byte.
- `references/edl_montage.py` + `build_montage.tpl.jsx` — tested 2026-11-13: the data line of the generated build equals
  R1's `build_CLB_R1_v14.jsx`; the template differs only by its SETTINGS block and the lines that read it. Not run in AE
  after the copy (the build saves and closes the open project).
