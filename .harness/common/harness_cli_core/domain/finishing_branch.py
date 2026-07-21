"""Pure helpers for finishing-branch stage commands."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

from harness_cli_core.infra.io import load_yaml
from harness_cli_core.infra.runtime_paths import mission_status_path, runtime_harness_root


def current_branch_for_mission(root: Path, mission: str) -> str | None:
    """Return the current git branch when it is clearly this mission branch."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:  # noqa: BLE001
        return None
    branch = result.stdout.strip()
    if result.returncode == 0 and branch and mission in branch:
        return branch
    return None


def mission_info(root: Path, mission: str) -> dict[str, Any]:
    """Load mission_branch / base_branch from mission-status.yaml.

    Falls back to ``base_branch="main"`` when not declared.
    """
    status_path = mission_status_path(root)
    status = load_yaml(status_path)
    entry = status.get(mission) if isinstance(status.get(mission), dict) else {}
    git = entry.get("git") if isinstance(entry.get("git"), dict) else {}
    mission_branch = (
        git.get("mission_branch")
        or entry.get("mission_branch")
        or current_branch_for_mission(root, mission)
    )
    return {
        "mission_branch": mission_branch,
        "base_branch": git.get("base_branch") or "main",
    }


def stage_dir(root: Path, mission: str) -> Path:
    return runtime_harness_root(root) / "stages" / mission


def load_contract(root: Path, mission: str) -> dict[str, Any]:
    """Load the finishing-branch contract if present, else ``{}``."""
    contract_path = stage_dir(root, mission) / "contracts" / "finishing-branch.contract.yaml"
    if not contract_path.exists():
        return {}
    try:
        doc = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except Exception:  # noqa: BLE001
        return {}
