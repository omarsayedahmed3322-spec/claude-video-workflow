// render_mp4_with_audio.jsx — render one or more ranges of the master to MP4 WITH the VO, plus optional RQ TIFF QA frames.
// One rq.render() for everything. AE 2026: "Output Audio":"On" (numeric 1 == Off); no PNG template -> TIFF for stills.
var SCR = "D:/AI/Claude/<project>/_build/";
var OUT_DIR = "D:/AI/Claude/<project>/Previews/";
var MASTER = "00_Master_Reel", VO_LAYER = "VO";
var JOBS = [ { start: 0, end: 2.6, name: "SC01_preview" } ];   // add { start: 0, end: -1, name: "00_Master_full" } for the whole comp
var QA = { from: 0, to: 0, step: 9 };                          // frames; set to:0 to skip TIFF QA
var log = [];
var resultFile = new File(SCR + "render_result.txt");
try {
    var master = null;
    for (var i = 1; i <= app.project.numItems; i++) {
        var it = app.project.item(i);
        if (it instanceof CompItem && it.name === MASTER) master = it;
    }
    if (!master) throw new Error(MASTER + " not found");
    var vo = master.layer(VO_LAYER);
    if (vo) { vo.audioEnabled = true; log.push("VO hasAudio=" + vo.hasAudio); }
    new Folder(OUT_DIR).create();
    var rq = app.project.renderQueue;
    for (var q = rq.numItems; q >= 1; q--) if (rq.item(q).comp === master) rq.item(q).remove();
    function tpl(om, re) {
        var n = om.templates;
        for (var t = 0; t < n.length; t++) if (re.test(n[t])) return n[t];
        throw new Error("No template " + re + ". Have: " + n.join(", "));
    }
    var files = [];
    for (var j = 0; j < JOBS.length; j++) {
        var J = JOBS[j], end = J.end < 0 ? master.duration : J.end;
        var r = rq.items.add(master);
        r.timeSpanStart = J.start; r.timeSpanDuration = end - J.start;
        var om = r.outputModule(1);
        om.applyTemplate(tpl(om, /^H\.264/i));
        om.setSettings({ "Output Audio": "On" });
        log.push(J.name + ": Output Audio = " + om.getSettings(GetSettingsFormat.STRING)["Output Audio"]);
        var f = new File(OUT_DIR + J.name + ".mp4");
        if (f.exists) f.remove();
        om.file = f; files.push(f);
    }
    if (QA.to > QA.from) {
        var qaDir = new Folder(SCR + "rq_qa"); qaDir.create();
        var old = qaDir.getFiles("*.tif"); for (var o = 0; o < old.length; o++) old[o].remove();
        for (var qf = QA.from; qf <= QA.to; qf += QA.step) {
            var r2 = rq.items.add(master);
            r2.timeSpanStart = qf / master.frameRate; r2.timeSpanDuration = 1 / master.frameRate;
            var om2 = r2.outputModule(1);
            om2.applyTemplate(tpl(om2, /^TIFF/i));
            om2.file = new File(qaDir.fsName + "/qa_" + ("000" + qf).slice(-4) + "_[#].tif");
        }
    }
    rq.render();
    for (var k = 0; k < files.length; k++) log.push("Rendered: " + files[k].fsName + " exists=" + files[k].exists + " size=" + files[k].length);
    for (var c = rq.numItems; c >= 1; c--) if (rq.item(c).comp === master && rq.item(c).status === RQItemStatus.DONE && rq.item(c).timeSpanDuration < 0.05) rq.item(c).remove();
    log.push("OK");
} catch (err) {
    log.push("Error: " + err.toString() + " at line " + err.line);
}
resultFile.encoding = "UTF-8"; resultFile.open("w"); resultFile.write(log.join("\n")); resultFile.close();
