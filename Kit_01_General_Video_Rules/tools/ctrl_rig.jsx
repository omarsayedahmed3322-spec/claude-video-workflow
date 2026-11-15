// ctrl_rig.jsx — keep the user's hand tweaks when a build script deletes and rebuilds a comp.
// Every scene comp gets one null "CTRL" with Expression Controls (sliders / points / checkboxes) for the values the
// user usually nudges (delays, offsets, sizes). Layers read them through expressions, so a slider change shows at once,
// and a rebuild reads the old CTRL values first and puts them back.
// Paste into a build script (inside the try block) — runner jobs don't support #include.
//
//   var saved = ctrlRead("SC01_Hook");          // BEFORE deleting the old comp ({} if it doesn't exist yet)
//   ... delete + rebuild comp ...
//   var K = ctrlLayer(comp);
//   ctrlDelay(title.transform.position, ctrlSlider(K, "Title delay (f)", 0, saved));
//   ctrlOffset(title.transform.position, ctrlPoint(K, "Title offset", [0, 0], saved));
//   ctrlScale(logo.transform.scale, ctrlSlider(K, "Logo size %", 100, saved));
//   ctrlReport(saved);                          // logs which values came back from the old comp
// Names are the contract: keep them identical between builds (English, unique per comp).

var CTRL_NAME = "CTRL";
var CTRL_KIND = { "ADBE Slider Control": 1, "ADBE Point Control": 1, "ADBE Checkbox Control": 1, "ADBE Angle Control": 1, "ADBE Color Control": 1 };

function ctrlFindComp(name) {
    for (var i = 1; i <= app.project.numItems; i++) {
        var it = app.project.item(i);
        if (it instanceof CompItem && it.name === name) return it;
    }
    return null;
}
// Values of every expression control on the old comp's CTRL layer: { "Title delay (f)": 3, ... }
function ctrlRead(compName) {
    var out = {}, c = ctrlFindComp(compName), L = null;
    if (!c) return out;
    try { L = c.layer(CTRL_NAME); } catch (e) {}
    if (!L) return out;
    var fx = L.property("ADBE Effect Parade");
    for (var i = 1; i <= fx.numProperties; i++) {
        var e = fx.property(i);
        if (CTRL_KIND[e.matchName]) out[e.name] = e.property(1).value;
    }
    return out;
}
function ctrlLayer(comp) {
    var L = null;
    try { L = comp.layer(CTRL_NAME); } catch (e) {}
    if (L) return L;
    L = comp.layers.addNull(comp.duration);
    L.name = CTRL_NAME;
    L.label = 2;              // yellow
    L.moveToBeginning();
    return L;
}
function ctrlAdd(L, matchName, name, def, saved) {
    var e = L.property("ADBE Effect Parade").addProperty(matchName);
    e.name = name;
    var v = (saved && saved.hasOwnProperty(name)) ? saved[name] : def;
    e.property(1).setValue(v);
    return e;
}
function ctrlSlider(L, name, def, saved) { return ctrlAdd(L, "ADBE Slider Control", name, def, saved); }
function ctrlPoint(L, name, def, saved) { return ctrlAdd(L, "ADBE Point Control", name, def, saved); }
function ctrlCheckbox(L, name, def, saved) { return ctrlAdd(L, "ADBE Checkbox Control", name, def ? 1 : 0, saved); }

function ctrlRef(e) { return 'thisComp.layer("' + CTRL_NAME + '").effect("' + e.name + '")(1)'; }
// Expressions stack: the last line of an expression is its value, so it becomes "var cN = <last line>;" and the
// new helper works on cN. Hand-written expressions on the same property must follow that shape too.
function ctrlWrap(prop, fn) {
    var base = "value", head = "";
    if (prop.expression) {
        var lines = prop.expression.replace(/;\s*$/, "").split("\n");
        var n = (prop.expression.match(/var c\d+ =/g) || []).length;
        base = "c" + n;
        head = lines.slice(0, -1).join("\n") + (lines.length > 1 ? "\n" : "") + "var " + base + " = " + lines[lines.length - 1] + ";\n";
    }
    prop.expression = head + fn(base);
}
// Shift the property's keyframes later by N frames (negative = earlier). Call it first, before the other helpers.
function ctrlDelay(prop, e) {
    if (prop.expression) throw new Error("ctrlDelay must be the first expression on " + prop.name);
    prop.expression = "valueAtTime(time - " + ctrlRef(e) + " * thisComp.frameDuration)";
}
function ctrlOffset(prop, e) { ctrlWrap(prop, function (b) { return b + " + (" + b + ".length > 2 ? " + ctrlRef(e) + ".concat([0]) : " + ctrlRef(e) + ")"; }); }
function ctrlScale(prop, e) { ctrlWrap(prop, function (b) { return b + " * (" + ctrlRef(e) + " / 100)"; }); }
function ctrlAdd1D(prop, e) { ctrlWrap(prop, function (b) { return b + " + " + ctrlRef(e); }); }

function ctrlReport(saved) {
    var n = 0, s = [];
    // AE overloads + for arrays (vector math): "txt" + [0,-100] throws, so join arrays explicitly
    for (var k in saved) if (saved.hasOwnProperty(k)) { n++; s.push(k + "=" + (saved[k] instanceof Array ? "[" + saved[k].join(",") + "]" : String(saved[k]))); }
    var line = n ? "CTRL restored " + n + ": " + s.join(", ") : "CTRL: first build (no saved values)";
    if (typeof clog === "function") clog(line);
    return line;
}
