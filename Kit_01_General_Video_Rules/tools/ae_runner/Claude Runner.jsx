// Claude Runner.jsx — docked status panel for the hot-folder runner (Window > Claude Runner.jsx).
// The runner itself starts from the Startup stub on every launch; this panel only shows the queue and can pause it.
// Installed by install_ae_runner.ps1, which replaces __CORE__ with the kit path of claude_runner_core.jsx.
(function (thisObj) {
    var core = new File("__CORE__");
    if (!$.global.CLAUDE_RUNNER && core.exists) $.evalFile(core);
    var R = $.global.CLAUDE_RUNNER;
    var win = (thisObj instanceof Panel) ? thisObj : new Window("palette", "Claude Runner", undefined, { resizeable: true });
    win.orientation = "column"; win.alignChildren = ["fill", "top"];
    var row = win.add("group");
    row.alignChildren = ["left", "center"];
    var pause = row.add("checkbox", undefined, "Pause");
    var state = row.add("statictext", undefined, "", { truncate: "end" });
    state.alignment = ["fill", "center"];
    state.preferredSize.width = 150;
    var hist = win.add("edittext", undefined, "", { multiline: true, readonly: true, scrolling: true });
    hist.alignment = ["fill", "fill"];
    hist.preferredSize = [200, 120];
    function refresh() {
        if (!R) { state.text = "Runner core not found: " + core.fsName; return; }
        state.text = (R.paused ? "Paused" : "Watching") + " · " + R.queue.name;
        state.helpTip = R.queue.fsName;
        pause.value = R.paused;
        hist.text = R.history.join("\n");
    }
    pause.onClick = function () { if (R) { R.paused = pause.value; refresh(); } };
    if (R) R.onUpdate = refresh;
    win.onResizing = win.onResize = function () { this.layout.resize(); };
    refresh();
    if (win instanceof Window) { win.center(); win.show(); } else { win.layout.layout(true); }
})(this);
