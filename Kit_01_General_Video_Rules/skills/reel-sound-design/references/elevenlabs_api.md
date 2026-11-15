# ElevenLabs: free-tier facts, API, cost, prompting (reel-sound-design)

> Moved out of `SKILL.md` on 2026-11-11 (plan phase 2) so the skill stays under 150 lines. Text unchanged.

### MCP / free-tier facts (tested on real reels, Nov 2026 — these override the API facts below)
- `text_to_sound_effects` via MCP: max **≈5 s** per sound; `prompt_influence` is **not exposed** (API default applies); output came as `mp3_44100_128` on free tier. `loop: true` works for beds.
- Ambience longer than 5 s: generate a 5 s seamless loop and tile it locally (tile the raw loop, not a longer render — a render can have its seam mid-file), or ffmpeg `-stream_loop`.
- `compose_music` is **blocked** on free tier → music bed = a 4–5 s tonal loop from `text_to_sound_effects`, looped to length.
- TTS: library/professional voices (e.g. "Mansour - Saudi") return 402; premade voices (Laura, Roger, Sarah, Lily…) and `eleven_v3` work. No Gulf dialect in premade voices → MSA-ish; add tashkeel to mispronounced words.
- `speech_to_text` only reads files under `C:\Users\PC\Desktop`.
- Check every take's peak: one UI-click take came back at −69 dBFS (silent) and had to be regenerated. Trim leading silence (a pop had 23 ms, a riser 333 ms).
- Credit estimates in `generations.json` are per call; show the planned call count before generating.

### ElevenLabs sound effects - best practices

API facts (verify against current docs if a call fails):
- Endpoint `POST https://api.elevenlabs.io/v1/sound-generation` (Python SDK: `client.text_to_sound_effects.convert`), model `eleven_text_to_sound_v2`.
- Params: `text`, `duration_seconds` (max 30; omit = model decides), `prompt_influence` 0-1 (default 0.3; high = literal and less varied, low = creative variations), `loop` (v2 only, for seamless beds), `output_format` (query param).
- Output: request `pcm_48000` (wrap into WAV 48 kHz yourself). If the plan refuses it, fall back to `mp3_44100_192`, then `mp3_44100_128`. Looping effects come as MP3 only.
- One API call = one sound (the website makes 4 per click). Credits are charged per generation request, not per download.

Cost rule (API): auto duration = 100 credits per call; fixed duration = 20 credits per second. So:
- Sounds under 5 s (clicks, whooshes, hits, risers): ALWAYS set `duration_seconds`. It is cheaper and avoids the known auto-duration problem (a 1 s sound followed by a long silent tail, or the same sound repeated to fill time).
- Ambience 5 s or longer: auto is cheaper; set duration only when length matters, or use `loop=true`.
- Before generating, show Omar the planned number of calls and estimated credits.

Prompting rules:
1. One sound per prompt. ElevenLabs itself recommends generating individual effects and combining them in an editor rather than describing a sequence. Never prompt a whole transition + hit + riser in one call.
2. Use the audio terms the model understands: `one-shot`, `loop`, `stem`, `ambience`, `impact`, `whoosh`, `braam`, `glitch`, `drone`, `riser`, `foley`, `room tone`.
3. Describe materials and physics, not just objects: what hits what, what moves through what, how fast, how heavy, how far.
4. Add a quality/cleanliness tail: `high-quality, professionally recorded, isolated one-shot, dry, sound effects foley`.
5. Say what you want, not what you don't: ask for `isolated, dry, single sound, ambience only` instead of `no music, no voices` (negative words can pull the unwanted thing in). If music or voices still appear, raise `prompt_influence` and add `isolated stem`.
6. 10-60 words. One or two words gives generic results; long paragraphs don't help.
7. Start generic, then narrow with adjectives (speed, size, material, distance, mood/style).
8. For the music pass, risers/drones can be prompted in the track's key and tempo, e.g. `tonal riser in F minor, 120 BPM, 4 bars`.

Prompt template: `[sound type] + [speed] + [size/weight] + [material/texture] + [distance/space] + [style/use] + [quality tail]`

Settings and examples by use:
| Use | duration_seconds | prompt_influence | Example prompt |
|---|---|---|---|
| UI / text click | 0.5-1.0 | 0.7-0.8 | `short crisp UI click, plastic, very close, isolated one-shot, dry, high-quality` |
| Mechanical tick | 0.5-1.0 | 0.7 | `mechanical camera shutter click, metallic, retro, isolated one-shot, dry` |
| Fast whoosh | 0.6-1.0 | 0.5-0.6 | `fast airy whoosh passing close, light, clean, for a video transition, isolated one-shot` |
| Luxury swoosh | 1.0-2.0 | 0.5 | `soft cinematic swoosh, slow, warm, silky air movement, wide stereo, luxury commercial, isolated` |
| Riser | 2-5 | 0.5 | `tonal riser building tension, airy, rising pitch, ends abruptly at peak, isolated stem` |
| Hit transient | 0.5-1.0 | 0.7 | `sharp metallic impact transient, very short, bright, dry, isolated one-shot` |
| Hit body / sub | 1-3 | 0.6-0.7 | `deep cinematic sub boom impact, short tail, low end, isolated one-shot` |
| Glitch | 0.5-1.5 | 0.6 | `digital glitch stutter, short, crisp, for a video transition, isolated one-shot` |
| Ambience bed | auto or 10-30, `loop` | 0.4-0.5 | `calm modern office room tone, distant soft air conditioning hum, ambience loop` |

Workflow:
- Missing sound? Deconstruct it into layers and generate each component separately (heavy hit = metallic transient + low body + sub), then combine locally.
- Generate 2-3 candidates per BASE sound, keep the best, derive cue variants locally (pitch, speed, reverse, EQ). Never generate one sound per cue.
- If a candidate fails QC twice, change the prompt (materials/physics/adjectives) or `prompt_influence`; don't just re-roll the same prompt.
- Log every call (prompt, params, credits, file, kept/rejected and why) in `sources/generations.json`. Over time this becomes Omar's proven prompt library: reuse prompts that passed.
- ElevenLabs' own website video-to-sound tool works the same way this skill does (sample frames, write a prompt, call the SFX API) but without timing control; use it only for quick ambience ideas.
