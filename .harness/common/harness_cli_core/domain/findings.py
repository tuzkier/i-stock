"""Shared finding-shape helpers.

Lives at the domain layer so any handler that emits ``status / findings``
payloads can stay free of inline boilerplate.
"""

from __future__ import annotations

import argparse
from typing import Any


def finding(level: str, code: str, message: str, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"level": level, "code": code, "message": message}
    item.update(extra)
    return item


def strict_status(findings: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Strict ``PASS`` / ``FAIL`` aggregation: any FAIL → FAIL."""
    failed = [f for f in findings if f.get("level") == "FAIL"]
    return ("FAIL" if failed else "PASS"), failed


def is_placeholder_text(value: Any) -> bool:
    """Detect template / TODO / N/A placeholder values that should be treated
    as "unset" when scanning contracts."""
    text = str(value or "").strip()
    if not text:
        return True
    lowered = text.lower()
    return (
        "{{" in text
        or lowered in {"n/a", "na", "none", "null", "tbd", "todo", "-", "不适用", "无"}
    )


def apply_compat_warning(
    args: argparse.Namespace, findings: list[dict[str, Any]]
) -> tuple[str, list[dict[str, Any]]]:
    """When ``--compat`` is set, downgrade FAIL findings to WARN and never
    surface them in ``failed_checks``. Returns ``(status, failed_checks)``.
    """
    if getattr(args, "compat", False):
        for item in findings:
            if item.get("level") == "FAIL":
                item["level"] = "WARN"
                item["compat_downgraded"] = True
        return ("WARN" if findings else "PASS"), []
    failed = [f for f in findings if f.get("level") == "FAIL"]
    return ("FAIL" if failed else "PASS"), failed
