from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import load_yaml


def runtime_harness_root(root: Path) -> Path:
    """Resolve the runtime harness directory for installed and source layouts."""
    installed = root / "harness-runtime" / "harness"
    source_repo = root / "package" / "harness-runtime" / "harness"
    if installed.exists():
        return installed
    if source_repo.exists():
        return source_repo
    return installed


def mission_stage_dir(root: Path, mission: str) -> Path:
    """Return ``<runtime>/stages/<mission>`` (control-plane metadata: contracts,
    gate-reports, traces). Stage artifact content lives under the artifact store,
    see :func:`mission_artifact_dir`."""
    return runtime_harness_root(root) / "stages" / mission


def mission_artifact_dir(root: Path, mission: str) -> Path:
    """Return ``<runtime>/artifacts/<mission>`` — the canonical stage-artifact
    store. Stage content is organized as ``artifacts/<mission>/<stage>/...``
    (e.g. ``product/``, ``interaction/``). ``stages/<mission>/`` is retained only
    for control-plane metadata and legacy-compat reads."""
    return runtime_harness_root(root) / "artifacts" / mission


def read_text_if_exists(path: Path) -> str:
    """Read ``path`` as UTF-8 text, returning ``""`` when the file does not exist."""
    return path.read_text(encoding="utf-8") if path.exists() else ""


def work_graph_root(root: Path) -> Path:
    return runtime_harness_root(root) / "work-graph"


def mission_status_path(root: Path) -> Path:
    return runtime_harness_root(root) / "mission-status.yaml"


def relpath(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def resolve_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def load_runtime_config(root: Path) -> dict[str, Any]:
    for path in (
        root / "harness-runtime" / "config" / "harness.yaml",
        root / "package" / "harness-runtime" / "config" / "harness.yaml",
    ):
        config = load_yaml(path)
        if config:
            return config
    return {}
