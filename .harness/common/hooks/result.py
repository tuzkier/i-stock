"""Hook check result type."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HookResult:
    """Outcome of a single hook check.

    decision:
      allow  — let the tool call proceed
      block  — PreToolUse: deny the tool call (dispatch exits 2);
               PostToolUse: feed `message` back to the model (cannot undo
               the call, but surfaces the error signal).
    note: a non-empty `message` carried on an allow result is printed to
          stderr as an advisory without blocking.
    """

    decision: str
    message: str = ""

    @classmethod
    def ok(cls) -> "HookResult":
        return cls("allow")

    @classmethod
    def advise(cls, message: str) -> "HookResult":
        return cls("allow", message)

    @classmethod
    def block(cls, message: str) -> "HookResult":
        return cls("block", message)

    @property
    def is_block(self) -> bool:
        return self.decision == "block"


ALLOW = HookResult("allow")
