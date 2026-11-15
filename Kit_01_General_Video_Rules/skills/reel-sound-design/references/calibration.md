# Calibration (reel-sound-design)

> Moved out of `SKILL.md` on 2026-11-11 (plan phase 2). Text unchanged. The level numbers moved to `Kit_01_General_Video_Rules\05_audio_sfx.md` §6; the rest stays here.

## Calibration (fill from Omar's own projects)

Source: Premiere -> File -> Export -> Final Cut Pro XML of his best finished reels. Parse clip names, track, in/out, levels; compute:
- whoosh start offset vs cut (frames), per style
- SFX events per 10 s, per style
- hits per reel
- level per layer relative to VO
- most-used library files / categories (his palette)

Status: PARTLY CALIBRATED — one real project (below). No Premiere XML parsed yet; keep the defaults wherever this column is empty.

### Calibration #1 — AG1 reel (39 s, 9:16, 30 fps, corporate/clean, Saudi VO, no music; Nov 2026)
- **Base palette (12 sounds):** ambience room-tone loop, fast whoosh, smooth swoosh, card pop, UI click, typing burst, marker strike, impact hit, tonal riser, phone vibrate, paper/envelope slide, success chime. Every cue was derived from these (varispeed pitch, HPF/LPF, trim, pan) — no per-cue generation.
- **Levels (clip peaks, ducking, pre-CTA dip, master limiter):** `05_audio_sfx.md` §6, SFX bullet.
- **Sync:** cues anchored on the sound's own smoothed peak (`peak`), or `start` / `end` anchors for risers and beds; logged error per cue in frames (target ±0).
- **Phone translation:** sub hits got a pitched-down pop transient above 200 Hz layered on (`hit(mid=True)`), and "warm punch" = LPF'd hit + mid transient.
- Cue timings came from the motion build itself (known keyframe frames per scene) plus measured VO windows — far cheaper and more exact than optical-flow detection when the edit was built by us in AE.
- User taste (other reel, CLC): calm soothing beds, no beat-synced shake, few long silences.

## Sources behind these rules
ElevenLabs official sound-effects docs, API reference and help-center pricing (Nov 2026); web research on ad/trailer/reel sound design (timing offsets, restraint, silence before hits, phone-speaker translation, -14 LUFS / -1 dBTP), the tutorial "How To Sound Design ANYTHING." (Skymography), and Gemini summaries Omar provided of two more tutorials (Gavin Herman's SHAPE method; a 4-step ambience -> dialogue -> SFX -> music framework). Defaults are starting points; Omar's calibration and feedback override them.
