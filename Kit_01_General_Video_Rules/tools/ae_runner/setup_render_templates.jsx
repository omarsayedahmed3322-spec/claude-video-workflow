// setup_render_templates.jsx — one-time job (ae_run.ps1 -NoVersion): creates the templates ae_render.ps1 uses.
//   Render Settings "Claude Preview Half"  = Draft quality, Half resolution, Motion Blur/Frame Blend off (fast review renders)
//   Render Settings "Claude Final"         = Best quality, Full resolution
//   Output Module   "Claude H264 Audio"    = H.264 with audio forced On (AE 2026: numeric 1 means Off, so use the string)
// Needs any comp: makes a temp one, removes it after.
(function () {
    var tmp = app.project.items.addComp("_claude_tpl_tmp", 1080, 1920, 1, 1, 24);
    var rq = app.project.renderQueue;
    function item() { return rq.items.add(tmp); }
    function pick(list, re) { for (var i = 0; i < list.length; i++) if (re.test(list[i])) return list[i]; throw new Error("no template " + re + " in: " + list.join(" | ")); }

    var a = item();
    a.applyTemplate(pick(a.templates, /^Draft Settings$/i));
    a.setSettings({ "Quality": "Draft", "Resolution": "Half", "Motion Blur": "Off for All Layers", "Frame Blending": "Off for All Layers" });
    a.saveAsTemplate("Claude Preview Half");
    clog("RS Claude Preview Half: " + a.getSettings(GetSettingsFormat.STRING)["Resolution"]);

    var b = item();
    b.applyTemplate(pick(b.templates, /^Best Settings$/i));
    b.saveAsTemplate("Claude Final");

    var om = b.outputModule(1);
    om.applyTemplate(pick(om.templates, /^H\.264/i));
    om.setSettings({ "Output Audio": "On" });
    clog("OM audio: " + om.getSettings(GetSettingsFormat.STRING)["Output Audio"]);
    om.saveAsTemplate("Claude H264 Audio");

    a.remove(); b.remove(); tmp.remove();
    var c = rq.items.add(app.project.items.addComp("_claude_tpl_chk", 16, 16, 1, 1, 24));
    var ok = c.templates.join("|").indexOf("Claude Preview Half") >= 0 && c.outputModule(1).templates.join("|").indexOf("Claude H264 Audio") >= 0;
    var chk = c.comp; c.remove(); chk.remove();
    return ok ? "templates ready" : "templates NOT found after save";
})();
