"""PreToolUse hook: ask Omar before any MCP tool that spends credits.

Installed in ~/.claude/settings.json by install.ps1 (hooks.PreToolUse, matcher on any mcp__ server whose
name contains elevenlabs, magnific or higgsfield).
Read-only tools (balance, model lists, search, cost lookup) pass with no question.

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
READ_WORDS = re.compile(r"(^|_)(get|list|search|check|balance|credits?|cost|status|models?|account|usage|history)(_|$)")

COMPANY = {
    "elevenlabs": ("ElevenLabs", None),
    "magnific": ("Magnific", "digital build"),
    "higgsfield": ("Higgsfield", "fmc"),
}
COMPANY_NAME = {"digital build": "AG1", "fmc": "AG2"}


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
        return 0
    if server == "elevenlabs":
        spend = name in ELEVENLABS_SPEND
    else:
        spend = not READ_WORDS.search(name.lower())
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
