// build_talking.jsx — talking-head reel, full AE build (runner job: tools\ae_run.ps1). Skill reel-talking-head.
// Copied on 2026-11-12 from CLA R1 (AG2/CLA/reel-01/scripts/build_CLA_R1.jsx, the v19 build of 2026-11-10).
// Everything that belongs to one reel sits in SETTINGS; the logic under it is the CLA logic unchanged.
// Use: copy this file into the reel's scripts\ folder next to the EDL from plan_talking.py (the include below is
// relative to this file), fill SETTINGS, run it with ae_run.ps1. It builds a new project from scratch and saves SAVE_AS.
// ============================ SETTINGS (CLA R1 v19 values) ============================
var R = "D:/Montage-02/Clients/AG2/CLA/reel-01/";       // every path below is relative to R
// claude-include: edl_CLA_R1.jsx
var FPS = 25, W = 1080, H = 1920, DUR = EDL.dur;   // EDL = cut plan from plan_talking.py (all times on the timeline)
var FONT_AR = "Cairo-Bold";
var FILES = {                                     // item keys used by the EDL b-roll list (doc = the speaker, logo = outro)
    trio: "footage/ai/ai_trio_raw.mp4", perf: "footage/ai/ai_perf_raw.mp4", beauty: "footage/ai/ai_beauty_raw.mp4",
    aClar: "footage/ai/ai_clarity2_raw.mp4", aPerf: "footage/ai/ai_perf2_raw.mp4", aBeau: "footage/ai/ai_beauty2_raw.mp4",
    doc: "footage/prep/g_doc_C0124.mp4", set: "footage/prep/g_set_C0125.mp4",
    e25: "footage/prep/g_ev_C9925.mp4", e27: "footage/prep/g_ev_C9927.mp4", e27s: "footage/prep/g_ev_C9927_slowstab.mp4", e29: "footage/prep/g_ev_C9929.mp4",
    e32: "footage/prep/g_ev_C9932.mp4", e43: "footage/prep/g_ev_C9943.mp4", e18: "footage/prep/g_ev_C9918.mp4",
    e95: "footage/prep/g_ev_C9895.mp4", e46: "footage/prep/g_ev_C9946.mp4", e52: "footage/prep/g_ev_C9952.mp4",
    sClar: "assets/site_images/Untitled_design_39.png", sPerf: "assets/site_images/Performance_1.png",
    sBeau: "assets/site_images/Website_images_shopify_3.png", logo: "assets/logo/yc_logo_alpha.png"
};
var MIX = "assets/audio/CLA_R1_mix_v17.wav";      // from mix_talking.py; missing = the speaker layers keep their own audio
var DOC_ANCHOR = [450, 700];                      // speaker zoom centre (between the face and the hands)
var CAP_SIZE = 40, CAP_Y = 1330;                  // captions at 1080 wide: 40 px for speech (46 was «مكبره اوي»)
var INTRO_CAP_SIZE = 54, INTRO_CAP_Y = 1300;      // big intro lines (only if introCaps below is filled)
var OUTRO_BG = [0.973, 0.957, 0.937];             // warm off-white #F8F4EF, closed 100%
var LOGO_W = 760, LOGO_POS = [540, 900];
var CHECK_TIMES = [1.2, 6.0, 10.6, 14, 20, 24, 27, 30, 35, 39, 42, 45, 50, 56, 62, 66, 70, 74, 77, 80];   // check PNGs
var CHECK_DIR = "scripts/check", SAVE_AS = "CLA_R1.aep";
// ========================================================================================
var log = [];
function F(n) { return n / FPS; }

function ease(prop, k, inf, outf) {
    var a = new KeyframeEase(0, inf), b = new KeyframeEase(0, outf), n = 1;
    if (prop.propertyValueType === PropertyValueType.TwoD) n = 2;      // spatial props take a single ease
    if (prop.propertyValueType === PropertyValueType.ThreeD) n = 3;
    var ia = [], ob = [];
    for (var i = 0; i < n; i++) { ia.push(a); ob.push(b); }
    prop.setTemporalEaseAtKey(k, ia, ob);
}
// key with (in, out) influence
function K(prop, t, v, inf, outf) {
    prop.setValueAtTime(t, v);
    var k = prop.nearestKeyIndex(t);
    ease(prop, k, inf || 33, outf || 33);
    return k;
}
function imp(p) { return app.project.importFile(new ImportOptions(new File(R + p))); }
function blurFx(l) {
    var fx = l.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
    try { fx.property(3).setValue(1); } catch (e) {}
    return l.property("ADBE Effect Parade").property(fx.name).property(1);
}
function cover(item) { return Math.max(W / item.width, H / item.height) * 100; }
function clip(comp, item, t0, t1, src, stretch) {
    var l = comp.layers.add(item);
    if (stretch) l.stretch = stretch;
    l.startTime = t0 - src * (stretch || 100) / 100; l.inPoint = t0; l.outPoint = t1;
    var s = cover(item); l.property("Scale").setValue([s, s]);
    l.audioEnabled = false;
    return l;
}

try {
    // a never-saved project here is a half build from a crashed run: drop it, or newProject() opens a Save As dialog
    if (app.project) app.project.close(app.project.file ? CloseOptions.SAVE_CHANGES : CloseOptions.DO_NOT_SAVE_CHANGES);
    app.beginSuppressDialogs();
    app.newProject();
    var proj = app.project;
    proj.bitsPerChannel = 8;

    var it = {};
    for (var k in FILES) it[k] = imp(FILES[k]);
    var mixF = new File(R + MIX);

    var comp = proj.items.addComp("00_Master_Reel", W, H, 1, DUR, FPS);
    comp.motionBlur = true;
    comp.bgColor = [0, 0, 0];

    // ---------- still precomps (blurred cover + fitted card, slow push) ----------
    function stillComp(name, item, dur) {
        var c = proj.items.addComp(name, W, H, 1, dur, FPS);
        var bg = c.layers.add(item); var s = cover(item) * 1.15; bg.property("Scale").setValue([s, s]);
        var bb = blurFx(bg); bb.setValue(80);
        var bc = bg.property("ADBE Effect Parade").addProperty("ADBE Brightness & Contrast 2");
        try { bc.property(1).setValue(-35); } catch (e) {}
        // card sits above the caption line (y 1330): 72% width, centred at y 800
        var fg = c.layers.add(item); var f = W / item.width * 100 * 0.72;
        fg.property("Position").setValue([540, 800]);
        var sc = fg.property("Scale"); K(sc, 0, [f, f], 33, 20); K(sc, dur, [f * 1.06, f * 1.06], 60, 33);
        var ds = fg.property("ADBE Effect Parade").addProperty("ADBE Drop Shadow");
        try { ds.property(2).setValue(110); } catch (e) { try { ds.property(2).setValue(45); } catch (e2) {} }
        try { ds.property(4).setValue(20); ds.property(5).setValue(60); } catch (e) {}
        return c;
    }

    // ---------- transitions ----------
    function rampIn(l, t0, s, push, strong) {      // blur dissolve (+ zoom push for the intro)
        var sc = l.property("Scale"), op = l.property("Opacity"), bl = blurFx(l);
        var d = strong ? F(8) : F(6);
        if (!strong) { K(op, t0, 0, 33, 60); K(op, t0 + F(5), 100, 60, 33); }   // intro = crisp zoom cut, no dissolve
        K(bl, t0, strong ? 16 : 18, 33, 15); K(bl, t0 + F(strong ? 5 : 6), 0, 85, 33);
        var a = strong ? 1.10 : 1.05;
        K(sc, t0, [s * a, s * a], 33, 15); K(sc, t0 + d, [s, s], 85, 40);
        K(sc, l.outPoint, [s * push, s * push], 40, 33);
        return bl;
    }
    function rampOut(l, t1, bl) {
        var op = l.property("Opacity");
        K(op, t1 - F(4), 100, 33, 40); K(op, t1, 0, 60, 33);
        if (bl) { K(bl, t1 - F(4), 0, 33, 40); K(bl, t1, 14, 60, 33); }
    }

    // ---------- doctor base ----------
    // one layer per kept (spoken) interval; framing comes from the topic the layer belongs to:
    // hold = static framing, push = very slow eased zoom (AE ease() = ease in + ease out) over the visible part
    // doctor framing per shot: a slow ease from the shot's first frame to its last, or a static frame (k0 = k1)
    var ds = [];
    for (var q = 0; q < EDL.shots.length; q++) { var sh = EDL.shots[q]; if (sh.br === null) ds.push("[" + [sh.t0, sh.t1, sh.k0, sh.k1].join(",") + "]"); }
    var docScaleExpr = "var S = [" + ds.join(",") + "], s = S[0][2]; " +
        "for (var i = 0; i < S.length; i++) if (time >= S[i][0]) s = ease(time, S[i][0], S[i][1], S[i][2], S[i][3]); [s, s]";
    for (var i = 0; i < EDL.doc.length; i++) {
        var d = EDL.doc[i], doc = comp.layers.add(it.doc);
        doc.name = "DOC_" + (i + 1);
        doc.startTime = d.t0 - d.src; doc.inPoint = d.t0; doc.outPoint = (i === EDL.doc.length - 1) ? DUR : d.t1;
        doc.audioEnabled = !mixF.exists;
        doc.property("Anchor Point").setValue(DOC_ANCHOR); doc.property("Position").setValue(DOC_ANCHOR);
        doc.property("Scale").expression = docScaleExpr;   // v15: per shot on screen (EDL.shots), see plan_CLA_R1.py
    }

    // v17: hold the doctor's last frame before a VO join until the b-roll cuts in on the next word (no visible jump)
    for (var h = 0; h < EDL.broll.length; h++) if (EDL.broll[h].hold_doc) {
        var hd = EDL.broll[h].hold_doc, d0 = EDL.doc[0], fr = comp.layers.add(it.doc);
        // v18: a frozen frame read as the picture stopping (Omar), so the first take keeps playing and dissolves into
        // the second one over the 6 frames (a morph-cut), then the b-roll cuts in on «we»
        fr.name = "DOC_MORPH"; fr.audioEnabled = false;
        fr.startTime = d0.t0 - d0.src; fr.inPoint = hd[0]; fr.outPoint = hd[1];
        K(fr.property("Opacity"), hd[0], 100, 33, 60); K(fr.property("Opacity"), hd[1], 0, 60, 33);
        fr.property("Anchor Point").setValue(DOC_ANCHOR); fr.property("Position").setValue(DOC_ANCHOR);
        fr.property("Scale").expression = docScaleExpr;
    }

    // ---------- intro (beat cuts) ----------
    // v10 (client): intro removed, these shots are b-roll over the doctor now (plan_CLA_R1.py)
    // was: [[0, 2.40, it.trio, 0.0], [2.40, 4.76, it.e27, 1.5], [4.76, 7.12, it.perf, 0.2], [7.12, 9.44, it.e25, 2.0], [9.44, 11.76, it.beauty, 1.0]]
    var intro = [];
    for (i = 0; i < intro.length; i++) {
        var g = intro[i], last = (i === intro.length - 1);
        var l = clip(comp, g[2], g[0], g[1], g[3]);
        l.name = "INTRO_" + (i + 1);
        var bl = rampIn(l, g[0], cover(g[2]), 1.05, i > 0);
        if (i === 0) { l.property("Opacity").removeKey(1); l.property("Opacity").setValueAtTime(0, 100); }
        if (last) rampOut(l, g[1], bl);
    }

    // ---------- b-roll over the doctor ----------
    // v12: every b-roll edge is a straight cut; the transition lives on adjustment / light layers above (trans() below)
    var br = EDL.broll, tpts = [];
    for (i = 0; i < br.length; i++) {
        var nextAdj = (i < br.length - 1 && Math.abs(br[i + 1].t0 - br[i].t1) < 0.01);
        var s0 = br[i].t0, s1 = br[i].t1, src = it[br[i].item];
        var need = s1 - s0, avail = src.duration - br[i].src;
        // speed = % from Omar's Premiere cut (50 = half speed, via xml_to_edl.py); AE stretch is the inverse (200)
        var st = (br[i].speed && br[i].speed !== 100) ? 10000 / br[i].speed : 0;
        if (need * 100 / (st || 100) > avail) st = Math.ceil(need / avail * 100);   // source too short: stretch to fill
        var lb = clip(comp, src, s0, s1, br[i].src, st);
        lb.name = "BROLL_" + (i + 1);
        var sc0 = cover(src);
        for (var q2 = 0; q2 < EDL.shots.length; q2++) if (EDL.shots[q2].br === i) {   // v15: slow zoom over the shot, or static
            var sh2 = EDL.shots[q2], a0 = sc0 * sh2.k0 / 100, a1 = sc0 * sh2.k1 / 100;
            if (sh2.zoom) { K(lb.property("Scale"), s0, [a0, a0], 33, 33); K(lb.property("Scale"), s1, [a1, a1], 33, 33); }
            else lb.property("Scale").setValue([a0, a0]);
        }
        tpts.push([s0, br[i].tin]);
        if (!nextAdj) tpts.push([s1, br[i].tout]);
    }

    function adj(name, t0, t1) {
        var a = comp.layers.addSolid([1, 1, 1], name, W, H, 1, t1 - t0);
        a.adjustmentLayer = true; a.startTime = t0; a.inPoint = t0; a.outPoint = t1;
        return a;
    }
    function fx(l, mn) { var e = l.property("ADBE Effect Parade").addProperty(mn); return l.property("ADBE Effect Parade").property(e.name); }
    function tile(l) { var m = fx(l, "ADBE Tile"); m.property(4).setValue(300); m.property(5).setValue(300); m.property(6).setValue(1); }   // mirror edges
    function xform(l, shutter) { var x = fx(l, "ADBE Geometry2"); x.property(10).setValue(0); x.property(11).setValue(shutter); return x; }
    // one half of a transition: a = the outgoing half (accelerates into the cut), b = the incoming half (fast, then settles)
    function half(name, t0, t1, out, setup) {
        var a = adj(name, t0, t1); tile(a); xform(a, 270); fx(a, "ADBE Gaussian Blur 2").property(3).setValue(1);
        var P = a.property("ADBE Effect Parade"), x = P.property(2), g = P.property(3);   // re-fetch: adding an effect invalidates older refs
        var e0 = out ? 60 : 20, e1 = out ? 20 : 60;          // ease in/out influences
        setup(x, g, t0, t1, e0, e1);
    }
    function trans(type, t) {
        if (type === "cut") return;
        if (type === "zoom") {                    // zoom-through: 100→120 into the cut, 84→100 out of it
            half("TR_ZOOM_A", t - F(6), t, true, function (x, g, a, b, e0, e1) {
                K(x.property(4), a, 100, 33, e0); K(x.property(4), b, 145, e1, 33); K(g.property(1), a, 0, 33, e0); K(g.property(1), b, 45, e1, 33); });
            half("TR_ZOOM_B", t, t + F(10), false, function (x, g, a, b, e0, e1) {
                K(x.property(4), a, 72, 33, e0); K(x.property(4), b, 100, e1, 33); K(g.property(1), a, 45, 33, e0); K(g.property(1), b, 0, e1, 33); });
        } else if (type === "whip") {             // horizontal whip pan, the frame keeps travelling left through the cut
            var d = 620;
            half("TR_WHIP_A", t - F(5), t, true, function (x, g, a, b, e0, e1) {
                K(x.property(2), a, [540, 960], 33, e0); K(x.property(2), b, [540 - d, 960], e1, 33); });
            half("TR_WHIP_B", t, t + F(7), false, function (x, g, a, b, e0, e1) {
                K(x.property(2), a, [540 + d, 960], 33, e0); K(x.property(2), b, [540, 960], e1, 33); });
            var db = fx(adj("TR_WHIP_BLUR", t - F(5), t + F(7)), "ADBE Motion Blur");
            db.property(1).setValue(90);
            K(db.property(2), t - F(5), 0, 33, 85); K(db.property(2), t, 140, 15, 15); K(db.property(2), t + F(7), 0, 85, 33);
        } else if (type === "flash") {            // warm light sweep: soft additive glow crossing the frame, the cut under its peak
            var sb = adj("TR_FLASH_SOFT", t - F(3), t + F(5)), gb = fx(sb, "ADBE Gaussian Blur 2"); gb.property(3).setValue(1);
            K(gb.property(1), t - F(3), 0, 33, 60); K(gb.property(1), t, 30, 40, 40); K(gb.property(1), t + F(5), 0, 60, 33);
            var lt = comp.layers.addSolid([1, 0.78, 0.52], "TR_FLASH_LIGHT", 3400, 3400, 1, F(15));   // > frame: no hard edges (v14)
            lt.startTime = t - F(6); lt.inPoint = t - F(6); lt.outPoint = t + F(9);
            lt.blendingMode = BlendingMode.ADD;
            var mk = lt.property("ADBE Mask Parade").addProperty("ADBE Mask Atom"), es2 = new Shape(), c2 = 0.5523, rx2 = 700, ry2 = 1050, cx2 = 1700, cy2 = 1700;
            es2.vertices = [[cx2, cy2 - ry2], [cx2 + rx2, cy2], [cx2, cy2 + ry2], [cx2 - rx2, cy2]];
            es2.inTangents = [[-rx2 * c2, 0], [0, -ry2 * c2], [rx2 * c2, 0], [0, ry2 * c2]];
            es2.outTangents = [[rx2 * c2, 0], [0, ry2 * c2], [-rx2 * c2, 0], [0, -ry2 * c2]]; es2.closed = true;
            mk.property("ADBE Mask Shape").setValue(es2); mk.property("ADBE Mask Feather").setValue([800, 800]);
            K(lt.property("Position"), t - F(6), [140, 760], 33, 33); K(lt.property("Position"), t + F(9), [940, 1160], 33, 33);
            K(lt.property("Opacity"), t - F(6), 0, 33, 70); K(lt.property("Opacity"), t, 55, 50, 50); K(lt.property("Opacity"), t + F(9), 0, 70, 33);
        }
    }
    for (i = 0; i < tpts.length; i++) trans(tpts[i][1], tpts[i][0]);

    // ---------- legibility gradient + vignette + grain ----------
    var gr = comp.layers.addSolid([0, 0, 0], "TEXT_GRADIENT", W, H, 1, DUR);
    gr.inPoint = 0; gr.outPoint = EDL.outro;
    var m = gr.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
    var sh = new Shape(); sh.vertices = [[-200, 1060], [1280, 1060], [1280, 2200], [-200, 2200]]; sh.closed = true;
    m.property("ADBE Mask Shape").setValue(sh); m.property("ADBE Mask Feather").setValue([420, 420]);
    gr.property("Opacity").setValue(48);
    var vg = comp.layers.addSolid([0, 0, 0], "VIGNETTE", W, H, 1, DUR);
    vg.inPoint = 0; vg.outPoint = EDL.outro;
    var vm = vg.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
    var es = new Shape(); var cx = 540, cy = 960, rx = 760, ry = 1150, c = 0.5523;
    es.vertices = [[cx, cy - ry], [cx + rx, cy], [cx, cy + ry], [cx - rx, cy]];
    es.inTangents = [[-rx * c, 0], [0, -ry * c], [rx * c, 0], [0, ry * c]];
    es.outTangents = [[rx * c, 0], [0, ry * c], [-rx * c, 0], [0, -ry * c]];
    es.closed = true;
    vm.property("ADBE Mask Shape").setValue(es); vm.inverted = true; vm.property("ADBE Mask Feather").setValue([600, 600]);
    vg.property("Opacity").setValue(28);

    // ---------- captions ----------
    function cap(str, t0, t1, size, y, name) {
        var l = comp.layers.addText(str); l.name = name;
        var p = l.property("ADBE Text Properties").property("ADBE Text Document"), td = p.value;
        td.resetCharStyle(); td.resetParagraphStyle();
        td.font = FONT_AR; td.fontSize = size; td.applyFill = true; td.fillColor = [1, 1, 1]; td.applyStroke = false;
        td.justification = ParagraphJustification.CENTER_JUSTIFY;
        try { td.composerEngine = ComposerEngine.UNIVERSAL_TYPE_ENGINE; } catch (e) {}
        try { td.direction = ParagraphDirection.DIRECTION_RIGHT_TO_LEFT; } catch (e) {}
        td.autoLeading = false; td.leading = size * 1.45;
        p.setValue(td);
        if (p.value.font !== FONT_AR) log.push("FONT MISMATCH " + p.value.font);
        l.inPoint = t0; l.outPoint = t1;
        var r = l.sourceRectAtTime(t0 + 0.5, false);
        l.property("Anchor Point").setValue([r.left + r.width / 2, r.top + r.height / 2]);
        var ds = l.property("ADBE Effect Parade").addProperty("ADBE Drop Shadow");
        try { ds.property(2).setValue(140); } catch (e) { try { ds.property(2).setValue(55); } catch (e2) {} }
        try { ds.property(4).setValue(0); ds.property(5).setValue(18); } catch (e) {}
        var bl = blurFx(l), pos = l.property("Position"), op = l.property("Opacity");
        K(pos, t0, [540, y + 22], 33, 15); K(pos, t0 + F(9), [540, y], 85, 33);
        K(op, t0, 0, 33, 40); K(op, t0 + F(4), 100, 60, 33);
        K(bl, t0, 24, 33, 15); K(bl, t0 + F(5), 0, 85, 33);
        K(op, t1 - F(4), 100, 33, 40); K(op, t1, 0, 60, 33);
        K(bl, t1 - F(4), 0, 15, 33); K(bl, t1, 24, 33, 33);
        return l;
    }
    var introCaps = [];   // v10: intro text removed (client)
    var introCapsV9 = [[0.20, 2.30, "نقضي وقتًا طويلًا في التفكير"], [2.55, 4.66, "في ما يجب أن نأكله\rوما يجب أن نتجنّبه"],
        [4.90, 7.02, "وما يفيدنا وما لا يفيدنا"], [7.26, 9.34, "لكن مع الوقت، بدأنا نشعر"],
        [9.58, 11.66, "أن العناية بأنفسنا تعني\rالتخلّي عن أشياء نحبّها"]];
    for (i = 0; i < introCaps.length; i++) cap(introCaps[i][2], introCaps[i][0], introCaps[i][1], INTRO_CAP_SIZE, INTRO_CAP_Y, "CAP_INTRO_" + (i + 1));
    for (i = 0; i < EDL.caps.length; i++) cap(EDL.caps[i].txt, EDL.caps[i].t0, EDL.caps[i].t1, CAP_SIZE, CAP_Y, "CAP_" + (i + 1));

    // ---------- outro: empty set under a white veil, logo ----------
    var T = EDL.outro;
    var wh = comp.layers.addSolid(OUTRO_BG, "WHITE_VEIL", W, H, 1, DUR);   // warm off-white
    wh.inPoint = T - 0.5; wh.outPoint = DUR;
    var wo = wh.property("Opacity"); K(wo, T - 0.5, 0, 33, 25); K(wo, T + 0.5, 100, 80, 33);
    var lg = comp.layers.add(it.logo); lg.inPoint = T; lg.outPoint = DUR; lg.name = "LOGO";
    var ls = LOGO_W / it.logo.width * 100, lt = T + 0.44;
    lg.property("Position").setValue(LOGO_POS);
    var lsc = lg.property("Scale"), lop = lg.property("Opacity"), lbl = blurFx(lg);
    K(lsc, lt, [ls * 0.93, ls * 0.93], 33, 15); K(lsc, lt + F(18), [ls, ls], 85, 40); K(lsc, DUR, [ls * 1.025, ls * 1.025], 40, 33);
    K(lop, lt, 0, 33, 40); K(lop, lt + F(10), 100, 60, 33);
    K(lbl, lt, 22, 33, 15); K(lbl, lt + F(12), 0, 85, 33);
    if (URL_TEXT) {
    var url = comp.layers.addText(URL_TEXT); url.name = "URL";
    var up = url.property("ADBE Text Properties").property("ADBE Text Document"), ut = up.value;
    ut.resetCharStyle(); ut.font = URL_FONT; ut.fontSize = 34; ut.tracking = 200;   // Raleway: only Bold/Black are installed
    ut.applyFill = true; ut.fillColor = URL_COLOR; ut.justification = ParagraphJustification.CENTER_JUSTIFY;
    up.setValue(ut);
    url.inPoint = T + 0.9; url.outPoint = DUR;
    var ur = url.sourceRectAtTime(T + 1.5, false);
    url.property("Anchor Point").setValue([ur.left + ur.width / 2, ur.top + ur.height / 2]);
    var upo = url.property("Position"), uop = url.property("Opacity");
    K(upo, T + 0.9, [540, 1190], 33, 15); K(upo, T + 0.9 + F(12), [540, 1170], 85, 33);
    K(uop, T + 0.9, 0, 33, 40); K(uop, T + 0.9 + F(10), 100, 60, 33);
    }

    // grain on top
    var adj = comp.layers.addSolid([1, 1, 1], "GRAIN", W, H, 1, DUR); adj.adjustmentLayer = true;
    var nz = adj.property("ADBE Effect Parade").addProperty("ADBE Noise");
    try { nz.property(1).setValue(2.5); } catch (e) {}

    if (mixF.exists) { var mix = comp.layers.add(app.project.importFile(new ImportOptions(mixF))); mix.startTime = 0; mix.name = "MIX"; }

    // check frames
    var times = CHECK_TIMES;
    var cf = new Folder(R + CHECK_DIR); if (!cf.exists) cf.create();
    for (i = 0; i < times.length; i++) comp.saveFrameToPng(times[i], new File(cf.fsName + "/f_" + ("0" + i).slice(-2) + ".png"));

    proj.save(new File(R + SAVE_AS));
    app.endSuppressDialogs(false);
    log.push("OK layers=" + comp.numLayers + " mix=" + mixF.exists);
} catch (err) {
    log.push("ERR line " + err.line + ": " + err.toString());
}
log.join("\n");
