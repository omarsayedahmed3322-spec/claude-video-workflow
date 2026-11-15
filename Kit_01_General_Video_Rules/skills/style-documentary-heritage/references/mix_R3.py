# mix_R3.py — AG1 R3 audio: VO + generated music loop + wind + clip ambience + SFX -> R3_audio/mix.wav (-14 LUFS, -1 dBTP)
# Run: python -I mix_R3.py   (needs ffmpeg on PATH)
import subprocess, os

REEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(REEL, "assets - AG1 R3")
SFX = os.path.join(A, "sfx")
LIB = os.path.join(os.environ.get("CLAUDE_WORKFLOW") or r"D:\AI\Claude-Workflow", "SFX_Library")   # <Claude-Workflow>: env CLAUDE_WORKFLOW (install.ps1); the default is where AG1 R3 ran (this script runs from the reel folder)
FT = os.path.join(REEL, "footage - AG1 R3")
OUT = os.path.join(REEL, "R3_audio")
os.makedirs(OUT, exist_ok=True)
MIX_NAME = os.environ.get("R3_MIX", "mix.wav")

# opening sung welcome pushes everything +SH; the ending is tightened (must match build_AG1_R3.jsx)
SH, ES, EC = 2.2, 0.6, 1.0
DUR, VO_AT, CARD = 25.0 + SH - EC, 0.6 + SH, 22.95 + SH - ES   # CARD = logo lands
VO_END = VO_AT + 17.79

# (file, start time in timeline, gain dB, extra filters, loop?)
inputs, chains = [], []
def add(path, at, gain, extra="", loop=False, trim=None):
    i = len(inputs)
    inputs.append((path, loop))
    f = f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo"
    if trim:
        f += f",atrim={trim[0]}:{trim[1]},asetpts=PTS-STARTPTS"
    if extra:
        f += "," + extra
    f += f",volume={gain}dB,adelay={int(at*1000)}|{int(at*1000)},apad=whole_dur={DUR}[s{i}]"
    chains.append(f)

# VO take 2 (Omar's pick): -24.7 LUFS measured -> about -18
add(os.path.join(A, "vo", "vo_take2.mp3"), VO_AT, 6.7)
# music: low under the VO, up after it, hard stop at the card
# music: low under the VO, up after it, swells to its loudest under the logo, fades at the very end
# with no opening vocal the music carries the intro, then dips under the VO
INTRO = 0.14 if os.environ.get("R3_VOCAL", "") != "none" else 0.40
music_vol = (f"volume='if(lt(t,{VO_AT - 0.3}),{INTRO},if(lt(t,{VO_END + 0.2}),0.14,if(lt(t,{CARD - 0.4}),0.5,"
             f"if(lt(t,{CARD + 0.3}),0.5+(t-{CARD - 0.4})/0.7*0.4,0.9))))':eval=frame,"
             f"afade=t=in:st=0:d=1.2,afade=t=out:st={DUR - 0.9}:d=0.9")
add(os.path.join(SFX, "music_loop_01.mp3"), 0, 0, music_vol + f",atrim=0:{DUR}", loop=True)
# desert wind bed until the card
add(os.path.join(SFX, "wind_loop_01.mp3"), 0, -20, f"atrim=0:{DUR},afade=t=out:st={DUR-0.9}:d=0.9", loop=True)
# clip ambience (Veo audio), per shot: (clip, timeline in, timeline out, source in, gain dB)
AMB = [("B2", 1.25, 2.30, 0.40, 2), ("B1r", 2.30, 3.86, 0.60, 2),
       ("A1", 3.86, 5.62, 3.40, -16), ("A2", 5.62, 7.00, 2.60, -14), ("C1", 7.00, 8.38, 0.40, 8),
       ("D1", 8.38, 9.40, 2.00, 4), ("D2", 9.40, 10.62, 0.30, -6), ("E1", 10.62, 11.90, 0.30, -6),
       ("F1n", 11.90, 13.72, 2.30, 2), ("E2", 13.72, 15.34, 3.40, -10)]
AMB = [(c, t0 + SH, t1 + SH, src, g) for c, t0, t1, src, g in AMB]
AMB.insert(0, ("H1", 0.00, 1.25 + SH, 1.60, -2))   # door ambience, kept under the song
for c, t0, t1, src, g in AMB:
    d = t1 - t0
    add(os.path.join(FT, c + "_a.mp4"), t0, g, f"afade=t=in:st=0:d=0.04,afade=t=out:st={d-0.08:.2f}:d=0.08", trim=(src, src + d))
# SFX
# the elder's sung welcome on the opening shot: one melodic line, a touch of outdoor echo, out before the VO
# R3_VOCAL picks the opening vocal: a file in sfx\ (default the sung "ya hala"), or "none" for no vocal
VOCAL = os.environ.get("R3_VOCAL", "sung_welcome_sfx_01.mp3")
if VOCAL != "none":
    add(os.path.join(SFX, VOCAL), 0.20, -3, "aecho=0.8:0.5:70|140:0.22|0.12,afade=t=out:st=2.55:d=0.4")
add(os.path.join(SFX, "falcon_flap_screech_01.mp3"), 3.80 + SH, -14)   # on the falconer reveal
for t in (3.86, 7.00, 10.62, 13.72, 18.20):
    add(os.path.join(SFX, "daf_hit_01.mp3"), t + SH - 0.02, 12)
add(os.path.join(SFX, "film_projector_01.mp3"), 16.50 + SH, -6, "afade=t=in:st=0:d=0.5,atrim=0:1.7,afade=t=out:st=1.45:d=0.25")
# logo reveal: library swoosh into the card, daf hit as it lands
add(os.path.join(LIB, "base_swoosh_smooth.wav"), CARD - 0.8, -4)
add(os.path.join(SFX, "daf_hit_01.mp3"), CARD - 0.02, 14)

cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
for p, loop in inputs:
    if loop:
        cmd += ["-stream_loop", "-1"]
    cmd += ["-i", p]
n = len(inputs)
fc = ";".join(chains) + ";" + "".join(f"[s{i}]" for i in range(n)) + \
     f"amix=inputs={n}:normalize=0:duration=longest,atrim=0:{DUR}," \
     "highpass=f=30,loudnorm=I=-14:TP=-1:LRA=11[out]"
cmd += ["-filter_complex", fc, "-map", "[out]", "-ar", "48000", "-c:a", "pcm_s24le", os.path.join(OUT, MIX_NAME)]
subprocess.run(cmd, check=True)
print("mix written: R3_audio/" + MIX_NAME)
