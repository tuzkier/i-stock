"""Agent role classification for reviewer / worker / data-producer hooks."""

from __future__ import annotations

_REVIEWER_SUFFIXES = ("-reviewer", "-effectiveness-reviewer")


def normalize(role: str | None) -> str:
    return (role or "").strip().lower()


def is_reviewer(role: str | None) -> bool:
    r = normalize(role)
    return bool(r) and r.endswith(_REVIEWER_SUFFIXES)


def is_worker(role: str | None) -> bool:
    """A non-reviewer named agent role (engineer / designer / analyst / etc.).
    Empty role is treated as the main agent, not a worker turn."""
    r = normalize(role)
    return bool(r) and not is_reviewer(r)
