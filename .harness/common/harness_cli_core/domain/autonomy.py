from __future__ import annotations

from typing import Any


AUTONOMY_CANONICAL_LEVELS = ("快速执行", "专家确认", "受控推进")
AUTONOMY_LEGACY_ALIASES = {
    "A1": "快速执行",
    "A2": "专家确认",
    "A3": "受控推进",
    "autonomous": "快速执行",
    "autonomous_with_checkpoints": "专家确认",
    "governed_execution": "受控推进",
}


def autonomy_alias_map(config: dict[str, Any]) -> dict[str, str]:
    governance = config.get("execution_governance") if isinstance(config, dict) else None
    if isinstance(governance, dict):
        aliases = governance.get("legacy_level_aliases")
        if isinstance(aliases, dict) and aliases:
            merged: dict[str, str] = dict(AUTONOMY_LEGACY_ALIASES)
            for alias, canonical in aliases.items():
                if isinstance(alias, str) and isinstance(canonical, str):
                    merged[alias] = canonical
            return merged
    return dict(AUTONOMY_LEGACY_ALIASES)


def normalize_autonomy_level(value: Any, aliases: dict[str, str]) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if stripped in AUTONOMY_CANONICAL_LEVELS:
        return stripped
    return aliases.get(stripped)


def reject_legacy_autonomy_level(
    control: str, value: Any, aliases: dict[str, str]
) -> dict[str, Any] | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if stripped in AUTONOMY_CANONICAL_LEVELS:
        return None
    if stripped not in aliases:
        return None
    suggested = aliases[stripped]
    return {
        "status": "FAIL",
        "control": control,
        "findings": [
            {
                "level": "FAIL",
                "code": "LEGACY_LEVEL_REJECTED",
                "message": f"autonomy_level={stripped!r} is a legacy alias; use canonical value {suggested!r}",
                "suggested_value": suggested,
                "received_value": stripped,
            }
        ],
    }
