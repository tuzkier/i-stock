"""HookContext — normalized view of a Claude Code hook payload.

A check function receives one `HookContext` and returns a `HookResult`.
The context lazily exposes the fields checks need (file path, command,
content, agent role) and resolves the active mission / stage once so every
check shares the same answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})


@dataclass
class HookContext:
    event: str  # "PreToolUse" | "PostToolUse"
    tool_name: str
    tool_input: dict
    tool_response: dict
    cwd: Path
    raw: dict
    # Filled by dispatch after stage resolution; checks may read them.
    stage: str | None = None
    mission_id: str | None = None

    @classmethod
    def from_payload(cls, payload: dict, event: str | None = None) -> "HookContext":
        if not isinstance(payload, dict):
            payload = {}
        tool_input = payload.get("tool_input")
        tool_response = payload.get("tool_response")
        cwd_raw = payload.get("cwd")
        cwd = Path(cwd_raw) if isinstance(cwd_raw, str) and cwd_raw else Path.cwd()
        return cls(
            event=event or payload.get("hook_event_name") or "",
            tool_name=payload.get("tool_name") or "",
            tool_input=tool_input if isinstance(tool_input, dict) else {},
            tool_response=tool_response if isinstance(tool_response, dict) else {},
            cwd=cwd,
            raw=payload,
        )

    # --- tool payload accessors -------------------------------------------
    @property
    def is_write_tool(self) -> bool:
        return self.tool_name in WRITE_TOOLS

    @property
    def file_path(self) -> str | None:
        for block in (self.tool_input, self.tool_response):
            for key in ("file_path", "filePath", "path", "notebook_path"):
                value = block.get(key)
                if isinstance(value, str) and value:
                    return value
        return None

    @property
    def command(self) -> str | None:
        for key in ("command", "cmd"):
            value = self.tool_input.get(key)
            if isinstance(value, str):
                return value
        return None

    @property
    def content(self) -> str:
        """Best-effort text payload of a write tool (Write content / Edit
        new_string). Empty string when not applicable."""
        parts: list[str] = []
        for key in ("content", "new_string", "newString"):
            value = self.tool_input.get(key)
            if isinstance(value, str):
                parts.append(value)
        edits = self.tool_input.get("edits")
        if isinstance(edits, list):
            for edit in edits:
                if isinstance(edit, dict) and isinstance(edit.get("new_string"), str):
                    parts.append(edit["new_string"])
        return "\n".join(parts)

    # --- path helpers ------------------------------------------------------
    @property
    def runtime_root(self) -> Path:
        return self.cwd / "harness-runtime" / "harness"

    def rel_path(self, target: str | None = None) -> str:
        """Path of `target` (default: the tool's file_path) relative to cwd,
        using forward slashes. Falls back to the raw string when outside cwd."""
        raw = target if target is not None else self.file_path
        if not raw:
            return ""
        try:
            return Path(raw).resolve().relative_to(self.cwd.resolve()).as_posix()
        except (ValueError, OSError):
            return raw.replace("\\", "/")

    # --- agent role --------------------------------------------------------
    @cached_property
    def agent_role(self) -> str:
        """Lower-cased agent / subagent role string, or '' when not present."""
        for key in ("subagent_type", "agent_name", "role"):
            value = self.raw.get(key)
            if isinstance(value, str) and value:
                return value.strip().lower()
        agent_context = self.raw.get("agent_context")
        if isinstance(agent_context, dict):
            for key in ("role", "agent_id", "subagent_type"):
                value = agent_context.get(key)
                if isinstance(value, str) and value:
                    return value.strip().lower()
        return ""
