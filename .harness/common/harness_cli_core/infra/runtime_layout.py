from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_cli_core.app.output import finding
from harness_cli_core.infra.runtime_paths import resolve_path


DEFAULT_COMMON_ROOT = Path(__file__).resolve().parents[2]


def control_common_root(root: Path, *, common_root: Path = DEFAULT_COMMON_ROOT) -> Path:
    for path in (root / ".harness" / "common", root / "package" / "common"):
        if path.exists():
            return path.resolve()
    return common_root.resolve()


def explicit_runtime_config_path(runtime_root: Path) -> Path:
    if runtime_root.name == "harness" and runtime_root.parent.name == "harness-runtime":
        return runtime_root.parent / "config" / "harness.yaml"
    if runtime_root.name == "harness-runtime":
        return runtime_root / "config" / "harness.yaml"
    return runtime_root.parent / "config" / "harness.yaml"


def resolve_runtime_layout(
    root: Path | str,
    explicit_runtime: str | None = None,
    *,
    common_root: Path = DEFAULT_COMMON_ROOT,
) -> dict[str, Any]:
    project_root = Path(root).expanduser().resolve()
    installed_runtime = project_root / "harness-runtime" / "harness"
    source_runtime = project_root / "package" / "harness-runtime" / "harness"
    checked_paths = [str(installed_runtime), str(source_runtime)]
    warnings: list[dict[str, Any]] = []
    is_harness_source_repo = (
        (project_root / "install.py").exists()
        and (project_root / "package" / "common").exists()
        and (project_root / "package" / "harness-runtime").exists()
    )

    if explicit_runtime:
        runtime_root = resolve_path(project_root, explicit_runtime) or Path(explicit_runtime).expanduser()
        runtime_root = runtime_root.resolve()
        config_path = explicit_runtime_config_path(runtime_root).resolve()
        if not runtime_root.exists():
            warnings.append(finding(
                "WARN",
                "explicit_runtime_missing",
                f"explicit runtime root does not exist: {runtime_root}",
                source="runtime_layout",
                checked_paths=[str(runtime_root)],
                follow_up="Verify --runtime-root or initialize Harness runtime.",
            ))
        return {
            "mode": "explicit_runtime",
            "project_root": str(project_root),
            "common_root": str(control_common_root(project_root, common_root=common_root)),
            "runtime_root": str(runtime_root),
            "config_path": str(config_path),
            "fallback_used": bool(warnings),
            "warnings": warnings,
            "checked_paths": [str(runtime_root)],
        }

    installed_exists = installed_runtime.exists()
    source_exists = source_runtime.exists()
    if installed_exists:
        mode = "self_hosted_source_repo" if source_exists and is_harness_source_repo else "installed_project"
        runtime_root = installed_runtime.resolve()
        config_path = (project_root / "harness-runtime" / "config" / "harness.yaml").resolve()
        if source_exists and not is_harness_source_repo:
            warnings.append(finding(
                "WARN",
                "multiple_runtime_roots_detected",
                "Both installed-project and source-repo runtime roots exist; installed-project runtime was selected.",
                source="runtime_layout",
                checked_paths=checked_paths,
                follow_up="Pass --runtime-root when a command must target the source template runtime explicitly.",
            ))
    elif source_exists:
        mode = "source_repo_template"
        runtime_root = source_runtime.resolve()
        config_path = (project_root / "package" / "harness-runtime" / "config" / "harness.yaml").resolve()
    else:
        mode = "installed_project"
        runtime_root = installed_runtime.resolve()
        config_path = (project_root / "harness-runtime" / "config" / "harness.yaml").resolve()
        warnings.append(finding(
            "WARN",
            "runtime_root_missing",
            "No Harness runtime root was found; default installed-project path was reported for initialization.",
            source="runtime_layout",
            checked_paths=checked_paths,
            follow_up="Run 'harness mission init' or pass --runtime-root if the runtime lives elsewhere.",
        ))

    return {
        "mode": mode,
        "project_root": str(project_root),
        "common_root": str(control_common_root(project_root, common_root=common_root)),
        "runtime_root": str(runtime_root),
        "config_path": str(config_path),
        "fallback_used": bool(warnings),
        "warnings": warnings,
        "checked_paths": checked_paths,
    }


def control_runtime_root(layout: dict[str, Any]) -> Path:
    return Path(str(layout.get("runtime_root") or ""))


def control_status_path(layout: dict[str, Any]) -> Path:
    return control_runtime_root(layout) / "mission-status.yaml"


def control_graph_root(layout: dict[str, Any]) -> Path:
    return control_runtime_root(layout) / "work-graph"
"""Infrastructure helpers for filesystem, process, runtime paths, and clocks."""
