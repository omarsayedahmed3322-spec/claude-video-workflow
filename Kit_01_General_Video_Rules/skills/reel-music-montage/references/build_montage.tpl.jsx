// build_montage.tpl.jsx (skill reel-music-montage) - template; edl_montage.py fills the data line and writes the build .jsx.
// Edit shots in the .py, not here. Copied on 2026-11-13 from CLB R1 (build_CLB_R1_v14.tpl.jsx, CLB_R1_vFinal.mp4).
// Builds the master comp (1080x1920) from the graded intermediates: one layer per shot (constant speed via stretch, scale keys
// with the shot's ease), music + SFX, outro veil + logo, a marker every 4 beats. Only SETTINGS below and the lines that read
// it changed from the R1 file.
// claude-include: <Claude-Workflow>\Kit_01_General_Video_Rules\tools\ctrl_rig.jsx
// ============================ SETTINGS (CLB R1 values) ============================
var MASTER_NAME = "00_Master_CLB_R1_v14";
var GRADED_BIN = "Graded v15";                                 // project folder for the graded intermediates
var MUSIC_LABEL = "MUSIC fassounds momentum (reel beat 8 = drop @69.195s)";
var BG_RGB = [0x1B, 0x1B, 0x1B];                               // comp background (CLB charcoal)
var VEIL_RGB = [0xF9, 0xF8, 0xF4], VEIL_NAME = "VEIL ivory", VEIL_OPACITY = 88;   // CLB outro: ivory veil
var LOGO_FILE = "/assets/logo/CLB_logo_gold.png", LOGO_PX = 700, LOGO_NAME = "LOGO gold";   // relative to D.reel
// =====================================================================================
/*__DATA__*/
var FPS = D.fps, MASTER = MASTER_NAME;
function F(n) { return n / FPS; }
function say(s) { if (typeof clog === "function") clog(s); }

app.beginSuppressDialogs();
var aep = new File(D.reel + "/CLB_R1.aep");
if (!(app.project && app.project.file && app.project.file.fsName === aep.fsName)) {
    if (aep.exists) app.open(aep); else { app.newProject(); app.project.save(aep); }
}
var proj = app.project;

function findItem(name, type) {
    for (var i = 1; i <= proj.numItems; i++) { var it = proj.item(i); if (it.name === name && it instanceof type) return it; }
    return null;
}
function folder(name) { return findItem(name, FolderItem) || proj.items.addFolder(name); }
var FOLD_FOOT = folder("Footage"), FOLD_COMP = folder("Comps"), FOLD_ASSET = folder("Assets");
function importFile(path, fold) {
    var f = new File(path);
    for (var i = 1; i <= proj.numItems; i++) {
        var it = proj.item(i);
        if (it instanceof FootageItem && it.file && it.file.fsName === f.fsName) return it;
    }
    var it2 = proj.importFile(new ImportOptions(f)); it2.parentFolder = fold; return it2;
}
var FOLD_GR = folder(GRADED_BIN);

// ---------- ease helpers ----------
function easeDims(p) {
    var t = p.propertyValueType;
    if (t === PropertyValueType.ThreeD_SPATIAL || t === PropertyValueType.TwoD_SPATIAL || t === PropertyValueType.OneD) return 1;
    if (t === PropertyValueType.TwoD) return 2;
    return 3;
}
function E(p, inf) { var a = [], n = easeDims(p); for (var i = 0; i < n; i++) a.push(new KeyframeEase(0, inf)); return a; }
// two keys on prop with a named ease: push (S 60/60) | crash (accelerate into the cut) | land (fast start, settle) | snap (85/15) | lin
function key2(p, t0, v0, t1, v1, ease) {
    p.setValueAtTime(t0, v0); p.setValueAtTime(t1, v1);
    var k0 = p.nearestKeyIndex(t0), k1 = p.nearestKeyIndex(t1);
    if (ease === "lin") {
        p.setInterpolationTypeAtKey(k0, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.LINEAR);
        p.setInterpolationTypeAtKey(k1, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.LINEAR);
        return;
    }
    var o = { push: [60, 60], crash: [85, 3], land: [3, 85], snap: [85, 15] }[ease] || [60, 60];
    p.setTemporalEaseAtKey(k0, E(p, o[0]), E(p, o[0]));
    p.setTemporalEaseAtKey(k1, E(p, o[1]), E(p, o[1]));
}

// ---------- one shot = one graded layer (constant speed via stretch) ----------
function placeClip(comp, s, t0, t1) {
    var item = importFile(s.file, FOLD_GR);
    var L = comp.layers.add(item);
    L.stretch = 100 / s.spd;
    L.startTime = t0 - s.src_g * (L.stretch / 100);
    L.inPoint = t0; L.outPoint = t1;
    L.frameBlendingType = FrameBlendingType.NO_FRAME_BLEND;
    var fill = 100 * comp.width / item.width;
    var T = L.property("ADBE Transform Group");
    T.property("ADBE Anchor Point").setValue([item.width / 2, item.height / 2]);
    key2(T.property("ADBE Scale"), t0, [fill * s.s0, fill * s.s0], t1, [fill * s.s1, fill * s.s1], s.ease);
    T.property("ADBE Position").setValue([comp.width / 2 + s.x, comp.height / 2 + s.y]);
    L.motionBlur = true;
    L.name = s.clip + " | " + s.tag;
    return L;
}

try {
    var saved = ctrlRead(MASTER);
    var old = [MASTER];
    for (var oi = 0; oi < old.length; oi++) { var oc = findItem(old[oi], CompItem); if (oc) oc.remove(); }

    var comp = proj.items.addComp(MASTER, 1080, 1920, 1, F(D.comp_frames), FPS);
    comp.parentFolder = FOLD_COMP;
    comp.motionBlur = true; comp.shutterAngle = 360; comp.shutterPhase = -180;   // Omar: visible blur on the zooms
    comp.motionBlurSamplesPerFrame = 16;
    comp.bgColor = [BG_RGB[0] / 255, BG_RGB[1] / 255, BG_RGB[2] / 255];

    // music
    var mus = comp.layers.add(importFile(D.music, FOLD_ASSET));
    mus.startTime = D.music_start; mus.inPoint = 0; mus.outPoint = comp.duration;
    mus.name = MUSIC_LABEL;
    var ml = mus.property("ADBE Audio Group").property("ADBE Audio Levels");
    key2(ml, F(D.music_fade[0]), [1.5, 1.5], F(D.music_fade[1]), [-40, -40], "push");

    // sfx (peak placed on the cut)
    for (var si = 0; si < D.sfx.length; si++) {
        var fx = D.sfx[si], SL = comp.layers.add(importFile(fx.f, FOLD_ASSET));
        SL.startTime = F(fx.frame) - fx.peak;
        SL.property("ADBE Audio Group").property("ADBE Audio Levels").setValue([fx.db, fx.db]);
        SL.name = "SFX " + fx.f.split("/").pop() + " @" + fx.frame;
    }

    // shots (bottom -> top in timeline order; they don't overlap)
    for (var i = 0; i < D.shots.length; i++) {
        var s = D.shots[i];
        placeClip(comp, s, F(s.f0), F(s.f1));
    }

    // outro: ivory veil + gold logo
    var K = ctrlLayer(comp);
    var veil = comp.layers.addSolid([VEIL_RGB[0] / 255, VEIL_RGB[1] / 255, VEIL_RGB[2] / 255], VEIL_NAME, 1080, 1920, 1, comp.duration - F(D.veil[0]));
    veil.startTime = F(D.veil[0]);
    var vo = veil.property("ADBE Transform Group").property("ADBE Opacity");
    key2(vo, F(D.veil[0]), 0, F(D.veil[1]), VEIL_OPACITY, "push");
    ctrlScale(vo, ctrlSlider(K, "Veil opacity %", 100, saved));
    var logoItem = importFile(D.reel + LOGO_FILE, FOLD_ASSET);
    var LG = comp.layers.add(logoItem);
    LG.startTime = 0; LG.inPoint = F(D.logo[0]); LG.outPoint = comp.duration;
    var ls = 100 * LOGO_PX / logoItem.width;
    var LT = LG.property("ADBE Transform Group");
    // v13: the outro footage is the real L'UOMO sign -> the logo sits on it and follows it (2 measured keys), so the sign
    // under the ivory veil reads as the logo's shadow instead of a second logo
    var TR = D.logo_track;
    key2(LT.property("ADBE Position"), F(D.logo[0]), [TR[0][0], TR[0][1]], F(D.comp_frames), [TR[1][0], TR[1][1]], "lin");
    LT.property("ADBE Scale").setValueAtTime(F(D.logo[0]), [ls * TR[0][2] * 0.9, ls * TR[0][2] * 0.9]);
    LT.property("ADBE Scale").setValueAtTime(F(D.logo[1]), [ls * TR[0][2], ls * TR[0][2]]);
    LT.property("ADBE Scale").setValueAtTime(F(D.comp_frames), [ls * TR[1][2], ls * TR[1][2]]);
    key2(LT.property("ADBE Opacity"), F(D.logo[0]), 0, F(D.logo[0] + 4), 100, "snap");
    var gb = LG.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
    gb.property(3).setValue(1);
    key2(LG.property("ADBE Effect Parade").property(1).property(1), F(D.logo[0]), 30, F(D.logo[1]), 0, "snap");
    ctrlScale(LT.property("ADBE Scale"), ctrlSlider(K, "Logo size %", 100, saved));
    ctrlOffset(LT.property("ADBE Position"), ctrlPoint(K, "Logo offset", [0, 0], saved));
    LG.motionBlur = true; LG.name = LOGO_NAME;
    K.moveToBeginning();

    // bar markers
    for (var m = 0; m < D.beats.length; m += 4) {
        var mv = new MarkerValue("beat " + m);
        try { comp.markerProperty.setValueAtTime(F(D.beats[m]), mv); } catch (eM) {}
    }
    ctrlReport(saved);
    comp.openInViewer();
    proj.save(aep);
    say("built " + MASTER + " " + D.shots.length + " shots, comp " + D.comp_frames + "f");
    "OK";
} catch (err) {
    say("ERROR line " + err.line + ": " + err.toString());
    "ERROR " + err.toString();
}
