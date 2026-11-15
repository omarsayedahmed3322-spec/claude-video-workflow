// build_AG1_R3.jsx — AG1 reel 3: Saudi heritage film, 9:16, 25fps, 24s.
// Idempotent: deletes 00_Master / 01_Picture and rebuilds them. CTRL values survive a rebuild.
// claude-include: <Claude-Workflow>\Kit_01_General_Video_Rules\tools\ae_helpers.jsx
// claude-include: <Claude-Workflow>\Kit_01_General_Video_Rules\tools\ctrl_rig.jsx

var FPS = 25, W = 1080, H = 1920, DUR = 25.0;
var JOBDIR = new Folder(String(CLAUDE_JOB.dir));
var REEL = JOBDIR.parent;                       // ...\ريل 3
var FOOT = REEL.fsName + "\\footage - AG1 R3\\";
var ASSET = REEL.fsName + "\\assets - AG1 R3\\";
var AEP = new File(REEL.fsName + "\\AG1_R3.aep");
var C = {}, FONT_AR = "ArefRuqaa-Bold", comp = null;
var BASE = 150;                                          // 720x1280 -> 1080x1920 (1080-wide clips get 100)
var VO_AT = 0.6;

// t0, t1, clip, source in (s), speed, scale start/end (x BASE)
var SHOTS = [
    [0.00, 1.25, "H1", 2.40, 1, 1.00, 1.10],   // elder welcomes at his door (reference opening)
    [1.25, 2.30, "B2", 0.40, 1, 1.00, 1.05],   // camel feet in sand
    [2.30, 3.86, "B1r", 0.60, 1, 1.00, 1.05],  // rider on the dunes
    [3.86, 5.62, "A1", 3.40, 1, 1.00, 1.05],   // falconer reveal
    [5.62, 7.00, "A2", 2.60, 1, 1.00, 1.05],   // wings spread
    [7.00, 8.38, "C1", 0.40, 1, 1.00, 1.05],   // coffee pour
    [8.38, 9.40, "D1", 2.00, 1, 1.00, 1.04],   // wide Najdi majlis
    [9.40, 10.62, "D2", 0.30, 1, 1.00, 1.05],  // host pours for guest
    [10.62, 11.90, "E1", 0.30, 1, 1.00, 1.05], // kids running
    [11.90, 13.72, "F1n", 2.30, 1, 1.00, 1.06], // grandson kisses the elder, then holds his hands
    [13.72, 15.34, "E2", 3.40, 1, 1.00, 1.05], // boy jumps
    [15.34, 16.70, "G1", 1.60, 1, 1.00, 1.06],  // finjan + dallah
    [16.70, 17.00, "A2", 4.00, 1, 1.08, 1.12], // fast montage
    [17.00, 17.30, "C2", 4.60, 1, 1.08, 1.12],
    [17.30, 17.60, "E1", 3.80, 1, 1.08, 1.12],
    [17.60, 17.90, "A1", 0.80, 1, 1.08, 1.12],
    [17.90, 18.20, "E2", 1.60, 1, 1.08, 1.12],
    [18.20, 25.00, "G2", 0.05, 1, 1.00, 1.12]   // sunset: time-remapped, slows + blurs under the logo
];
var TITLE_AT = 18.95, TITLE_OUT = 21.70;
var BLUR_AT = 21.75, RING_AT = 22.35, LOGO_AT = 22.55, CARD_AT = 22.95, FLAG_AT = 22.95, SHINE_AT = 23.20;   // CARD_AT = logo lands
// captions: text, first word starts, last word ends + 0.12s (measured on vo_take2, +0.6s offset)
var CAPS = [
    ["من رمل الصحراء بدأت حكايتنا", 0.60, 3.75],
    ["ومن نخوة أهلنا ورثنا العز", 4.11, 6.89],
    ["قهوة تجمعنا ومجلس يلم شملنا", 7.23, 10.55],
    ["وأجيال تحمل أصالتنا للمستقبل", 10.83, 13.59],
    ["هذه هي السعودية", 13.99, 15.26],
    ["جذور راسخة وعز يمتد", 15.56, 18.14]
];
var CAP_FONT = "Palestine-Regular", CAP_Y = 1330;
// Opening sung welcome (Omar 2026-11-05): everything after the first shot moves +SH; the ending is tightened by
// ES (title hold + logo build) and EC in total, so the film stays about 26s.
var SH = 2.2, ES = 0.6, EC = 1.0;
for (var si = 0; si < SHOTS.length; si++) {
    var Q = SHOTS[si];
    if (si === 0) { Q[1] += SH; Q[3] = 1.6; }          // elder starts raising his hand with the song
    else if (Q[2] === "G2") { Q[0] += SH; Q[1] += SH - EC; }
    else { Q[0] += SH; Q[1] += SH; }
}
for (var cq = 0; cq < CAPS.length; cq++) { CAPS[cq][1] += SH; CAPS[cq][2] += SH; }
TITLE_AT += SH; TITLE_OUT += SH - ES; BLUR_AT += SH - ES; RING_AT += SH - ES; LOGO_AT += SH - ES;
CARD_AT += SH - ES; FLAG_AT += SH - ES; SHINE_AT += SH - ES; DUR += SH - EC; VO_AT += SH;
var REMAP_T = TITLE_OUT - 0.10;                        // sunset slows from here

function findItem(name) {
    for (var i = 1; i <= app.project.numItems; i++) if (app.project.item(i).name === name) return app.project.item(i);
    return null;
}
function importOnce(path, name) {
    var it = findItem(name);
    if (it) return it;
    it = app.project.importFile(new ImportOptions(new File(path)));
    it.name = name;
    return it;
}
function delComp(name) {
    for (var i = app.project.numItems; i >= 1; i--) {
        var it = app.project.item(i);
        if (it instanceof CompItem && it.name === name) it.remove();
    }
}
function fx(l, m) { return l.property("ADBE Effect Parade").addProperty(m); }
function setByName(e, name, v) { try { e.property(name).setValue(v); } catch (er) { clog("fx prop missing: " + name); } }

try {
    // ---------- project ----------
    if (AEP.exists) { if (!app.project.file || app.project.file.fsName !== AEP.fsName) app.open(AEP); }
    else { app.newProject(); app.project.save(AEP); }

    var CLIPS = { A1: "A1_a.mp4", A2: "A2_a.mp4", B1r: "B1r_a.mp4", B2: "B2_a.mp4", C1: "C1_a.mp4", C2: "C2_a.mp4", D2: "D2_a.mp4", E1: "E1_a.mp4", E2: "E2_a.mp4", F1: "F1_a.mp4", G2: "B1_a.mp4", D1: "D1_a.mp4", F1n: "F1n_a.mp4", G1: "G1_a.mp4", H1: "H1_a.mp4" }; // B1_a is the sunset shot
    var SRC = {};
    for (var k in CLIPS) SRC[k] = importOnce(FOOT + CLIPS[k], k + "_" + CLIPS[k]);
    var VO = importOnce(ASSET + "vo\\vo_take2.mp3", "VO_take2");
    var LOGO = importOnce(ASSET + "logo_alpha.png", "logo_alpha");
    try { LOGO.mainSource.reload(); } catch (eR) {}

    var savedP = ctrlRead("01_Picture"), saved = ctrlRead("00_Master");
    delComp("00_Master"); delComp("01_Picture"); delComp("02_Look");

    // ---------- 01_Picture: the cut ----------
    var pic = app.project.items.addComp("01_Picture", W, H, 1, DUR, FPS);
    comp = pic;
    for (var s = SHOTS.length - 1; s >= 0; s--) {   // add in reverse so shot 1 ends on top
        var S = SHOTS[s], it = SRC[S[2]];
        var L = pic.layers.add(it);
        L.name = "S" + (s + 1 < 10 ? "0" : "") + (s + 1) + "_" + S[2];
        if (L.hasAudio) L.audioEnabled = false;
        if (S[2] === "G2") {
            // sunset: ~0.79x until the title leaves, then slows to ~0.35x under the logo (frame mix)
            L.startTime = S[0];
            L.timeRemapEnabled = true;
            var tr = L.property("ADBE Time Remapping");
            var oldT = [];
            for (var kq = 1; kq <= tr.numKeys; kq++) oldT.push(tr.keyTime(kq));
            tr.setValueAtTime(REMAP_T, 2.75);
            tr.setValueAtTime(DUR, 3.98);
            tr.setValueAtTime(S[0], S[3]);
            for (var ko = 0; ko < oldT.length; ko++) {
                var ot = oldT[ko];
                if (Math.abs(ot - S[0]) > 0.001 && Math.abs(ot - REMAP_T) > 0.001 && Math.abs(ot - DUR) > 0.001) tr.removeKey(tr.nearestKeyIndex(ot));
            }
            applySmoothEase(tr, tr.numKeys, 70, 10);
            L.outPoint = S[1]; L.inPoint = S[0];
            L.frameBlendingType = FrameBlendingType.FRAME_MIX;
            var gbG = fx(L, "ADBE Gaussian Blur 2"); gbG.property(3).setValue(1);
            move(gbG.property(1), BLUR_AT, 0, BLUR_AT + 0.7, 38, 80, 80);
            var bcG = fx(L, "ADBE Brightness & Contrast 2");
            move(bcG.property(1), BLUR_AT, 0, BLUR_AT + 0.7, -28, 80, 80);
        } else {
            if (S[4] !== 1) L.stretch = 100 / S[4];
            L.startTime = S[0] - S[3] / S[4];
            L.inPoint = S[0]; L.outPoint = S[1];
        }
        L.transform.position.setValue([W / 2, H / 2]);
        // push: leaves the cut fast, settles slowly (Law C)
        var bs = BASE * 720 / it.width;
        move(L.transform.scale, S[0], [bs * S[5], bs * S[5], 100], S[1], [bs * S[6], bs * S[6], 100], 85, 15);
        L.motionBlur = true;
    }
    pic.motionBlur = true;
    pic.frameBlending = true;

    // ---------- 00_Master ----------
    var m = app.project.items.addComp("00_Master", W, H, 1, DUR, FPS);
    comp = m;
    m.bgColor = [0, 0, 0];
    var K = ctrlLayer(m);

    var P = m.layers.add(pic);
    P.name = "PICTURE";
    // film weave + bounded drift (nothing static)
    P.transform.position.expression = "var w = wiggle(3, 1.6); w + [Math.sin(time*1.1)*3, Math.cos(time*0.8)*3]";
    // grade: lower saturation, soft contrast, slight flicker
    var hs = fx(P, "ADBE HUE SATURATION"); setByName(hs, "Master Saturation", -18);
    var bc = fx(P, "ADBE Brightness & Contrast 2");
    setByName(bc, "Contrast", -10);
    try { bc.property("Brightness").expression = "wiggle(9, 1.5)"; } catch (e1) {}
    var nz = fx(P, "ADBE Noise"); setByName(nz, "Amount of Noise", 6); setByName(nz, "Noise Type", 0);

    // lifted blacks: warm-brown solid in Lighten
    var lift = m.layers.addSolid([0.10, 0.075, 0.05], "LIFT_Blacks", W, H, 1, DUR);
    lift.blendingMode = BlendingMode.LIGHTEN;
    lift.moveBefore(P);
    // vignette
    var vg = m.layers.addSolid([0, 0, 0], "VIGNETTE", W, H, 1, DUR);
    var mk = vg.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
    var sh = new Shape(), rx = W * 0.62, ry = H * 0.58, cx = W / 2, cy = H / 2, kk = 0.5523;
    sh.vertices = [[cx, cy - ry], [cx + rx, cy], [cx, cy + ry], [cx - rx, cy]];
    sh.inTangents = [[-rx * kk, 0], [0, -ry * kk], [rx * kk, 0], [0, ry * kk]];
    sh.outTangents = [[rx * kk, 0], [0, ry * kk], [-rx * kk, 0], [0, -ry * kk]];
    sh.closed = true;
    mk.property("ADBE Mask Shape").setValue(sh);
    mk.inverted = true;
    mk.property("ADBE Mask Feather").setValue([420, 420]);
    vg.opacity.setValue(55);

    // ---------- title on the sunset ----------
    // adding an effect invalidates earlier effect objects -> keep names only (ctrlRef needs .name)
    ctrlSlider(K, "Title delay (f)", 0, saved);
    ctrlPoint(K, "Title offset", [0, 0], saved);
    ctrlSlider(K, "Title size %", 100, saved);
    ctrlSlider(K, "Logo size %", 100, saved);
    var tDelay = { name: "Title delay (f)" }, tOff = { name: "Title offset" }, tSize = { name: "Title size %" }, lSize = { name: "Logo size %" };
    var cream = hex("#F3E5C8");
    var t1 = makeText("السعودية..", 170, cream, "TITLE_1");
    var t2 = makeText("أصالة تجمعنا وعزّ نفخر به", 104, cream, "TITLE_2");
    var gotFont = t1.property("Source Text").value.font;
    clog("title font: " + gotFont);
    fit(t1, 880, 400, 0); fit(t2, 880, 200, 0);
    place(t1, W / 2, 640, 0); place(t2, W / 2, 830, 0);
    var lines = [[t1, TITLE_AT], [t2, TITLE_AT + 0.16]];
    for (var q = 0; q < 2; q++) {
        var T = lines[q][0], ta = lines[q][1];
        shadow(T);
        dropIn(T, ta);
        // exit: blur up + rise + fade together (15/85 whip)
        var yv = T.transform.yPosition.keyValue(T.transform.yPosition.numKeys);
        move(T.transform.yPosition, TITLE_OUT, yv, TITLE_OUT + 0.35, yv - 70, 15, 85);
        move(T.property("ADBE Effect Parade").property("ADBE Gaussian Blur 2").property(1), TITLE_OUT, 0, TITLE_OUT + 0.35, 40, 15, 85);
        move(T.transform.opacity, TITLE_OUT + 0.05, 100, TITLE_OUT + 0.35, 0, 15, 85);
        T.outPoint = TITLE_OUT + 0.4;
        ctrlDelay(T.transform.yPosition, tDelay);
        ctrlDelay(T.transform.scale, tDelay);
        ctrlScale(T.transform.scale, tSize);
        T.motionBlur = true;
    }
    // slow lift while it holds (bounded, never static)
    t1.transform.xPosition.expression = "value + " + ctrlRef(tOff) + "[0]";
    t2.transform.xPosition.expression = "value + " + ctrlRef(tOff) + "[0]";

    // ---------- rounded film gate (matte over everything picture-side) ----------
    var gate = m.layers.addShape(); gate.name = "GATE_Matte";
    var gg = grp(gate);
    var rr = gg.property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Rect");
    rr.property("ADBE Vector Rect Size").setValue([W - 40, H - 72]);
    rr.property("ADBE Vector Rect Roundness").setValue(46);
    gg.property("ADBE Vectors Group").addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue([1, 1, 1]);
    gate.transform.position.setValue([W / 2, H / 2]);
    // precompose the picture stack so one matte cuts it all
    var stackIdx = [P.index, lift.index, vg.index];
    var look = m.layers.precompose(stackIdx, "02_Look", true);
    var LOOK = m.layer("02_Look");
    gate.moveBefore(LOOK);
    try { LOOK.setTrackMatte(gate, TrackMatteType.ALPHA); } catch (e2) { LOOK.trackMatteType = TrackMatteType.ALPHA; }


    // ---------- end: heart + logo (dropped from the top, + shine) + flag, over the blurred sunset ----------
    var END = m.layers.addNull(DUR); END.name = "END_Null";
    END.transform.position.setValue([W / 2, 900]);
    move(END.transform.scale, CARD_AT, [100, 100, 100], DUR, [104, 104, 100], 80, 80);   // slow push, never static
    var CY = 790 - 900;                                                            // logo landing centre in END space
    function endChild(l, x, y) { l.parent = END; l.transform.position.setValue([x, y]); }

    // sketched heart around the logo + flag (Omar: «قلب كأنه رسمه أو ظل، مش قلب واضح»)
    var HK = 30, HCY = 810;                                    // size and centre (screen y): lobes ~460, tip ~1320
    function heartShape(k) {
        var n = 72, v = [], ti = [], to = [], dt = 2 * Math.PI / n;
        for (var i = 0; i < n; i++) {
            var t = i * dt, sn = Math.sin(t), cs = Math.cos(t);
            var x = 16 * sn * sn * sn, y = -(13 * cs - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t));
            var dx = 48 * sn * sn * cs, dy = -(-13 * sn + 10 * Math.sin(2 * t) + 6 * Math.sin(3 * t) + 4 * Math.sin(4 * t));
            v.push([x * k, y * k]);
            to.push([dx * k * dt / 3, dy * k * dt / 3]);
            ti.push([-dx * k * dt / 3, -dy * k * dt / 3]);
        }
        var sh = new Shape(); sh.vertices = v; sh.inTangents = ti; sh.outTangents = to; sh.closed = true;
        return sh;
    }
    var rg = m.layers.addShape(); rg.name = "END_Heart";
    var HEART = heartShape(HK);
    // soft shadow fill
    var hf = grp(rg), hfv = hf.property("ADBE Vectors Group");
    hfv.addProperty("ADBE Vector Shape - Group").property("ADBE Vector Shape").setValue(HEART);
    hfv.addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue(cream);
    move(tf(hf).property("ADBE Vector Group Opacity"), RING_AT + 0.6, 0, RING_AT + 1.4, 9, 80, 80);
    // two sketchy strokes drawing on, the second slightly off like a hand-drawn pass
    for (var ri = 0; ri < 2; ri++) {
        var g2 = grp(rg), vgp = g2.property("ADBE Vectors Group");
        vgp.addProperty("ADBE Vector Shape - Group").property("ADBE Vector Shape").setValue(HEART);
        var rgh = vgp.addProperty("ADBE Vector Filter - Roughen");
        rgh.property("ADBE Vector Roughen Size").setValue(ri ? 3 : 1.5);
        rgh.property("ADBE Vector Roughen Detail").setValue(ri ? 3 : 6);
        var st = vgp.addProperty("ADBE Vector Graphic - Stroke");
        st.property("ADBE Vector Stroke Color").setValue(cream);
        st.property("ADBE Vector Stroke Width").setValue(ri ? 2 : 4);
        var trm = vgp.addProperty("ADBE Vector Filter - Trim");
        move(trm.property("ADBE Vector Trim End"), RING_AT + ri * 0.15, 0, RING_AT + ri * 0.15 + 1.1, 100, 80, 80);
        tf(g2).property("ADBE Vector Group Opacity").setValue(ri ? 30 : 60);
        if (ri) { tf(g2).property("ADBE Vector Scale").setValue([102.5, 102.5]); tf(g2).property("ADBE Vector Rotation").setValue(1.5); }
    }
    endChild(rg, 0, HCY - 900);
    rg.transform.rotation.expression = "Math.sin(time * 0.8) * 1.2";
    rg.inPoint = RING_AT;
    var hglow = rg.duplicate(); hglow.name = "END_HeartGlow";
    var hgb = fx(hglow, "ADBE Gaussian Blur 2"); hgb.property(1).setValue(14);
    hglow.transform.opacity.setValue(55);
    hglow.moveAfter(rg);

    // logo: no card, only at the end (Omar 2026-11-05: the blue at the top during the video didn't fit)
    var lg = m.layers.add(LOGO); lg.name = "LOGO";
    var LEND = [W / 2, 790], SEND = 44;   // lands inside the heart
    lg.transform.position.setValue(LEND);
    addBlur(lg, LOGO_AT);
    move(lg.transform.scale, LOGO_AT, [SEND * 0.82, SEND * 0.82, 100], LOGO_AT + 0.4, [SEND, SEND, 100], 85, 15);
    move(lg.transform.scale, LOGO_AT + 0.4, [SEND, SEND, 100], DUR, [SEND * 1.04, SEND * 1.04, 100], 80, 80);
    lg.transform.position.dimensionsSeparated = true;
    move(lg.transform.yPosition, LOGO_AT, LEND[1] + 40, LOGO_AT + 0.4, LEND[1], 85, 15);
    var lds = fx(lg, "ADBE Drop Shadow");   // soft dark halo so the blue reads on the blurred sunset
    lds.property(2).setValue(150); lds.property(4).setValue(0); lds.property(5).setValue(30);
    ctrlScale(lg.transform.scale, lSize);
    lg.inPoint = LOGO_AT;
    lg.motionBlur = true;

    // shine: soft white bar sweeping across the logo twice, matted by the logo's alpha
    var bar = m.layers.addShape(); bar.name = "LOGO_Shine";
    var bg2 = grp(bar), bvg = bg2.property("ADBE Vectors Group");
    bvg.addProperty("ADBE Vector Shape - Rect").property("ADBE Vector Rect Size").setValue([110, 900]);
    bvg.addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue([1, 1, 1]);
    bar.transform.rotation.setValue(22);
    var bgb = fx(bar, "ADBE Gaussian Blur 2"); bgb.property(1).setValue(28);
    bar.parent = END;
    bar.transform.position.dimensionsSeparated = true;
    bar.transform.yPosition.setValue(CY);
    move(bar.transform.xPosition, SHINE_AT, -380, SHINE_AT + 0.75, 380, 80, 80);
    move(bar.transform.xPosition, SHINE_AT + 1.45, -380, SHINE_AT + 2.1, 380, 80, 80);
    // hold off-screen between the two sweeps
    bar.transform.xPosition.setValueAtTime(SHINE_AT + 1.44, -380);
    bar.transform.xPosition.setInterpolationTypeAtKey(bar.transform.xPosition.nearestKeyIndex(SHINE_AT + 0.75), KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.HOLD);
    bar.blendingMode = BlendingMode.ADD;
    bar.transform.opacity.setValue(85);
    var lgM = lg.duplicate(); lgM.name = "LOGO_ShineMatte";
    var lfx = lgM.property("ADBE Effect Parade"); for (var lf = lfx.numProperties; lf >= 1; lf--) lfx.property(lf).remove();
    lgM.moveBefore(bar);
    try { bar.setTrackMatte(lgM, TrackMatteType.ALPHA); } catch (e3) { bar.trackMatteType = TrackMatteType.ALPHA; }
    lgM.enabled = false;
    bar.inPoint = SHINE_AT - 0.05;

    // flag under the logo (only if the user supplied it): waving cloth
    var FLAGF = new File(ASSET + "flag.png");
    if (FLAGF.exists) {
        var FL = importOnce(FLAGF.fsName, "flag");
        try { FL.mainSource.reload(); } catch (eF) {}
        var fl = m.layers.add(FL); fl.name = "FLAG";
        var fk = 230 / FL.width * 100;
        fl.transform.scale.setValue([fk, fk, 100]);
        endChild(fl, 0, 1045 - 900);
        var ww = fx(fl, "ADBE Wave Warp");
        setByName(ww, "Wave Height", 12); setByName(ww, "Wave Width", 240); setByName(ww, "Wave Speed", 1.1);
        var chk = fx(fl, "ADBE Simple Choker"); setByName(chk, "Choke Matte", 1.5);   // trims the white fringe left by the bg removal
        shadow(fl);
        addBlur(fl, FLAG_AT);
        fl.transform.position.dimensionsSeparated = true;
        move(fl.transform.yPosition, FLAG_AT, 1045 - 900 + 50, FLAG_AT + 0.4, 1045 - 900, 85, 15);
        fl.inPoint = FLAG_AT;
        clog("flag added: " + FL.width + "x" + FL.height);
    } else clog("no flag.png yet");
    END.moveToBeginning();

    // ---------- captions with the VO ----------
    ctrlSlider(K, "Caption Y offset", 0, saved);
    var capY = { name: "Caption Y offset" };
    for (var ci = 0; ci < CAPS.length; ci++) {
        var CP = CAPS[ci], c0 = CP[1] - 0.12, c1 = CP[2];
        FONT_AR = CAP_FONT;
        var cl = makeText(CP[0], 74, cream, "CAP_" + (ci + 1));
        FONT_AR = "ArefRuqaa-Bold";
        if (ci === 0) clog("caption font: " + cl.property("Source Text").value.font);
        fit(cl, 880, 160, 0);
        place(cl, W / 2, CAP_Y, 0);
        var ds = fx(cl, "ADBE Drop Shadow");
        ds.property(2).setValue(190); ds.property(4).setValue(3); ds.property(5).setValue(16);
        var cb = fx(cl, "ADBE Gaussian Blur 2"); cb.property(3).setValue(1);
        move(cb.property(1), c0, 18, c0 + 0.25, 0, 85, 15);
        move(cb.property(1), c1 - 0.15, 0, c1, 18, 15, 85);
        move(cl.transform.opacity, c0, 0, c0 + 0.25, 100, 85, 15);
        move(cl.transform.opacity, c1 - 0.15, 100, c1, 0, 15, 85);
        cl.transform.position.dimensionsSeparated = true;
        move(cl.transform.yPosition, c0, CAP_Y + 22, c0 + 0.25, CAP_Y, 85, 15);
        ctrlAdd1D(cl.transform.yPosition, capY);
        cl.inPoint = c0; cl.outPoint = c1 + 0.04;
    }

    // ---------- VO guide (final mix is remuxed from Python) ----------
    var vo = m.layers.add(VO); vo.name = "VO_take2"; vo.startTime = VO_AT; vo.audioEnabled = true;

    K.moveToBeginning();
    ctrlReport(saved);
    m.openInViewer();
    app.project.save(AEP);

    // ---------- check frames ----------
    var outDir = new Folder(JOBDIR.fsName + "\\checks");
    if (!outDir.exists) outDir.create();
    var times = [0.6, 2.0, 4.5, 6.2, 7.6, 8.9, 10.0, 11.2, 12.4, 13.3, 14.5, 16.0, 17.3, 19.6, 24.3];
    for (var f = 0; f < times.length; f++) {
        var nm = ("00" + f).slice(-2) + "_" + times[f].toFixed(1).replace(".", "_") + ".png";
        m.saveFrameToPng(times[f], new File(outDir.fsName + "\\" + nm));
    }
    clog("frames: " + times.length);
    "OK " + m.numLayers + " layers";
} catch (err) {
    "ERROR line " + err.line + ": " + err.toString();
}
