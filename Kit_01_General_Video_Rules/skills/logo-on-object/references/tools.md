# الأدوات (logo-on-object)

Scripts live in `<Claude-Workflow>\Kit_01_General_Video_Rules\tools\`. Source: `01_workflow.md` §D logo bullet, CLC R1 + R3 (moved 2026-11-11).

## `patch_track.py` — remove a logo or Veo's invented text
- `tools/patch_track.py <in> <out> <clean.png> <box>`: clean frame 0 with ChatGPT image («remove X, keep everything else identical»), then it lays only the changed pixels over every frame (affine ECC around the box, light matched, grain).
- Veo often adds text **mid-clip** (frame 0 clean): pass `self` instead of a clean image.
- Always check a frame from the middle and the end, not only the first (CLC R3 L05: «Qalviing» appeared after 1 s).
- When a Veo take only has a logo problem, keep the Veo take and remove the logo with this instead of regenerating in Kling (`01_workflow.md` §D, Kling bullet).

## `logo_place.py` — move a logo to the right panel in a finished clip
- When the AI put it on a different door per shot: remove it (`patch_track.py`), then `tools/logo_place.py <clean> <out> <logo> <ellipse>` puts it on the chosen spot, tracked with affine ECC, verticals upright (shear), lit by the paint, with grain.
- Locked-off shot: pass `track_scale 0`. Plain white paint gives ECC nothing to hold and the logo ran off the door.
- Take the ellipse from an image that already shows the right place (CLC R3: the Codex «livery» frames), ECC-aligned to frame 0.
- Then check the size against the van (logo height / door-panel height, SKILL.md «الفحص»).

## `logo_replace.py` — flat UI only
- Stays only for flat UI (a chat avatar): `rigid <diameter> <screen_angle>`.
- «upright» means upright **on the screen**, not in the frame: measure the phone's tilt at frame 0 (fitLine on the black camera notch) and pass it; the logo then turns with the phone (CLC R1 L05: the phone was at −5°, an upright logo read as crooked).
- Not for logos on objects: CLC R1 per-frame replacement turned the logo with the disc's tilt («مايلة بشكل غريب»).

## Phone-screen text
- `CLC R1 scripts\chat_edit.py`: affine track (move + zoom), ~1 px blur at 720p, lit by the screen, grain.

## `place_clean.py` — the flat logo on a clean still, the way Omar approved it (CLC R4)
- `tools/place_clean.py in.png out.png cx cy ang screen_w vertical_extent` — shear, not rotation: text lines at `ang` (the van's lower grey line, measured with `HoughLinesP` on the clean frame), verticals vertical; lit by the paint (92nd percentile under it), 0.35 px blur, light grain.
- Size from the approved shots: `screen_w` ≈ 0.95 × front-door width at the logo's height, `vertical_extent` ≈ 0.8 × (window bottom → grey line), centre = door centre. `DARKCUT=95` drops it where the frame is dark (tyre, arch), `HANDLE=cx,cy,rx,ry` keeps the handle on top.
- Make a side-by-side of all the van shots after each one: Omar compares them («زي 5 و6»).

## `logo_track.py` — our logo on a moving AI clip (CLC R4 S07)
- `tools/logo_track.py clean.mp4 out.mp4 cx cy ang screen_w vertical_extent x0 y0 x1 y1` — same shear as `place_clean.py` on frame 0, then affine ECC on the van box (x0..y1) frame by frame; hidden where the frame differs from the tracked frame 0 (people, reflector passing in front).
- The clean clip: `patch_track.py` with the Codex clean still, then inpaint whatever pink is left (`r-g>35, r-b>15`) — the AI logo drifted out of the patch box.
