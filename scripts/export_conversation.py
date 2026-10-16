#!/usr/bin/env python3
"""Exports the conversation transcript to clean, readable Markdown and JSON formats."""

import json
from pathlib import Path
import re
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
TRANSCRIPT_PATH = Path("/Users/shashwath/.gemini/antigravity-cli/brain/a6af1bbe-c9de-415f-b60b-cf2562665924/.system_generated/logs/transcript_full.jsonl")
OUT_MD = ROOT_DIR / "CONVERSATION_EXPORT.md"
OUT_JSON = ROOT_DIR / "CONVERSATION_EXPORT.json"
ARTIFACT_MD = Path("/Users/shashwath/.gemini/antigravity-cli/brain/a6af1bbe-c9de-415f-b60b-cf2562665924/CONVERSATION_EXPORT.md")


def clean_user_text(raw: str) -> str:
    """Strips system wrapper tags like <USER_REQUEST> and <ADDITIONAL_METADATA>."""
    if not raw:
        return ""
    # Extract inside <USER_REQUEST> if present
    m = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Otherwise strip metadata
    raw = re.sub(r"<ADDITIONAL_METADATA>.*?</ADDITIONAL_METADATA>", "", raw, flags=re.DOTALL)
    return raw.strip()


def export_conversation():
    if not TRANSCRIPT_PATH.exists():
        print(f"Error: {TRANSCRIPT_PATH} not found")
        sys.exit(1)

    turns = []
    current_turn = {"user": None, "assistant": [], "tools": [], "timestamp": None}

    with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            t_type = entry.get("type")
            source = entry.get("source")
            content = entry.get("content", "")
            created_at = entry.get("created_at")

            if t_type == "USER_INPUT" and source == "USER_EXPLICIT":
                clean_text = clean_user_text(content)
                if clean_text:
                    if current_turn["user"] is not None:
                        turns.append(current_turn)
                    current_turn = {
                        "user": clean_text,
                        "assistant": [],
                        "tools": [],
                        "timestamp": created_at,
                    }
            elif t_type == "PLANNER_RESPONSE" and source == "MODEL":
                if content:
                    current_turn["assistant"].append(content.strip())
                # Collect tool calls if present
                for tc in entry.get("tool_calls", []):
                    current_turn["tools"].append({
                        "name": tc.get("name"),
                        "summary": tc.get("summary") or tc.get("arguments", {}).get("toolSummary", ""),
                        "action": tc.get("action") or tc.get("arguments", {}).get("toolAction", ""),
                    })

    if current_turn["user"] is not None:
        turns.append(current_turn)

    # 1. Generate Markdown export
    md_lines = [
        "# Antigravity Pair-Programming Conversation Export",
        "",
        f"- **Conversation ID**: `a6af1bbe-c9de-415f-b60b-cf2562665924`",
        f"- **Workspace**: `/Users/shashwath/Desktop/Effect of Drugs on Neurological Activity`",
        f"- **Total Interaction Turns**: {len(turns)}",
        f"- **Export Date**: {turns[-1]['timestamp'] if turns else 'N/A'}",
        "",
        "---",
        "",
    ]

    for idx, t in enumerate(turns, 1):
        md_lines.append(f"## Turn {idx}: User Request ({t['timestamp']})")
        md_lines.append("")
        md_lines.append(f"> **User**: {t['user']}")
        md_lines.append("")

        if t["tools"]:
            unique_tools = []
            seen = set()
            for tool in t["tools"]:
                desc = tool["summary"] or tool["name"]
                if desc and desc not in seen:
                    seen.add(desc)
                    unique_tools.append(desc)
            if unique_tools:
                md_lines.append(f"*Key Actions Performed*: {', '.join(unique_tools[:6])}")
                md_lines.append("")

        if t["assistant"]:
            md_lines.append("### Assistant Response")
            md_lines.append("")
            # Join assistant parts
            full_assistant = "\n\n".join(t["assistant"])
            md_lines.append(full_assistant)
            md_lines.append("")

        md_lines.append("---")
        md_lines.append("")

    full_md = "\n".join(md_lines)
    OUT_MD.write_text(full_md, encoding="utf-8")
    ARTIFACT_MD.write_text(full_md, encoding="utf-8")
    print(f"Wrote Markdown export to: {OUT_MD}")
    print(f"Wrote Markdown export to: {ARTIFACT_MD}")

    # 2. Generate JSON export
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(turns, f, indent=2)
    print(f"Wrote JSON export to: {OUT_JSON}")


if __name__ == "__main__":
    export_conversation()
