"""Contract YAML helpers.

All hook checks treat YAML / contract IO as fail-open: a missing file,
parse error, or absent PyYAML degrades to "no signal" rather than blocking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:  # PyYAML is expected at runtime but hooks must not hard-crash without it.
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

HAVE_YAML = yaml is not None


def load_yaml(path: Path) -> dict | None:
    """Parse a YAML file into a dict, or None on any failure."""
    if yaml is None or not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def save_yaml(path: Path, data: dict) -> bool:
    """Write a dict back to YAML. Returns False on failure (never raises)."""
    if yaml is None:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return True
    except (OSError, yaml.YAMLError):
        return False


def unwrap(data: dict | None) -> dict:
    """Return the `control_contract` body when contracts are nested, else the
    document itself. Always returns a dict."""
    if not isinstance(data, dict):
        return {}
    inner = data.get("control_contract")
    return inner if isinstance(inner, dict) else data


def load_contract(path: Path) -> dict:
    """Load a contract file and return its unwrapped control_contract body."""
    return unwrap(load_yaml(path))


def stage_contract_path(
    cwd: Path, mission_id: str, filename: str, *, base: str = "stages"
) -> Path:
    """Path to a contract under harness-runtime/harness/<base>/<id>/contracts/.

    base is "stages" for stage contracts, "missions" for the intake
    mission-contract.
    """
    return (
        cwd
        / "harness-runtime"
        / "harness"
        / base
        / mission_id
        / "contracts"
        / filename
    )


def _dig(contract: dict, dotted: str) -> Any:
    node: Any = contract
    for part in dotted.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def pending_recheck(contract_path: Path, *, field_path: str = "pending_reviewer_recheck") -> bool:
    """True when the contract carries an unresolved reviewer recheck flag.

    field_path is dotted relative to the unwrapped contract body
    (e.g. "pending_reviewer_recheck" or
    "effectiveness_review.pending_reviewer_recheck").
    """
    contract = load_contract(contract_path)
    return bool(_dig(contract, field_path))


def set_pending_recheck(
    contract_path: Path, value: bool = True, *, field_path: str = "pending_reviewer_recheck"
) -> bool:
    """Flip a pending-recheck flag on the contract YAML. Preserves the
    control_contract wrapper when present. Returns False on any failure."""
    if yaml is None or not contract_path.exists():
        return False
    raw = load_yaml(contract_path)
    if raw is None:
        return False
    body = raw.get("control_contract") if isinstance(raw.get("control_contract"), dict) else raw
    if not isinstance(body, dict):
        return False
    parts = field_path.split(".")
    node = body
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    if bool(node.get(parts[-1])) == value:
        return True  # already in desired state
    node[parts[-1]] = value
    return save_yaml(contract_path, raw)
