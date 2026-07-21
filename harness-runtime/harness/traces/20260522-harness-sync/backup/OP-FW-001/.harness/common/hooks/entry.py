"""HookEntry — one registered check in the dispatch registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from context import HookContext
from result import HookResult

Check = Callable[[HookContext], HookResult]

# Common tool sets for entry declarations.
WRITE = frozenset({"Write", "Edit", "MultiEdit"})
WRITE_NB = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})
BASH = frozenset({"Bash"})
TASK = frozenset({"Task"})
READ = frozenset({"Read"})


@dataclass(frozen=True)
class HookEntry:
    """A single check bound to an event and a set of tools.

    id     — stable identifier (kept aligned with the legacy hook id)
    event  — "PreToolUse" | "PostToolUse"
    check  — callable(HookContext) -> HookResult
    tools  — tool names this check applies to; empty frozenset = any tool
    """

    id: str
    event: str
    check: Check
    tools: frozenset = field(default_factory=frozenset)

    def matches(self, ctx: HookContext) -> bool:
        if self.event != ctx.event:
            return False
        if self.tools and ctx.tool_name not in self.tools:
            return False
        return True
