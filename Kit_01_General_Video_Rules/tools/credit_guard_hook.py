"""PreToolUse hook: ask Omar before any MCP tool that spends credits.

Installed in ~/.claude/settings.json by install.py (hooks.PreToolUse, matcher on any mcp__ server whose
name contains elevenlabs, magnific or higgsfield, or whose name is a connector id).
Read-only tools (balance, model lists, search, cost lookup) pass with no question.

Connector ids (2026-11-25): the desktop app names a claude.ai connector by its id, not its name
(`mcp__<connector id>__generate_video` is Higgsfield), so a name-only match let those tools spend with no question.
  - Known ids are passed on the hook's command line in settings.json, one per service:
        credit_guard_hook.py --id <connector id>=higgsfield --id <connector id>=magnific
    They belong to this account, so they live in settings.json (per machine), not in this file. THIS-PC.md lists them.
  - A connector id that was not passed (new PC, connector added again): the hook still asks when the tool name
    clearly generates media (GENERATE_WORDS), and says the connector is not registered.

Company rule (Omar, plan phase 1, 11 Nov 2026):
  - Magnific belongs to AG1: no extra warning when the session folder is under Clients\\AG1\\.
  - Higgsfield belongs to AG2: no extra warning when the session folder is under Clients\\AG2\\.
  - Outside both: still only ASK (never deny), because the session folder is not always the work folder.
Higgsfield is a claude.ai connector (01_workflow §D); it was not loaded in the 11 Nov 2026 session,
so its tool names were not seen: like Magnific, every tool asks unless its name is a lookup.
Browser generation (Flow, Higgsfield in Chrome) and free_llm.py image are NOT covered by this hook.
"""
import json
import re
import sys

# ElevenLabs: names read from the live MCP on 11 Nov 2026. Spend = the tools whose own
# description carries "COST WARNING". Everything else on elevenlabs is read-only.
ELEVENLABS_SPEND = {
    "add_knowledge_base_to_agent", "compose_music", "create_agent", "create_voice_from_preview",
    "isolate_audio", "make_outbound_call", "simulate_conversation", "speech_to_speech",
    "speech_to_text", "text_to_sound_effects", "text_to_speech", "text_to_voice",
    "upload_music_for_inpainting", "video_to_music", "voice_clone",
}
# Magnific / Higgsfield tool names are not visible (Magnific needs sign-in, Higgsfield has no MCP),
# so for them every tool asks unless its name is clearly a lookup.
# wait/show/read/view added 2026-11-23 (CLG R7): creations_wait only polls a running job, it was asking every 30 s.
# transactions/display/quote/estimate/explore/inspect/describe added 2026-11-25 from Higgsfield's live tool list.
READ_WORDS = re.compile(r"(^|_)(get|list|search|check|balance|credits?|cost|status|models?|account|usage|history|wait|show|read|view|metadata|simulate|lineage|notifications|profile|guides?|transactions|display|quote|estimate|explore|inspect|describe)(_|$)")
# A server named by a bare connector id that no --id names: ask only for tools that clearly generate media.
UUID_SERVER = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
GENERATE_WORDS = re.compile(r"(^|_)(generate|upscale|outpaint|reframe|animate|tts|compose|execute_preset|motion_control|voice_change|voice_clone|create_voice)(_|$)")

COMPANY = {
    "elevenlabs": ("ElevenLabs", None),
    "magnific": ("Magnific", "AG1"),
    "higgsfield": ("Higgsfield", "AG2"),
}
COMPANY_NAME = {"AG1": "AG1", "AG2": "AG2"}


def connector_ids(argv):
    """--id <connector id>=<service> pairs from the command line -> {id: service}. Bad pairs are ignored."""
    ids = {}
    for i, a in enumerate(argv):
        if a == "--id" and i + 1 < len(argv) and "=" in argv[i + 1]:
            cid, _, service = argv[i + 1].partition("=")
            if cid.strip() and service.strip().lower() in COMPANY:
                ids[cid.strip().lower()] = service.strip().lower()
    return ids


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name", "")
    m = re.match(r"mcp__(.+?)__(.+)$", tool)
    if not m:
        return 0
    # Server may be "magnific" (local MCP) or "claude_ai_Higgsfield" (claude.ai connector): match by substring.
    raw, name = m.group(1).lower(), m.group(2)
    server = next((k for k in COMPANY if k in raw), None)
    if not server:
        server = next((v for k, v in connector_ids(sys.argv).items() if k in raw), None)
    low = name.lower()
    if not server:
        # Unregistered connector id: only a tool that clearly generates media asks.
        if UUID_SERVER.match(raw) and GENERATE_WORDS.search(low) and not READ_WORDS.search(low):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": f"أداة شكلها بتولّد وممكن تصرف كريدت: `{name}` على كونيكتور رقمه `{raw[:8]}` ومش متسجل في هوك الكريدت. توافق؟",
                }
            }, ensure_ascii=False))
        return 0
    if server == "elevenlabs":
        spend = name in ELEVENLABS_SPEND
    else:
        spend = not READ_WORDS.search(low)
    if not spend:
        return 0

    label, owner = COMPANY[server]
    cwd = (data.get("cwd") or "").replace("/", "\\").lower()
    reason = f"أداة بتصرف كريدت: `{name}` على اكونت {label}."
    if owner:
        inside = ("\\clients\\" + owner + "\\") in cwd + "\\"
        if inside:
            reason += f" الاكونت ده بتاع {COMPANY_NAME[owner]}، والجلسة في فولدر {COMPANY_NAME[owner]}."
        else:
            reason += f" تنبيه: الاكونت ده بتاع {COMPANY_NAME[owner]} بس، والجلسة مش في فولدر {COMPANY_NAME[owner]}."
    reason += " توافق؟"

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
