# Cue placement, band slots, phone translation (reel-sound-design)

> Moved out of `SKILL.md` §4 and §6 on 2026-11-11 (plan phase 2). Text unchanged.

## Placement rules (SKILL.md §4)
Motion (whooshes):
- Transition whoosh: starts 2-4 frames before the cut, peak on the cut, ends ~2 frames after.
- Camera-move whoosh: starts 10-20 ms before the move begins; length = length of the move (fast 0.2-0.4 s, normal 0.5-1.0 s, slow 1-2 s).
- Character follows the motion: speed, mass, direction, distance, where it stops. Bright plasticky whoosh on a dark/moody shot = wrong.
- Transition SFX are OPTIONAL, not a rule: use on visible transitions (zoom, whip, slide, push); skip on plain hard cuts in calm styles; skip if it lands on an important VO word; never 3 transition SFX in a row without a breath.
- Never the same whoosh twice in a row; rotate 3-4 variants or pitch ±1-2 semitones.
- Pan follows on-screen direction; keep anything below 150 Hz centered.

Texture (clicks/pops/UI):
- 30-200 ms, mostly high-frequency, quieter than motion.
- Only on the important text/graphic, not every element. Emphasis words roughly every 5-8 s.
- Keep the SONIC RHYTHM even: if one cut in a regular sequence is 1 frame off, shift its click 1 frame so the pattern stays regular.
- Non-literal sounds are welcome (clock gears, bike freewheel, camera shutter, typewriter on text).
- Ascending clicks (pitch -4, -3, -2, -1, 0 st) = a riser made of clicks before a climax.

Emotional (risers/hits):
- A riser must END exactly on its hit/reveal. No music: 1.5-4 s. With music: end on the downbeat of the next section.
- Hits: only on reveal/logo/CTA/key claim; count per profile table.
- 0.3-0.5 s of relative silence (drop ambience/other SFX) before the biggest hit.
- Emphasis hits may land 1-3 frames AFTER the visual; anticipation sounds land slightly before.
- Hit construction: mid transient (snap/metal/click) + body + sub. The sub alone vanishes on phones.
- Custom riser: reverse an impact and cut it at the last frame before the cut.
- Bridge empty gaps between big moments with soft whooshes, swells or a tonal bed so energy keeps moving.

Ambience:
- Bed under the whole reel or per section, low and filtered (HPF ~100 Hz, LPF 8-10 kHz) so it never fights VO.
- Fast montage: chop one ambience into per-shot pieces, pitch each ±1 st so every shot feels different.
- Micro vignettes: a few frames of each shot's own sound (water, traffic, crowd) build a sense of place.
- Let tails ring across the next shots to glue them.

Hook (first 1.5 s):
- An audio event that reinforces the first visual/headline: sharp whoosh, snap, hit, or a short deliberate silence then a hit.
- Plan an audio-energy change every 3-5 s (cue, pause, swell) as a pattern interrupt.

Sound-off rule: SFX never carry information. If the message only exists in sound, flag it to Omar.

## Band slots and phone translation (SKILL.md §6)
Band slots (EQ per layer) so layers don't collide:
- Ambience: HPF 100 Hz, LPF 8-10 kHz.
- Whooshes: HPF ~120 Hz, energy 300 Hz-8 kHz.
- Clicks/UI: HPF ~800 Hz-1 kHz.
- Hits: sub 40-80 Hz mono + transient/body 200 Hz-3 kHz.
- Keep everything below 150 Hz mono.

Phone translation (most viewers hear reels on phone speakers, which roll off the low end): every low sound needs a mid-range component (200 Hz-4 kHz) to be audible; never rely on sub alone; a small 200-400 Hz presence keeps weight audible.

## Second pass when music arrives (SKILL.md §9)
- Detect beats/downbeats and drops (librosa).
- Remove or move hits that double a music hit; align riser ends to downbeats.
- Carve EQ where music low end clashes with sub drops (cut one of them).
- Rebalance levels: dense music -> SFX up slightly; sparse music -> SFX down.
- Expect to change ~20% of cues, not to redo the work.
