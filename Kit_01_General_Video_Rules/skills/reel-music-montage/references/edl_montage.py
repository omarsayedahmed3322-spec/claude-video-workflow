r"""Cut-on-the-beat montage EDL -> graded intermediates + AE build (skill reel-music-montage). Copied on 2026-11-13 from
CLB R1 (AG2/CLB/Reel-01/scripts/edl_CLB_R1_v14.py = CLB_R1_vFinal.mp4, 22.6 s, 2026-11-09, after the client's round).
SETTINGS = the reel: paths, the beat grid (beat_grid.py), the cut (one shot() per shot, in beats), outro, SFX. The logic
under it is the R1 logic unchanged. Shot params: clip key, b0/b1 in beats, src = source second at b0, spd, s0/s1 zoom
(1 = fill), x/y offset in output px, ease (push | crash | land | snap | lin), ri = shot index in rough_map.json (grade params).
Usage: python -I edl_montage.py grade [k...]  -> GR\NN_<clip>.mp4 (per-shot .cube from grade.py, GW x GH, 4 in parallel)
       python -I edl_montage.py sheet         -> SHEET_OUT (one frame per shot)
       python -I edl_montage.py jsx [out.jsx] -> JSX_OUT (the template build_montage.tpl.jsx with the data line filled)"""
import json, os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); import grade as G

# ============================ SETTINGS (CLB R1 v14 values) ============================
REEL = r"D:\Montage-02\Clients\AG2\CLB\Reel-01"
FOOT = r"D:\Montage-02\Clients\AG2\AG2\Dropbox\4-11-2026"
HF = os.path.join(REEL, "assets", "higgsfield")
GR = os.path.join(REEL, "work", "graded_v15"); os.makedirs(GR, exist_ok=True)   # new folder per version (AE locks the old files)
MUSIC = os.path.join(REEL, "assets", "music", "CLB_R1_music_v11_omar.mp3")   # ASCII path for AE
BRAAM = os.path.join(REEL, "assets", "bryansantosbreton-biodynamic-impact-braam-tonal-dark-176441.mp3")
TPL = os.path.join(HERE, "build_montage.tpl.jsx")
JSX_OUT = os.path.join(REEL, "scripts", "build_CLB_R1_v14.jsx")
SHEET_OUT = os.path.join(REEL, "exports", "previews", "framing_sheet_v14.jpg")
# measured: librosa beat grid 0.6457 s (92.9 BPM) checked against isolated kicks (15.679 s = beat 24 from 0.182); break 16-17.5 s
FPS = 25; B = 0.6457; S0 = 0.110                              # song second at reel 0 = reel beat 0
GW, GH = 1620, 2880                                             # graded intermediate size (1.5x headroom over 1080; native 2160x3840 past 1.5x)
def bf(b): return round(b * B * FPS)
S = []
def shot(clip, b0, b1, src, spd=1.0, s0=1.0, s1=1.05, x=0, y=0, ease="push", ri=None, tag=""):
    S.append(dict(clip=clip, f0=bf(b0), f1=bf(b1), src=src, spd=spd, s0=s0, s1=s1, x=x, y=y, ease=ease, ri=ri, tag=tag))
# grade params for clips that are not in the rough cut: measured from 3 frames of the clip itself
def ri_of(clip, times):
    G.SHOTS.append(dict(clip=clip, src=[[clip, t, 0] for t in times])); return len(G.SHOTS) - 1
def src_path(c):
    if c == "HF4": return os.path.join(HF, "HF4_logo_dolly_gen01.mp4")
    if c == "HF5": return os.path.join(HF, "HF5_macro_pin_omar.mp4")
    return os.path.join(FOOT, c + ".MP4")

# ---- THE CUT (CLB R1 v14: a cut on every beat; bursts on half beats at b0-4 and b27-29; HF4 b4-7; HF5 holds the break b23-27)
R407, R419, R437, R411 = ri_of("C0407", [1.5, 2.5, 3.5]), ri_of("C0419", [1.0, 2.0, 3.0]), ri_of("C0437", [0.3, 0.8, 1.3]), ri_of("C0411", [0.8, 1.5, 2.2])
H = 0.5
# 1) b0-4 burst: a cut every half beat, forward crash zooms; first eases in, last (the sign) settles
for i, (c, src, ri) in enumerate([("C0402", 2.0, 25), ("C0406", 3.5, 28), ("C0376", 1.5, 0), ("C0377", 4.0, 2), ("C0394", 2.75, 16),
                                  ("C0419", 1.5, R419), ("C0381", 1.75, 5), ("C0387", 2.5, 12)]):
    shot(c, i * H, (i + 1) * H, src, 2.0 if i < 7 else 1.5, 1.00, 1.30 if i < 7 else 1.25, ease="land" if i == 7 else "crash", ri=ri, tag="burst 1")
# 2) b4-7 the quiet bit: AI macro of the real sign
shot("HF4", 4, 7, 0.4, 1.0, 1.00, 1.04, ease="lin", ri=12, tag="sign macro (AI)")
# 3) b7-23 one shot per beat, cut on the bass hit (C0390 and C0401 get a punch-in on their second beat)
for i, (c, src, ri, kw) in enumerate([("C0395", 3.75, 17, dict(s0=1.25, s1=1.30, x=-130)), ("C0383", 3.0, 7, {}), ("C0408", 1.75, 29, {}),
        ("C0384", 5.0, 8, dict(s0=1.32, s1=1.28, y=-260)), ("C0399", 1.75, 22, dict(s0=1.40, s1=1.42, y=-380)), ("C0413", 4.75, 32, {}),
        ("C0392", 2.25, 15, {}), ("C0407", 2.0, R407, {}), ("C0412", 2.25, 31, {}), ("C0389", 2.25, 13, {}), ("C0437", 0.4, R437, {}),
        ("C0378", 2.75, 3, {})]):
    shot(c, 7 + i, 8 + i, src, 1.2, kw.get("s0", 1.00), kw.get("s1", 1.06), x=kw.get("x", 0), y=kw.get("y", 0), ri=ri, tag="beat")
shot("C0390", 19, 20, 2.5, 1.0, 1.00, 1.03, ri=14, tag="beat"); shot("C0390", 20, 21, 2.5 + B, 1.0, 1.22, 1.25, ri=14, tag="beat punch-in")
shot("C0401", 21, 22, 4.5, 1.0, 1.00, 1.03, ri=24, tag="beat"); shot("C0401", 22, 23, 4.5 + B, 1.0, 1.22, 1.25, ri=24, tag="beat punch-in")
# 4) b23-27 the break: Omar's AI macro holds it
shot("HF5", 23, 27, 0.05, 1.12, 1.00, 1.00, ease="lin", ri=9, tag="macro pin (AI)")
# 5) b27-29 strongest hit: second burst on half beats
for i, (c, src, ri) in enumerate([("C0396", 1.5, 18), ("C0409", 4.75, 30), ("C0397", 5.75, 20), ("C0411", 1.0, R411)]):
    shot(c, 27 + i * H, 27 + (i + 1) * H, src, 1.5, 1.00, 1.20, ease="crash", ri=ri, tag="burst 2")
# 6) b29 one shot, then the filmed L'UOMO sign pulling back; ivory veil + logo (logo rides the sign)
shot("C0400", 29, 30, 1.25, 1.0, 1.40, 1.42, y=-380, ri=23, tag="loafer")
shot("C0386", 30, 35, 4.525, 0.6, 1.03, 1.00, ease="lin", ri=11, tag="outro L'UOMO sign pull-out")
COMP_FRAMES = bf(35)   # +2 beats of logo hold so the music fades out instead of stopping
VEIL_IN = (bf(31), bf(31) + 12)
LOGO_IN = (bf(31) + 6, bf(31) + 16)
LOGO_TRACK = [[593, 699, 0.97], [570, 584, 0.89]]   # logo x, y, scale at LOGO_IN and at the end (measured on the sign)
MUSIC_FADE = (bf(31), COMP_FRAMES)
WF = (os.environ.get("CLAUDE_WORKFLOW") or os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))).replace("\\", "/")
LIB = WF + "/SFX_Library/"   # WF = <Claude-Workflow>: env CLAUDE_WORKFLOW (install.ps1), else the repo this file sits in
WH, SW = LIB + "base_whoosh_fast.wav", LIB + "base_swoosh_smooth.wav"
# (file, frame of the cut, peak offset s, dB): whoosh on every burst cut, swoosh into the outro, braam on the veil
SFX = ([(WH, bf(k * 0.5), 0.116, -14) for k in range(1, 8)] + [(WH, bf(4), 0.116, -9)] + [(WH, bf(27 + k * 0.5), 0.116, -13) for k in range(4)]
       + [(SW, bf(30), 0.279, -12), (BRAAM.replace("\\", "/"), bf(31), 0.30, -9)])
N_BEATS = 34                    # beat markers 0..N_BEATS-1 (every 4th becomes a comp marker)
# =========================================================================================

def gname(k, s): return os.path.join(GR, "%02d_%s.mp4" % (k, s["clip"]))

def render_graded(only=None):
    from concurrent.futures import ThreadPoolExecutor
    todo = [k for k in range(len(S)) if not only or k in only]
    for ri in sorted({S[k]["ri"] for k in todo}):            # measure + write each shot's .cube first
        p, _ = G.params(ri); G.write_cube(os.path.join(G.OUT, "luts", "shot%02d.cube" % ri), p)
    def one(k):
        s = S[k]; dur = (s["f1"] - s["f0"]) / FPS * s["spd"]; a = max(0.0, s["src"] - 0.3)
        cube = os.path.join(G.OUT, "luts", "shot%02d.cube" % s["ri"]).replace("\\", "/").replace(":", "\\:")
        vf = "scale=%d:%d:flags=lanczos,format=rgb24,lut3d=file='%s':interp=tetrahedral,format=yuv420p" % (GW, GH, cube)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", "%.3f" % a, "-t", "%.3f" % (dur + 0.6), "-i", src_path(s["clip"]),
                        "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "12", "-threads", "4",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", gname(k, s)], check=True)
        print("graded", k, s["clip"], s["tag"], flush=True)
    with ThreadPoolExecutor(4) as ex: list(ex.map(one, todo))

def sheet():
    from PIL import Image, ImageDraw
    import numpy as np
    W, H = 150, 267; o = Image.new("RGB", (len(S) * W, H)); dr = ImageDraw.Draw(o)
    for k, s in enumerate(S):
        g0 = max(0.0, s["src"] - 0.3); mid = (s["f1"] - s["f0"]) / 2 / FPS * s["spd"]
        raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", "%.2f" % (s["src"] - g0 + mid), "-i", gname(k, s), "-frames:v", "1",
                              "-vf", "scale=%d:%d" % (W, H), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        if len(raw) == W * H * 3: o.paste(Image.fromarray(np.frombuffer(raw, np.uint8).reshape(H, W, 3)), (k * W, 0))
        dr.rectangle([k * W, 0, k * W + 60, 12], fill=(0, 0, 0)); dr.text((k * W + 2, 0), "%02d %s" % (k, s["clip"]), fill=(255, 255, 0))
    o.save(SHEET_OUT, quality=82); print(o.size)

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "grade": render_graded([int(a) for a in sys.argv[2:]] or None)
    elif cmd == "sheet": sheet()
    else:
        if len(sys.argv) > 2: JSX_OUT = sys.argv[2]
        for k, s in enumerate(S):
            s["file"] = gname(k, s).replace("\\", "/"); s["src_g"] = s["src"] - max(0.0, s["src"] - 0.3)
        data = dict(logo_track=LOGO_TRACK, fps=FPS, comp_frames=COMP_FRAMES, shots=S, veil=VEIL_IN, logo=LOGO_IN, music=MUSIC.replace("\\", "/"),
                    music_start=-S0, music_fade=MUSIC_FADE, sfx=[dict(f=f_, frame=fr, peak=pk, db=db) for f_, fr, pk, db in SFX],
                    beats=[bf(b) for b in range(0, N_BEATS)], reel=REEL.replace("\\", "/"))
        tpl = open(TPL, encoding="utf-8").read()
        tpl = tpl.replace("<Claude-Workflow>", os.path.normpath(WF))   # include lines get this PC's root
        open(JSX_OUT, "w", encoding="utf-8").write(tpl.replace("/*__DATA__*/", "var D = " + json.dumps(data) + ";"))
        print("jsx ok", len(S), "shots, comp frames", COMP_FRAMES, "music starts at song %.3f s" % S0)
