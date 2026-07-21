#!/usr/bin/env python3
"""retrospective-improvement-plan M3.1 PreToolUse hook: deny fenced YAML
contract blocks in retrospective.md.

retrospective.md is a narrative artifact. All structured control data lives
in the external `contracts/retrospective.contract.yaml`. This hook blocks any
Write/Edit that would insert:
  - fenced YAML blocks containing contract keys
  - `## memory_update_contract`, `## execution_result`, or `## role_verdicts`
  section headings

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import sys

_RETRO_MD_MARKER = "retrospective.md"
_FORBIDDEN_SECTIONS = (
    "## memory_update_contract",
    "## execution_result",
    "## role_verdicts",
)
_FORBIDDEN_YAML_KEYS = (
    "memory_update_contract:",
    "execution_result:",
    "role_verdicts:",
    "control_contract:",
)


def _contains_forbidden_content(text: str) -> str | None:
    """Return a description of the forbidden content, or None if clean."""
    for section in _FORBIDDEN_SECTIONS:
        if section in text:
            return f"forbidden section heading {section!r}"
    in_fence = False
    fence_content: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_fence:
                # End of fence — check accumulated content.
                block = "\n".join(fence_content)
                for key in _FORBIDDEN_YAML_KEYS:
                    if key in block:
                        return f"fenced YAML block contains forbidden key {key!r}"
                fence_content = []
                in_fence = False
            else:
                lang = stripped[3:].strip().lower()
                if lang in {"yaml", "yml", ""}:
                    in_fence = True
        elif in_fence:
            fence_content.append(line)
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = payload.get("tool_name")
    if tool_name not in {"Write", "Edit", "MultiEdit"}:
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if _RETRO_MD_MARKER not in file_path:
        return 0

    # For Write: check the new_content; for Edit/MultiEdit: check new_string.
    content_to_check: list[str] = []
    if tool_name == "Write":
        content_to_check.append(str(tool_input.get("content") or ""))
    elif tool_name == "Edit":
        content_to_check.append(str(tool_input.get("new_string") or ""))
    elif tool_name == "MultiEdit":
        for edit in tool_input.get("edits") or []:
            content_to_check.append(str((edit or {}).get("new_string") or ""))

    for text in content_to_check:
        reason = _contains_forbidden_content(text)
        if reason:
            print(
                f"HarnessV2 retrospective hook BLOCKED: {reason} detected in "
                f"{file_path}. retrospective.md must not embed control YAML — "
                "write structured data to contracts/retrospective.contract.yaml "
                "via `harness contract init/patch --json`.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
