// ae_helpers.jsx — generic helper library extracted from the AG1 reel builds (Nov 2026).
// Paste these into a build script (inside the try block, after `comp` and `proj` exist) or #include this file.
// NOTE: cameraRig() and auditKeys() were reconstructed from the reel scripts, not copied verbatim — check them on first use.
// Expects globals: FPS, comp (current comp), C (palette of [r,g,b] 0–1), FONT_AR (default font PostScript name).

function applySmoothEase(prop, keyIndex, inInfluence, outInfluence) {
    var inEase = new KeyframeEase(0, Math.max(0.1, Math.min(100, inInfluence)));
    var outEase = new KeyframeEase(0, Math.max(0.1, Math.min(100, outInfluence)));
    var valType = prop.propertyValueType;
    if (valType === PropertyValueType.TwoD) {
        prop.setTemporalEaseAtKey(keyIndex, [inEase, inEase], [outEase, outEase]);
    } else if (valType === PropertyValueType.ThreeD) {
        prop.setTemporalEaseAtKey(keyIndex, [inEase, inEase, inEase], [outEase, outEase, outEase]);
    } else {
        prop.setTemporalEaseAtKey(keyIndex, [inEase], [outEase]);
    }
    prop.setInterpolationTypeAtKey(keyIndex, KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.BEZIER);
}
// Two-key move: both keys get the same in/out influence pair
function move(prop, t0, v0, t1, v1, inInf, outInf) {
    prop.setValueAtTime(t0, v0);
    prop.setValueAtTime(t1, v1);
    applySmoothEase(prop, prop.nearestKeyIndex(t0), inInf, outInf);
    applySmoothEase(prop, prop.nearestKeyIndex(t1), inInf, outInf);
}
function hex(h) {
    return [parseInt(h.substr(1, 2), 16) / 255, parseInt(h.substr(3, 2), 16) / 255, parseInt(h.substr(5, 2), 16) / 255];
}
function F(n) { return n / FPS; }

// Inertial bounce — icons / cards / logos only, never text
var BOUNCE = [
    "var amp = 0.05;", "var freq = 2.5;", "var decay = 5.0;", "var n = 0;",
    "if (numKeys > 0) {", "    n = nearestKey(time).index;", "    if (key(n).time > time) { n--; }", "}",
    "if (n === 0) {", "    value;", "} else {",
    "    var t = time - key(n).time;",
    "    var v = velocityAtTime(key(n).time - thisComp.frameDuration / 10);",
    "    value + v * amp * Math.sin(freq * t * 2 * Math.PI) / Math.exp(decay * t);", "}"
].join("\n");

// Bounded camera drift (never static, ≤3% push)
var DRIFT_EXPR = "var driftSpeed = 35;\nvalue + [Math.sin(time * 1.2) * 8, Math.cos(time * 0.9) * 8, driftSpeed * 0.6 * (1 - Math.cos(time * 0.8))];";

function makeText(str, size, color, name, font) {
    var l = comp.layers.addText(str);
    l.name = name;
    var p = l.property("ADBE Text Properties").property("ADBE Text Document");
    var td = p.value;
    td.resetCharStyle();
    td.resetParagraphStyle();
    td.font = font || FONT_AR;
    td.fontSize = size;
    td.applyFill = true;
    td.fillColor = color;
    td.applyStroke = false;          // Arabic never gets a stroke
    td.tracking = 0;
    td.justification = ParagraphJustification.CENTER_JUSTIFY;
    if (!font) {
        try { td.composerEngine = ComposerEngine.UNIVERSAL_TYPE_ENGINE; } catch (e1) {}
        try { td.direction = ParagraphDirection.DIRECTION_RIGHT_TO_LEFT; } catch (e2) {}
    }
    p.setValue(td);
    l.threeDLayer = true;
    l.motionBlur = true;
    return l;
}
// English display text with the thickening stroke (only thin / English display fonts)
function strokeText(l, width) {
    var p = l.property("ADBE Text Properties").property("ADBE Text Document");
    var td = p.value;
    td.applyStroke = true; td.strokeColor = td.fillColor; td.strokeWidth = width || 5; td.strokeOverFill = true;
    p.setValue(td);
}
function rectAt(l, t) { return l.sourceRectAtTime(t || 0, false); }
function place(l, x, y, t, z) {   // anchor at the ink-box centre, then position
    var r = rectAt(l, t);
    l.transform.anchorPoint.setValue([r.left + r.width / 2, r.top + r.height / 2, 0]);
    l.transform.position.setValue([x, y, z || 0]);
}
function fit(l, maxW, maxH, t) {  // scale down only
    var r = rectAt(l, t);
    var k = Math.min(1, maxW / r.width, maxH ? maxH / r.height : 1);
    l.transform.scale.setValue([100 * k, 100 * k, 100]);
    return { w: r.width * k, h: r.height * k, k: k };
}

// ---------- shapes ----------
function grp(l) { return l.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group"); }
function tf(g) { return g.property("ADBE Vector Transform Group"); }
function paint(g, fill, strokeColor, strokeW) {
    if (strokeColor) {
        var st = g.property("ADBE Vectors Group").addProperty("ADBE Vector Graphic - Stroke");
        st.property("ADBE Vector Stroke Color").setValue(strokeColor);
        st.property("ADBE Vector Stroke Width").setValue(strokeW);
        try { st.property("ADBE Vector Stroke Line Join").setValue(2); st.property("ADBE Vector Stroke Line Cap").setValue(2); } catch (eJ) {}
    }
    if (fill) g.property("ADBE Vectors Group").addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue(fill);
}
function addRect(l, w, h, color, pos, round, strokeColor, strokeW, rectPos) {
    var g = grp(l);
    var r = g.property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Rect");
    r.property("ADBE Vector Rect Size").setValue([w, h]);
    if (round) r.property("ADBE Vector Rect Roundness").setValue(round);
    if (rectPos) r.property("ADBE Vector Rect Position").setValue(rectPos);
    paint(g, color, strokeColor, strokeW);
    if (pos) tf(g).property("ADBE Vector Position").setValue(pos);
    return g;
}
function addEllipse(l, d, pos, fill, strokeColor, strokeW) {
    var g = grp(l);
    g.property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Ellipse").property("ADBE Vector Ellipse Size").setValue([d, d]);
    paint(g, fill, strokeColor, strokeW);
    if (pos) tf(g).property("ADBE Vector Position").setValue(pos);
    return g;
}
function addPath(l, pts, closed, fill, strokeColor, strokeW, pos) {
    var g = grp(l);
    var p = g.property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Group");
    var sh = new Shape();
    sh.vertices = pts;
    sh.closed = closed;
    p.property("ADBE Vector Shape").setValue(sh);
    paint(g, fill, strokeColor, strokeW);
    if (pos) tf(g).property("ADBE Vector Position").setValue(pos);
    return g;
}
function shape3D(name) {
    var l = comp.layers.addShape();
    l.name = name;
    l.threeDLayer = true;
    l.motionBlur = true;
    l.transform.anchorPoint.setValue([0, 0, 0]);
    return l;
}

// ---------- entries ----------
function addBlur(l, t0) {
    var gb = l.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
    gb.property(3).setValue(1); // Repeat Edge Pixels ON
    move(gb.property(1), t0, 45, t0 + 0.35, 0, 80, 20);
}
function blurIn(l, t0) {        // blur 45->0 + scale 85->100
    addBlur(l, t0);
    var s0 = l.transform.scale.value[0];
    move(l.transform.scale, t0, [s0 * 0.85, s0 * 0.85, 100], t0 + 0.35, [s0, s0, 100], 80, 20);
    l.inPoint = t0;
}
function dropIn(l, t0) {        // text: blur + scale + separated Y from above, no bounce
    blurIn(l, t0);
    var p = l.transform.position.value;
    l.transform.position.dimensionsSeparated = true;
    move(l.transform.yPosition, t0, p[1] - 50, t0 + 0.35, p[1], 85, 15);
}
function pop(l, t0, sc) {       // cards / icons: scale 0->sc + 12fps bounce
    sc = sc || 100;
    addBlur(l, t0);
    move(l.transform.scale, t0, [0, 0, 100], t0 + 0.35, [sc, sc, 100], 85, 15);
    l.transform.scale.expression = "posterizeTime(12);\n" + BOUNCE;
    l.inPoint = t0;
}
function shadow(l) {            // crisp card shadow 25% / dist 12 / soft 25
    var ds = l.property("ADBE Effect Parade").addProperty("ADBE Drop Shadow");
    ds.property(2).setValue(64); ds.property(3).setValue(135); ds.property(4).setValue(12); ds.property(5).setValue(25);
}

// ---------- Arabic kashida grow (1 -> 5 tatweels between joined letters) ----------
var TATWEEL = "ـ";
var K5 = "ـــــ";
function kashidaGrow(l, parts, t0, dur) {
    var q = [];
    for (var pi = 0; pi < parts.length; pi++) q.push("'" + parts[pi] + "'");
    l.property("ADBE Text Properties").property("ADBE Text Document").expression =
        "var n = Math.round(ease(time, " + t0.toFixed(4) + ", " + (t0 + (dur || 0.45)).toFixed(4) + ", 1, 5));\n" +
        "var k = '';\nfor (var i = 0; i < n; i++) k += '" + TATWEEL + "';\n" + q.join(" + k + ") + ";";
    l.motionBlur = false;   // per-frame text change + motion blur smears
}
function kText(parts, size, color, name) { return makeText(parts.join(K5), size, color, name); }

// ---------- backgrounds ----------
function makeGrid(name, color, step, opacity) {   // white grid 8% on dark beats
    var grid = comp.layers.addShape();
    grid.name = name;
    var STEP = step || 90;
    var gv = addRect(grid, 2, comp.height, color, [0, comp.height / 2]);
    var rv = gv.property("ADBE Vectors Group").addProperty("ADBE Vector Filter - Repeater");
    rv.property("ADBE Vector Repeater Copies").setValue(comp.width / STEP + 1);
    rv.property("ADBE Vector Repeater Transform").property("ADBE Vector Repeater Position").setValue([STEP, 0]);
    var gh = addRect(grid, comp.width, 2, color, [comp.width / 2, 0]);
    var rh = gh.property("ADBE Vectors Group").addProperty("ADBE Vector Filter - Repeater");
    rh.property("ADBE Vector Repeater Copies").setValue(comp.height / STEP + 1);
    rh.property("ADBE Vector Repeater Transform").property("ADBE Vector Repeater Position").setValue([0, STEP]);
    grid.transform.anchorPoint.setValue([0, 0]);
    grid.transform.position.setValue([0, 0]);
    grid.transform.opacity.setValue(opacity || 8);
    return grid;
}

// ---------- two-null camera rig ----------
function cameraRig(c) {
    var drift = c.layers.addNull(c.duration); drift.name = "Cam_Drift_Null"; drift.threeDLayer = true;
    drift.transform.position.setValue([c.width / 2, c.height / 2, 0]);
    drift.transform.position.expression = DRIFT_EXPR;
    var beat = c.layers.addNull(c.duration); beat.name = "Cam_Beat_Null"; beat.threeDLayer = true;
    beat.transform.position.setValue([c.width / 2, c.height / 2, 0]);
    beat.parent = drift;
    beat.transform.position.dimensionsSeparated = true;
    var cam = c.layers.addCamera("Scene_Camera", [c.width / 2, c.height / 2]);
    cam.autoOrient = AutoOrientType.NO_AUTO_ORIENT;
    cam.transform.position.setValue([c.width / 2, c.height / 2, -cam.cameraOption.zoom.value]);
    cam.parent = beat;
    return { drift: drift, beat: beat, cam: cam };   // key beat.transform.zPosition (88/12)
}

// ---------- audit ----------
function auditKeys(c) {
    var total = 0, linear = 0;
    function walk(g) {
        for (var i = 1; i <= g.numProperties; i++) {
            var p = g.property(i);
            if (p.propertyType === PropertyType.PROPERTY) {
                if (p.numKeys) for (var k = 1; k <= p.numKeys; k++) {
                    total++;
                    if (p.keyOutInterpolationType(k) === KeyframeInterpolationType.LINEAR) linear++;
                }
            } else walk(p);
        }
    }
    for (var l = 1; l <= c.numLayers; l++) walk(c.layer(l));
    return total + " keys, " + linear + " LINEAR";
}
