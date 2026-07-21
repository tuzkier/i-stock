"""harness CLI command parsing + dangerous git command detection.

Centralizes the flag regexes that were duplicated across ~25 legacy hook
scripts (each with a slightly different `--mission` pattern). All parsing is
tolerant: a missing flag returns None.
"""

from __future__ import annotations

import re

# --- harness command flag extraction --------------------------------------
_MISSION_RE = re.compile(r"--mission[=\s]+([^\s'\"]+)")
_STAGE_RE = re.compile(r"--stage[=\s]+([^\s'\"]+)")
_STATUS_RE = re.compile(r"--status[=\s]+([^\s'\"]+)")
_MODE_RE = re.compile(r"--mode[=\s]+([^\s'\"]+)")

_ADVANCE_RE = re.compile(r"\bharness\s+(?:gate|contract)\s+advance\b")
_STAGE_COMPLETE_RE = re.compile(r"\bharness\s+mission\s+stage\s+complete\b")
_STAGE_START_RE = re.compile(r"\bharness\s+mission\s+stage\s+start\b")
_MISSION_CLOSE_RE = re.compile(r"\bharness\s+mission\s+close\b")
_GATE_RUN_RE = re.compile(r"\bharness\s+(?:\S+\s+)?gate\s+run\b")


def _grp(regex: re.Pattern, command: str) -> str | None:
    if not command:
        return None
    m = regex.search(command)
    return m.group(1) if m else None


def mission_id(command: str | None) -> str | None:
    return _grp(_MISSION_RE, command or "")


def stage(command: str | None) -> str | None:
    return _grp(_STAGE_RE, command or "")


def status(command: str | None) -> str | None:
    return _grp(_STATUS_RE, command or "")


def mode(command: str | None) -> str | None:
    return _grp(_MODE_RE, command or "")


def is_advance(command: str | None) -> bool:
    return bool(command) and bool(_ADVANCE_RE.search(command))


def is_stage_complete(command: str | None, expect_stage: str | None = None) -> bool:
    if not command or not _STAGE_COMPLETE_RE.search(command):
        return False
    if expect_stage is None:
        return True
    # `harness mission stage complete <stage>` — stage is a positional token.
    return bool(re.search(rf"\bcomplete\s+{re.escape(expect_stage)}\b", command))


def is_stage_start(command: str | None) -> bool:
    return bool(command) and bool(_STAGE_START_RE.search(command))


def is_mission_close(command: str | None) -> bool:
    return bool(command) and bool(_MISSION_CLOSE_RE.search(command))


def is_gate_run(command: str | None) -> bool:
    return bool(command) and bool(_GATE_RUN_RE.search(command))


# --- dangerous git detection ----------------------------------------------
# kind -> regex. Granular so each stage can pick its own policy.
_GIT_DANGER = {
    "force-push": re.compile(r"\bgit\s+push\b.*(?:--force\b|--force-with-lease\b|\s-f\b)"),
    "any-push": re.compile(r"\bgit\s+push\b"),
    "hard-reset": re.compile(r"\bgit\s+reset\b.*--hard\b"),
    "branch-delete": re.compile(r"\bgit\s+branch\b.*\s-D\b"),
    "clean-force": re.compile(r"\bgit\s+clean\b.*\s-[a-z]*f"),
    "checkout-discard": re.compile(r"\bgit\s+checkout\b\s+--\s"),
    "restore-discard": re.compile(r"\bgit\s+restore\b\s+\."),
    "worktree-remove": re.compile(r"\bgit\s+worktree\s+remove\b"),
}


def git_danger(command: str | None, kinds=None) -> str | None:
    """Return the first dangerous-git kind matched in `command`, or None.

    `kinds` restricts which categories to test (default: all). Pass an
    ordered iterable when more specific kinds should win over generic ones.
    """
    if not command:
        return None
    for kind in (kinds or _GIT_DANGER.keys()):
        regex = _GIT_DANGER.get(kind)
        if regex is not None and regex.search(command):
            return kind
    return None
