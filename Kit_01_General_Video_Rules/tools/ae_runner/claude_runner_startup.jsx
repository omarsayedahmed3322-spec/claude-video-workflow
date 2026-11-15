// claude_runner_startup.jsx — copied into AE's Scripts\Startup by install_ae_runner.ps1; starts the runner on every launch.
// __CORE__ is replaced with the kit path, so edits to the core apply on the next AE launch without reinstalling.
(function () {
    var core = new File("__CORE__");
    if (core.exists) $.evalFile(core);
})();
