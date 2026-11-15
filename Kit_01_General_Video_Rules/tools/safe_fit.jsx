// GENERIC COPY from the AG1 reel: edit SCR, CONTENT_COMPS, FRAMES and S/PX/PY for the new project.
// 17_safe_fit.jsx — fit every scene's CONTENT into the real Reels safe zone (user map 2026-11-02) WITHOUT rebuilding any scene:
// in each content comp a 3D null "SAFE_Fit" (identity when created, so parenting changes nothing) becomes the parent of every
// top-level content layer; then the null scales 90.8% and shifts left/down. Backgrounds and full-bleed decor stay untouched.
// Safe zone: y 250–1500; x 70–1025 above y≈860, x 70–887 below (Reels action buttons). Content box 90–990 × 220–1520 maps to 70–887 × 285–1465.
// Idempotent: re-running only re-applies the null's transform. Keeps the user's manual SC01/SC02 edits (Rule 08: nothing is rebuilt).
var SCR = "D:/AI/Claude/edit project/_build/";
var log = [];
var resultFile = new File(SCR + "17_safe_fit_result.txt");
var S = 88.5, PX = 470, PY = 957;   // v2: 88.5% leaves room for the (now bounded) camera drift push of ≤3%
// v2: the drift null pushed Z forever (time*35 -> +12% zoom by 4.6s, content crossed the edges again) -> bounded push, still never stops (Law A)
var DRIFT_EXPR = "var driftSpeed = 35;\nvalue + [Math.sin(time * 1.2) * 8, Math.cos(time * 0.9) * 8, driftSpeed * 0.6 * (1 - Math.cos(time * 0.8))];";
var CONTENT_COMPS = ["SC01_Hook", "SC02_Identity", "SC03_P1_Pain", "SC03_P2_Goal", "SC04_P1_Understand", "SC04_P2_Build", "SC05_Campaigns",
    "SC06_P1_Attention", "SC06_P2_Convince", "SC06_P3_Contact", "SC07_P1_Message", "SC07_P2_Design", "SC07_P3_Campaign", "SC08_P1_Ready", "SC08_P2_CTA"];
var SKIP_PREFIX = /^(BG_|FX_|Cam_|Scene_Camera|VO_Ref|PLANE_|BAR_|SAFE_Fit)/;
var FRAMES = [0.5, 1.5, 2.2, 3.5, 5.0, 6.0, 7.5, 9.5, 12.5, 13.6, 15.5, 17.0, 18.5, 20.4, 22.0, 23.2, 25.5, 27.2, 28.2, 30.6, 32.9, 36.5, 38.8];

function fullBleed(l) {
    try {
        if (l.source instanceof FootageItem && l.source.mainSource instanceof SolidSource) return l.source.width >= 1000;
        if (l instanceof ShapeLayer) {
            var t = Math.max(l.inPoint, Math.min(l.outPoint - 0.04, l.inPoint + 1.5));
            return l.sourceRectAtTime(t, false).width >= 1000;
        }
    } catch (e) {}
    return false;
}

app.beginUndoGroup("Claude_Safe_Fit");
try {
    var proj = app.project, comps = {}, master = null;
    for (var i = 1; i <= proj.numItems; i++) {
        var it = proj.item(i);
        if (it instanceof CompItem) { comps[it.name] = it; if (it.name === "00_Master_Reel") master = it; }
    }
    var drifts = 0;
    for (var dn in comps) {
        var dc = comps[dn];
        for (var dl = 1; dl <= dc.numLayers; dl++) {
            if (dc.layer(dl).name === "Cam_Drift_Null") { dc.layer(dl).transform.position.expression = DRIFT_EXPR; drifts++; }
        }
    }
    log.push("Drift nulls bounded: " + drifts);
    for (var c = 0; c < CONTENT_COMPS.length; c++) {
        var comp = comps[CONTENT_COMPS[c]];
        if (!comp) { log.push("MISSING comp " + CONTENT_COMPS[c]); continue; }
        var nul = null;
        for (var k = 1; k <= comp.numLayers; k++) if (comp.layer(k).name === "SAFE_Fit") nul = comp.layer(k);
        if (!nul) {
            nul = comp.layers.addNull(comp.duration);
            nul.name = "SAFE_Fit";
            nul.threeDLayer = true;
            nul.transform.anchorPoint.setValue([540, 960, 0]);
            nul.transform.position.setValue([540, 960, 0]);      // identity -> parenting below moves nothing
            var took = [], kept = [];
            for (var j = 1; j <= comp.numLayers; j++) {
                var L = comp.layer(j);
                if (L === nul || L.parent) continue;
                if (L instanceof CameraLayer || L instanceof LightLayer || L.adjustmentLayer || L.guideLayer ||
                    SKIP_PREFIX.test(L.name) || fullBleed(L)) { kept.push(L.name); continue; }
                L.parent = nul;
                took.push(L.name);
            }
            log.push(comp.name + ": fit " + took.length + " [" + took.join(", ") + "] | kept " + kept.length + " [" + kept.join(", ") + "]");
        } else {
            log.push(comp.name + ": SAFE_Fit already there (transform re-applied)");
        }
        nul.transform.position.setValue([PX, PY, 0]);
        nul.transform.scale.setValue([S, S, S]);
    }
    // check frames from the master (sheet + safe-zone overlay is drawn outside AE)
    for (var f = 0; f < FRAMES.length; f++) {
        var png = new File(SCR + "safe_" + ("0" + FRAMES[f].toFixed(1)).slice(-4).replace(".", "_") + ".png");
        if (png.exists) png.remove();
        master.saveFrameToPng(FRAMES[f], png);
    }
    log.push("OK");
} catch (err) {
    log.push("Error: " + err.toString() + " at line " + err.line);
} finally {
    app.endUndoGroup();
    resultFile.encoding = "UTF-8"; resultFile.open("w"); resultFile.write(log.join("\n")); resultFile.close();
}
