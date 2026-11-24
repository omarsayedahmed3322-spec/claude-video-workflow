---
name: reel-talking-head
description: Edit a reel built on a real person talking to the camera (seated talking head, presenter explaining a product, doctor, interview, podcast clip) from raw footage to delivery - dead-air cut plan, framing and slow zooms, B-roll over the cuts, rare transitions, captions, speech cleanup and mix, QC. Use when Omar says «متكلم», «توكينج هيد», «دكتور بيتكلم», «مقدم», «بودكاست», «واحد بيتكلم للكاميرا», «انترفيو», talking head, presenter.
---

# ريل المتكلم (Talking head)

> Moved here on 2026-11-12 (plan phase 5-أ) from `01_workflow.md` §D (Talking presenter, Seated talking head) + §E (series),
> `02_motion_laws.md` §3–4 and `05_audio_sfx.md` §1 (cut inside a sentence) + §5b. Source reels: CLA R1 (seated doctor,
> AG2), CLB R2 (presenter in a shop, AG2), CLH R1–R5 (phone clips), CLD R5 (phone takes).
> Scripts (copied from CLA R1, the v19 build; the originals stay in `AG2\CLA\reel-01\scripts\`):
> `references/plan_talking.py` (cut plan → EDL), `references/mix_talking.py` (speech + music + SFX), `references/build_talking.jsx`
> (AE build). Each has a SETTINGS block at the top with CLA's values; copy them to the reel's `scripts\` and fill it.

## أول حاجة: أنهي نوع وأنهي عميل
- **The client's own reference wins.** If they sent a talking reel to copy, follow how it cuts (CLB R2 did); the defaults below are for when there is none.
- **Two kinds, two defaults** (both written this way in the kit before the move):
  - **Seated talking head, no client reference** (Omar, CLA R1): no punch-ins at all, slow zooms only (§الكاميرا).
  - **Presenter who points at / demonstrates something** (Omar, CLB R2): small punch-ins only where there's a reason.
- **Client taste stays under the client's name** — never make it the default for another client:
  - CLA: the approved v19 shape is in `Kit_04_Clients\CLA - CLA.md` (wide 100 % all along, one zoom-through + one flash, brand sounds).
  - CLB: hide speech cuts under B-roll; no B-roll → cut inside a 2× punch-in on the hand (§القص جوه الكلام). Caption click ≤ −15 dB (`CLB` file).
  - CLH: WhatsApp phone clips, one clip = one reel; grade, background and logo rules in `CLH - CLH.md`.
- Read the client file and its «قايمة فحص قبل التسليم» before the plan; the checklist is reviewed before every send.

## طرق تانية للريل ده (واحدة من كذا طريقة، مش الوحيدة)
- **The defaults in this file are one way, not the only way** (Omar, CLA R3, 2026-11-13). A client with an established page
  style gets that style; this skill still gives the base (speech first, cut plan, b-roll edges, levels, QC).
- **Page-style captions + numbered items over stock b-roll** (CLA Academy: mint box with words rising, big white hooks,
- Seated doctor, wide 100 %, Arabic captions (CLA & CLA R1) and presenter punch-ins (CLB R2): the sections below.

## الخطوات بالترتيب
1. **Probe the footage** (rotation flag, audio `codec_name`): `01` §D. Camera vertical footage often reads 16:9 (`rotation=90`).
2. **Speech first, before any cut** `[ذوق عمر]`: Omar cleans every recorded voice in Adobe Podcast «Enhance Speech» (§الصوت).
3. **Word times:** `tools/hf_captions/whisper_gpu.py` (GPU, `large-v3-turbo`, not `small`; `03`, `00_quick_rules`); with a script `stable-ts --align`, and score the methods each time (`03` captions step 1, Omar 2026-11-14). A phrase starts at the end of the silence before it, never at whisper's first word (`05` §1).
4. **Cut plan = one EDL** (`plan_talking.py`): the speaker layers, B-roll, captions, framing and the mix all read the same file.
5. **Build** in AE with `build_talking.jsx` through `tools\ae_run.ps1`; the mix comes from `mix_talking.py` (the build imports it as one WAV).
6. **QC:** `tools\qc_reel.py <mp4> --type talking` (or `ae_render.ps1 -Type talking`). Use its `.qc_sheet.png` (one frame per shot + safe zone) instead of a separate contact sheet. Then the client checklist as a table, every «نعم» with a second or frame (`01` §E).
7. **Premiere timeline with the delivery** `[تقني]`: `tools\edl_to_premiere_xml.py <edl.json> --root <reel> --jsx build_talking.jsx --vo <speech.wav> --music <file> --music-cut/--music-loop/--music-db (from mix_talking SETTINGS) --mix <mix.wav> --out <reel>_timeline.xml`. V1 speaker, V2 B-roll, A1 speech, A2 music, A3 full mix (off). Zooms, speed, transitions, captions and the outro are markers. Omar: File › Import (plan phase 6, 2026-11-12).
8. **Omar's cut back** `[تقني]`: he cuts V1/V2 only (notes as markers), then File › Export › Final Cut Pro XML. `tools\xml_to_edl.py <his.xml> --edl <old edl.json> --root <reel> --jsx build_talking.jsx --out <new edl.json>` → rebuild with `mix_talking.py` and `build_talking.jsx`. Captions, zooms, transitions and the outro follow the words; his markers are printed and saved as `notes`. Constant speed on a V2 clip (Speed/Duration) → broll `speed` (%) → AE stretch `10000/speed`; speed on V1 is refused (speech off the lips).

## قص السكوت (Seated, Omar on CLA R1)
- **Cut all dead air:** `silencedetect=noise=-38dB:d=0.28`; keep 0.06 s after the last word and 0.10 s before the next.
- **The clip's start and end too:** open 0.10 s before his first word (whisper word time), not at the end of the first silence — a breath before the word left the camera operator's finger in frame (Omar: «تتقص… خلي المشهد يبدا مع اول كلمه»).
- One EDL file drives the speaker layers, B-roll, captions and the mix (`plan_talking.py`, was `plan_CLA_R1.py`).

## القص جوه الكلام
- **Client shortens a line** (CLA R1 v10): if the client sends their own re-cut, run whisper `--word_timestamps` on both theirs and our source and match their join. Whisper's word edges inside fluent speech are off by 0.2–0.4 s, so find the join on a 10 ms RMS profile: end on the last syllable's tail, resume in the breath/silence before the next word (a join mid-voicing still works with the mix's 8 ms fades).
- **Hide the picture jump with a plain classic cut to B-roll exactly on the join** — nothing else (CLA v19: «ليه لازم تبهرني؟ اعمل كات عادي خالص»). Rejected there, in order: a zoom transition (too early in the reel), a frozen last frame until the next word (read as the picture stopping), a morph-cut dissolve.
- **CLB (presenter, follows CLB's own reference `DY5cGrSPw0S`):** hide the cuts under B-roll cutaways while the voice carries on (L-cut), not under digital punch-ins on the face: speaker on camera 1–2 s, then 1 s gliding B-roll, never a jump cut on the face.
  - Keep the speaker on screen while he points at the thing he's explaining or smooths the fabric (agy on CLB R2 v1: cutaways during the demonstration «interrupt»).
  - No B-roll available or wanted → make the cut happen INSIDE a close punch-in (≈2×) on his hand/the garment, head out of frame, then ease back out. Cutting from a punch-in back to the same medium shot shows the head and torso snap.

- **Lip sync: take each speaker shot's source time from the frame-rounded cut times** `[تقني]` (CLA R4, v1–v6 all wrong): the build rounded cuts to frames but `srcAt()` used the raw joins, so a shot starting on a rounded cut (22.24 vs 22.25) read the previous segment: 0.4 s late, or the wrong take. Print every speaker shot's source in the build log and check it against the speech timing.
- **The last shot under the blurred outro never freezes:** slow it (from the 50p) or start it earlier so it plays to the end `[ذوق عمر]` (CLA R4 v5).

## الكاميرا والكادر
- **A punch-in (static framing change on the same take) only where a new sentence starts after a real pause, on its first word; otherwise none** `[ذوق عمر]` (CLA R3 v3: cuts in 0.14 / 0.2 s gaps inside running speech read as «PUNCH IN في نص الكلمة»). The frame can still change with a transition back from b-roll.
- **Slow zoom per shot, never two in a row** (Omar, CLA R1 v15): a slow digital zoom (≈5–6 %, eased) starts on the shot's first visible frame and ends on its last — a talking-head stretch between two cutaways counts as one shot. The next shot is static; alternate along the whole reel (B-roll included). Shots under 1.5 s stay static.
- **Approved speed ≈ 1.9 %/s** (106→100 over 3.2 s); a longer shot keeps that speed and simply travels further (CLA's 6.8 s doctor stretch: 100→112.8, the shots either side static). Omar liked the very slow subtle zoom and asked for a slow zoom-out (106→100) too, not right after a zoom.
- **Seated talking head (CLA R1 v15–v16): no punch-ins at all** — the 1.18/1.20 static punch framings were «مش حلو»; keep the full wide frame and let only the slow zooms move it. (Before v16 the framing changed per topic: slow push 100→105 / static punch 118–120 / static wide.)
- **A topic that starts under B-roll takes its framing from the B-roll's first frame:** setting it when the B-roll leaves showed the old framing for the 4 fade-out frames and then a snap (Omar: «قطع مفاجئ بعد الترانزيشن»).
- **Presenter punch-ins** (Omar on CLB R2: «زي ما تكون بتصور فرح»): 1.15–1.18× at most, pure ease-out (leave fast, settle slowly), only where there's a reason (he points at something), never on two segments in a row. Other cuts: a STATIC framing change 1.0 ↔ 1.15 (reads as a second, closer camera). No digital zoom on top of a real camera move or an AI move. The 2× "tailor's eye" pumps of v1–v2 were rejected.

## البي رول
- **Its edges sit exactly on the speaker's cuts** (Omar, CLA R1 v10: «فريم او فريمين… وتزغلل العين»). An edge 1–5 frames off a dead-air cut shows the old framing, then it jumps. Snap any B-roll edge within 0.4 s of a speaker cut onto the cut, and run its exit fade after the cut so it reveals the new framing (`plan_talking.py` does both).
- **Static shot into a fast handheld one is harsh** (Omar, CLA R1: «بيتنقل من كادر ثابت لفيديو متحرك بسرعة كبيرة»). Slow it to 50 % from the 50p original (`setpts=2*PTS`, `-r 25`: real frames, no blending) and stabilize it (`vidstabdetect` + `vidstabtransform smoothing=40 optzoom=1`, then the same grade as the other prep clips). On CLA C9927 the frame-to-frame motion fell from 4.4 to 2.1. Land the transition on the next spoken word, not on the audio join before it.
- **A big title over a b-roll clip never sits on a face** `[ذوق عمر]` (CLA R3): crop the clip from the bottom (scale + anchor at y 1920) so the face leaves the title zone, and add a soft dark band at the top (black ≈ 38 %, feather 420) if the title sits on white.
- Skip frames with crew, rigs or script notes in hand, and web banners with baked-in buttons («ORDER NOW») (`00_quick_rules`, CLA R1).
- **Stock B-roll prep:** `setsar=1` in the ffmpeg prep, and a 9:16 crop of a 3840-wide clip keeps only 1215 px (~32 %), so pick stock whose subject sits in the middle `[تقني]` (CLA R4).

## إضاءة المتكلم لوحده
- **The client asks to brighten the speaker → build the control, Omar sets the value** `[عميل + ذوق عمر]` (CLA R4: «عايز اتحكم انا»): adjustment layers right above the speaker layers and under all B-roll (`DOC_LIGHT` for every shot, `DOC_FACE_LIGHT` with a feathered ellipse mask per framing), Levels gamma 1.35, strength = layer Opacity ← a `CTRL` slider, left at 0. Same label colour on the speaker and light layers.
- **When the element can't sit at the bottom of the stack** (motion graphics): precompose it and put the adjustment inside, or a track matte on the adjustment, or one effect per layer linked to one slider.

## عمر بيلوّن المتكلم بنفسه (رايح جاي مع Premiere)
- **Send two raw files, not one plate** `[ذوق عمر]` (CLA R6, 19 Nov 2026): «الجزء الراو اللي من الماتيريال المتصور مش من البيرولز», and the used b-roll as a second file. Speaker = only the used source ranges, camera originals, full frame (no crop / zoom), native fps (50p, so slow outros keep real frames), ProRes 422 10-bit, camera sound; b-roll = only the used ranges at the clip's own fps. Give the range table with it. Scripts: `reel-06\scripts\make_docraw_CLA_R6.py`, `make_brollraw_CLA_R6.py`.
- **Back in:** check his file frame for frame against the raw (cut-frame diff spikes must match), then put each graded frame back on the speaker timebase (`place_graded_CLA_R6.py`; hold the nearest graded frame 2 f at each run edge so a rounded `srcAt` never lands on black). His grade is the look: the build's FINAL_GRADE stays off the speaker shots (opacity expression on the doctor intervals) and the AI shots are matched to his levels.

## الترانزيشن
- **Transitions are rare; most edits are plain cuts** (Omar, CLA R1 v14: «مش لازم كل نقلة ترانزيشن»). One signature transition **once or twice per reel**, on the moments that matter (the return after a product run) — **never in the first seconds**: a transition one second in «بنوجع العين» (CLA v16).
- Approved zoom-through = adjustment layer, scale 100→145 + blur 0→45 into the cut, 72→100 + blur 45→0 out of it, 6+10 frames (`trans("zoom")` in `build_talking.jsx`).
- A light sweep **once at most**, on the brand moment. A whip pan on every event shot was too much. Light/flare layers must be **much larger than the frame** (3400 px solid, feather 800): a frame-size solid moving across showed its hard edges.

## الكابشن
- At 1080 wide: **40 px for speech, 54 for big intro lines** (46/62 were «مكبره اوي»), with a quick blur pop in and out (24→0 in 5 frames, 0→24 in 4). Font and colour: the client file.
- A line leaves 0.12 s after its last word (`05` §1).
- **Key phrases as big type (small white line + big italic accent word, rising with blur on the spoken word):** the numbers are in `02_motion_laws.md` §4b `[ذوق عمر]` (CLA R8, 2026-11-23). Use it on class `A` / `A+` talking heads; the caption hides while it is up.
- **Translated captions (speech in Arabic, text in English) are timed on the Arabic words they translate** `[ذوق عمر]` (CLA R3 v2: «مش متزامنة»): each line 1 f before its words' onset (10 ms RMS). Word order differs → one line for the sentence, or split in the Arabic order with the client's same words. **No caption tap sound by default** (§الصوت).

## الصوت
- **Levels: `05` §6, row «متكلم قاعد»** (phrase peaks −10…−6 dBFS, music ≈ 20 dB under, no LUFS target for the whole reel — CLA measured ≈ −19).
- **Adobe Podcast «Enhance Speech» before anything else** `[ذوق عمر]` (CLB R2; Omar, 11 Nov 2026). Join all the takes in one 48k WAV (note each offset) so it's one upload, then split it back.
  - The Adobe connector's `media_enhance_speech` doesn't work from Claude Code: it starts the job but the result only comes through a widget that never reaches this app, and nothing is saved to Creative Cloud.
  - **The built-in browser can't upload a local file** `[تقني]` (CLA R6): it has no `file_upload`, and a `fetch` from the page to a localhost server is blocked (CSP / private network). If Claude in Chrome isn't connected, open the page in the built-in browser for Omar's login, give him the WAV's full path, and take the `-esv2-` file from `~\Downloads` (check length + cross-correlation lag 0).
  - Use `podcast.adobe.com/en/enhance` in Claude in Chrome instead (Omar's Adobe login, he picks the profile): `file_upload` on the «Choose files» input, ~1 min for 38 s, then «Download» saves `<name>-esv2-100p-bg-5p-music-m.wav` to `~\Downloads` (same length as the input, so the split offsets stay exact — check with a cross-correlation).
  - **Omar can enhance it himself to save tokens (CLA R1):** send him the clip's audio **full length, before any cut** (`ffmpeg -vn -ac 1 -ar 48000 pcm_s16le`), he drops `<name>-esv2-...wav` into `assets\audio\`. Cut the dead air afterwards from the same source times, so the sync can't drift.
- **Voice level** (Omar, CLA R1; 11 Nov 2026: any recorded voice of a person, all reels): light 2-stage compression, median 400 ms peak at −8.5, limiter at −6 (`mix_talking.py`). Say the reel measures ≈ −19 LUFS rather than pushing the voice past −6. Music ≈ 20 dB under the voice (he said it was louder than the man at ≈ −15 relative).
- **Raw phone clips cut into one reel: level each clip before joining** (`loudnorm=I=-20` per segment, 2-frame audio fades at every cut). CLD R5: talking-head takes measured −21…−24 LUFS against −18 for the close-up VO takes, so the voice dropped at every switch and agy heard «two different girls». After per-clip leveling they sat within 2 LU.
- **Caption taps: none by default.** Both CLA tries read wrong: `soft-click` (≈560 Hz) twice as «مكتوم… كأن فيه عيب تصوير» (v4 and v17, also `soft-switch` on a transition), and the version that used `select` was rejected as a whole. Ask before adding one. Add SFX after any loudness gain so their peaks stay where you set them. `glass-tap-*.wav` and `click-*.wav` in Flex UI don't decode in ffmpeg.
- **Transition SFX: only on real transitions, and varied** (Omar, CLA R1: «whooshes كتير… متعلقش ع صوت واحد», then «مش لازم كل نقلة ترانزيشن»). Plain cuts carry no transition sound. Zoom-through → silent (its soft switch read as a camera fault), light sweep → steel sparkle `jingle-steel-0N` starting with the light, whip → whoosh peaking on the cut (`tsound()` in `mix_talking.py`).
- **Brand moments (Omar asked for them, CLA R1 v16):** a signature sound the first time the product/brand name is said, and one other sound repeated on every product name in a list. Peak on the word start (from the silence ends, not whisper). CLA: `ES_Bass, Sharp Detail Riser` + `hit.mp3` sub under it on «CLA»; the first 1.4 s of `ES_Select, Soft Round Pluck, Short, Reverb` on Clarity / Performance / Beauty (SETTINGS of `mix_talking.py`).

## سلسلة ريلز من نفس التصوير
- **CLH R2+:** open the finished previous reel's `.aep`, Save As the new reel, swap the footage item (`replace`), set the comp duration, and rebuild only the captions and graphics. That copies the approved grade, light, watermark cover and logo card exactly, which is what «بنفس الطريقة بالظبط» means.

## اللي اترفض (متعملوش)
- Punch-in framings 1.18/1.20 on a seated speaker (CLA v15–v16); 2× "tailor's eye" pumps (CLB R2 v1–v2).
- A transition in the first seconds; a whip on every event shot; a frame-size light layer.
- At a sentence join: zoom transition, frozen frame, morph-cut dissolve (CLA v17–v19).
- Caption taps (`soft-click`, `select`); a whoosh on every cut; `soft-switch` on the zoom-through.
- Cutting from a punch-in straight back to the same medium shot (CLB); cutaways during a demonstration (CLB R2 v1).

## المراجع
- `references/plan_talking.py` — the EDL: silences, framing per topic, B-roll list with snapped edges, transitions, captions, slow-zoom shots. Tested 2026-11-12: with CLA's SETTINGS it rewrites `edl_CLA_R1.json` byte for byte.
- `references/mix_talking.py` — speech chain, music loop and envelope, transition sounds, brand moments. Tested 2026-11-12: with CLA's SETTINGS the WAV equals `CLA_R1_mix_v17.wav` sample for sample.
- `tools\edl_to_premiere_xml.py` (Kit_01) — the same EDL as an FCP7 XML for Premiere (step 7).
- `tools\xml_to_edl.py` (Kit_01) — Omar's Premiere cut back into an EDL (step 8).
- `references/build_talking.jsx` — the AE build (speaker layers with the zoom expression, B-roll, `trans()`, captions, outro, grain, check PNGs). Not run in AE after the copy (only the SETTINGS block and the lines that read it changed).
