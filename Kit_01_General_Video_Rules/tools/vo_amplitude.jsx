// vo_amplitude.jsx — read-only: per-frame VO amplitude for a time range (master seconds). Temp comp is deleted after.
// Edit the 5 constants, run via AfterFX.exe -r, read the result txt: "time<TAB>amplitude". Silence ≈ < 1–2.
var VO_NAME = "vo.mp3";
var MASTER = "00_Master_Reel";
var T0 = 0, T1 = 3;          // range to measure (s)
var FPS = 30;
var resultFile = new File("D:/AI/Claude/<project>/_build/vo_result.txt");

var out = [], tmp = null;
app.beginUndoGroup("Claude_VO_Analysis");
try {
    var vo = null;
    for (var i = 1; i <= app.project.numItems; i++) {
        var it = app.project.item(i);
        if (it.name === VO_NAME && it instanceof FootageItem) vo = it;
    }
    if (!vo) throw new Error(VO_NAME + " not in project");
    tmp = app.project.items.addComp("_tmp_vo_analysis", 100, 100, 1, T1 - T0 + 0.5, FPS);
    var l = tmp.layers.add(vo);
    l.startTime = -T0;
    tmp.openInViewer();
    for (var k = 1; k <= tmp.numLayers; k++) tmp.layer(k).selected = false;
    l.selected = true;
    app.executeCommand(app.findMenuCommandId("Convert Audio to Keyframes"));
    var amp = tmp.layer("Audio Amplitude").effect("Both Channels")("Slider");
    for (var f = 0; f <= Math.round((T1 - T0) * FPS); f++) {
        var t = f / FPS;
        out.push((T0 + t).toFixed(3) + "\t" + amp.valueAtTime(t, false).toFixed(2));
    }
} catch (err) {
    out.push("Error: " + err.toString() + " at line " + err.line);
} finally {
    if (tmp) tmp.remove();
    app.endUndoGroup();
    for (var j = 1; j <= app.project.numItems; j++) if (app.project.item(j).name === MASTER) app.project.item(j).openInViewer();
    resultFile.encoding = "UTF-8"; resultFile.open("w"); resultFile.write(out.join("\n")); resultFile.close();
}
