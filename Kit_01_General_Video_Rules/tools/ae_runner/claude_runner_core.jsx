// claude_runner_core.jsx — hot-folder job runner for After Effects (replaces AfterFX.exe -r and the MCP Bridge for scripts).
// Loaded by the Startup stub (runs on every AE launch) and by the docked "Claude Runner" panel. Safe to load twice.
// Queue: <Documents>\claude-ae-queue\  ·  job = <id>.jsx (UTF-8 with BOM, written by ae_run.ps1)
//   -> <id>.result.txt (STATUS / VERSION / RETURN / log)  ·  job moved to done\  ·  runner.heartbeat rewritten every tick.
// Before every job the open project is saved and a timestamped copy goes to <project folder>\_versions\
// (skip with a "// claude-no-version" line in the job's first 5 lines — read-only jobs, renders).
// Inside a job: CLAUDE_JOB.src / .dir = the original script path / folder, clog(x) = add a line to the result file.

(function () {
    var VER = "1.3";
    var G = $.global;
    if (G.CLAUDE_RUNNER && G.CLAUDE_RUNNER.version === VER && G.CLAUDE_RUNNER.taskId) return;
    if (G.CLAUDE_RUNNER && G.CLAUDE_RUNNER.taskId) { try { app.cancelTask(G.CLAUDE_RUNNER.taskId); } catch (e0) {} }

    var Q = new Folder(Folder.myDocuments.fsName + "/claude-ae-queue");
    if (!Q.exists) Q.create();
    var DONE = new Folder(Q.fsName + "/done");
    if (!DONE.exists) DONE.create();

    // Global-scope eval: job variables can't clash with the runner's own locals.
    G.claudeEval = new Function("__claudeSrc", "return eval(__claudeSrc);");
    var R = G.CLAUDE_RUNNER = { version: VER, queue: Q, paused: false, busy: false, history: [], taskId: 0, onUpdate: null };

    function pad(n, w) { var s = String(n); while (s.length < (w || 2)) s = "0" + s; return s; }
    function stamp() {
        var d = new Date();
        return d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + "_" + pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds());
    }
    function writeText(f, s) { f.encoding = "UTF-8"; f.lineFeed = "Windows"; if (f.open("w")) { f.write(s); f.close(); } }
    function readText(f) { f.encoding = "UTF-8"; if (!f.open("r")) return ""; var s = f.read(); f.close(); return s; }
    function note(s) {
        R.history.unshift(new Date().toLocaleTimeString() + "  " + s);
        if (R.history.length > 30) R.history.length = 30;
        if (R.onUpdate) { try { R.onUpdate(); } catch (e) {} }
    }

    // Save the open project, then copy it to _versions\<name>_<stamp>.aep. Returns the copy path or a reason it was skipped.
    function saveVersion(tag) {
        var pf = app.project.file;
        if (!pf) return "skipped (project never saved — no file yet)";
        app.project.save();
        var vf = new Folder(pf.parent.fsName + "/_versions");
        if (!vf.exists) vf.create();
        var base = pf.name.replace(/\.aep$/i, "");
        var dst = new File(vf.fsName + "/" + base + "_" + stamp() + "_" + tag + ".aep");
        if (!pf.copy(dst)) return "copy FAILED -> " + dst.fsName;
        var moved = 0;
        try { moved = pruneVersions(vf, base); } catch (ep) { return dst.fsName + " (prune error: " + ep.toString() + ")"; }
        return dst.fsName + (moved ? " (" + moved + " old copies -> archive)" : "");
    }

    // _versions keeps the newest KEEP copies + the newest copy of every older day; the rest MOVE (never deleted) to
    // ARCHIVE\<project name>\ — the user empties the archive. No archive drive (another PC) -> _versions\_old\.
    // ARCHIVE = <parent of Claude-Workflow>/_Archive/aep_versions: env CLAUDE_WORKFLOW (install.ps1), else 4 folders above
    // this file (<Claude-Workflow>\Kit_01_General_Video_Rules\tools\ae_runner\), else "" -> _versions\_old\.
    var KEEP = 10, ARCHIVE = (function () {
        try {
            var wf = $.getenv("CLAUDE_WORKFLOW");
            var root = wf ? new Folder(wf) : new File($.fileName).parent.parent.parent.parent;
            return root.parent.fsName.replace(/\\/g, "/") + "/_Archive/aep_versions";
        } catch (e) { return ""; }
    })();
    function pruneVersions(vf, base, archive) {
        archive = archive || ARCHIVE;
        var all = vf.getFiles("*.aep"), mine = [];
        for (var i = 0; i < all.length; i++) {
            var n = File.decode(all[i].name);
            if (n.indexOf(base + "_") === 0 && /^\d{8}_\d{6}_/.test(n.substr(base.length + 1))) mine.push(all[i]);
        }
        mine.sort(function (a, b) { return File.decode(a.name) < File.decode(b.name) ? 1 : -1; });   // newest first
        if (mine.length <= KEEP) return 0;
        var root = (archive && new Folder(archive).parent.exists) ? new Folder(archive + "/" + base) : new Folder(vf.fsName + "/_old");
        var seenDay = {}, moved = 0;
        for (var k = KEEP; k < mine.length; k++) {
            var day = File.decode(mine[k].name).substr(base.length + 1, 8);
            if (!seenDay[day]) { seenDay[day] = true; continue; }        // newest copy of that day stays
            if (!root.exists) root.create();
            var to = new File(root.fsName + "/" + File.decode(mine[k].name));
            if (mine[k].copy(to) && to.length === mine[k].length) { mine[k].remove(); moved++; }
        }
        return moved;
    }
    R.pruneVersions = pruneVersions;   // exposed for tests

    function runJob(f) {
        var id = f.name.replace(/\.jsx$/i, "");
        var running = new File(Q.fsName + "/" + id + ".running");
        if (running.exists) running.remove();
        f.rename(running.name);
        var src = readText(running).replace(/^﻿/, "");
        var head = src.split("\n").slice(0, 5).join("\n");
        var out = [], status = "OK", ret = "";
        var srcPath = (head.match(/\/\/ claude-src: (.+)/) || [0, ""])[1].replace(/\s+$/, "");
        G.CLAUDE_JOB = { id: id, src: srcPath, dir: srcPath ? new File(srcPath).parent.fsName : Q.fsName, log: [] };
        G.clog = function (x) { G.CLAUDE_JOB.log.push(String(x)); };
        note("run  " + id);
        try {
            out.push("VERSION: " + (/claude-no-version/.test(head) ? "skipped (claude-no-version)" : saveVersion(id.split("_").slice(3).join("_").substr(0, 40) || "job")));
        } catch (ev) { out.push("VERSION: error " + ev.toString()); }
        var t0 = new Date().getTime();
        app.beginUndoGroup("Claude: " + id);
        try {
            ret = G.claudeEval(src);   // text read as UTF-8 above, so Arabic literals work; #include is not supported in jobs
        } catch (err) {
            status = "ERROR";
            ret = err.toString() + (err.line ? " (line " + err.line + ")" : "");
        }
        app.endUndoGroup();
        var secs = ((new Date().getTime() - t0) / 1000).toFixed(1);
        var res = ["STATUS: " + status, "JOB: " + id, "SRC: " + srcPath, "SECONDS: " + secs].concat(out);
        res.push("RETURN: " + (ret === undefined ? "" : String(ret)));
        res.push("--- log");
        res = res.concat(G.CLAUDE_JOB.log);
        writeText(new File(Q.fsName + "/" + id + ".result.txt"), res.join("\n"));
        var dst = new File(DONE.fsName + "/" + id + ".jsx");
        if (dst.exists) dst.remove();
        running.copy(dst); running.remove();
        note(status + "  " + id + "  " + secs + "s");
    }

    G.claudeRunnerTick = function () {
        if (R.busy) return;
        R.busy = true;
        try {
            writeText(new File(Q.fsName + "/runner.heartbeat"),
                new Date().getTime() + "\n" + app.version + "\n" + (app.project.file ? app.project.file.fsName : "(unsaved)") + "\n" + (R.paused ? "paused" : "ready"));
            if (!R.paused) {
                var jobs = Q.getFiles("*.jsx");
                jobs.sort(function (a, b) { return a.name < b.name ? -1 : 1; });
                if (jobs.length) runJob(jobs[0]);
            }
        } catch (e) {
            note("runner error: " + e.toString());
        }
        R.busy = false;
    };
    R.taskId = app.scheduleTask("claudeRunnerTick()", 1000, true);
    note("Claude Runner " + VER + " watching " + Q.fsName);
})();
