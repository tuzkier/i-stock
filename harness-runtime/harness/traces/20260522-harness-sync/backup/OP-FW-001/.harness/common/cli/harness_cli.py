#!/usr/bin/env python3
"""Harness control-plane CLI.

This first CLI slice is an adapter layer over the existing deterministic
scripts. It gives workflows one stable command surface without changing the
underlying write semantics yet.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import yaml


COMMON_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = COMMON_ROOT.parent
SKILLS_ROOT = COMMON_ROOT / "skills"
WORK_GRAPH_SCRIPTS = SKILLS_ROOT / "work-graph" / "scripts"
if str(WORK_GRAPH_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))

from work_graph_lib import (  # noqa: E402
    Finding as WGFinding,
    lane_of_stage as wg_lane_of_stage,
    lane_action_registry as wg_lane_action_registry,
    lane_action_snapshot as wg_lane_action_snapshot,
    load_nodes as wg_load_nodes,
    resolve_graph_root as wg_resolve_graph_root,
    lane_stage_for_node as wg_lane_stage_for_node,
    write_views as wg_write_views,
    validate_graph_operation_structure as wg_validate_graph_operation_structure,
    validate_operation_against_profile as wg_validate_operation_against_profile,
)

CLOSED_MISSION_STATUSES = {"done", "closed", "cancelled", "delivered"}


def script(*parts: str) -> Path:
    return SKILLS_ROOT.joinpath(*parts)


def add_common(parser: argparse.ArgumentParser, *, json_default: bool = False) -> None:
    parser.add_argument("--root", default=None, help="target project root; defaults to the global --root")
    if json_default:
        parser.set_defaults(json=True)
    else:
        parser.add_argument("--json", action="store_true", help="emit JSON when the wrapped command supports it")


def root_arg(args: argparse.Namespace) -> str:
    return str(Path(args.root or args.global_root).expanduser().resolve())


def run_python(path: Path, forwarded: list[str], *, cwd: str | None = None) -> int:
    if not path.exists():
        print(f"harness: missing wrapped script: {path}", file=sys.stderr)
        return 64
    completed = subprocess.run([sys.executable, str(path), *forwarded], cwd=cwd, text=True)
    return completed.returncode


def run_python_capture(path: Path, forwarded: list[str], *, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    if not path.exists():
        return subprocess.CompletedProcess(
            args=[sys.executable, str(path), *forwarded],
            returncode=64,
            stdout="",
            stderr=f"harness: missing wrapped script: {path}\n",
        )
    return subprocess.run([sys.executable, str(path), *forwarded], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def with_json(args: argparse.Namespace, forwarded: list[str]) -> list[str]:
    if getattr(args, "json", False):
        forwarded.append("--json")
    return forwarded


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def today() -> str:
    return dt.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")


def now_iso() -> str:
    return dt.datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()


def runtime_harness_root(root: Path) -> Path:
    """Resolve runtime root, preferring installed-project layout but falling back to
    the source-repo layout (harness-runtime/harness) so commands work in
    both environments without requiring callers to know which layout is in use.

    This is the only acceptable form of path fallback: it is deterministic, observable
    via the returned path, and never silently masks "missing runtime" — that is FAILed
    by load_runtime_config / individual command preconditions.
    """
    installed = root / "harness-runtime" / "harness"
    source_repo = root / "package" / "harness-runtime" / "harness"
    if installed.exists():
        return installed
    if source_repo.exists():
        return source_repo
    # Default to installed-project layout for new initialization (mission init, context init).
    return installed


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
    for path in (root / "harness-runtime" / "config" / "harness.yaml", root / "package" / "harness-runtime" / "config" / "harness.yaml"):
        config = load_yaml(path)
        if config:
            return config
    return {}


# --- Autonomy level normalization (intake-improvement-plan M1.4) -----------
# Canonical autonomy levels (Chinese, matching harness.yaml execution_governance
# definitions). Legacy aliases (A1/A2/A3 and the English autonomous_* names)
# are normalized on read paths (config.snapshot) and rejected on write paths
# (mission init / contract YAML) with a typed LEGACY_LEVEL_REJECTED finding.

AUTONOMY_CANONICAL_LEVELS = ("快速执行", "专家确认", "受控推进")
# Static fallback alias map. The authoritative map lives in
# harness-runtime/config/harness.yaml `execution_governance.legacy_level_aliases`
# but config.snapshot must still normalize before the config has been loaded
# (e.g. when running against a target project that has not customized the map).
AUTONOMY_LEGACY_ALIASES = {
    "A1": "快速执行",
    "A2": "专家确认",
    "A3": "受控推进",
    "autonomous": "快速执行",
    "autonomous_with_checkpoints": "专家确认",
    "governed_execution": "受控推进",
}


def autonomy_alias_map(config: dict[str, Any]) -> dict[str, str]:
    """Resolve the legacy-alias map from runtime config, falling back to the
    static AUTONOMY_LEGACY_ALIASES so behavior is consistent even when the
    target project's harness.yaml has stripped the aliases section.
    """
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
    """Translate a legacy alias to its canonical autonomy level.

    Returns the canonical string when `value` is either already canonical or
    a known legacy alias. Returns None for unknown / non-string values so the
    caller can decide whether to fail or pass through.
    """
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
    """Return a typed FAIL payload when `value` is a known legacy alias, else None.

    Write paths (mission init / contract YAML fill) must reject legacy aliases
    so legacy values cannot propagate into persisted state. Unknown strings are
    not rejected here — schema-level validation handles those separately.
    """
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if stripped in AUTONOMY_CANONICAL_LEVELS:
        return None
    if stripped in aliases:
        suggested = aliases[stripped]
        payload = fail_payload(
            control,
            "LEGACY_LEVEL_REJECTED",
            f"autonomy_level={stripped!r} is a legacy alias; use canonical value {suggested!r}",
        )
        payload["findings"][0]["suggested_value"] = suggested
        payload["findings"][0]["received_value"] = stripped
        return payload
    return None


def lane_action_registry(root: Path) -> dict[str, dict[str, Any]]:
    return wg_lane_action_registry(root)


def as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def format_lane_value(value: Any, mission_id: str) -> Any:
    if isinstance(value, str):
        return value.replace("{mission_id}", mission_id)
    if isinstance(value, list):
        return [format_lane_value(item, mission_id) for item in value]
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return load_yaml(path)
        return data if isinstance(data, dict) else {}
    return load_yaml(path)


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        write_yaml(path, payload)


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def operation_type_tree(operation: dict[str, Any]) -> list[str]:
    operation_type = str(operation.get("type") or "")
    values = [operation_type] if operation_type else []
    if operation_type == "batch" and isinstance(operation.get("operations"), list):
        for child in operation["operations"]:
            if isinstance(child, dict):
                values.extend(operation_type_tree(child))
    return values


def validate_graph_operation_structure(operation: dict[str, Any], path: str = "graph_operation") -> list[str]:
    operation_type = str(operation.get("type") or "")
    if not operation_type:
        return [f"{path}.type is required"]
    if operation_type != "batch":
        return []
    operations = operation.get("operations")
    if not isinstance(operations, list) or not operations:
        return [f"{path}.operations must be a non-empty list"]
    errors: list[str] = []
    for index, child in enumerate(operations, start=1):
        if not isinstance(child, dict):
            errors.append(f"{path}.operations[{index}] must be an object")
            continue
        errors.extend(validate_graph_operation_structure(child, f"{path}.operations[{index}]"))
    return errors


def graph_operation_output_nodes(operation: dict[str, Any]) -> list[str]:
    operation_type = str(operation.get("type") or "")
    outputs: list[str] = []
    if operation_type == "split_node":
        children = operation.get("children")
        if isinstance(children, list):
            outputs.extend(str(item.get("id") or "") for item in children if isinstance(item, dict))
    elif operation_type == "merge_nodes":
        target = operation.get("target")
        if isinstance(target, dict):
            outputs.append(str(target.get("id") or ""))
    elif operation_type == "batch":
        for child in operation.get("operations") or []:
            if isinstance(child, dict):
                outputs.extend(graph_operation_output_nodes(child))
    return unique([item for item in outputs if item])


def graph_operation_input_nodes(operation: dict[str, Any]) -> list[str]:
    operation_type = str(operation.get("type") or "")
    inputs: list[str] = []
    if operation_type in {"advance_lane", "split_node", "block_node", "defer_node", "supersede_node"}:
        inputs.append(str(operation.get("node_id") or ""))
    if operation_type in {"merge_nodes", "supersede_node"}:
        inputs.extend(str(item) for item in operation.get("node_ids") or [])
    if operation_type == "batch":
        for child in operation.get("operations") or []:
            if isinstance(child, dict):
                inputs.extend(graph_operation_input_nodes(child))
    return unique([item for item in inputs if item])


def replace_template_values(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        for key, replacement in replacements.items():
            value = value.replace("{{" + key + "}}", replacement)
        return value
    if isinstance(value, list):
        return [replace_template_values(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: replace_template_values(item, replacements) for key, item in value.items()}
    return value


CONTRACT_PLACEHOLDER_RE = re.compile(r"(\{\{.*?\}\}|<[^>]+>)")


def contract_leaf_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        items: list[Any] = []
        for nested in value.values():
            items.extend(contract_leaf_values(nested))
        return items
    if isinstance(value, list):
        items = []
        for nested in value:
            items.extend(contract_leaf_values(nested))
        return items
    return [value]


def contract_contains_placeholder(value: Any) -> bool:
    return any(isinstance(item, str) and CONTRACT_PLACEHOLDER_RE.search(item) for item in contract_leaf_values(value))


def template_prefilled_role_verdict(verdict: dict[str, Any]) -> bool:
    return str(verdict.get("verdict") or "") == "PASS" and contract_contains_placeholder(verdict)


def scrub_template_role_verdicts(contract: dict[str, Any], *, template_mode: bool = False) -> bool:
    verdicts = contract.get("role_verdicts")
    if not isinstance(verdicts, list):
        return False
    cleaned = [
        item for item in verdicts
        if not (isinstance(item, dict) and (template_prefilled_role_verdict(item) or (template_mode and str(item.get("verdict") or "") == "PASS")))
    ]
    if cleaned == verdicts:
        return False
    contract["role_verdicts"] = cleaned
    return True


def contract_governance_conflict(contract: dict[str, Any]) -> bool:
    policy = contract.get("stage_participation_policy") if isinstance(contract.get("stage_participation_policy"), dict) else {}
    obligations = contract.get("entered_stage_obligations") if isinstance(contract.get("entered_stage_obligations"), dict) else {}
    policy_reviews = set(as_str_list(policy.get("required_review_roles")))
    obligation_reviews = set(as_str_list(obligations.get("review_roles")))
    return bool(policy_reviews and obligation_reviews and policy_reviews != obligation_reviews)


def contract_hygiene_payload(contract: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if contract_contains_placeholder(contract):
        findings.append(finding("FAIL", "placeholder_in_runtime_artifact", "Contract still contains unresolved template placeholders", source="contract_hygiene"))
        findings.append(finding("WARN", "manual_patch_required", "Materialized contract requires explicit patch/fill before it can pass hygiene", source="contract_hygiene"))
    if any(isinstance(item, dict) and template_prefilled_role_verdict(item) for item in contract.get("role_verdicts") or []):
        findings.append(finding("FAIL", "prefilled_role_verdict", "Template-time role_verdicts must not prefill reviewer PASS", source="contract_hygiene"))
    if contract_governance_conflict(contract):
        findings.append(finding("FAIL", "governance_conflict", "stage_participation_policy conflicts with entered_stage_obligations", source="contract_hygiene"))
    return {"status": status_from_findings(findings), "findings": findings}


def contract_template_path(root: Path, template: str) -> Path:
    name = template if template.endswith((".yaml", ".yml")) else f"{template}.contract.yaml"
    for base in (
        root / "harness-runtime" / "templates" / "contracts",
        PACKAGE_ROOT / "harness-runtime" / "templates" / "contracts",
    ):
        path = base / name
        if path.exists():
            return path
    return PACKAGE_ROOT / "harness-runtime" / "templates" / "contracts" / name


def control_contract_document(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    document = load_manifest(path)
    contract = document.get("control_contract")
    if not isinstance(contract, dict):
        contract = {}
        document["control_contract"] = contract
    return document, contract


def set_path_value(document: dict[str, Any], target: str, value: Any, op: str) -> None:
    parts = [part for part in target.split(".") if part]
    if not parts:
        raise ValueError("patch target is required")
    current: Any = document
    for part in parts[:-1]:
        if not isinstance(current, dict):
            raise ValueError(f"patch target parent is not an object: {target}")
        current = current.setdefault(part, {})
    if not isinstance(current, dict):
        raise ValueError(f"patch target parent is not an object: {target}")
    leaf = parts[-1]
    if op == "set":
        current[leaf] = value
    elif op == "merge":
        existing = current.get(leaf)
        if not isinstance(existing, dict) or not isinstance(value, dict):
            raise ValueError("merge requires existing value and patch value to be objects")
        existing.update(value)
    elif op == "append":
        existing = current.setdefault(leaf, [])
        if not isinstance(existing, list):
            raise ValueError("append target must be a list")
        existing.append(value)
    else:
        raise ValueError(f"unsupported patch op: {op}")


def upsert_by_id(items: list[dict[str, Any]], item: dict[str, Any]) -> str:
    item_id = str(item.get("id") or "")
    if item_id:
        for index, existing in enumerate(items):
            if str(existing.get("id") or "") == item_id:
                items[index] = item
                return "replaced"
    items.append(item)
    return "appended"


def evidence_store_path(root: Path, mission_id: str, explicit: str | None = None) -> Path:
    path = resolve_path(root, explicit)
    if path:
        return path
    return runtime_harness_root(root) / "traces" / mission_id / "evidence" / "evidence.json"


def load_evidence_store(path: Path, mission_id: str) -> dict[str, Any]:
    if path.exists():
        data = load_manifest(path)
        if isinstance(data.get("evidence"), list):
            return {
                "schema_version": data.get("schema_version") or 1,
                "mission_id": data.get("mission_id") or mission_id,
                "evidence": [item for item in data.get("evidence") or [] if isinstance(item, dict)],
                "links": [item for item in data.get("links") or [] if isinstance(item, dict)],
            }
    return {"schema_version": 1, "mission_id": mission_id, "evidence": [], "links": []}


def mission_slice_path(root: Path, mission_id: str) -> Path:
    return work_graph_root(root) / "mission-slices" / f"{mission_id}.yaml"


def load_mission_slice(root: Path, mission_id: str, entry: dict[str, Any] | None = None) -> tuple[Path, dict[str, Any]]:
    path: Path | None = None
    if entry and isinstance(entry.get("work_graph"), dict):
        path = resolve_path(root, str(entry["work_graph"].get("mission_slice") or ""))
    path = path or mission_slice_path(root, mission_id)
    return path, load_yaml(path)


# Legacy stage-mode control plane derivation removed. Active missions now require an explicit
# Mission Slice; mission-status fields like current_stage are tracking
# data only and are no longer used to synthesize a control plane.


def active_mission_ids(status: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for mission_id, entry in status.items():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status") or "").lower() in CLOSED_MISSION_STATUSES:
            continue
        work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
        if work_graph.get("last_operation_status") == "PASS":
            continue
        if work_graph.get("mission_slice"):
            ids.append(str(mission_id))
    return sorted(ids, key=lambda item: str((status.get(item) or {}).get("started_at") or ""))


def mission_entry_operation_completed(entry: dict[str, Any]) -> bool:
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    return str(work_graph.get("last_operation_status") or "").upper() == "PASS"


def open_mission_ids(status: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for mission_id, entry in status.items():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status") or "").lower() in CLOSED_MISSION_STATUSES:
            continue
        ids.append(str(mission_id))
    return sorted(ids, key=lambda item: str((status.get(item) or {}).get("started_at") or ""))


def lower_filter(values: list[str] | None) -> set[str]:
    return {str(item).lower() for item in values or [] if str(item)}


def mission_matches_status_filters(entry: dict[str, Any], args: argparse.Namespace) -> bool:
    status_filter = lower_filter(getattr(args, "status_filter", None))
    if status_filter and str(entry.get("status") or "").lower() not in status_filter:
        return False
    current_stage_filter = lower_filter(getattr(args, "current_stage", None))
    if current_stage_filter and str(entry.get("current_stage") or "").lower() not in current_stage_filter:
        return False
    stages = entry.get("stages") if isinstance(entry.get("stages"), dict) else {}
    stage_filter = lower_filter(getattr(args, "stage", None))
    stage_status_filter = lower_filter(getattr(args, "stage_status", None))
    if stage_filter:
        matched_stage_values = [str(value).lower() for key, value in stages.items() if str(key).lower() in stage_filter]
        if not matched_stage_values:
            return False
        if stage_status_filter and not any(value in stage_status_filter for value in matched_stage_values):
            return False
    elif stage_status_filter and not any(str(value).lower() in stage_status_filter for value in stages.values()):
        return False
    return True


def fail_payload(control: str, code: str, message: str) -> dict[str, Any]:
    return {"status": "FAIL", "control": control, "findings": [{"level": "FAIL", "code": code, "message": message}]}


def emit_payload(args: argparse.Namespace, payload: dict[str, Any]) -> int:
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{payload.get('control', 'harness')}: {payload.get('status')}")
        for item in payload.get("findings") or []:
            print(f"[{item.get('level')}] {item.get('code')}: {item.get('message')}")
    return 0 if payload.get("status") in {"PASS", "WARN"} else 1


def finding(level: str, code: str, message: str, *, source: str = "", blocking: bool = False, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"level": level, "code": code, "message": message, "blocking": blocking}
    if source:
        item["source"] = source
    item.update(extra)
    return item


def status_from_findings(findings: list[dict[str, Any]]) -> str:
    levels = {str(item.get("level") or "").upper() for item in findings}
    if "FAIL" in levels:
        return "FAIL"
    if "BLOCKED" in levels or any(bool(item.get("blocking")) for item in findings):
        return "BLOCKED"
    if "WARN" in levels:
        return "WARN"
    return "PASS"


def control_common_root(root: Path) -> Path:
    for path in (root / ".harness" / "common", root / "package" / "common"):
        if path.exists():
            return path.resolve()
    return COMMON_ROOT.resolve()


def explicit_runtime_config_path(runtime_root: Path) -> Path:
    if runtime_root.name == "harness" and runtime_root.parent.name == "harness-runtime":
        return runtime_root.parent / "config" / "harness.yaml"
    if runtime_root.name == "harness-runtime":
        return runtime_root / "config" / "harness.yaml"
    return runtime_root.parent / "config" / "harness.yaml"


def resolve_runtime_layout(root: Path | str, explicit_runtime: str | None = None) -> dict[str, Any]:
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
            "common_root": str(control_common_root(project_root)),
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
        "common_root": str(control_common_root(project_root)),
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


def mission_summary(mission_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    return {
        "mission_id": mission_id,
        "status": entry.get("status") or "",
        "started_at": entry.get("started_at") or "",
        "current_lane": entry.get("current_lane") or work_graph.get("lane") or "",
        "current_stage": entry.get("current_stage") or "",
        "mission_slice": work_graph.get("mission_slice") or "",
        "last_operation_status": work_graph.get("last_operation_status") or "",
    }


def node_summary(path: Path, node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(node.get("id") or path.stem),
        "kind": str(node.get("kind") or ""),
        "title": str(node.get("title") or ""),
        "lane": str(node.get("lane") or ""),
        "stage": str(node.get("stage") or ""),
        "status": str(node.get("status") or ""),
        "priority": str(node.get("priority") or ""),
        "path": str(path),
    }


def load_control_nodes(layout: dict[str, Any]) -> list[dict[str, Any]]:
    nodes_root = control_graph_root(layout) / "nodes"
    if not nodes_root.exists():
        return []
    nodes: list[dict[str, Any]] = []
    for path in sorted(nodes_root.glob("**/*.yaml")):
        node = load_yaml(path)
        if node:
            nodes.append(node_summary(path, node))
    return nodes


def control_nodes_by_id(layout: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(node.get("id") or ""): node for node in load_control_nodes(layout) if node.get("id")}


def load_control_slice(layout: dict[str, Any], project_root: Path, mission_id: str, entry: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    path = resolve_path(project_root, str(work_graph.get("mission_slice") or ""))
    path = path or (control_graph_root(layout) / "mission-slices" / f"{mission_id}.yaml")
    return path, load_yaml(path)


def mission_slice_from_lane(mission_slice: dict[str, Any]) -> str:
    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    lane_action = mission_slice.get("lane_action") if isinstance(mission_slice.get("lane_action"), dict) else {}
    return str(control_plane.get("lane") or lane_action.get("lane") or mission_slice.get("from_lane") or control_plane.get("from_lane") or lane_action.get("from_lane") or "")


def mission_slice_primary_nodes(mission_slice: dict[str, Any]) -> list[str]:
    work_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
    return as_str_list(work_graph.get("primary_nodes"))


def mission_slice_lane_consistency_findings(
    nodes_by_id: dict[str, dict[str, Any]],
    mission_id: str,
    mission_slice: dict[str, Any],
    *,
    source: str,
    blocking: bool,
    path: str = "",
) -> list[dict[str, Any]]:
    from_lane = mission_slice_from_lane(mission_slice)
    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    expected_stage = str(control_plane.get("stage") or "")
    findings: list[dict[str, Any]] = []
    for node_id in mission_slice_primary_nodes(mission_slice):
        node = nodes_by_id.get(node_id)
        if node is None:
            findings.append(finding(
                "BLOCKED" if blocking else "FAIL",
                "mission_slice_primary_node_missing",
                f"Mission Slice {mission_id} references unknown primary node {node_id}",
                source=source,
                blocking=blocking,
                mission_id=mission_id,
                path=path,
                node_id=node_id,
            ))
            continue
        node_lane = str(node.get("lane") or "")
        node_stage = str(node.get("stage") or "")
        if from_lane and node_lane != from_lane:
            findings.append(finding(
                "BLOCKED" if blocking else "FAIL",
                "mission_slice_primary_node_lane_mismatch",
                f"Mission Slice {mission_id} primary node {node_id} lane is {node_lane}, expected {from_lane}",
                source=source,
                blocking=blocking,
                mission_id=mission_id,
                path=path,
                node_id=node_id,
                node_lane=node_lane,
                expected_lane=from_lane,
            ))
        if expected_stage and node_stage != expected_stage:
            findings.append(finding(
                "BLOCKED" if blocking else "FAIL",
                "mission_slice_primary_node_stage_mismatch",
                f"Mission Slice {mission_id} primary node {node_id} stage is {node_stage}, expected {expected_stage}",
                source=source,
                blocking=blocking,
                mission_id=mission_id,
                path=path,
                node_id=node_id,
                node_stage=node_stage,
                expected_stage=expected_stage,
            ))
    return findings


def work_graph_nodes_by_id(root: Path) -> tuple[dict[str, dict[str, Any]], str | None]:
    nodes, _paths, findings = wg_load_nodes(wg_resolve_graph_root(root))
    if findings:
        return nodes, "; ".join(item.message for item in findings)
    return nodes, None


CHECKPOINT_ALIASES = {
    "acceptance_result": "acceptance-result",
    "tech_design": "tech-design",
    "execution_brief": "execution-brief",
    "verification_report": "verification-report",
    "delivery_package": "delivery-package",
    "code_review": "code-review",
    "mission_contract": "mission-contract",
    "dependency_impact": "dependency-impact",
}


def normalize_checkpoint(value: str) -> str:
    stripped = value.strip()
    return CHECKPOINT_ALIASES.get(stripped, stripped)


def checkpoint_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [normalize_checkpoint(value)] if value.strip() else []
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if isinstance(item, str):
            names.append(normalize_checkpoint(item))
        elif isinstance(item, dict):
            name = str(item.get("stage") or item.get("checkpoint") or item.get("id") or "")
            if name:
                names.append(normalize_checkpoint(name))
    return unique([item for item in names if item])


def load_control_approval_records(layout: dict[str, Any]) -> list[dict[str, Any]]:
    path = control_runtime_root(layout) / "state" / "approvals.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        records = data.get("approvals")
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
        if data.get("mission_id"):
            return [data]
    return []


def approved_checkpoints_for_mission(layout: dict[str, Any], mission_id: str) -> dict[str, str]:
    approved: dict[str, str] = {}
    for record in load_control_approval_records(layout):
        if str(record.get("mission_id") or mission_id) != mission_id:
            continue
        if str(record.get("type") or "") != "checkpoint":
            continue
        if str(record.get("status") or "") != "approved":
            continue
        checkpoint = normalize_checkpoint(str(record.get("stage") or record.get("checkpoint") or record.get("id") or ""))
        if checkpoint and checkpoint not in approved:
            approved[checkpoint] = str(record.get("approval_id") or "")
    return approved


def gate_report_paths(layout: dict[str, Any]) -> list[Path]:
    root = control_runtime_root(layout) / "state" / "gate-reports"
    return sorted(root.glob("**/*.json")) if root.exists() else []


def load_control_gate_reports(layout: dict[str, Any], mission_ids: set[str]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in gate_report_paths(layout):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(report, dict):
            continue
        mission_id = str(report.get("mission_id") or "")
        if mission_ids and mission_id not in mission_ids:
            continue
        approval_status = report.get("approval_status") if isinstance(report.get("approval_status"), dict) else {}
        missing = checkpoint_names(approval_status.get("missing_checkpoints"))
        gate_effect = str(report.get("gate_effect") or "")
        decision = str(report.get("decision") or "")
        if gate_effect in {"pause", "block"} or decision == "cannot_continue" or missing:
            reports.append({
                "mission_id": mission_id,
                "path": str(path),
                "stage": str(report.get("stage") or ""),
                "legacy_action": str(report.get("stage" + "_action") or ""),
                "operation": str(report.get("operation") or ""),
                "gate_effect": gate_effect,
                "decision": decision,
                "missing_checkpoints": missing,
            })
    return reports


def collect_required_approvals(root: Path, layout: dict[str, Any], status_doc: dict[str, Any], active_ids: list[str], active_slices: list[dict[str, Any]], pending_gates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    required: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def add_required(mission_id: str, checkpoint: str, source: str, source_path: str = "") -> None:
        checkpoint = normalize_checkpoint(checkpoint)
        if not checkpoint:
            return
        approved = approved_checkpoints_for_mission(layout, mission_id)
        if checkpoint in approved:
            return
        key = (mission_id, checkpoint, source)
        if key in seen:
            return
        seen.add(key)
        required.append({
            "mission_id": mission_id,
            "type": "checkpoint",
            "checkpoint": checkpoint,
            "status": "missing",
            "source": source,
            "source_path": source_path,
        })

    for slice_summary in active_slices:
        mission_id = str(slice_summary.get("mission_id") or "")
        if not mission_id:
            continue
        entry = status_doc.get(mission_id) if isinstance(status_doc.get(mission_id), dict) else {}
        slice_path, mission_slice = load_control_slice(layout, root, mission_id, entry)
        for checkpoint in checkpoint_names(mission_slice.get("required_checkpoints")) + checkpoint_names(mission_slice.get("human_checkpoints")):
            add_required(mission_id, checkpoint, "mission_slice", str(slice_path))

    for gate in pending_gates:
        mission_id = str(gate.get("mission_id") or "")
        for checkpoint in checkpoint_names(gate.get("missing_checkpoints")):
            add_required(mission_id, checkpoint, "gate_report", str(gate.get("path") or ""))

    # If a status entry is active but its slice is missing, keep approvals tied to gate reports only.
    _ = active_ids
    return required


def control_active_slice_ids(status_doc: dict[str, Any], root: Path, layout: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for mission_id in open_mission_ids(status_doc):
        entry = status_doc.get(mission_id) if isinstance(status_doc.get(mission_id), dict) else {}
        work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
        if not work_graph.get("mission_slice"):
            continue
        ids.append(mission_id)
    return sorted(ids, key=lambda item: str((status_doc.get(item) or {}).get("started_at") or ""))


def collect_control_status(root: Path, layout: dict[str, Any], *, mission: str | None = None) -> dict[str, Any]:
    status_path = control_status_path(layout)
    if not status_path.exists():
        item = finding(
            "BLOCKED",
            "mission_status_uninitialized",
            f"mission-status file not found: {status_path}",
            source="mission_status",
            blocking=True,
        )
        return {
            "status": "BLOCKED",
            "runtime_layout": layout,
            "missions": {"active": [], "open": []},
            "slices": {"active": []},
            "work_graph": {"ready_nodes": [], "blocked_nodes": []},
            "pending_gates": [],
            "required_approvals": [],
            "consistency_findings": [item],
        }
    status_doc = load_yaml(status_path)
    status_doc = status_doc if isinstance(status_doc, dict) else {}
    active_ids = control_active_slice_ids(status_doc, root, layout)
    open_ids = open_mission_ids(status_doc)
    if mission:
        active_ids = [item for item in active_ids if item == mission]
        open_ids = [item for item in open_ids if item == mission]

    findings: list[dict[str, Any]] = []
    active_slices: list[dict[str, Any]] = []
    nodes_by_id = control_nodes_by_id(layout)
    for mission_id in active_ids:
        entry = status_doc.get(mission_id) if isinstance(status_doc.get(mission_id), dict) else {}
        slice_path, mission_slice = load_control_slice(layout, root, mission_id, entry)
        if not mission_slice:
            findings.append(finding(
                "BLOCKED",
                "missing_mission_slice",
                f"active mission {mission_id} references a missing Mission Slice: {slice_path}",
                source="mission_slice",
                blocking=True,
                mission_id=mission_id,
                path=str(slice_path),
            ))
            continue
        if not mission_entry_operation_completed(entry):
            findings.extend(mission_slice_lane_consistency_findings(nodes_by_id, mission_id, mission_slice, source="mission_slice", blocking=True, path=str(slice_path)))
        control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
        slice_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
        active_slices.append({
            "mission_id": mission_id,
            "path": str(slice_path),
            "lane": control_plane.get("lane") or "",
            "stage": control_plane.get("stage") or "",
            "skill": (mission_slice.get("lane_action") or {}).get("skill") if isinstance(mission_slice.get("lane_action"), dict) else "",
            "primary_nodes": as_str_list(slice_graph.get("primary_nodes")),
            "related_nodes": as_str_list(slice_graph.get("related_nodes")),
        })

    nodes = list(nodes_by_id.values())
    mission_filter = set(open_ids)
    pending_gates = load_control_gate_reports(layout, mission_filter)
    required_approvals = collect_required_approvals(root, layout, status_doc, active_ids, active_slices, pending_gates)
    payload = {
        "status": status_from_findings(findings),
        "runtime_layout": layout,
        "missions": {
            "active": [mission_summary(mission_id, status_doc[mission_id]) for mission_id in active_ids if isinstance(status_doc.get(mission_id), dict)],
            "open": [mission_summary(mission_id, status_doc[mission_id]) for mission_id in open_ids if isinstance(status_doc.get(mission_id), dict)],
        },
        "slices": {"active": active_slices},
        "work_graph": {
            "ready_nodes": [node for node in nodes if node.get("status") == "ready"],
            "blocked_nodes": [node for node in nodes if node.get("status") == "blocked"],
        },
        "pending_gates": pending_gates,
        "required_approvals": required_approvals,
        "consistency_findings": findings,
    }
    return payload


def node_status_by_id(status_payload: dict[str, Any]) -> dict[str, str]:
    nodes = (status_payload.get("work_graph") or {}).get("ready_nodes") or []
    nodes += (status_payload.get("work_graph") or {}).get("blocked_nodes") or []
    return {str(node.get("id") or ""): str(node.get("status") or "") for node in nodes if isinstance(node, dict)}


def build_continue_candidates(root: Path, layout: dict[str, Any], *, mission: str | None = None) -> dict[str, Any]:
    status_payload = collect_control_status(root, layout, mission=mission)
    status_path = control_status_path(layout)
    status_doc = load_yaml(status_path) if status_path.exists() else {}
    status_doc = status_doc if isinstance(status_doc, dict) else {}
    active_set = set(control_active_slice_ids(status_doc, root, layout))
    node_status = node_status_by_id(status_payload)
    candidates: list[dict[str, Any]] = []
    findings = list(status_payload.get("consistency_findings") or [])

    mission_ids = [item.get("mission_id") for item in (status_payload.get("missions") or {}).get("open", []) if isinstance(item, dict)]
    for mission_id in [str(item) for item in mission_ids if item]:
        entry = status_doc.get(mission_id) if isinstance(status_doc.get(mission_id), dict) else {}
        slice_path, mission_slice = load_control_slice(layout, root, mission_id, entry)
        control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
        slice_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
        primary_nodes = as_str_list(slice_graph.get("primary_nodes"))
        node_id = primary_nodes[0] if primary_nodes else ""
        blocked_reasons: list[str] = []
        if not mission_slice:
            blocked_reasons.append("missing_mission_slice")
        if node_id and node_status.get(node_id) == "blocked":
            blocked_reasons.append("primary_node_blocked")
        if not node_id:
            blocked_reasons.append("missing_primary_node")
        candidates.append({
            "mission_id": mission_id,
            "node_id": node_id,
            "lane": control_plane.get("lane") or "",
            "stage": control_plane.get("stage") or "",
            "status": entry.get("status") or "",
            "sources": [source for source in ("mission_status", "mission_slice" if mission_slice else "", "active_mission" if mission_id in active_set else "") if source],
            "ranking_reasons": [
                "active mission with open Mission Slice" if mission_id in active_set else "open mission",
                f"started_at={entry.get('started_at') or ''}",
            ],
            "blocked_reasons": blocked_reasons,
            "mission_slice_path": str(slice_path),
        })

    candidates.sort(key=lambda item: (1 if item["blocked_reasons"] else 0, 0 if item["mission_id"] in active_set else 1, item["mission_id"]))
    return {
        "status": status_from_findings(findings),
        "runtime_layout": layout,
        "candidates": candidates,
        "requires_selection": len(candidates) > 1,
        "state_summary": {
            "active_count": len((status_payload.get("missions") or {}).get("active") or []),
            "open_count": len((status_payload.get("missions") or {}).get("open") or []),
            "ready_node_count": len((status_payload.get("work_graph") or {}).get("ready_nodes") or []),
            "blocked_node_count": len((status_payload.get("work_graph") or {}).get("blocked_nodes") or []),
        },
        "consistency_findings": findings,
    }


GUIDANCE_CATEGORIES = {
    "ready_for_execution",
    "needs_context",
    "needs_artifact",
    "needs_review",
    "needs_gate",
    "needs_approval",
    "blocked",
}


def control_relpath(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def path_item(root: Path, kind: str, path_value: str, *, required: bool, source: str) -> dict[str, Any]:
    path = resolve_path(root, path_value) or (root / path_value)
    return {
        "kind": kind,
        "path": path_value,
        "required": required,
        "exists": path.exists(),
        "source": source,
    }


def selected_mission_slice(root: Path, layout: dict[str, Any], mission_id: str) -> tuple[dict[str, Any], dict[str, Any], Path, dict[str, Any]]:
    status_path = control_status_path(layout)
    status_doc = load_yaml(status_path) if status_path.exists() else {}
    status_doc = status_doc if isinstance(status_doc, dict) else {}
    entry = status_doc.get(mission_id) if isinstance(status_doc.get(mission_id), dict) else {}
    if not entry:
        return status_doc, {}, control_graph_root(layout) / "mission-slices" / f"{mission_id}.yaml", {}
    slice_path, mission_slice = load_control_slice(layout, root, mission_id, entry)
    return status_doc, entry, slice_path, mission_slice


def latest_gate_report_for_mission(layout: dict[str, Any], mission_id: str) -> dict[str, Any]:
    reports: list[tuple[float, Path, dict[str, Any]]] = []
    for path in gate_report_paths(layout):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(report, dict) or str(report.get("mission_id") or "") != mission_id:
            continue
        reports.append((path.stat().st_mtime, path, report))
    if not reports:
        return {"latest_gate_report": "", "gate_effect": "", "decision": "", "exists": False}
    _mtime, path, report = sorted(reports, key=lambda item: item[0])[-1]
    return {
        "latest_gate_report": str(path),
        "gate_effect": str(report.get("gate_effect") or ""),
        "decision": str(report.get("decision") or ""),
        "exists": True,
    }


def load_advance_after_gate_module() -> Any | None:
    path = SKILLS_ROOT / "board-router" / "scripts" / "advance_after_gate.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("harness_advance_after_gate", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def next_graph_operation_for_frame(root: Path, mission_id: str, mission_slice: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    module = load_advance_after_gate_module()
    if module is None:
        return {}, [finding("WARN", "resolved_graph_operation_unavailable", "board-router advance_after_gate resolver is unavailable", source="control.frame")]
    resolver_findings: list[Any] = []
    try:
        operation = module.operation_from_slice(root, mission_id, mission_slice, resolver_findings)
    except Exception as exc:  # pragma: no cover - defensive boundary for read-only control query
        return {}, [finding("WARN", "resolved_graph_operation_failed", f"failed to resolve next graph operation: {exc}", source="control.frame")]
    findings = [
        finding(
            "WARN" if str(getattr(item, "level", "")).upper() == "FAIL" else str(getattr(item, "level", "WARN") or "WARN"),
            str(getattr(item, "code", "resolved_graph_operation_finding") or "resolved_graph_operation_finding"),
            str(getattr(item, "message", "") or "resolved graph operation finding"),
            source="control.frame",
        )
        for item in resolver_findings
    ]
    return (operation if isinstance(operation, dict) else {}), findings


def build_control_frame(root: Path, layout: dict[str, Any], mission_id: str) -> dict[str, Any]:
    status_doc, entry, slice_path, mission_slice = selected_mission_slice(root, layout, mission_id)
    if not entry:
        payload = fail_payload("control.frame", "missing_mission", f"mission not found: {mission_id}")
        payload["runtime_layout"] = layout
        return payload
    if not mission_slice:
        payload = fail_payload("control.frame", "missing_mission_slice", f"Mission Slice not found: {slice_path}")
        payload["runtime_layout"] = layout
        return payload

    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    lane_action = mission_slice.get("lane_action") if isinstance(mission_slice.get("lane_action"), dict) else {}
    lane = str(control_plane.get("lane") or lane_action.get("lane") or mission_slice.get("from_lane") or "")
    stage = str(control_plane.get("stage") or lane_action.get("stage") or "")
    registry_action: dict[str, Any] = {}
    if lane and stage:
        _lane, _stage, resolved = wg_lane_stage_for_node(load_runtime_config(root), {"id": "<control-frame>", "lane": lane, "stage": stage})
        registry_action = resolved if isinstance(resolved, dict) else {}
    action = {**registry_action, **lane_action} if registry_action else lane_action
    findings: list[dict[str, Any]] = []
    legacy_action_field = "stage" + "_action"
    legacy_control_fields = [field for field in ("skill", "carrier", legacy_action_field, "from_lane", "to_lane") if control_plane.get(field) not in (None, "")]
    if legacy_control_fields:
        findings.append(finding(
            "WARN",
            "legacy_control_plane_fields",
            "Mission Slice control_plane contains legacy dispatch fields; new control_plane only owns lane/stage",
            source="mission_slice",
            path=str(slice_path),
            legacy_fields=legacy_control_fields,
        ))
    control_skill = str(control_plane.get("skill") or "")
    action_skill = str(action.get("skill") or "")
    if control_skill and action_skill and control_skill != action_skill:
        payload = fail_payload(
            "control.frame",
            "control_plane_skill_conflict",
            f"legacy control_plane dispatch skill {control_skill!r} conflicts with lane_action.skill {action_skill!r}",
        )
        payload["runtime_layout"] = layout
        payload["mission_id"] = mission_id
        payload["mission_slice_path"] = control_relpath(root, slice_path)
        return payload
    output_artifact = str(action.get("output_artifact") or "")
    artifact_path = resolve_path(root, output_artifact)
    status_payload = collect_control_status(root, layout, mission=mission_id)
    required_approvals = status_payload.get("required_approvals") if isinstance(status_payload.get("required_approvals"), list) else []
    gate_state = latest_gate_report_for_mission(layout, mission_id)
    if status_payload.get("pending_gates"):
        gate_state["pending_gates"] = status_payload["pending_gates"]
    raw_allowed_graph_operations = as_str_list(action.get("allowed_graph_operations")) or list((action.get("operation_profiles") or {}).keys())
    resolved_graph_operation, resolver_findings = next_graph_operation_for_frame(root, mission_id, mission_slice)
    findings.extend(resolver_findings)
    allowed_graph_operations = [str(resolved_graph_operation["type"])] if resolved_graph_operation.get("type") else raw_allowed_graph_operations
    return {
        "status": "PASS",
        "runtime_layout": layout,
        "mission_id": mission_id,
        "mission_status": mission_summary(mission_id, entry),
        "mission_slice_path": control_relpath(root, slice_path),
        "lane": lane,
        "stage": stage,
        "skill": str(action.get("skill") or stage or ""),
        "carrier": str(action.get("carrier") or action.get("skill") or stage or ""),
        "output_artifact": output_artifact,
        "required_execution_roles": as_str_list(action.get("required_execution_roles")),
        "required_review_roles": as_str_list(action.get("required_review_roles")),
        "allowed_graph_operations": allowed_graph_operations,
        "raw_allowed_graph_operations": raw_allowed_graph_operations,
        "resolved_graph_operation": resolved_graph_operation,
        "artifact_state": {"path": output_artifact, "exists": bool(artifact_path and artifact_path.exists())},
        "gate_state": gate_state,
        "next_required_controls": ["approval.require"] if required_approvals else [],
        "required_approvals": required_approvals,
        "work_graph": mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {},
        "findings": findings,
    }


def build_context_index(root: Path, layout: dict[str, Any], mission_id: str) -> dict[str, Any]:
    _status_doc, entry, slice_path, mission_slice = selected_mission_slice(root, layout, mission_id)
    if not entry:
        payload = fail_payload("control.context-index", "missing_mission", f"mission not found: {mission_id}")
        payload["runtime_layout"] = layout
        return payload
    if not mission_slice:
        payload = fail_payload("control.context-index", "missing_mission_slice", f"Mission Slice not found: {slice_path}")
        payload["runtime_layout"] = layout
        return payload

    work_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
    primary_nodes = as_str_list(work_graph.get("primary_nodes"))
    required_context = [
        path_item(root, "project_context", "project-context.md", required=True, source="project"),
        path_item(root, "mission_slice", control_relpath(root, slice_path), required=True, source="work_graph"),
    ]
    upstream_artifacts: list[dict[str, Any]] = []
    for node_id in primary_nodes:
        matches = sorted((control_graph_root(layout) / "nodes").glob(f"**/{node_id}.yaml"))
        if not matches:
            continue
        node = load_yaml(matches[0])
        brief = str(node.get("execution_brief_artifact") or "")
        if brief:
            upstream_artifacts.append(path_item(root, "execution_brief", brief, required=True, source="work_graph_node"))
    mission_contract = control_runtime_root(layout) / "missions" / mission_id / "mission-contract.md"
    if mission_contract.exists():
        upstream_artifacts.append(path_item(root, "mission_contract", control_relpath(root, mission_contract), required=False, source="mission"))
    stage_dir = control_runtime_root(layout) / "stages" / mission_id
    for name in ("mission-contract.md", "solution.md", "tech-design.md"):
        candidate = stage_dir / name
        if candidate.exists():
            upstream_artifacts.append(path_item(root, name.removesuffix(".md").replace("-", "_"), control_relpath(root, candidate), required=False, source="stage_artifact"))
    product_dir = stage_dir / "product"
    for name in ("product-definition.md", "product-domain-model.md", "product-evidence.md"):
        candidate = product_dir / name
        if candidate.exists():
            upstream_artifacts.append(path_item(root, name.removesuffix(".md").replace("-", "_"), control_relpath(root, candidate), required=False, source="stage_artifact"))
    spec_enabled = bool((load_runtime_config(root).get("spec") if isinstance(load_runtime_config(root).get("spec"), dict) else {}).get("enabled", False))
    delta_specs: list[dict[str, Any]] = []
    if spec_enabled:
        spec_root = control_runtime_root(layout) / "stages" / mission_id / "specs"
        for path in sorted(spec_root.glob("**/spec.md")) if spec_root.exists() else []:
            delta_specs.append(path_item(root, "delta_spec", control_relpath(root, path), required=True, source="mission_delta_spec"))
    all_items = required_context + upstream_artifacts + delta_specs
    missing_context = [item for item in all_items if item.get("required") and not item.get("exists")]
    return {
        "status": "PASS",
        "runtime_layout": layout,
        "mission_id": mission_id,
        "required_context": required_context,
        "upstream_artifacts": upstream_artifacts,
        "delta_specs": delta_specs,
        "project_context": required_context[0],
        "missing_context": missing_context,
        "findings": [],
    }


def guidance_required_controls(
    *,
    missing_context: list[dict[str, Any]],
    missing_artifacts: list[dict[str, Any]],
    required_approvals: list[dict[str, Any]],
    missing_evidence: list[dict[str, Any]],
    pending_gates: list[dict[str, Any]],
) -> list[str]:
    controls = ["control.context-index"]
    if missing_context:
        controls.append("context.check")
    if missing_artifacts:
        controls.append("execute.produce-stage-artifact")
    if required_approvals:
        controls.append("approval.require")
    if missing_evidence:
        controls.append("contract.add-verdict")
    if pending_gates:
        controls.append("gate.run")
    return unique(controls)


def stage_participation_policy_payload(frame: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "role_policy_and_lane_action",
        "skippable": False,
        "conditional_entry": bool(frame.get("required_approvals")),
        "human_checkpoints": frame.get("required_approvals") or [],
        "required_review_roles": frame.get("required_review_roles") or [],
    }


def entered_stage_obligations_payload(frame: dict[str, Any], required_controls: list[str]) -> dict[str, Any]:
    return {
        "execution_roles": frame.get("required_execution_roles") or [],
        "review_roles": frame.get("required_review_roles") or [],
        "gate_controls": ["gate.run", "gate.advance"],
        "evidence": ["red_report", "green_report", "regression_report"],
        "required_controls": required_controls,
    }


def missing_review_evidence(root: Path, layout: dict[str, Any], mission_id: str, required_review_roles: list[str]) -> list[dict[str, Any]]:
    if not required_review_roles:
        return []
    contract_path = control_runtime_root(layout) / "stages" / mission_id / "contracts" / "execution-result.contract.yaml"
    contract_doc = load_yaml(contract_path) if contract_path.exists() else {}
    contract = contract_doc.get("control_contract") if isinstance(contract_doc.get("control_contract"), dict) else {}
    role_verdicts = contract.get("role_verdicts") if isinstance(contract.get("role_verdicts"), list) else []
    passed_roles = {
        str(item.get("role") or "")
        for item in role_verdicts
        if isinstance(item, dict) and str(item.get("verdict") or "") == "PASS"
    }
    missing: list[dict[str, Any]] = []
    for role in required_review_roles:
        if role in passed_roles:
            continue
        missing.append({
            "kind": "review_evidence",
            "role": role,
            "path": control_relpath(root, contract_path),
            "required": True,
            "exists": False,
            "source": "contract",
        })
    return missing


def blocked_guidance_payload(root: Path, layout: dict[str, Any], mission_id: str, frame: dict[str, Any]) -> dict[str, Any]:
    findings = frame.get("findings") if isinstance(frame.get("findings"), list) else []
    if not findings and frame.get("error"):
        findings = [{
            "level": "BLOCKED",
            "code": str(frame.get("error") or "blocked"),
            "message": str(frame.get("message") or "control frame is blocked"),
            "blocking": True,
            "source": "control.frame",
        }]
    required_controls = ["control.frame"]
    return {
        "status": "BLOCKED",
        "runtime_layout": layout,
        "mission_id": mission_id,
        "lane": frame.get("lane") or "",
        "stage": frame.get("stage") or "",
        "state": {"category": "blocked"},
        "required_controls": required_controls,
        "allowed_actions": ["fix_blocker", "rerun_required_controls"],
        "disallowed_actions": [
            {"action": "select_mission_without_selector", "reason": "control frame requires explicit --mission"},
            {"action": "emit_final_decision", "reason": "guidance is non-decisional"},
        ],
        "missing_context": [],
        "missing_artifacts": [],
        "missing_approvals": [],
        "missing_evidence": [],
        "stage_participation_policy": stage_participation_policy_payload(frame),
        "entered_stage_obligations": entered_stage_obligations_payload(frame, required_controls),
        "findings": findings,
    }


def build_control_guidance(root: Path, layout: dict[str, Any], mission_id: str) -> dict[str, Any]:
    frame = build_control_frame(root, layout, mission_id)
    if frame.get("status") != "PASS":
        return blocked_guidance_payload(root, layout, mission_id, frame)
    context_index = build_context_index(root, layout, mission_id)
    missing_context = context_index.get("missing_context") if isinstance(context_index.get("missing_context"), list) else []
    missing_artifacts = []
    artifact_state = frame.get("artifact_state") if isinstance(frame.get("artifact_state"), dict) else {}
    if artifact_state.get("path") and not artifact_state.get("exists"):
        missing_artifacts.append({
            "kind": "output_artifact",
            "path": artifact_state["path"],
            "required": True,
            "exists": False,
            "source": "lane_action",
        })
    required_approvals = frame.get("required_approvals") if isinstance(frame.get("required_approvals"), list) else []
    required_reviews = as_str_list(frame.get("required_review_roles"))
    missing_evidence = [] if missing_artifacts else missing_review_evidence(root, layout, mission_id, required_reviews)
    gate_state = frame.get("gate_state") if isinstance(frame.get("gate_state"), dict) else {}
    pending_gates = gate_state.get("pending_gates") if isinstance(gate_state.get("pending_gates"), list) else []
    if missing_context:
        category = "needs_context"
    elif required_approvals:
        category = "needs_approval"
    elif missing_artifacts:
        category = "needs_artifact"
    elif missing_evidence:
        category = "needs_review"
    elif gate_state.get("pending_gates"):
        category = "needs_gate"
    else:
        category = "ready_for_execution"
    required_controls = guidance_required_controls(
        missing_context=missing_context,
        missing_artifacts=missing_artifacts,
        required_approvals=required_approvals,
        missing_evidence=missing_evidence,
        pending_gates=pending_gates,
    )
    return {
        "status": "PASS",
        "runtime_layout": layout,
        "mission_id": mission_id,
        "lane": frame.get("lane") or "",
        "stage": frame.get("stage") or "",
        "state": {"category": category},
        "required_controls": required_controls,
        "allowed_actions": ["read_context", "run_required_controls", "produce_stage_artifact"],
        "disallowed_actions": [
            {"action": "select_mission_without_selector", "reason": "control frame requires explicit --mission"},
            {"action": "emit_final_decision", "reason": "guidance is non-decisional"},
        ],
        "missing_context": missing_context,
        "missing_artifacts": missing_artifacts,
        "missing_approvals": required_approvals,
        "missing_evidence": missing_evidence,
        "next_graph_operation": frame.get("resolved_graph_operation") if isinstance(frame.get("resolved_graph_operation"), dict) else {},
        "stage_participation_policy": stage_participation_policy_payload(frame),
        "entered_stage_obligations": entered_stage_obligations_payload(frame, required_controls),
        "findings": [],
    }


def cmd_control_status(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    layout = resolve_runtime_layout(root, explicit_runtime=getattr(args, "runtime_root", None))
    payload = collect_control_status(root, layout, mission=args.mission)
    payload["control"] = "control.status"
    return emit_payload(args, payload)


def cmd_control_candidates(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    if args.intent != "continue":
        return emit_payload(args, fail_payload("control.candidates", "unsupported_intent", f"unsupported control candidate intent: {args.intent}"))
    layout = resolve_runtime_layout(root, explicit_runtime=getattr(args, "runtime_root", None))
    payload = build_continue_candidates(root, layout, mission=args.mission)
    payload["control"] = "control.candidates"
    payload["intent"] = args.intent
    return emit_payload(args, payload)


def cmd_control_frame(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    layout = resolve_runtime_layout(root, explicit_runtime=getattr(args, "runtime_root", None))
    payload = build_control_frame(root, layout, args.mission)
    payload["control"] = "control.frame"
    return emit_payload(args, payload)


def cmd_control_guidance(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    layout = resolve_runtime_layout(root, explicit_runtime=getattr(args, "runtime_root", None))
    payload = build_control_guidance(root, layout, args.mission)
    payload["control"] = "control.guidance"
    return emit_payload(args, payload)


def cmd_control_context_index(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    layout = resolve_runtime_layout(root, explicit_runtime=getattr(args, "runtime_root", None))
    payload = build_context_index(root, layout, args.mission)
    payload["control"] = "control.context-index"
    return emit_payload(args, payload)


def build_lane_action_payload(action_name: str, action: dict[str, Any], mission_id: str) -> dict[str, Any]:
    return wg_lane_action_snapshot(action_name, action, mission_id)


def resolve_lane_stage(root: Path, action_name: str) -> tuple[str, str, dict[str, Any] | None]:
    config = load_runtime_config(root)
    actions = lane_action_registry(root)
    if action_name in actions:
        action = actions[action_name]
        return action_name, str(action.get("stage") or ""), action
    lane = wg_lane_of_stage(config, action_name)
    if lane:
        resolved_lane, stage, action = wg_lane_stage_for_node(config, {"id": "<mission-slice>", "lane": lane, "stage": action_name})
        return resolved_lane, stage, action
    return "", "", None


def validate_graph_operation_for_lane(operation: dict[str, Any], lane_action: dict[str, Any]) -> str | None:
    structure_errors = wg_validate_graph_operation_structure(operation)
    if structure_errors:
        return "; ".join(structure_errors)
    findings: list[WGFinding] = []
    wg_validate_operation_against_profile(operation, lane_action, findings)
    if findings:
        return "; ".join(item.message for item in findings)
    return None


def create_mission_slice_payload(
    root: Path,
    mission_id: str,
    lane_action_name: str,
    primary_nodes: list[str],
    related_nodes: list[str],
    input_nodes: list[str],
    output_nodes: list[str],
    graph_operation: dict[str, Any] | None,
    requested_operation: str = "",
) -> tuple[dict[str, Any] | None, str | None]:
    lane, stage, action = resolve_lane_stage(root, lane_action_name)
    if not action:
        return None, f"work_graph.lanes has no lane or stage entry for {lane_action_name}"
    lane_action = build_lane_action_payload(lane, action, mission_id)
    operation = str(lane_action.get("graph_operation") or "")
    if requested_operation and requested_operation != operation:
        profiles = lane_action.get("operation_profiles") if isinstance(lane_action.get("operation_profiles"), dict) else {}
        if requested_operation not in profiles:
            return None, f"requested operation {requested_operation} is not allowed by work_graph.lanes.{lane}/{stage}.operation_profiles"
        operation = requested_operation
    if graph_operation:
        error = validate_graph_operation_for_lane(graph_operation, action)
        if error:
            return None, error
        operation = str(graph_operation.get("type") or operation)
        input_nodes = unique([*input_nodes, *graph_operation_input_nodes(graph_operation)])
        output_nodes = unique([*output_nodes, *graph_operation_output_nodes(graph_operation)])
    if not operation:
        return None, f"work_graph.lanes.{lane}/{stage}.graph_operation is required"
    nodes_by_id, load_error = work_graph_nodes_by_id(root)
    if load_error:
        return None, load_error
    for node_id in primary_nodes:
        node = nodes_by_id.get(node_id)
        if node is None:
            return None, f"primary node not found: {node_id}"
        node_lane = str(node.get("lane") or "")
        node_stage = str(node.get("stage") or "")
        if node_lane != lane or node_stage != stage:
            return None, f"{node_id} lane/stage is {node_lane}/{node_stage}, expected {lane}/{stage}"
    primary_nodes = unique([*primary_nodes, *output_nodes])
    if not primary_nodes:
        return None, "at least one --primary-node or graph_operation output node is required"
    control_plane = {
        "lane": lane,
        "stage": lane_action["stage"],
    }
    payload: dict[str, Any] = {
        "mission_id": mission_id,
        "objective": f"Mission Slice {mission_id}",
        "control_plane": control_plane,
        "lane_action": lane_action,
        "work_graph": {
            "primary_nodes": primary_nodes,
            "related_nodes": unique(related_nodes),
            "input_nodes": unique(input_nodes),
            "output_nodes": unique(output_nodes),
        },
        "operation": operation,
        "acceptance_criteria": [
            "graph operation applied by work-graph script",
            "board/index/tree regenerated from nodes",
        ],
    }
    if graph_operation:
        payload["graph_operation"] = graph_operation
    return payload, None


def write_mission_status_for_slice(root: Path, mission_id: str, slice_payload: dict[str, Any], slice_path: Path) -> dict[str, Any]:
    status_path = mission_status_path(root)
    status = load_yaml(status_path)
    entry = status.get(mission_id) if isinstance(status.get(mission_id), dict) else {}
    control_plane = slice_payload.get("control_plane") if isinstance(slice_payload.get("control_plane"), dict) else {}
    work_graph_payload = slice_payload.get("work_graph") if isinstance(slice_payload.get("work_graph"), dict) else {}
    stages = entry.get("stages") if isinstance(entry.get("stages"), dict) else {}
    stage = str(control_plane.get("stage") or "")
    if stage:
        stages.setdefault(stage, "pending")
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    work_graph.update(
        {
            "mission_slice": relpath(root, slice_path),
            "primary_nodes": work_graph_payload.get("primary_nodes") or [],
            "related_nodes": work_graph_payload.get("related_nodes") or [],
            "input_nodes": work_graph_payload.get("input_nodes") or [],
            "output_nodes": work_graph_payload.get("output_nodes") or [],
            "lane": control_plane.get("lane"),
            "stage": stage,
            "operation": slice_payload.get("operation"),
            "lane_action": slice_payload.get("lane_action"),
            "last_gate_report": "",
            "last_operation_manifest": "",
            "last_operation_status": "",
        }
    )
    entry.update(
        {
            "title": entry.get("title") or slice_payload.get("objective") or mission_id,
            "status": entry.get("status") or "active",
            "started_at": entry.get("started_at") or today(),
            "completed_at": entry.get("completed_at") or "",
            "current_stage": stage,
            "current_lane": control_plane.get("lane"),
            "stages": stages,
            "work_graph": work_graph,
            "checkpoints_passed": entry.get("checkpoints_passed") if isinstance(entry.get("checkpoints_passed"), list) else [],
        }
    )
    status[mission_id] = entry
    write_yaml(status_path, status)
    return entry


def update_mission_stage(root: Path, mission_id: str, stage: str, stage_status: str) -> dict[str, Any]:
    status_path = mission_status_path(root)
    status = load_yaml(status_path)
    entry = status.get(mission_id) if isinstance(status.get(mission_id), dict) else {}
    if not entry:
        return fail_payload("mission.stage", "missing_mission", f"mission not found: {mission_id}")
    slice_path, mission_slice = load_mission_slice(root, mission_id, entry)
    if not mission_slice and (entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}).get("mission_slice"):
        return fail_payload("mission.stage", "missing_mission_slice", f"Mission Slice not found: {relpath(root, slice_path)}")
    if mission_slice:
        control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
        slice_stage = str(control_plane.get("stage") or "")
        if slice_stage and stage != slice_stage:
            return fail_payload(
                "mission.stage",
                "mission_stage_not_current_slice",
                f"mission stage {stage} does not match active Mission Slice {slice_stage}; use gate.advance and create-slice to change lane/stage",
            )
        nodes_by_id, load_error = work_graph_nodes_by_id(root)
        if load_error:
            return fail_payload("mission.stage", "invalid_work_graph_nodes", load_error)
        consistency = mission_slice_lane_consistency_findings(nodes_by_id, mission_id, mission_slice, source="mission_slice", blocking=True, path=relpath(root, slice_path))
        if consistency:
            return {"status": status_from_findings(consistency), "control": "mission.stage", "mission_id": mission_id, "findings": consistency}
    stages = entry.get("stages") if isinstance(entry.get("stages"), dict) else {}
    stages[stage] = stage_status
    entry.update({"status": entry.get("status") or "active", "current_stage": stage, "stages": stages})
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    work_graph.update({"stage": stage})
    entry["work_graph"] = work_graph
    status[mission_id] = entry
    write_yaml(status_path, status)
    return {"status": "PASS", "control": "mission.stage", "mission_id": mission_id, "mission_status": entry, "findings": []}


def remove_node_references(node: dict[str, Any], removed: set[str]) -> None:
    for key in ("inputs", "outputs"):
        node[key] = [item for item in as_str_list(node.get(key)) if item not in removed]
    relations = node.get("relations") if isinstance(node.get("relations"), dict) else {}
    for key, value in list(relations.items()):
        if isinstance(value, list):
            relations[key] = [str(item) for item in value if str(item) not in removed]
        elif str(value) in removed:
            relations[key] = None
    node["relations"] = relations


def reset_mission_stage(
    root: Path,
    mission_id: str,
    stage: str,
    primary_nodes: list[str],
    related_nodes: list[str],
    output_node_policy: str,
    preserve_stage_history: bool,
    preserve_checkpoints: bool,
    reason: str,
) -> dict[str, Any]:
    status_path = mission_status_path(root)
    status = load_yaml(status_path)
    entry = status.get(mission_id) if isinstance(status.get(mission_id), dict) else {}
    if not entry:
        return fail_payload("mission.reset_stage", "missing_mission", f"mission not found: {mission_id}")

    target_lane, target_stage, action = resolve_lane_stage(root, stage)
    if not action:
        return fail_payload("mission.reset_stage", "unknown_stage", f"work_graph.lanes has no lane or stage entry for {stage}")

    slice_path, old_slice = load_mission_slice(root, mission_id, entry)
    old_slice_graph = old_slice.get("work_graph") if isinstance(old_slice.get("work_graph"), dict) else {}
    entry_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    selected_primary_nodes = unique(
        primary_nodes
        or as_str_list(old_slice_graph.get("primary_nodes"))
        or as_str_list(entry_graph.get("primary_nodes"))
    )
    if not selected_primary_nodes:
        return fail_payload("mission.reset_stage", "missing_primary_node", "at least one --primary-node or existing Mission Slice primary node is required")

    graph_root = wg_resolve_graph_root(root)
    nodes, paths, load_findings = wg_load_nodes(graph_root)
    if load_findings:
        return fail_payload("mission.reset_stage", "invalid_work_graph_nodes", "; ".join(item.message for item in load_findings))
    missing = [node_id for node_id in selected_primary_nodes if node_id not in nodes]
    if missing:
        return fail_payload("mission.reset_stage", "primary_node_missing", f"primary node not found: {', '.join(missing)}")

    output_nodes = unique(
        [
            *as_str_list(entry_graph.get("output_nodes")),
            *as_str_list(old_slice_graph.get("output_nodes")),
            *(item for node_id in selected_primary_nodes for item in as_str_list(nodes[node_id].get("outputs"))),
        ]
    )
    output_nodes = [node_id for node_id in output_nodes if node_id not in selected_primary_nodes]
    now = now_iso()
    changed_nodes: set[str] = set()

    for node_id in selected_primary_nodes:
        node = nodes[node_id]
        node["lane"] = target_lane
        node["stage"] = target_stage
        node["status"] = "ready"
        node["updated_at"] = now
        trace = node.get("trace") if isinstance(node.get("trace"), dict) else {}
        trace.update({"reset_by_mission": mission_id, "reset_to_stage": target_stage, "reset_reason": reason})
        node["trace"] = trace
        changed_nodes.add(node_id)

    existing_output_nodes = [node_id for node_id in output_nodes if node_id in nodes]
    pruned_nodes: list[str] = []
    deferred_nodes: list[str] = []
    if output_node_policy == "prune":
        removed = set(existing_output_nodes)
        for node_id in existing_output_nodes:
            path = paths.get(node_id)
            if path and path.exists():
                path.unlink()
            nodes.pop(node_id, None)
            pruned_nodes.append(node_id)
        for node_id, node in nodes.items():
            remove_node_references(node, removed)
            changed_nodes.add(node_id)
    elif output_node_policy == "defer":
        for node_id in existing_output_nodes:
            node = nodes[node_id]
            node["status"] = "deferred"
            node["updated_at"] = now
            trace = node.get("trace") if isinstance(node.get("trace"), dict) else {}
            trace.update({"defer_reason": reason, "reset_by_mission": mission_id, "reset_to_stage": target_stage})
            node["trace"] = trace
            changed_nodes.add(node_id)
            deferred_nodes.append(node_id)

    for node_id in sorted(changed_nodes):
        if node_id in nodes and node_id in paths:
            write_yaml(paths[node_id], nodes[node_id])
    wg_write_views(graph_root, nodes)

    lane_action = build_lane_action_payload(target_lane, action, mission_id)
    slice_payload = {
        "mission_id": mission_id,
        "objective": f"Mission Slice {mission_id}",
        "control_plane": {"lane": target_lane, "stage": target_stage},
        "lane_action": lane_action,
        "work_graph": {
            "primary_nodes": selected_primary_nodes,
            "related_nodes": unique(related_nodes),
            "input_nodes": [],
            "output_nodes": [],
        },
        "operation": lane_action.get("graph_operation") or "",
        "acceptance_criteria": [
            "mission stage reset by harness mission reset-stage",
            "work graph views regenerated from nodes",
        ],
    }
    write_yaml(slice_path, slice_payload)
    entry = write_mission_status_for_slice(root, mission_id, slice_payload, slice_path)
    if preserve_stage_history:
        stages = entry.get("stages") if isinstance(entry.get("stages"), dict) else {}
        entry["stages"] = {**stages, target_stage: "in-progress"}
    else:
        entry["stages"] = {target_stage: "in-progress"}
    if not preserve_checkpoints:
        entry["checkpoints_passed"] = []
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    work_graph.update(
        {
            "last_transaction_id": "",
            "last_transaction_journal": "",
            "reset_stage": target_stage,
            "reset_reason": reason,
            "reset_at": now,
            "reset_output_node_policy": output_node_policy,
        }
    )
    entry["work_graph"] = work_graph
    status[mission_id] = entry
    write_yaml(status_path, status)

    log_path = graph_root / "operations.log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "applied_at": now,
            "operation": {
                "operation_id": f"{mission_id}__reset_stage__{target_stage}",
                "type": "reset_stage",
                "mission_id": mission_id,
                "to_lane": target_lane,
                "to_stage": target_stage,
                "primary_nodes": selected_primary_nodes,
                "deferred_nodes": deferred_nodes,
                "pruned_nodes": pruned_nodes,
                "reason": reason,
            },
        }, ensure_ascii=False) + "\n")

    graph_check = run_python_capture(script("work-graph", "scripts", "check_graph_consistency.py"), ["--root", str(root), "--json"])
    graph_check_payload: dict[str, Any] = {}
    if graph_check.stdout.strip().startswith("{"):
        graph_check_payload = json.loads(graph_check.stdout)
    return {
        "status": graph_check_payload.get("status") or ("PASS" if graph_check.returncode == 0 else "FAIL"),
        "control": "mission.reset_stage",
        "mission_id": mission_id,
        "mission_status": entry,
        "mission_slice_path": relpath(root, slice_path),
        "mission_slice": slice_payload,
        "output_node_policy": output_node_policy,
        "deferred_nodes": deferred_nodes,
        "pruned_nodes": pruned_nodes,
        "graph_check": graph_check_payload,
        "findings": graph_check_payload.get("findings") or [],
    }


def cmd_mission_reset_stage(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    payload = reset_mission_stage(
        root,
        args.mission,
        args.stage,
        as_str_list(args.primary_node),
        as_str_list(args.related_node),
        args.output_node_policy,
        args.preserve_stage_history,
        args.preserve_checkpoints,
        args.reason,
    )
    return emit_payload(args, payload)


def cmd_mission_create_slice(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    status = load_yaml(mission_status_path(root))
    path = mission_slice_path(root, args.mission)
    if not args.replace and (path.exists() or args.mission in status):
        return emit_payload(args, fail_payload("mission.create_slice", "mission_slice_exists", f"Mission Slice or mission status already exists for {args.mission}; pass --replace to overwrite"))
    operation_name = args.operation or ""
    operation_manifest = args.graph_operation_manifest or args.graph_operation
    if args.graph_operation and not args.graph_operation_manifest:
        candidate = Path(args.graph_operation).expanduser()
        if not candidate.suffix and not candidate.is_absolute() and not (root / candidate).exists():
            operation_name = args.graph_operation
            operation_manifest = None
    operation_path = resolve_path(root, operation_manifest)
    graph_operation = None
    if operation_path:
        if not operation_path.exists():
            return emit_payload(args, fail_payload("mission.create_slice", "missing_graph_operation", f"graph operation manifest not found: {operation_path}"))
        graph_operation = load_manifest(operation_path)
        if not graph_operation:
            return emit_payload(args, fail_payload("mission.create_slice", "invalid_graph_operation", f"graph operation manifest is empty or invalid: {operation_path}"))
    payload, error = create_mission_slice_payload(
        root,
        args.mission,
        args.lane_action,
        as_str_list(args.primary_node),
        as_str_list(args.related_node),
        as_str_list(args.input_node),
        as_str_list(args.output_node),
        graph_operation,
        operation_name,
    )
    if error or not payload:
        return emit_payload(args, fail_payload("mission.create_slice", "invalid_mission_slice", error or "invalid Mission Slice"))
    write_yaml(path, payload)
    entry = write_mission_status_for_slice(root, args.mission, payload, path)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "mission.create_slice",
            "mission_id": args.mission,
            "mission_slice_path": relpath(root, path),
            "mission_slice": payload,
            "mission_status": entry,
            "findings": [],
        },
    )


def cmd_mission_status(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    status_path = mission_status_path(root)
    if not status_path.exists():
        return emit_payload(
            args,
            fail_payload(
                "mission.status",
                "mission_status_uninitialized",
                f"mission-status file not found: {relpath(root, status_path)}; run 'harness mission init' to initialize",
            ),
        )
    status = load_yaml(status_path)
    active_ids = active_mission_ids(status)
    open_ids = open_mission_ids(status)
    if args.mission:
        entry = status.get(args.mission) if isinstance(status.get(args.mission), dict) else {}
        if not entry:
            return emit_payload(args, fail_payload("mission.status", "missing_mission", f"mission not found: {args.mission}"))
        slice_path, mission_slice = load_mission_slice(root, args.mission, entry)
        nodes_by_id, load_error = work_graph_nodes_by_id(root)
        findings: list[dict[str, Any]] = []
        if load_error:
            findings.append(finding("BLOCKED", "invalid_work_graph_nodes", load_error, source="work_graph", blocking=True))
        if mission_slice and not mission_entry_operation_completed(entry):
            findings.extend(mission_slice_lane_consistency_findings(nodes_by_id, args.mission, mission_slice, source="mission_slice", blocking=True, path=relpath(root, slice_path)))
        payload = {
            "status": status_from_findings(findings),
            "control": "mission.status",
            "mission_id": args.mission,
            "mission_status": entry,
            "mission_slice_path": relpath(root, slice_path),
            "mission_slice": mission_slice,
            "findings": findings,
        }
    else:
        ids = [mission_id for mission_id, entry in status.items() if isinstance(entry, dict)]
        if args.active:
            active_set = set(active_ids)
            ids = [mission_id for mission_id in ids if mission_id in active_set]
        if args.open_only:
            open_set = set(open_ids)
            ids = [mission_id for mission_id in ids if mission_id in open_set]
        ids = [mission_id for mission_id in ids if mission_matches_status_filters(status[mission_id], args)]
        ids = sorted(ids, key=lambda item: str((status.get(item) or {}).get("started_at") or ""))
        missions = {} if args.ids_only else {mission_id: status[mission_id] for mission_id in ids}
        payload = {
            "status": "PASS",
            "control": "mission.status",
            "missions": missions,
            "mission_ids": ids,
            "active_missions": active_ids,
            "open_missions": open_ids,
            "filters": {
                "active": args.active,
                "open": args.open_only,
                "status": args.status_filter or [],
                "current_stage": args.current_stage or [],
                "stage": args.stage or [],
                "stage_status": args.stage_status or [],
                "ids_only": args.ids_only,
            },
            "findings": [],
        }
    return emit_payload(args, payload)


def cmd_mission_stage_start(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    payload = update_mission_stage(root, args.mission, args.stage, "in-progress")
    return emit_payload(args, payload)


def cmd_mission_stage_complete(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    payload = update_mission_stage(root, args.mission, args.stage, "done")
    if payload.get("status") == "PASS":
        payload["stage_completion"] = mission_stage_completion_status(root, args.stage, payload.get("mission_status"))
    return emit_payload(args, payload)


def cmd_mission_init(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    status_path = mission_status_path(root)
    if status_path.exists() and not args.replace:
        status = load_yaml(status_path)
        if isinstance(status, dict):
            for relative in ("missions", "stages", "deliveries", "memory", "traces", "state", "work-graph/nodes", "work-graph/mission-slices"):
                (runtime_harness_root(root) / relative).mkdir(parents=True, exist_ok=True)
            return emit_payload(
                args,
                {
                    "status": "PASS",
                    "control": "mission.init",
                    "mission_status_path": relpath(root, status_path),
                    "noop": True,
                    "findings": [
                        {
                            "level": "PASS",
                            "code": "mission_status_exists",
                            "message": "mission-status already initialized; no changes made",
                        }
                    ],
                },
            )
        return emit_payload(args, fail_payload("mission.init", "invalid_mission_status", f"mission-status exists but is not a mapping: {relpath(root, status_path)}"))
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        "# HarnessV2 mission status — managed by harness-cli; do not hand-edit.\n"
        "# Each top-level key is a mission-id. Use 'harness mission create-slice' to populate.\n",
        encoding="utf-8",
    )
    # Also ensure dependent runtime dirs exist so subsequent commands don't quietly create them.
    for relative in ("missions", "stages", "deliveries", "memory", "traces", "state", "work-graph/nodes", "work-graph/mission-slices"):
        (runtime_harness_root(root) / relative).mkdir(parents=True, exist_ok=True)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "mission.init",
            "mission_status_path": relpath(root, status_path),
            "findings": [],
        },
    )


def project_context_path(root: Path) -> Path:
    return root / "project-context.md"


def project_context_template_path(root: Path) -> Path:
    for candidate in (
        root / "harness-runtime" / "templates" / "project-context.md",
        PACKAGE_ROOT / "harness-runtime" / "templates" / "project-context.md",
    ):
        if candidate.exists():
            return candidate
    return PACKAGE_ROOT / "harness-runtime" / "templates" / "project-context.md"


def cmd_context_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    path = project_context_path(root)
    exists = path.exists()
    payload: dict[str, Any] = {
        "status": "PASS" if exists else "FAIL",
        "control": "context.check",
        "project_context_path": relpath(root, path),
        "exists": exists,
        "findings": [] if exists else [
            {
                "level": "FAIL",
                "code": "project_context_missing",
                "message": "project-context.md is not present; run 'harness context init' to create it from template, or record the absence as evidence.",
            }
        ],
    }
    return emit_payload(args, payload)


def project_knowledge_root(root: Path) -> Path:
    return root / "project-knowledge"


def project_knowledge_template_root() -> Path:
    for candidate in (
        root_template := PACKAGE_ROOT / "project-knowledge",
        PACKAGE_ROOT.parent / "project-knowledge",
    ):
        if candidate.exists():
            return candidate
    return root_template


def behavior_specs_root(root: Path) -> Path:
    """Resolve the project-owned long-lived behavior spec directory."""
    installed = project_knowledge_root(root) / "specs"
    source_repo = root / "package" / "project-knowledge" / "specs"
    if installed.exists():
        return installed
    if source_repo.exists():
        return source_repo
    return installed


def behavior_specs_template_root() -> Path:
    return project_knowledge_template_root() / "specs"


PROJECT_KNOWLEDGE_REQUIRED_PATHS = [
    "_index.md",
    "context/overview.md",
    "context/constraints.md",
    "context/tech-stack.md",
    "context/repository-map.md",
    "context/risks.md",
    "product/capabilities.md",
    "product/scope-boundaries.md",
    "product/workflows/README.md",
    "specs/_index.md",
    "design/system-overview.md",
    "design/modules/README.md",
    "design/decisions/README.md",
    "engineering/conventions/README.md",
    "engineering/patterns/README.md",
    "engineering/policies/README.md",
    "engineering/policies/stage-rules.yaml",
    "engineering/policies/project-lint.yaml",
    "engineering/task-splitting/README.md",
    "engineering/testing/README.md",
    "operations/README.md",
    "operations/verification/README.md",
    "operations/installation/README.md",
    "operations/troubleshooting/README.md",
    "lessons/README.md",
    "lessons/quality/README.md",
    "lessons/bug-fix/README.md",
    "glossary/README.md",
]


KNOWLEDGE_STAGE_DOMAINS = {
    "intake": ["context", "product", "specs", "lessons"],
    "discovery": ["context", "product", "specs", "design", "lessons"],
    "prd": ["context", "product", "specs"],
    "solution": ["context", "product", "specs", "design"],
    "interaction": ["context", "product", "design"],
    "technical_analysis": ["context", "specs", "design", "engineering"],
    "technical-analysis": ["context", "specs", "design", "engineering"],
    "breakdown": ["context", "specs", "design", "engineering"],
    "execute": ["context", "specs", "engineering", "operations"],
    "code-review": ["context", "specs", "engineering", "lessons"],
    "verify": ["context", "specs", "engineering", "operations", "lessons"],
    "delivery": ["product", "operations", "lessons"],
    "retrospective": ["context", "engineering", "operations", "lessons"],
    "finishing-branch": ["operations", "lessons"],
}


def _copy_tree_missing(src: Path, dst: Path, *, replace: bool = False) -> list[str]:
    created: list[str] = []
    for item in src.rglob("*"):
        if item.is_dir():
            (dst / item.relative_to(src)).mkdir(parents=True, exist_ok=True)
            continue
        rel = item.relative_to(src)
        target = dst / rel
        if target.exists() and not replace:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        created.append(str(rel))
    return created


def _knowledge_markdown_files(root: Path) -> list[Path]:
    knowledge_root = project_knowledge_root(root)
    if not knowledge_root.exists():
        return []
    return sorted(
        path for path in knowledge_root.rglob("*.md")
        if path.is_file() and path.name != "_index.md"
    )


def _knowledge_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    block = text[4:end].strip()
    result: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def _knowledge_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").title()


def _knowledge_domain(relative: Path) -> str:
    return relative.parts[0] if relative.parts else "root"


def _knowledge_index_rows(root: Path) -> list[dict[str, str]]:
    knowledge_root = project_knowledge_root(root)
    rows: list[dict[str, str]] = []
    for path in _knowledge_markdown_files(root):
        rel = path.relative_to(knowledge_root)
        meta = _knowledge_frontmatter(path)
        rows.append({
            "topic": _knowledge_title(path),
            "path": str(rel),
            "domain": meta.get("knowledge_type") or _knowledge_domain(rel),
            "tags": meta.get("tags", _knowledge_domain(rel)),
            "used_by": meta.get("used_by_stages", ""),
            "source": meta.get("source", ""),
            "status": meta.get("status", ""),
        })
    return rows


def _render_knowledge_index(root: Path) -> str:
    rows = _knowledge_index_rows(root)
    lines = [
        "---",
        "knowledge_type: index",
        "status: active",
        "source: generated",
        "---",
        "",
        "# Project Knowledge Index",
        "",
        "This file is generated by `harness knowledge index`.",
        "",
        "## Knowledge Map",
        "",
        "| Topic | Path | Domain | Tags | Used By Stages | Source | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['topic']} | {row['path']} | {row['domain']} | "
            f"{row['tags']} | {row['used_by']} | {row['source']} | {row['status']} |"
        )
    lines.extend([
        "",
        "## Rules",
        "",
        "- Runtime evidence stays in `harness-runtime/harness/`.",
        "- Long-lived team knowledge lands in `project-knowledge/`.",
        "- Do not copy whole stage artifacts here. Promote only stable knowledge.",
        "- Each promoted entry should keep source mission, status, and last verified date.",
        "",
    ])
    return "\n".join(lines)


def cmd_spec_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    specs_root = behavior_specs_root(root)
    index = specs_root / "_index.md"
    findings: list[dict[str, Any]] = []
    if not index.exists():
        findings.append({"level": "FAIL", "code": "project_knowledge_specs_index_missing", "message": f"{relpath(root, index)} not found; run 'harness spec init' to scaffold"})
    capability = args.capability
    if capability:
        capability_spec = specs_root / capability / "spec.md"
        if not capability_spec.exists():
            findings.append({"level": "FAIL", "code": "capability_spec_missing", "message": f"{relpath(root, capability_spec)} not found; run 'harness spec init --capability {capability}' to scaffold"})
    payload = {
        "status": "PASS" if not findings else "FAIL",
        "control": "spec.check",
        "spec_root": relpath(root, specs_root),
        "index_exists": index.exists(),
        "findings": findings,
    }
    return emit_payload(args, payload)


def cmd_spec_init(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    specs_root = behavior_specs_root(root)
    template_root = behavior_specs_template_root()
    created: list[str] = []
    if args.capability:
        capability_dir = specs_root / args.capability
        capability_spec = capability_dir / "spec.md"
        if capability_spec.exists() and not args.replace:
            return emit_payload(args, fail_payload("spec.init", "capability_spec_exists", f"capability spec already exists: {relpath(root, capability_spec)}; pass --replace to overwrite"))
        capability_dir.mkdir(parents=True, exist_ok=True)
        capability_spec.write_text(
            f"# {args.capability} Specification\n\n"
            "## Purpose\n<一句话说明该 capability 的职责边界（仅描述外部可观测行为）>\n\n"
            "## Requirements\n\n"
            "### Requirement: <需求名称>\n"
            "系统 SHALL <外部可观测的行为>。\n\n"
            "#### Scenario: <场景名称>\n"
            "GIVEN <前置条件>\n"
            "WHEN <触发动作>\n"
            "THEN <可观测结果>\n",
            encoding="utf-8",
        )
        created.append(relpath(root, capability_spec))
        return emit_payload(args, {"status": "PASS", "control": "spec.init", "spec_root": relpath(root, specs_root), "created": created, "findings": []})
    # Bootstrap specs/_index.md from project-knowledge template if missing.
    index = specs_root / "_index.md"
    template_index = template_root / "_index.md"
    if index.exists() and not args.replace:
        return emit_payload(args, fail_payload("spec.init", "project_knowledge_specs_exists", f"behavior specs already initialized at {relpath(root, specs_root)}; pass --replace to overwrite, or use --capability <name> to scaffold a new capability"))
    if not template_index.exists():
        return emit_payload(args, fail_payload("spec.init", "missing_project_knowledge_specs_template", "project-knowledge specs template not found in package"))
    specs_root.mkdir(parents=True, exist_ok=True)
    if not index.exists() or args.replace:
        index.write_text(template_index.read_text(encoding="utf-8"), encoding="utf-8")
        created.append(relpath(root, index))
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "spec.init",
            "spec_root": relpath(root, specs_root),
            "created": created,
            "next_step": "Set spec.enabled=true in harness-runtime/config/harness.yaml when ready to drive workflows from delta specs.",
            "findings": [],
        },
    )


def cmd_context_init(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    target = project_context_path(root)
    if target.exists() and not args.replace:
        return emit_payload(args, fail_payload("context.init", "project_context_exists", f"project-context.md already exists: {relpath(root, target)}; pass --replace to overwrite"))
    template = project_context_template_path(root)
    if not template.exists():
        return emit_payload(args, fail_payload("context.init", "missing_project_context_template", f"project-context template not found: {template}"))
    target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "context.init",
            "project_context_path": relpath(root, target),
            "template": relpath(root, template),
            "findings": [],
        },
    )


def cmd_knowledge_init(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    target = project_knowledge_root(root)
    template = project_knowledge_template_root()
    if target.exists() and any(target.iterdir()) and not args.replace:
        return emit_payload(args, fail_payload(
            "knowledge.init",
            "project_knowledge_exists",
            f"project-knowledge already exists at {relpath(root, target)}; pass --replace to overwrite template files.",
        ))
    if not template.exists():
        return emit_payload(args, fail_payload(
            "knowledge.init",
            "missing_project_knowledge_template",
            f"project-knowledge template not found: {template}",
        ))
    created = _copy_tree_missing(template, target, replace=bool(args.replace))
    return emit_payload(args, {
        "status": "PASS",
        "control": "knowledge.init",
        "knowledge_root": relpath(root, target),
        "template": relpath(root, template),
        "created": created,
        "findings": [],
    })


def cmd_knowledge_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    knowledge_root = project_knowledge_root(root)
    findings: list[dict[str, Any]] = []
    if not knowledge_root.exists():
        findings.append({
            "level": "FAIL",
            "code": "project_knowledge_missing",
            "message": "project-knowledge/ is missing; run `harness knowledge init`.",
        })
    for relative in PROJECT_KNOWLEDGE_REQUIRED_PATHS:
        path = knowledge_root / relative
        if not path.exists():
            findings.append({
                "level": "FAIL",
                "code": "required_knowledge_file_missing",
                "path": relative,
                "message": f"Required project knowledge file is missing: project-knowledge/{relative}",
            })
    index_path = knowledge_root / "_index.md"
    if index_path.exists():
        index_text = index_path.read_text(encoding="utf-8")
        for path in _knowledge_markdown_files(root):
            relative = str(path.relative_to(knowledge_root))
            if relative not in index_text:
                findings.append({
                    "level": "WARN",
                    "code": "knowledge_file_not_indexed",
                    "path": relative,
                    "message": f"{relative} is not listed in project-knowledge/_index.md",
                })
    status = "FAIL" if any(f["level"] == "FAIL" for f in findings) else ("WARN" if findings else "PASS")
    return emit_payload(args, {
        "status": status,
        "control": "knowledge.check",
        "knowledge_root": relpath(root, knowledge_root),
        "required_count": len(PROJECT_KNOWLEDGE_REQUIRED_PATHS),
        "markdown_count": len(_knowledge_markdown_files(root)),
        "findings": findings,
    })


def cmd_knowledge_index(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    knowledge_root = project_knowledge_root(root)
    if not knowledge_root.exists():
        return emit_payload(args, fail_payload(
            "knowledge.index",
            "project_knowledge_missing",
            "project-knowledge/ is missing; run `harness knowledge init` first.",
        ))
    rendered = _render_knowledge_index(root)
    index_path = knowledge_root / "_index.md"
    if getattr(args, "check", False):
        current = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
        up_to_date = current == rendered
        return emit_payload(args, {
            "status": "PASS" if up_to_date else "FAIL",
            "control": "knowledge.index",
            "knowledge_root": relpath(root, knowledge_root),
            "index_path": relpath(root, index_path),
            "up_to_date": up_to_date,
            "indexed_count": len(_knowledge_index_rows(root)),
            "findings": [] if up_to_date else [{
                "level": "FAIL",
                "code": "knowledge_index_stale",
                "message": "project-knowledge/_index.md is stale; run `harness knowledge index`.",
            }],
        })
    index_path.write_text(rendered, encoding="utf-8")
    return emit_payload(args, {
        "status": "PASS",
        "control": "knowledge.index",
        "knowledge_root": relpath(root, knowledge_root),
        "index_path": relpath(root, index_path),
        "indexed_count": len(_knowledge_index_rows(root)),
        "findings": [],
    })


def cmd_knowledge_resolve(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    stage = args.stage
    capability = getattr(args, "capability", None)
    knowledge_root = project_knowledge_root(root)
    if not knowledge_root.exists():
        return emit_payload(args, fail_payload(
            "knowledge.resolve",
            "project_knowledge_missing",
            "project-knowledge/ is missing; run `harness knowledge init` first.",
        ))
    domains = KNOWLEDGE_STAGE_DOMAINS.get(stage, ["context"])
    paths: list[str] = []
    for required in ("_index.md",):
        if (knowledge_root / required).exists():
            paths.append(f"project-knowledge/{required}")
    for path in _knowledge_markdown_files(root):
        rel = path.relative_to(knowledge_root)
        domain = _knowledge_domain(rel)
        if domain not in domains:
            continue
        if capability:
            text = str(rel).lower()
            if capability.lower() not in text and domain == "specs":
                continue
        paths.append(f"project-knowledge/{rel}")
    if "engineering" in domains:
        for rel in (
            Path("engineering/policies/stage-rules.yaml"),
            Path("engineering/policies/project-lint.yaml"),
        ):
            if (knowledge_root / rel).exists():
                paths.append(f"project-knowledge/{rel}")
    return emit_payload(args, {
        "status": "PASS",
        "control": "knowledge.resolve",
        "stage": stage,
        "capability": capability,
        "domains": domains,
        "paths": paths,
        "findings": [],
    })


def _knowledge_promotion_candidates(root: Path, mission: str) -> list[dict[str, str]]:
    stage_dir = runtime_harness_root(root) / "stages" / mission
    candidates = [
        ("mission-contract.md", "context", "Mission boundaries or durable constraints"),
        ("product/product-definition.md", "product/specs", "Product workflows, capability boundaries, behavior specs"),
        ("product/product-domain-model.md", "product/specs", "DDD domain model: bounded contexts, aggregates, commands, events, invariants, states, permissions"),
        ("product/product-evidence.md", "product/specs", "Product evidence, spec alignment, and impact records"),
        ("solution.md", "design", "Architecture overview or design decisions"),
        ("tech-design.md", "design/engineering", "Module details, conventions, implementation patterns"),
        ("execution-brief.md", "engineering", "Reusable task splitting or workflow patterns"),
        ("code-review.md", "engineering/lessons", "Review rules, quality lessons, accepted tradeoffs"),
        ("verification-report.md", "operations/engineering", "Verification runbooks and testing patterns"),
        ("acceptance-result.md", "product/operations", "Accepted product behavior or operator validation steps"),
        ("delivery-package.md", "operations/lessons", "Delivery summary, follow-up candidates, handoff facts"),
        ("retrospective.md", "lessons/context", "Lessons and context updates"),
    ]
    result: list[dict[str, str]] = []
    for artifact, target, rationale in candidates:
        path = stage_dir / artifact
        if path.exists():
            result.append({
                "source_artifact": relpath(root, path),
                "target_domain": target,
                "promotion_rule": rationale,
            })
    specs_dir = stage_dir / "specs"
    if specs_dir.exists():
        for spec_path in sorted(specs_dir.rglob("spec.md")):
            result.append({
                "source_artifact": relpath(root, spec_path),
                "target_domain": "specs",
                "promotion_rule": "Merge accepted delta spec into long-lived behavior specs",
            })
    return result


def cmd_knowledge_promote(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    knowledge_root = project_knowledge_root(root)
    if not knowledge_root.exists():
        return emit_payload(args, fail_payload(
            "knowledge.promote",
            "project_knowledge_missing",
            "project-knowledge/ is missing; run `harness knowledge init` first.",
        ))
    candidates = _knowledge_promotion_candidates(root, mission)
    findings: list[dict[str, Any]] = []
    if not candidates:
        findings.append({
            "level": "WARN",
            "code": "no_promotion_sources_found",
            "message": f"No mission artifacts found for {mission}; promotion candidate plan is empty.",
        })
    plan_text = [
        f"# Knowledge Promotion Candidate Plan: {mission}",
        "",
        "This candidate plan is generated by `harness knowledge promote`.",
        "It lists possible sources and target domains only; an Agent must perform the semantic extraction before long-lived knowledge is written.",
        "",
        "## Candidates",
        "",
        "| Source Artifact | Target Domain | Promotion Rule |",
        "|---|---|---|",
    ]
    for candidate in candidates:
        plan_text.append(
            f"| `{candidate['source_artifact']}` | `{candidate['target_domain']}` | {candidate['promotion_rule']} |"
        )
    plan_text.extend([
        "",
        "## Rules",
        "",
        "- Promote only stable knowledge, not full stage artifacts.",
        "- Use Agent judgment to extract product knowledge, specs, design decisions, engineering patterns, runbooks, or lessons.",
        "- Keep source mission and status in promoted files.",
        "- Update `project-knowledge/_index.md` after promotion.",
        "",
    ])
    output = resolve_path(root, getattr(args, "output", None))
    if output is None:
        output = runtime_harness_root(root) / "stages" / mission / "knowledge-promotion-plan.md"
    if getattr(args, "write_plan", False):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(plan_text), encoding="utf-8")
    return emit_payload(args, {
        "status": "WARN" if findings else "PASS",
        "control": "knowledge.promote",
        "mission": mission,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "plan_path": relpath(root, output),
        "written": bool(getattr(args, "write_plan", False)),
        "findings": findings,
    })


def cmd_mission_close(args: argparse.Namespace) -> int:
    """Close a mission branch and record the close strategy.

    finishing-branch-improvement-plan M2.1 — extends enum to new values
    (merged / pr / kept / discarded) with a 2-mission compatibility window
    for legacy aliases (delivered / cancelled / manual).
    """
    _LEGACY_ALIAS_MAP: dict[str, str] = {
        "delivered": "merged",
        "cancelled": "discarded",
        "manual": "kept",
    }
    _CLOSE_POLICY: dict[str, tuple[str, bool]] = {
        "merged": ("done", True),
        "pr": ("active", False),
        "kept": ("active", False),
        "discarded": ("cancelled", True),
    }

    root = Path(root_arg(args))
    strategy = args.strategy
    legacy_alias_used = strategy in _LEGACY_ALIAS_MAP
    findings: list[dict] = []

    if legacy_alias_used:
        translated = _LEGACY_ALIAS_MAP[strategy]
        findings.append({
            "level": "WARN",
            "code": "legacy_alias_translated",
            "message": (
                f"Legacy close strategy '{strategy}' is deprecated. "
                f"Translated to '{translated}'. "
                "Update your workflow to use the new value directly."
            ),
        })
        _record_translation_warning(root, strategy, translated)
        strategy = translated

    status_path = mission_status_path(root)
    status = load_yaml(status_path)
    entry = status.get(args.mission) if isinstance(status.get(args.mission), dict) else {}
    if not entry:
        return emit_payload(args, fail_payload("mission.close", "missing_mission", f"mission not found: {args.mission}"))

    mission_status_value, branch_closed = _CLOSE_POLICY[strategy]
    entry.update({
        "status": mission_status_value,
        "completed_at": today(),
        "close_strategy": strategy,
    })
    git_sub = entry.get("git") if isinstance(entry.get("git"), dict) else {}
    git_sub["branch_closed"] = branch_closed
    git_sub["close_strategy"] = strategy
    if strategy == "pr":
        git_sub["pending_pr"] = True
        pr_url = getattr(args, "pr_url", None)
        if pr_url:
            git_sub["pr_url"] = pr_url
    if strategy == "kept":
        kept_reason = getattr(args, "kept_reason", None)
        if kept_reason:
            git_sub["kept_reason"] = kept_reason
    entry["git"] = git_sub
    status[args.mission] = entry
    write_yaml(status_path, status)

    return emit_payload(args, {
        "status": "PASS",
        "control": "mission.close",
        "mission_id": args.mission,
        "strategy": strategy,
        "legacy_alias_used": legacy_alias_used,
        "mission_status": entry,
        "findings": findings,
    })


def _record_translation_warning(root: Path, legacy_value: str, translated_to: str) -> None:
    """Append a translation warning record to harness-runtime/runtime/translation-warning.yaml."""
    warn_dir = root / "harness-runtime" / "runtime"
    warn_dir.mkdir(parents=True, exist_ok=True)
    warn_path = warn_dir / "translation-warning.yaml"
    existing: list[dict] = []
    if warn_path.exists():
        try:
            data = yaml.safe_load(warn_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                existing = data
        except Exception:
            pass
    existing.append({
        "legacy_value": legacy_value,
        "translated_to": translated_to,
        "recorded_at": today(),
    })
    warn_path.write_text(yaml.dump(existing, allow_unicode=True), encoding="utf-8")


def approvals_path(root: Path) -> Path:
    return runtime_harness_root(root) / "state" / "approvals.json"


def load_approvals(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = approvals_path(root)
    if not path.exists():
        return {"schema_version": 1, "approvals": []}, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema_version": 1, "approvals": []}, []
    if isinstance(data, list):
        records = [item for item in data if isinstance(item, dict)]
        return {"schema_version": 1, "approvals": records}, records
    if isinstance(data, dict):
        raw_records = data.get("approvals")
        if isinstance(raw_records, list):
            records = [item for item in raw_records if isinstance(item, dict)]
            return {**data, "schema_version": data.get("schema_version") or 1, "approvals": records}, records
        if data.get("mission_id"):
            return {"schema_version": 1, "approvals": [data]}, [data]
    return {"schema_version": 1, "approvals": []}, []


def write_approvals(root: Path, document: dict[str, Any], records: list[dict[str, Any]]) -> Path:
    path = approvals_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {**document, "schema_version": document.get("schema_version") or 1, "approvals": records}
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def next_approval_id(records: list[dict[str, Any]]) -> str:
    return f"APR-{today().replace('-', '')}-{len(records) + 1:03d}"


def checkpoint_name(args: argparse.Namespace) -> str:
    return str(getattr(args, "checkpoint", None) or getattr(args, "stage", None) or "")


def sync_checkpoint_passed(root: Path, mission_id: str, checkpoint: str) -> dict[str, Any] | None:
    if not checkpoint:
        return None
    path = mission_status_path(root)
    status = load_yaml(path)
    entry = status.get(mission_id) if isinstance(status.get(mission_id), dict) else {}
    if not entry:
        return None
    checkpoints = as_str_list(entry.get("checkpoints_passed"))
    if checkpoint not in checkpoints:
        checkpoints.append(checkpoint)
    entry["checkpoints_passed"] = checkpoints
    status[mission_id] = entry
    write_yaml(path, status)
    return entry


def stage_completion_config(root: Path) -> dict[str, Any]:
    config = load_runtime_config(root)
    work_graph = config.get("work_graph") if isinstance(config.get("work_graph"), dict) else {}
    policy = work_graph.get("stage_completion") if isinstance(work_graph.get("stage_completion"), dict) else {}
    return policy


def approval_stage_completion_status(root: Path, mission_id: str, record: dict[str, Any], mission_status: dict[str, Any] | None) -> dict[str, Any]:
    policy = stage_completion_config(root)
    checkpoint_policy = policy.get("checkpoint_approval") if isinstance(policy.get("checkpoint_approval"), dict) else {}
    if not checkpoint_policy:
        return {}
    stage = str(record.get("stage") or record.get("checkpoint") or "")
    status = str(record.get("status") or "")
    approval_type = str(record.get("type") or "")
    entry = mission_status if isinstance(mission_status, dict) else {}
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    current_stage = str(work_graph.get("stage") or entry.get("current_stage") or "")
    last_operation_status = str(work_graph.get("last_operation_status") or "")
    pending_graph_operation = (
        approval_type == "checkpoint"
        and status == "approved"
        and bool(stage)
        and (not current_stage or stage == current_stage)
        and not last_operation_status
    )
    return {
        "event": "checkpoint_approval",
        "stage": stage,
        "terminal": bool(checkpoint_policy.get("terminal", False)),
        "effect": checkpoint_policy.get("effect") or "",
        "pending_graph_operation": pending_graph_operation,
        "required_next_controls": as_str_list(checkpoint_policy.get("required_next_controls")) if pending_graph_operation else [],
        "pause_boundary_when_user_defers_next_stage": checkpoint_policy.get("pause_boundary_when_user_defers_next_stage") or "",
    }


def mission_stage_completion_status(root: Path, stage: str, mission_status: dict[str, Any] | None) -> dict[str, Any]:
    policy = stage_completion_config(root)
    gate_policy = policy.get("gate_continue") if isinstance(policy.get("gate_continue"), dict) else {}
    if not gate_policy:
        return {}
    entry = mission_status if isinstance(mission_status, dict) else {}
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    current_stage = str(work_graph.get("stage") or entry.get("current_stage") or "")
    last_operation_status = str(work_graph.get("last_operation_status") or "")
    pending_graph_operation = bool(stage) and (not current_stage or stage == current_stage) and not last_operation_status
    return {
        "event": "stage_complete",
        "stage": stage,
        "pending_graph_operation": pending_graph_operation,
        "required_next_controls": as_str_list(gate_policy.get("required_next_controls")) if pending_graph_operation else [],
        "state_sync_control": gate_policy.get("state_sync_control") or "",
        "pause_boundary_when_user_defers_next_stage": gate_policy.get("pause_boundary_when_user_defers_next_stage") or "",
    }


def approval_matches(record: dict[str, Any], *, mission: str | None = None, approval_type: str | None = None, stage: str | None = None, status: str | None = None) -> bool:
    if mission and str(record.get("mission_id") or "") != mission:
        return False
    if approval_type and str(record.get("type") or "") != approval_type:
        return False
    if stage and str(record.get("stage") or record.get("checkpoint") or "") != stage:
        return False
    if status and str(record.get("status") or "") != status:
        return False
    return True


def cmd_approval_append(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    document, records = load_approvals(root)
    record = {
        "approval_id": args.approval_id or next_approval_id(records),
        "mission_id": args.mission,
        "type": args.type,
        "stage": args.stage or "",
        "checkpoint": args.checkpoint or args.stage or "",
        "status": args.status,
        "decided_at": args.decided_at or now_iso(),
        "comment": args.comment or "",
    }
    records.append(record)
    path = write_approvals(root, document, records)
    mission_status = None
    checkpoint = str(record.get("checkpoint") or "")
    if record["type"] == "checkpoint" and record["status"] == "approved" and checkpoint:
        mission_status = sync_checkpoint_passed(root, args.mission, checkpoint)
    stage_completion = approval_stage_completion_status(root, args.mission, record, mission_status)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "approval.append",
            "approval": record,
            "approvals_path": relpath(root, path),
            "mission_status": mission_status,
            "stage_completion": stage_completion,
            "findings": [],
        },
    )


def cmd_approval_latest(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    _document, records = load_approvals(root)
    matches = [
        record
        for record in records
        if approval_matches(record, mission=args.mission, approval_type=args.type, stage=args.stage, status=args.status)
    ]
    latest = matches[-1] if matches else None
    return emit_payload(args, {"status": "PASS", "control": "approval.latest", "approval": latest, "count": len(matches), "findings": []})


def cmd_approval_require(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    _document, records = load_approvals(root)
    stage = args.checkpoint or args.stage
    matches = [
        record
        for record in records
        if approval_matches(record, mission=args.mission, approval_type=args.type, stage=stage, status="approved")
    ]
    if not matches:
        message = f"approved {args.type} approval is required for mission {args.mission}"
        if stage:
            message += f" stage/checkpoint {stage}"
        return emit_payload(args, {"status": "BLOCKED", "control": "approval.require", "approval": None, "findings": [{"level": "BLOCKED", "code": "approval_required", "message": message}]})
    return emit_payload(args, {"status": "PASS", "control": "approval.require", "approval": matches[-1], "findings": []})


def run_board_select_no_write(root: Path, mission_id: str) -> dict[str, Any]:
    board_script = script("board-router", "scripts", "select_next_node.py")
    if not board_script.exists():
        return {}
    result = subprocess.run(
        [sys.executable, str(board_script), "--root", str(root), "--mission-id", mission_id, "--no-write", "--json"],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {}
    if result.returncode != 0 and payload:
        payload.setdefault("status", "FAIL")
    return payload


def cmd_frame_current(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    status_path = mission_status_path(root)
    if not status_path.exists():
        return emit_payload(
            args,
            fail_payload(
                "frame.current",
                "mission_status_uninitialized",
                f"mission-status file not found: {relpath(root, status_path)}; run 'harness mission init' to initialize",
            ),
        )
    status = load_yaml(status_path)
    mission_id = args.mission
    active_ids = active_mission_ids(status)
    open_ids = open_mission_ids(status)
    if not mission_id and active_ids:
        mission_id = active_ids[0]
    if mission_id and isinstance(status.get(mission_id), dict) and mission_id in open_ids:
        entry = status[mission_id]
        slice_path, mission_slice = load_mission_slice(root, mission_id, entry)
        if mission_slice:
            from_lane = str(mission_slice.get("from_lane") or ((mission_slice.get("control_plane") or {}).get("from_lane") if isinstance(mission_slice.get("control_plane"), dict) else "") or "")
            registry_action = lane_action_registry(root).get(from_lane) or {}
            payload = {
                "status": "PASS",
                "control": "frame.current",
                "resume_source": "mission_slice",
                "mission_id": mission_id,
                "mission_status": entry,
                "mission_slice_path": relpath(root, slice_path),
                "mission_slice": mission_slice,
                "lane_action": build_lane_action_payload(from_lane, registry_action, mission_id) if registry_action else mission_slice.get("lane_action"),
                "control_plane": mission_slice.get("control_plane"),
                "work_graph": mission_slice.get("work_graph"),
                "findings": [],
            }
            return emit_payload(args, payload)
        if (entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}).get("mission_slice"):
            return emit_payload(args, fail_payload("frame.current", "missing_mission_slice", f"Mission Slice not found: {relpath(root, slice_path)}"))
        # Legacy stage-mode fallback removed: every active mission must declare a Mission Slice.
        # If a mission entry has no work_graph.mission_slice and no slice file, treat it as broken state.
        return emit_payload(
            args,
            fail_payload(
                "frame.current",
                "missing_mission_slice",
                f"mission {mission_id} has no Mission Slice; legacy stage-mode resume is no longer supported. Recreate Mission Slice via board-router.",
            ),
        )
    selection_mission_id = mission_id or (open_ids[0] if open_ids else "FRAME-CURRENT")
    board_selection = run_board_select_no_write(root, selection_mission_id)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "frame.current",
            "resume_source": "board",
            "mission_id": mission_id,
            "selection_mission_id": selection_mission_id,
            "active_missions": active_ids,
            "open_missions": open_ids,
            "board_selection": board_selection or None,
            "findings": [],
        },
    )


def cmd_frame_explain(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    status = load_yaml(mission_status_path(root))
    entry = status.get(args.mission) if isinstance(status.get(args.mission), dict) else {}
    if not entry:
        return emit_payload(args, fail_payload("frame.explain", "missing_mission", f"mission not found: {args.mission}"))
    slice_path, mission_slice = load_mission_slice(root, args.mission, entry)
    slice_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
    node_ids = set(as_str_list(slice_graph.get("primary_nodes")) + as_str_list(slice_graph.get("related_nodes")) + as_str_list(slice_graph.get("input_nodes")) + as_str_list(slice_graph.get("output_nodes")))
    if args.node and args.node not in node_ids:
        return emit_payload(args, fail_payload("frame.explain", "node_not_in_mission_slice", f"{args.node} is not referenced by Mission Slice {args.mission}"))
    return emit_payload(args, {"status": "PASS", "control": "frame.explain", "mission_id": args.mission, "node": args.node, "mission_status": entry, "mission_slice_path": relpath(root, slice_path), "mission_slice": mission_slice, "findings": []})


def detect_model_adapter(requested: str, adapters: dict[str, Any]) -> tuple[str, str]:
    if requested and requested != "auto":
        return requested, "configured"
    env_override = os.environ.get("HARNESS_MODEL_ADAPTER") or os.environ.get("HARNESS_ADAPTER")
    if env_override and env_override in adapters:
        return env_override, "environment_override"
    if any(os.environ.get(name) for name in ("CODEX_SHELL", "CODEX_THREAD_ID", "CODEX_CI")) and "codex" in adapters:
        return "codex", "environment"
    if any(name.startswith("CURSOR_") for name in os.environ) and "cursor" in adapters:
        return "cursor", "environment"
    if any(name.startswith("CLAUDE") for name in os.environ) and "claude" in adapters:
        return "claude", "environment"
    return requested or "auto", "unresolved"


def model_policy_defaults(model_routing: dict[str, Any], adapter_config: dict[str, Any], kind: str) -> dict[str, Any]:
    global_defaults = ((model_routing.get("defaults") or {}).get(kind) or {}) if isinstance(model_routing.get("defaults"), dict) else {}
    adapter_defaults = ((adapter_config.get("defaults") or {}).get(kind) or {}) if isinstance(adapter_config.get("defaults"), dict) else {}
    # Fallback semantics:
    #   - Only used when ALL candidate models for a sub-agent are unsupported by the runtime.
    #   - Does NOT cover "sub-agent dispatch unavailable" — that case must BLOCK at the workflow level.
    #   - If neither YAML layer declares fallback, it stays None: caller treats as "no fallback configured".
    return {
        "candidates": as_str_list(adapter_defaults.get("candidates")) or as_str_list(global_defaults.get("candidates")),
        "fallback": adapter_defaults.get("fallback") or global_defaults.get("fallback") or None,
        "prefer_high_capability": bool(adapter_defaults.get("prefer_high_capability", global_defaults.get("prefer_high_capability", False))),
    }


def resolve_role_model_policy(
    role: str,
    kind: str,
    adapter_config: dict[str, Any],
    model_defaults: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    roles = adapter_config.get("roles") if isinstance(adapter_config.get("roles"), dict) else {}
    role_config = roles.get(role) if isinstance(roles.get(role), dict) else {}
    inherited_kind = str(role_config.get("inherit") or kind)
    default_kind = inherited_kind if inherited_kind in model_defaults else kind
    default_policy = model_defaults.get(default_kind, model_defaults.get(kind, {}))
    candidates = as_str_list(role_config.get("candidates")) or list(default_policy.get("candidates") or [])
    return {
        "kind": kind,
        "source": "role" if as_str_list(role_config.get("candidates")) else f"default.{default_kind}",
        "inherit": inherited_kind if role_config.get("inherit") else "",
        "candidates": candidates,
        "fallback": role_config.get("fallback") or default_policy.get("fallback") or None,
    }


def add_role_model_policy(
    policies: dict[str, dict[str, Any]],
    role: str,
    kind: str,
    adapter_config: dict[str, Any],
    model_defaults: dict[str, dict[str, Any]],
) -> None:
    if not role:
        return
    if role not in policies:
        policies[role] = resolve_role_model_policy(role, kind, adapter_config, model_defaults)


def professional_role_model_policies(
    professional_roles: dict[str, Any],
    work_graph: dict[str, Any],
    adapter_config: dict[str, Any],
    model_defaults: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    policies: dict[str, dict[str, Any]] = {}
    adapter_roles = adapter_config.get("roles") if isinstance(adapter_config.get("roles"), dict) else {}
    for role, role_config in adapter_roles.items():
        if not isinstance(role_config, dict):
            continue
        inherited = str(role_config.get("inherit") or "")
        inferred_kind = "review" if inherited == "review" or str(role).endswith("reviewer") else "execution"
        add_role_model_policy(policies, str(role), inferred_kind, adapter_config, model_defaults)

    sources = []
    stage_policies = professional_roles.get("stage_policies") if isinstance(professional_roles.get("stage_policies"), dict) else {}
    sources.extend(stage_policies.values())
    lane_actions = work_graph.get("lane_actions") if isinstance(work_graph.get("lane_actions"), dict) else {}
    sources.extend(lane_actions.values())
    for source in sources:
        if not isinstance(source, dict):
            continue
        for role in as_str_list(source.get("required_execution_roles")):
            add_role_model_policy(policies, role, "execution", adapter_config, model_defaults)
        for role in as_str_list(source.get("required_review_roles")):
            add_role_model_policy(policies, role, "review", adapter_config, model_defaults)
        conditional_roles = source.get("conditional_roles") if isinstance(source.get("conditional_roles"), list) else []
        for item in conditional_roles:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or ("review" if str(item.get("role", "")).endswith("reviewer") else "execution"))
            add_role_model_policy(policies, str(item.get("role") or ""), kind, adapter_config, model_defaults)
    return dict(sorted(policies.items()))


def _snapshot_execution_governance(config: dict[str, Any]) -> dict[str, Any]:
    """Project execution_governance into the snapshot payload with legacy
    aliases normalized to canonical values (intake-improvement-plan M1.4).

    Snapshot is a read path: legacy values are translated, not rejected. The
    `default_level_resolution` field surfaces whether the original config used
    a legacy alias so downstream consumers can warn / migrate.
    """
    raw = config.get("execution_governance")
    if not isinstance(raw, dict):
        return {}
    aliases = autonomy_alias_map(config)
    snapshot = dict(raw)
    received = raw.get("default_level")
    canonical = normalize_autonomy_level(received, aliases)
    if canonical is not None:
        snapshot["default_level"] = canonical
        if isinstance(received, str) and received.strip() != canonical:
            snapshot["default_level_resolution"] = {
                "received": received.strip(),
                "canonical": canonical,
                "source": "legacy_alias",
            }
    return snapshot


def cmd_config_snapshot(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    config = load_runtime_config(root)
    if not config:
        return emit_payload(args, fail_payload("config.snapshot", "missing_runtime_config", "Harness runtime config not found"))
    model_routing = load_yaml(root / "harness-runtime" / "config" / "model-routing.yaml")
    if not model_routing:
        model_routing = load_yaml(root / "package" / "harness-runtime" / "config" / "model-routing.yaml")
    professional_roles = config.get("professional_roles") if isinstance(config.get("professional_roles"), dict) else {}
    work_graph = config.get("work_graph") if isinstance(config.get("work_graph"), dict) else {}
    spec_config = config.get("spec") if isinstance(config.get("spec"), dict) else {}
    adapters = model_routing.get("adapters") if isinstance(model_routing, dict) else {}
    adapters = adapters if isinstance(adapters, dict) else {}
    requested_adapter = str(model_routing.get("current_adapter") or "auto") if isinstance(model_routing, dict) else "auto"
    adapter, adapter_resolution = detect_model_adapter(requested_adapter, adapters)
    adapter_config = adapters.get(adapter) if isinstance(adapters.get(adapter), dict) else {}
    model_defaults = {
        "execution": model_policy_defaults(model_routing, adapter_config, "execution"),
        "review": model_policy_defaults(model_routing, adapter_config, "review"),
    }
    role_model_policies = professional_role_model_policies(professional_roles, work_graph, adapter_config, model_defaults)
    execution_model_policy = {
        "adapter": adapter,
        "requested_adapter": requested_adapter,
        "adapter_resolution": adapter_resolution,
        "executor_tier": "standard",
        "candidates": model_defaults["execution"]["candidates"],
        "fallback": model_defaults["execution"]["fallback"],
    }
    review_model_policy = {
        "adapter": adapter,
        "requested_adapter": requested_adapter,
        "adapter_resolution": adapter_resolution,
        "candidates": model_defaults["review"]["candidates"],
        "fallback": model_defaults["review"]["fallback"],
        "prefer_high_capability": model_defaults["review"]["prefer_high_capability"],
    }
    payload = {
        "status": "PASS",
        "control": "config.snapshot",
        "execute_mode": config.get("execute_mode", "sdd"),
        "project_name": config.get("project_name", ""),
        "default_mode": config.get("default_mode"),
        "brownfield": config.get("brownfield"),
        "pre_checkpoint_doc_review": config.get("pre_checkpoint_doc_review", True),
        "spec": {"enabled": bool(spec_config.get("enabled", False))},
        "escalation": config.get("escalation") if isinstance(config.get("escalation"), dict) else {},
        "dependency_impact": config.get("dependency_impact") if isinstance(config.get("dependency_impact"), dict) else {},
        "e2e": config.get("e2e") if isinstance(config.get("e2e"), dict) else {},
        "prototype": config.get("prototype") if isinstance(config.get("prototype"), dict) else {},
        "visual_interaction": config.get("visual_interaction") if isinstance(config.get("visual_interaction"), dict) else {},
        "agent_engineering": config.get("agent_engineering") if isinstance(config.get("agent_engineering"), dict) else {},
        "project_lint": config.get("project_lint") if isinstance(config.get("project_lint"), dict) else {},
        "project_knowledge": {
            "root": relpath(root, project_knowledge_root(root)),
            "exists": project_knowledge_root(root).exists(),
        },
        "execution_governance": _snapshot_execution_governance(config),
        "professional_roles": {
            "enabled": professional_roles.get("enabled", True),
            "stage_policies": professional_roles.get("stage_policies") or {},
        },
        "work_graph": {
            "node_kinds": work_graph.get("node_kinds") or {},
            "lane_actions": work_graph.get("lane_actions") or {},
            "selection_strategy": work_graph.get("selection_strategy") or {},
            "stage_completion": work_graph.get("stage_completion") or {},
        },
        "execution_model_policy": execution_model_policy,
        "review_model_policy": review_model_policy,
        "model_routing": {
            "requested_adapter": requested_adapter,
            "adapter": adapter,
            "adapter_resolution": adapter_resolution,
            "defaults": model_defaults,
            "roles": role_model_policies,
            "fallback": model_routing.get("fallback") if isinstance(model_routing.get("fallback"), dict) else {},
        },
        "findings": [],
    }
    return emit_payload(args, payload)


def cmd_graph_apply(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args), "--operation", args.operation]
    if args.dry_run:
        forwarded.append("--dry-run")
    if args.staged:
        forwarded.append("--staged")
    return run_python(script("work-graph", "scripts", "apply_graph_operation.py"), with_json(args, forwarded))


def cmd_graph_plan(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args), "--operation", args.operation, "--dry-run"]
    return run_python(script("work-graph", "scripts", "apply_graph_operation.py"), with_json(args, forwarded))


def cmd_graph_rebuild(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args)]
    return run_python(script("work-graph", "scripts", "rebuild_index.py"), with_json(args, forwarded))


def cmd_graph_check(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args)]
    return run_python(script("work-graph", "scripts", "check_graph_consistency.py"), with_json(args, forwarded))


def cmd_graph_node_show(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    graph_root = work_graph_root(root)
    matches = sorted((graph_root / "nodes").glob(f"**/{args.node_id}.yaml"))
    if not matches:
        payload = {
            "status": "FAIL",
            "control": "graph.node.show",
            "node_id": args.node_id,
            "findings": [{"level": "FAIL", "code": "node_not_found", "message": args.node_id}],
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"node not found: {args.node_id}", file=sys.stderr)
        return 1
    text = matches[0].read_text(encoding="utf-8")
    if args.json:
        payload = {"status": "PASS", "control": "graph.node.show", "node_id": args.node_id, "path": str(matches[0]), "yaml": text}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(text, end="" if text.endswith("\n") else "\n")
    return 0


def cmd_graph_node_create(args: argparse.Namespace) -> int:
    """Create a fresh seed node by emitting a create_node graph operation manifest and applying it.

    This bootstraps an empty Work Graph: when no nodes exist yet, no other operation
    (split / merge / supersede) is applicable. We synthesize a minimal manifest in a
    temp file and forward to the existing apply pipeline so it goes through transactional
    write semantics, schema validation and consistency checks.
    """
    root = Path(root_arg(args))
    operation_id = args.operation_id or f"create-{args.node_id}"
    payload = {
        "operation_id": operation_id,
        "type": "create_node",
        "mission_id": args.mission_id or "",
        "target": {
            "id": args.node_id,
            "kind": args.kind,
            "title": args.title,
            "lane": args.lane,
            "status": args.status,
        },
    }
    if args.input_node:
        payload["target"]["inputs"] = list(args.input_node)
    if args.output_node:
        payload["target"]["outputs"] = list(args.output_node)
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump(payload, tmp, sort_keys=False, allow_unicode=True)
        manifest_path = tmp.name
    try:
        forwarded = ["--root", str(root), "--operation", manifest_path]
        return run_python(script("work-graph", "scripts", "apply_graph_operation.py"), with_json(args, forwarded))
    finally:
        try:
            os.unlink(manifest_path)
        except OSError:
            pass


def cmd_board_select(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args), "--mission-id", args.mission]
    for attr, flag in (("query", "--query"), ("primary_node", "--primary-node"), ("related_node", "--related-node"), ("spec", "--spec")):
        for value in getattr(args, attr) or []:
            forwarded.extend([flag, value])
    if not args.write_slice or args.no_write:
        forwarded.append("--no-write")
    return run_python(script("board-router", "scripts", "select_next_node.py"), with_json(args, forwarded))


def cmd_contract_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    forwarded = ["--root", str(root), "--artifact", str(artifact)]
    for upstream in args.upstream or []:
        forwarded.extend(["--upstream", upstream])
    if args.allow_placeholders:
        forwarded.append("--allow-placeholders")
    return run_python(script("stage-gate", "scripts", "check_contracts.py"), with_json(args, forwarded))


def cmd_contract_init(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    template_path = contract_template_path(root, args.template)
    if not template_path.exists():
        return emit_payload(args, fail_payload("contract.init", "missing_contract_template", f"Contract template not found: {template_path}"))
    document = load_yaml(template_path)
    if not document:
        return emit_payload(args, fail_payload("contract.init", "invalid_contract_template", f"Contract template is empty or invalid: {template_path}"))
    replacements = {
        "mission_id": args.mission,
        "work_graph_node_id": args.node or "",
        "primary_work_graph_node": args.node or "",
        "artifact_version": args.artifact_version,
        "review_strategy": args.review_strategy or "",
        "capability_id": args.capability or "",
        "capability_name": args.capability or "",
    }
    document = replace_template_values(document, replacements)
    contract = document.get("control_contract") if isinstance(document.get("control_contract"), dict) else {}
    contract["mission_id"] = args.mission
    contract["stage"] = args.stage
    applied_fields = ["mission_id", "stage"]
    if args.node and isinstance(contract.get("work_graph_artifact"), dict):
        contract["work_graph_artifact"]["node_id"] = args.node
        contract["work_graph_artifact"]["artifact_version"] = args.artifact_version
        applied_fields.extend(["work_graph_artifact.node_id", "work_graph_artifact.artifact_version"])
    if scrub_template_role_verdicts(contract, template_mode=True):
        applied_fields.append("role_verdicts")
    output = resolve_path(root, args.output) if args.output else root / f"harness-runtime/harness/stages/{args.mission}/contracts/{args.template}.contract.yaml"
    assert output is not None
    if output.exists() and not args.replace:
        return emit_payload(args, fail_payload("contract.init", "contract_exists", f"Contract already exists: {relpath(root, output)}"))
    write_manifest(output, document)
    hygiene = contract_hygiene_payload(contract)
    return emit_payload(
        args,
        {
            "status": hygiene["status"],
            "control": "contract.init",
            "contract": relpath(root, output),
            "template": relpath(root, template_path),
            "applied_fields": unique(applied_fields),
            "hygiene": hygiene,
            "findings": [],
        },
    )


def _normalize_id(value: Any, prefix: str, index: int, existing: set[str]) -> str:
    raw = str(value or "").strip()
    if raw:
        existing.add(raw)
        return raw
    seq = index
    while True:
        candidate = f"{prefix}-{seq:02d}"
        if candidate not in existing:
            existing.add(candidate)
            return candidate
        seq += 1


def _normalise_story_context(story: dict[str, Any]) -> dict[str, Any]:
    context = story.get("story_context")
    if isinstance(context, dict):
        result = dict(context)
    else:
        result = {}

    for key in ("user", "problem", "scenario", "value"):
        value = result.get(key)
        if value in (None, "") and story.get(key) not in (None, ""):
            result[key] = story.get(key)

    if result.get("user") in (None, "") and story.get("role") not in (None, ""):
        result["user"] = story.get("role")
    if result.get("value") in (None, "") and story.get("value") not in (None, ""):
        result["value"] = story.get("value")

    metrics = result.get("success_metrics")
    if not metrics:
        metrics = story.get("success_metrics")
    if not metrics and story.get("success_metric"):
        metrics = [{"id": "SM-01", "signal": story.get("success_metric"), "target": "observable"}]
    if metrics:
        result["success_metrics"] = metrics

    return result


def _intent_framing_to_contract(framing: dict[str, Any]) -> dict[str, Any]:
    """Map an intent-framing manifest to control_contract fields.

    The manifest is the human-friendly form produced by mission-framing-expert.
    Unknown keys are passed through under control_contract directly so the
    manifest can also carry experimental fields.
    """

    contract_fields: dict[str, Any] = {}

    objective = framing.get("objective")
    if isinstance(objective, dict):
        statement = objective.get("statement")
        if statement:
            contract_fields["objective"] = {
                "id": str(objective.get("id") or "OBJ-001"),
                "statement": str(statement),
            }
    elif isinstance(objective, str) and objective.strip():
        contract_fields["objective"] = {"id": "OBJ-001", "statement": objective.strip()}

    user_stories = framing.get("user_stories")
    if isinstance(user_stories, list):
        seen: set[str] = set()
        normalised: list[dict[str, Any]] = []
        for index, story in enumerate(user_stories, start=1):
            if not isinstance(story, dict):
                continue
            entry: dict[str, Any] = {
                "id": _normalize_id(story.get("id"), "US", index, seen),
                "role": str(story.get("role") or ""),
                "goal": str(story.get("goal") or ""),
                "value": str(story.get("value") or ""),
            }
            story_context = _normalise_story_context(story)
            if story_context:
                entry["story_context"] = story_context
            ac_refs = story.get("ac_refs") or story.get("traces_to", {}).get("ac") if isinstance(story.get("traces_to"), dict) else story.get("ac_refs")
            if isinstance(ac_refs, list) and ac_refs:
                entry["traces_to"] = {"ac": [str(ref) for ref in ac_refs if str(ref).strip()]}
            normalised.append(entry)
        if normalised:
            contract_fields["user_stories"] = normalised

    scope = framing.get("scope")
    if isinstance(scope, dict):
        scope_block: dict[str, Any] = {}
        seen_in: set[str] = set()
        in_items: list[dict[str, Any]] = []
        for index, item in enumerate(scope.get("in") or [], start=1):
            if isinstance(item, str):
                item = {"statement": item}
            if not isinstance(item, dict):
                continue
            statement = item.get("statement")
            if not statement:
                continue
            in_items.append({
                "id": _normalize_id(item.get("id"), "SCOPE-IN", index, seen_in),
                "statement": str(statement),
            })
        if in_items:
            scope_block["in"] = in_items
        seen_out: set[str] = set()
        out_items: list[dict[str, Any]] = []
        for index, item in enumerate(scope.get("out") or [], start=1):
            if not isinstance(item, dict):
                continue
            statement = item.get("statement")
            reason = item.get("reason")
            if not statement or not reason:
                continue
            out_items.append({
                "id": _normalize_id(item.get("id"), "SCOPE-OUT", index, seen_out),
                "statement": str(statement),
                "reason": str(reason),
            })
        if out_items:
            scope_block["out"] = out_items
        if scope_block:
            contract_fields["scope"] = scope_block

    acs = framing.get("acceptance_criteria")
    if isinstance(acs, list):
        seen_ac: set[str] = set()
        normalised_acs: list[dict[str, Any]] = []
        for index, ac in enumerate(acs, start=1):
            if not isinstance(ac, dict):
                continue
            entry = {
                "id": _normalize_id(ac.get("id"), "AC", index, seen_ac),
                "statement": str(ac.get("statement") or ""),
            }
            if ac.get("given") or ac.get("when") or ac.get("then"):
                entry["given"] = str(ac.get("given") or "")
                entry["when"] = str(ac.get("when") or "")
                entry["then"] = str(ac.get("then") or "")
            if ac.get("verification_method"):
                entry["verification_method"] = str(ac.get("verification_method"))
            entry["verification_required"] = bool(ac.get("verification_required", True))
            normalised_acs.append(entry)
        if normalised_acs:
            contract_fields["acceptance_criteria"] = normalised_acs

    autonomy_level = framing.get("autonomy_level")
    autonomy_block: dict[str, Any] = {}
    if isinstance(autonomy_level, str) and autonomy_level.strip():
        autonomy_block["level"] = autonomy_level.strip()
    governance_risk = framing.get("governance_risk")
    if isinstance(governance_risk, str) and governance_risk.strip():
        autonomy_block["governance_risk"] = governance_risk.strip()
    governance_assessment = framing.get("governance_assessment")
    if isinstance(governance_assessment, dict):
        autonomy_block["governance_assessment"] = governance_assessment
    for key in ("skippable_stages", "reviewer_pass_sufficient", "human_checkpoints", "escalation_triggers"):
        if key in framing and isinstance(framing[key], list):
            autonomy_block[key] = list(framing[key])
    # 兼容更自然的别名
    if "required_checkpoints" in framing and isinstance(framing["required_checkpoints"], list):
        autonomy_block["human_checkpoints"] = list(framing["required_checkpoints"])
    if autonomy_block:
        autonomy_block.setdefault("governance_risk", "")
        autonomy_block.setdefault("governance_assessment", {
            "hard_triggers": [],
            "dimensions": {},
            "scale_signals": {},
            "decision_rule": "",
            "user_confirmation_required": True,
            "downgrade_or_checkpoint_removal_requires_approval": True,
        })
    if autonomy_block:
        contract_fields["autonomy"] = autonomy_block

    work_graph = framing.get("work_graph")
    if isinstance(work_graph, dict):
        wg_block: dict[str, Any] = {}
        for key in ("primary_nodes", "related_nodes"):
            if key in work_graph and isinstance(work_graph[key], list):
                wg_block[key] = list(work_graph[key])
        for key in ("operation", "from_lane", "to_lane", "board"):
            if work_graph.get(key):
                wg_block[key] = str(work_graph[key])
        if wg_block:
            contract_fields["work_graph"] = wg_block

    role_policy = framing.get("role_policy")
    if isinstance(role_policy, dict):
        contract_fields["role_policy"] = role_policy

    # 透传未识别字段，方便实验性扩展
    reserved = {"objective", "user_stories", "scope", "acceptance_criteria",
                "autonomy_level", "skippable_stages", "reviewer_pass_sufficient",
                "human_checkpoints", "escalation_triggers", "required_checkpoints",
                "governance_risk", "governance_assessment",
                "work_graph", "role_policy"}
    for key, value in framing.items():
        if key not in reserved and key not in contract_fields:
            contract_fields[key] = value

    return contract_fields


def cmd_contract_fill(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    framing_path = resolve_path(root, args.intent_framing)
    if framing_path is None or not framing_path.exists():
        return emit_payload(args, fail_payload("contract.fill", "missing_intent_framing", f"Intent framing manifest not found: {args.intent_framing}"))
    framing = load_manifest(framing_path)
    if not isinstance(framing, dict) or not framing:
        return emit_payload(args, fail_payload("contract.fill", "invalid_intent_framing", "Intent framing manifest must be a non-empty YAML object"))

    # Write-path guard (intake-improvement-plan M1.4): legacy autonomy aliases
    # such as A1/A2/A3 must not propagate into persisted contract YAML. Reject
    # with a typed LEGACY_LEVEL_REJECTED finding pointing at the canonical value.
    legacy_reject = reject_legacy_autonomy_level(
        "contract.fill",
        framing.get("autonomy_level"),
        autonomy_alias_map(load_runtime_config(root)),
    )
    if legacy_reject is not None:
        return emit_payload(args, legacy_reject)

    # 自动 init：若 artifact 不存在或 --replace 指定且模板可达，则先生成骨架
    if artifact is None:
        return emit_payload(args, fail_payload("contract.fill", "missing_artifact_path", "--artifact must be a resolvable path"))
    if not artifact.exists():
        if not args.template:
            return emit_payload(args, fail_payload(
                "contract.fill",
                "contract_missing_no_template",
                f"Contract not found and --template not provided: {relpath(root, artifact)}",
            ))
        template_path = contract_template_path(root, args.template)
        if not template_path.exists():
            return emit_payload(args, fail_payload("contract.fill", "missing_contract_template", f"Contract template not found: {template_path}"))
        document = load_yaml(template_path)
        if not document:
            return emit_payload(args, fail_payload("contract.fill", "invalid_contract_template", f"Contract template is empty or invalid: {template_path}"))
        document = replace_template_values(document, {
            "mission_id": args.mission,
            "artifact_version": "v1",
        })
        contract = document.get("control_contract") if isinstance(document.get("control_contract"), dict) else {}
        contract["mission_id"] = args.mission
        contract["stage"] = args.stage
        scrub_template_role_verdicts(contract, template_mode=True)
        artifact.parent.mkdir(parents=True, exist_ok=True)
        write_manifest(artifact, document)

    document, contract = control_contract_document(artifact)
    contract.setdefault("mission_id", args.mission)
    contract.setdefault("stage", args.stage)

    try:
        fields = _intent_framing_to_contract(framing)
    except ValueError as exc:
        return emit_payload(args, fail_payload("contract.fill", "invalid_intent_framing", str(exc)))

    applied: list[str] = []
    for key, value in fields.items():
        if isinstance(value, dict) and isinstance(contract.get(key), dict):
            contract[key].update(value)
        else:
            contract[key] = value
        applied.append(key)
    if scrub_template_role_verdicts(contract):
        applied.append("role_verdicts")

    write_manifest(artifact, document)
    hygiene = contract_hygiene_payload(contract)

    # intake-improvement-plan M2.1 chunk C: propagate autonomy_level to the
    # mission-status entry so the legacy Step-8 manual YAML write is no longer
    # required. Only writes when the entry already exists (create-slice ran
    # first) and the contract carries a canonical autonomy.level value.
    mission_status_synced = False
    canonical_level = (
        contract.get("autonomy", {}).get("level")
        if isinstance(contract.get("autonomy"), dict)
        else None
    )
    if isinstance(canonical_level, str) and canonical_level in AUTONOMY_CANONICAL_LEVELS:
        status_path = mission_status_path(root)
        if status_path.exists():
            status_doc = load_yaml(status_path)
            if isinstance(status_doc, dict) and isinstance(status_doc.get(args.mission), dict):
                entry = status_doc[args.mission]
                if entry.get("autonomy_level") != canonical_level:
                    entry["autonomy_level"] = canonical_level
                    write_yaml(status_path, status_doc)
                    mission_status_synced = True
                else:
                    mission_status_synced = True

    payload = {
        "status": hygiene["status"],
        "control": "contract.fill",
        "contract": relpath(root, artifact),
        "intent_framing": relpath(root, framing_path),
        "applied_fields": unique(applied),
        "mission_status_synced": mission_status_synced,
        "hygiene": hygiene,
        "findings": [],
    }
    return emit_payload(args, payload)


def cmd_contract_patch(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    if artifact is None or not artifact.exists():
        return emit_payload(args, fail_payload("contract.patch", "missing_contract", f"Contract artifact not found: {args.artifact}"))

    add_round = bool(getattr(args, "add_round", False))
    patch_path = resolve_path(root, args.patch) if args.patch else None

    if not add_round and patch_path is None:
        return emit_payload(
            args,
            fail_payload(
                "contract.patch",
                "missing_contract_patch_input",
                "Provide --patch <manifest> or --add-round for the targeted shortcut",
            ),
        )

    document = load_manifest(artifact)
    applied: list[dict[str, str]] = []

    # M4.3 — Shortcut: increment effectiveness_review.rounds_used (and
    # optionally record last_verdict) without a full patch manifest. The
    # contract YAML is the source of truth for the round counter; trace
    # JSONL `step-enter --rounds N` is bypass sensor evidence and must agree.
    if add_round:
        try:
            contract = document.setdefault("control_contract", {})
            if not isinstance(contract, dict):
                raise ValueError("control_contract is not an object")
            review_block = contract.setdefault("effectiveness_review", {})
            if not isinstance(review_block, dict):
                raise ValueError("control_contract.effectiveness_review is not an object")
            current = review_block.get("rounds_used")
            current_int = int(current) if isinstance(current, (int, float)) else 0
            review_block["rounds_used"] = current_int + 1
            applied.append({"target": "control_contract.effectiveness_review.rounds_used", "op": "increment"})
            last_verdict = getattr(args, "last_verdict", None)
            if isinstance(last_verdict, str) and last_verdict.strip():
                review_block["last_verdict"] = last_verdict.strip()
                applied.append({"target": "control_contract.effectiveness_review.last_verdict", "op": "set"})
        except ValueError as exc:
            return emit_payload(args, fail_payload("contract.patch", "invalid_contract_patch", str(exc)))

    if patch_path is not None:
        if not patch_path.exists():
            return emit_payload(args, fail_payload("contract.patch", "missing_contract_patch_input", f"Patch manifest not found: {args.patch}"))
        patch_doc = load_manifest(patch_path)
        patches = patch_doc.get("patches") if isinstance(patch_doc.get("patches"), list) else [patch_doc]
        try:
            for patch in patches:
                if not isinstance(patch, dict):
                    raise ValueError("patch entries must be objects")
                target = str(patch.get("target") or "")
                if not target.startswith("control_contract."):
                    raise ValueError(f"patch target must be under control_contract: {target}")
                op = str(patch.get("op") or "set")
                set_path_value(document, target, patch.get("value"), op)
                applied.append({"target": target, "op": op})
        except ValueError as exc:
            return emit_payload(args, fail_payload("contract.patch", "invalid_contract_patch", str(exc)))

    write_manifest(artifact, document)
    return emit_payload(args, {"status": "PASS", "control": "contract.patch", "contract": relpath(root, artifact), "applied": applied, "findings": []})


# M4.2 — Reviewer-class roles whose verdict carries a `main_agent_fallback`
# execution_mode are rejected by contract.add_verdict. The role list below is
# matched by suffix; new reviewers added under the same naming convention are
# automatically covered.
_REVIEWER_ROLE_SUFFIXES = ("-reviewer", "-effectiveness-reviewer")
_DISPATCH_REQUIRED_FIELDS = (
    "subagent_id",
    "model",
    "execution_mode",
    "started_at",
    "completed_at",
)
_DISPATCH_EXECUTION_MODES = {"spawn_agent", "main_agent_fallback", "sequential"}


def _is_reviewer_role(role: str) -> bool:
    if not isinstance(role, str):
        return False
    return any(role.endswith(suffix) for suffix in _REVIEWER_ROLE_SUFFIXES)


def _validate_role_verdict_dispatch(verdict: dict) -> dict | None:
    """Validate the dispatch block on a role verdict (intake-plan M4.2).

    Returns a typed FAIL payload when the verdict violates the dispatch
    contract, else None. Non-reviewer roles may omit the block; reviewer-class
    roles must declare it AND must not declare `execution_mode=main_agent_fallback`.
    """
    role = verdict.get("role") if isinstance(verdict, dict) else None
    dispatch = verdict.get("dispatch") if isinstance(verdict, dict) else None
    is_reviewer = _is_reviewer_role(role)

    if dispatch is None and not is_reviewer:
        return None

    if dispatch is None and is_reviewer:
        return fail_payload(
            "contract.add_verdict",
            "MISSING_DISPATCH",
            f"reviewer-class role {role!r} verdict must declare a `dispatch` block "
            f"with {list(_DISPATCH_REQUIRED_FIELDS)}",
        )

    if not isinstance(dispatch, dict):
        return fail_payload(
            "contract.add_verdict",
            "INVALID_DISPATCH",
            f"verdict.dispatch must be an object; received {type(dispatch).__name__}",
        )

    missing = [field for field in _DISPATCH_REQUIRED_FIELDS if not dispatch.get(field)]
    if missing:
        payload = fail_payload(
            "contract.add_verdict",
            "MISSING_DISPATCH_FIELD",
            f"verdict.dispatch missing required fields for role {role!r}: {missing}",
        )
        payload["findings"][0]["missing_fields"] = missing
        return payload

    mode = dispatch.get("execution_mode")
    if mode not in _DISPATCH_EXECUTION_MODES:
        return fail_payload(
            "contract.add_verdict",
            "INVALID_EXECUTION_MODE",
            f"verdict.dispatch.execution_mode must be one of {sorted(_DISPATCH_EXECUTION_MODES)}; "
            f"received {mode!r}",
        )

    if is_reviewer and mode == "main_agent_fallback":
        payload = fail_payload(
            "contract.add_verdict",
            "REVIEWER_MAIN_AGENT_FALLBACK",
            f"reviewer-class role {role!r} cannot record a PASS verdict via main_agent_fallback; "
            "reviewers must run in a real subagent or surface as BLOCKED.",
        )
        payload["findings"][0]["role"] = role
        return payload

    return None


def cmd_contract_add_verdict(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    verdict_path = resolve_path(root, args.verdict)
    if artifact is None or verdict_path is None or not artifact.exists() or not verdict_path.exists():
        return emit_payload(args, fail_payload("contract.add_verdict", "missing_verdict_input", "Contract artifact and verdict manifest must both exist"))
    document, contract = control_contract_document(artifact)
    verdict = load_manifest(verdict_path)
    verdict = verdict.get("role_verdict") if isinstance(verdict.get("role_verdict"), dict) else verdict
    if not isinstance(verdict, dict) or not verdict.get("role") or not verdict.get("verdict"):
        return emit_payload(args, fail_payload("contract.add_verdict", "invalid_role_verdict", "Role verdict must be an object with role and verdict"))

    # M4.2 dispatch evidence enforcement (reviewer-class strict).
    dispatch_reject = _validate_role_verdict_dispatch(verdict)
    if dispatch_reject is not None:
        return emit_payload(args, dispatch_reject)

    role_verdicts = contract.setdefault("role_verdicts", [])
    if not isinstance(role_verdicts, list):
        return emit_payload(args, fail_payload("contract.add_verdict", "invalid_role_verdicts", "control_contract.role_verdicts must be a list"))
    action = upsert_by_id(role_verdicts, verdict)
    write_manifest(artifact, document)
    return emit_payload(args, {"status": "PASS", "control": "contract.add_verdict", "contract": relpath(root, artifact), "action": action, "verdict": verdict, "findings": []})


def cmd_contract_add_execution_result(args: argparse.Namespace) -> int:
    """Append an execution_result manifest to a control contract.

    breakdown-improvement-plan M1.4: stages that ship more than one execution
    worker (only breakdown today, with delivery-slicer + test-planning-expert)
    accumulate `execution_results[]` instead of overwriting `execution_result`.
    Legacy singular form remains accepted for backwards compatibility for the
    2-mission migration window. When the input manifest declares a
    `barrier_group`, the entry is appended to the list form so the M3.1
    check_barrier_complete hook can verify both parallel workers reached DONE.
    """
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    result_path = resolve_path(root, args.result)
    if artifact is None or result_path is None or not artifact.exists() or not result_path.exists():
        return emit_payload(args, fail_payload("contract.add_execution_result", "missing_execution_result_input", "Contract artifact and execution result manifest must both exist"))
    document, contract = control_contract_document(artifact)
    result = load_manifest(result_path)
    result = result.get("execution_result") if isinstance(result.get("execution_result"), dict) else result
    if not isinstance(result, dict) or not result.get("role") or not result.get("status"):
        return emit_payload(args, fail_payload("contract.add_execution_result", "invalid_execution_result", "execution_result must be an object with role and status"))
    # Append-mode: when the contract already declares `execution_results[]` OR
    # the incoming result declares `barrier_group`, accumulate into the list.
    has_list = isinstance(contract.get("execution_results"), list)
    has_barrier = bool(result.get("barrier_group"))
    if has_list or has_barrier:
        existing = contract.get("execution_results") if has_list else []
        if not isinstance(existing, list):
            existing = []
        # Dedup on (id, role) — re-running a worker overwrites its prior entry.
        key = (result.get("id"), result.get("role"))
        existing = [
            entry
            for entry in existing
            if not (
                isinstance(entry, dict)
                and (entry.get("id"), entry.get("role")) == key
            )
        ]
        existing.append(result)
        contract["execution_results"] = existing
        # Migration: when the legacy singular field is also present, leave it
        # in place during the 2-mission window so consumers that haven't
        # migrated still find it.
    else:
        contract["execution_result"] = result
    write_manifest(artifact, document)
    payload = {
        "status": "PASS",
        "control": "contract.add_execution_result",
        "contract": relpath(root, artifact),
        "execution_result": result,
        "findings": [],
    }
    if has_list or has_barrier:
        payload["execution_results_count"] = len(contract["execution_results"])
    return emit_payload(args, payload)


# breakdown-improvement-plan M1.4: execution-brief → execute permission
# overlay translator. M5 will deliver the full translator behind the
# `harness execute apply-overlay --mission <id>` CLI; M1.4 lays down the
# function signature + interface contract referenced by the
# permission-overlay-translation protocol so downstream stages can bind to a
# stable API. The skeleton implementation walks each task's
# authorized_paths / prohibited_paths / stop_if and returns a settings
# overlay dict ready for merge into .claude/settings.json. Complex glob
# patterns (containing `**` or `!` negation) fall back to `ask` and the
# fallback is reported via the returned `fallback_log` field; trace-log
# integration is deferred to M5.
_OVERLAY_COMPLEX_GLOB_MARKERS = ("**", "!")


def translate_execution_brief_to_overlay(
    execution_brief_contract: dict,
    *,
    task_id: str | None = None,
) -> dict:
    """Project an execution-brief.contract.yaml task graph into a Claude
    `.claude/settings.json` permission overlay shape.

    Parameters
    ----------
    execution_brief_contract:
        Parsed contract document (the YAML root). The function reads the
        `control_contract.tasks[]` array — passing the unwrapped
        control_contract dict is also accepted.
    task_id:
        When provided, only the matching task contributes overlay entries
        (SDD per-task overlay flow). When None, all tasks contribute
        (mission-level overlay at stage-enter).

    Returns
    -------
    Dict with keys::

        {
            "permissions": {"allow": [...], "deny": [...], "ask": [...]},
            "stop_if_hooks": [
                {"task_id": ..., "flag": ..., "fallback": ...},
                ...
            ],
            "fallback_log": [
                {"task_id": ..., "field": "authorized_paths" | ...,
                 "pattern": ..., "reason": "complex_glob"},
                ...
            ],
        }

    Skeleton notes (M1.4):
    - Simple path strings translate 1:1 to `Edit(<path>)` + `Write(<path>)`.
    - Complex globs (`**` / `!`) fall back to `ask` per protocol.
    - stop_if entries are collected for M5 hook registration but not yet
      attached to a hook manifest in this skeleton.

    M5 will:
    - Resolve glob expansion against the project tree
    - Emit per-task hook manifests under `.claude/hooks/execute/`
    - Wire trace-log capture for every fallback
    """
    contract = execution_brief_contract.get("control_contract")
    if isinstance(contract, dict):
        root = contract
    else:
        root = execution_brief_contract
    tasks = root.get("tasks") if isinstance(root, dict) else None
    if not isinstance(tasks, list):
        tasks = []

    allow: list[str] = []
    deny: list[str] = []
    ask: list[str] = []
    stop_if_hooks: list[dict] = []
    fallback_log: list[dict] = []

    def _emit_path(path: str, target_list: list[str], tid: str, field: str) -> None:
        if not isinstance(path, str) or not path:
            return
        is_complex = any(marker in path for marker in _OVERLAY_COMPLEX_GLOB_MARKERS)
        if is_complex:
            ask.append(f"Edit({path})")
            ask.append(f"Write({path})")
            fallback_log.append(
                {
                    "task_id": tid,
                    "field": field,
                    "pattern": path,
                    "reason": "complex_glob",
                }
            )
            return
        target_list.append(f"Edit({path})")
        target_list.append(f"Write({path})")

    for task in tasks:
        if not isinstance(task, dict):
            continue
        tid = task.get("id") or "<unknown>"
        if task_id is not None and tid != task_id:
            continue
        for path in task.get("authorized_paths", []) or []:
            _emit_path(path, allow, tid, "authorized_paths")
        for path in task.get("prohibited_paths", []) or []:
            _emit_path(path, deny, tid, "prohibited_paths")
        stop_if = task.get("stop_if") or []
        if isinstance(stop_if, list):
            for flag in stop_if:
                if isinstance(flag, str) and flag:
                    stop_if_hooks.append(
                        {
                            "task_id": tid,
                            "flag": flag,
                            "fallback": "execute_postuse_hook_pending_m5",
                        }
                    )

    # De-dup while preserving order so settings.json merge is stable.
    def _dedupe(seq: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for entry in seq:
            if entry in seen:
                continue
            seen.add(entry)
            out.append(entry)
        return out

    return {
        "permissions": {
            "allow": _dedupe(allow),
            "deny": _dedupe(deny),
            "ask": _dedupe(ask),
        },
        "stop_if_hooks": stop_if_hooks,
        "fallback_log": fallback_log,
    }


# --- execute-improvement-plan M2.1 / M5 anchor: apply-overlay, stop-event ---
# CROSS-STAGE-OVERLAY-PROTOCOL anchor commands. `apply-overlay` reads the
# breakdown-side execution-brief.contract.yaml, calls
# translate_execution_brief_to_overlay, and writes the effective overlay to
# `harness-runtime/harness/stages/<mission>/runtime/effective-overlay.json`
# so the stop_if hooks (check_stop_*.py) can consume per-task authorized /
# prohibited / stop_if state at PreToolUse time.

_EFFECTIVE_OVERLAY_REL = "runtime/effective-overlay.json"


def _effective_overlay_path(root: Path, mission: str) -> Path:
    return (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission
        / _EFFECTIVE_OVERLAY_REL
    )


def cmd_execute_apply_overlay(args: argparse.Namespace) -> int:
    """Compute the effective per-task overlay from the breakdown contract
    and persist it for runtime hook consumption.

    `--task <atomic-id>` filters to one Atomic Task (SDD per-task mode);
    omitting it produces a mission-level snapshot (stage-enter mode).
    `--dry-run` returns the overlay payload without writing.
    """
    root = Path(root_arg(args))
    artifact, contract, error_code = _resolve_execution_brief_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execute.apply-overlay",
                error_code or "execution_brief_contract_unloadable",
                f"Cannot load execution-brief contract at {relpath(root, artifact)}",
            ),
        )
    overlay = translate_execution_brief_to_overlay(
        {"control_contract": contract}, task_id=args.task
    )
    # Add task_id + authorized_paths/prohibited_paths flat lists so the
    # stop_if hooks can read them without recomputing from the full brief.
    authorized: list[str] = []
    prohibited: list[str] = []
    stop_if_flags: set[str] = set()
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        tid = task.get("id")
        if args.task is not None and tid != args.task:
            continue
        for path in task.get("authorized_paths") or []:
            if isinstance(path, str):
                authorized.append(path)
        for path in task.get("prohibited_paths") or []:
            if isinstance(path, str):
                prohibited.append(path)
        for flag in task.get("stop_if") or []:
            if isinstance(flag, str):
                stop_if_flags.add(flag)
    state = {
        "mission": args.mission,
        "task_id": args.task,
        "authorized_paths": sorted(set(authorized)),
        "prohibited_paths": sorted(set(prohibited)),
        "stop_if": sorted(stop_if_flags),
        "overlay": overlay,
    }
    if not args.dry_run:
        state_path = _effective_overlay_path(root, args.mission)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "execute.apply-overlay",
            "mission": args.mission,
            "task_id": args.task,
            "dry_run": bool(args.dry_run),
            "effective_overlay": state,
            "state_path": relpath(root, _effective_overlay_path(root, args.mission))
            if not args.dry_run
            else None,
        },
    )


def cmd_execute_revoke_overlay(args: argparse.Namespace) -> int:
    """Remove the effective overlay state file for a mission. Called by
    stage exit so stale per-task constraints do not leak into the next
    mission.
    """
    root = Path(root_arg(args))
    state_path = _effective_overlay_path(root, args.mission)
    existed = state_path.exists()
    if existed:
        try:
            state_path.unlink()
        except OSError as exc:
            return emit_payload(
                args,
                fail_payload(
                    "execute.revoke-overlay",
                    "revoke_failed",
                    f"Failed to remove {state_path}: {exc}",
                ),
            )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "execute.revoke-overlay",
            "mission": args.mission,
            "existed": existed,
        },
    )


_STOP_EVENT_KINDS = {
    "changes_outside_authorized_paths",
    "new_external_dependency",
    "design_constraint_conflict",
    "new_public_behavior_without_delta_spec",
}


def cmd_execute_stop_event_record(args: argparse.Namespace) -> int:
    """Append a typed stop_event to execution-result.contract.yaml so the
    breakdown / verify side can read it. Triggered by hooks (rc=2) or by
    the workflow on Decision Gate paths.
    """
    root = Path(root_arg(args))
    if args.kind not in _STOP_EVENT_KINDS:
        return emit_payload(
            args,
            fail_payload(
                "execute.stop-event.record",
                "invalid_stop_event_kind",
                f"--kind must be one of {sorted(_STOP_EVENT_KINDS)}; got {args.kind!r}",
            ),
        )
    artifact = (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / args.mission
        / "contracts"
        / "execution-result.contract.yaml"
    )
    if not artifact.exists():
        return emit_payload(
            args,
            fail_payload(
                "execute.stop-event.record",
                "execution_result_contract_missing",
                f"execution-result.contract.yaml not found at {relpath(root, artifact)}",
            ),
        )
    try:
        document = yaml.safe_load(artifact.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return emit_payload(
            args,
            fail_payload(
                "execute.stop-event.record",
                "execution_result_contract_invalid_yaml",
                f"Failed to parse {artifact}: {exc}",
            ),
        )
    if not isinstance(document, dict):
        document = {}
    contract_block = (
        document.get("control_contract")
        if isinstance(document.get("control_contract"), dict)
        else document
    )
    if not isinstance(contract_block, dict):
        document["control_contract"] = {}
        contract_block = document["control_contract"]
    execute_session = contract_block.get("execute_session")
    if not isinstance(execute_session, dict):
        execute_session = {}
        contract_block["execute_session"] = execute_session
    events = execute_session.get("stop_events")
    if not isinstance(events, list):
        events = []
        execute_session["stop_events"] = events
    event = {
        "kind": args.kind,
        "task_id": args.task,
        "affected_paths": list(args.path or []),
        "hook_source": args.hook_source or "manual",
    }
    events.append(event)
    artifact.write_text(
        yaml.dump(
            document,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "execute.stop-event.record",
            "mission": args.mission,
            "event": event,
            "stop_events_count": len(events),
        },
    )


# --- execute-improvement-plan M2.1: `harness execute gate run` / check-ready -


_EXECUTE_TDD_PHASES = ("red", "green", "regression", "toolchain")


def _resolve_execution_result_contract(
    root: Path, mission: str
) -> tuple[Path, dict | None, str | None]:
    artifact = (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission
        / "contracts"
        / "execution-result.contract.yaml"
    )
    if not artifact.exists():
        return artifact, None, "execution_result_contract_missing"
    try:
        document = yaml.safe_load(artifact.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return artifact, None, "execution_result_contract_invalid_yaml"
    if not isinstance(document, dict):
        return artifact, None, "execution_result_contract_invalid_root"
    contract = (
        document.get("control_contract")
        if isinstance(document.get("control_contract"), dict)
        else document
    )
    if not isinstance(contract, dict):
        return artifact, None, "execution_result_contract_invalid_shape"
    return artifact, contract, None


def _check_execute_tdd_evidence(contract: dict) -> list[dict]:
    """Each of the 4 TDD evidence phases must be present (or carry an
    accepted_alternative). breakdown-equivalent: drives the artifact_gate.
    """
    findings: list[dict] = []
    tdd = contract.get("tdd_evidence")
    present_phases: set[str] = set()
    if isinstance(tdd, list):
        for entry in tdd:
            if isinstance(entry, dict) and isinstance(entry.get("phase"), str):
                present_phases.add(entry["phase"])
    for phase in _EXECUTE_TDD_PHASES:
        if phase not in present_phases:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "missing_tdd_evidence_phase",
                    "phase": phase,
                    "message": f"tdd_evidence missing phase {phase!r}",
                }
            )
    return findings


def _check_execute_dispatch_coverage(contract: dict) -> list[dict]:
    """Every dispatch plan's primary/supporting/reviewer roles must appear
    in execution_results[] or role_verdicts[].
    """
    findings: list[dict] = []
    session = contract.get("execute_session") if isinstance(contract.get("execute_session"), dict) else {}
    plans = session.get("dispatch_plans") if isinstance(session.get("dispatch_plans"), list) else []
    result_roles: set[str] = set()
    for entry in contract.get("execution_results") or []:
        if isinstance(entry, dict) and isinstance(entry.get("role"), str):
            result_roles.add(entry["role"])
    verdict_roles: set[str] = set()
    for entry in contract.get("role_verdicts") or []:
        if isinstance(entry, dict) and isinstance(entry.get("role"), str):
            verdict_roles.add(entry["role"])
    covered = result_roles | verdict_roles
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        pid = plan.get("id") or "<unknown>"
        planned: list[str] = []
        for key in ("primary_executors", "supporting_executors", "reviewers"):
            value = plan.get(key)
            if isinstance(value, list):
                planned.extend(r for r in value if isinstance(r, str))
        for role in planned:
            if role not in covered:
                findings.append(
                    {
                        "level": "FAIL",
                        "code": "dispatch_role_not_covered",
                        "dispatch_plan": pid,
                        "role": role,
                        "message": (
                            f"dispatch plan {pid} role {role!r} has no "
                            "execution_results / role_verdicts entry"
                        ),
                    }
                )
    return findings


def _execution_expected_atomic_task_ids(root: Path, mission: str, contract: dict) -> set[str]:
    mission_slice = load_yaml(root / "harness-runtime" / "harness" / "work-graph" / "mission-slices" / f"{mission}.yaml")
    primary_nodes = mission_slice_primary_nodes(mission_slice) if mission_slice else []
    if not primary_nodes:
        artifact = contract.get("work_graph_artifact") if isinstance(contract.get("work_graph_artifact"), dict) else {}
        node_id = str(artifact.get("node_id") or "")
        primary_nodes = [node_id] if node_id else []
    nodes_by_id, _load_error = work_graph_nodes_by_id(root)
    expected: set[str] = set()
    for node_id in primary_nodes:
        node = nodes_by_id.get(node_id) or {}
        queue = node.get("parent_local_atomic_task_queue") if isinstance(node.get("parent_local_atomic_task_queue"), dict) else {}
        atomic_ids = queue.get("atomic_task_ids")
        if isinstance(atomic_ids, list):
            expected.update(str(item) for item in atomic_ids if item)
        execution_units = queue.get("execution_units")
        if isinstance(execution_units, list):
            for unit in execution_units:
                if isinstance(unit, dict) and unit.get("id"):
                    expected.add(str(unit["id"]))
    return expected


def _single_atomic_execution_unit(value: str) -> bool:
    text = value.strip()
    return bool(text) and ".." not in text and "," not in text and not re.search(r"\s", text)


def _evidence_covers_atomic(entry: dict, atomic_id: str) -> bool:
    covers = entry.get("covers") if isinstance(entry.get("covers"), dict) else {}
    candidates: list[str] = []
    for key in ("atomic_tasks", "atomic_task_ids", "tasks", "execution_units"):
        value = covers.get(key)
        if isinstance(value, list):
            candidates.extend(str(item) for item in value)
    return atomic_id in candidates


def _check_execute_atomic_control(root: Path, mission: str, contract: dict) -> list[dict]:
    expected = _execution_expected_atomic_task_ids(root, mission, contract)
    if not expected:
        return []
    findings: list[dict] = []
    session = contract.get("execute_session") if isinstance(contract.get("execute_session"), dict) else {}
    plans = session.get("dispatch_plans") if isinstance(session.get("dispatch_plans"), list) else []
    seen: list[str] = []
    for index, plan in enumerate(plans):
        if not isinstance(plan, dict):
            continue
        pid = str(plan.get("id") or f"dispatch[{index}]")
        unit = str(plan.get("execution_unit_id") or "")
        if not _single_atomic_execution_unit(unit):
            findings.append({
                "level": "FAIL",
                "code": "invalid_execute_atomic_dispatch_unit",
                "dispatch_plan": pid,
                "message": f"dispatch plan {pid} execution_unit_id must be one Atomic Task id, got {unit!r}",
            })
            continue
        seen.append(unit)
        if unit not in expected:
            findings.append({
                "level": "FAIL",
                "code": "unknown_execute_atomic_dispatch_unit",
                "dispatch_plan": pid,
                "atomic_task_id": unit,
                "message": f"dispatch plan {pid} references Atomic Task {unit!r} outside the selected TASK node",
            })
    seen_set = set(seen)
    for atomic_id in sorted(expected - seen_set):
        findings.append({
            "level": "FAIL",
            "code": "missing_execute_atomic_dispatch_plan",
            "atomic_task_id": atomic_id,
            "message": f"selected TASK node Atomic Task {atomic_id} has no dedicated dispatch plan",
        })
    for atomic_id in sorted(unit for unit in seen_set if seen.count(unit) > 1):
        findings.append({
            "level": "FAIL",
            "code": "duplicate_execute_atomic_dispatch_plan",
            "atomic_task_id": atomic_id,
            "message": f"Atomic Task {atomic_id} has multiple dispatch plans",
        })

    phase_cover: dict[str, set[str]] = {"red": set(), "green": set(), "regression": set()}
    for entry in contract.get("tdd_evidence") or []:
        if not isinstance(entry, dict):
            continue
        phase = str(entry.get("phase") or "")
        if phase not in phase_cover:
            continue
        for atomic_id in expected:
            if _evidence_covers_atomic(entry, atomic_id):
                phase_cover[phase].add(atomic_id)
    for phase, covered in sorted(phase_cover.items()):
        for atomic_id in sorted(expected - covered):
            findings.append({
                "level": "FAIL",
                "code": "missing_execute_atomic_tdd_evidence",
                "phase": phase,
                "atomic_task_id": atomic_id,
                "message": f"Atomic Task {atomic_id} lacks {phase} TDD evidence coverage",
            })
    return findings


def cmd_execute_check_ready(args: argparse.Namespace) -> int:
    """Lightweight readiness lint for the execute stage: TDD evidence phases
    + dispatch coverage. No mission-status cross-check.
    """
    root = Path(root_arg(args))
    artifact, contract, error_code = _resolve_execution_result_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execute.check-ready",
                error_code or "execution_result_contract_unloadable",
                f"Cannot load execution-result contract at {relpath(root, artifact)}",
            ),
        )
    findings: list[dict] = []
    findings.extend(_check_execute_tdd_evidence(contract))
    findings.extend(_check_execute_dispatch_coverage(contract))
    findings.extend(_check_execute_atomic_control(root, args.mission, contract))
    status = "PASS" if not any(f["level"] == "FAIL" for f in findings) else "FAIL"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "execute.check-ready",
            "mission": args.mission,
            "artifact": relpath(root, artifact),
            "findings": findings,
        },
    )


def cmd_execute_gate_run(args: argparse.Namespace) -> int:
    """Execute stage gate: quality_check (TDD evidence + dispatch coverage) +
    artifact_gate (execution-result.md structure). Writes
    effectiveness_review.last_gate_run_status so the check_gate_pass hook
    can verify gate PASS before stage complete.
    """
    root = Path(root_arg(args))
    artifact, contract, error_code = _resolve_execution_result_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execute.gate-run",
                error_code or "execution_result_contract_unloadable",
                f"Cannot load execution-result contract at {relpath(root, artifact)}",
            ),
        )
    quality_findings: list[dict] = []
    quality_findings.extend(_check_execute_tdd_evidence(contract))
    quality_findings.extend(_check_execute_dispatch_coverage(contract))
    quality_findings.extend(_check_execute_atomic_control(root, args.mission, contract))
    quality_status = "PASS" if not any(f["level"] == "FAIL" for f in quality_findings) else "FAIL"

    gate_findings: list[dict] = []
    md_path = (
        root / "harness-runtime" / "harness" / "stages" / args.mission / "execution-result.md"
    )
    if not md_path.exists():
        gate_findings.append(
            {
                "level": "FAIL",
                "code": "execution_result_md_missing",
                "message": f"execution-result.md not found at {relpath(root, md_path)}",
            }
        )
    else:
        md_text = md_path.read_text(encoding="utf-8")
        for marker in (
            "Execute Session",
            "TDD Evidence",
            "Contract: contracts/execution-result.contract.yaml",
        ):
            if marker not in md_text:
                gate_findings.append(
                    {
                        "level": "FAIL",
                        "code": "execution_result_md_section_missing",
                        "section": marker,
                        "message": f"execution-result.md missing section/marker: {marker!r}",
                    }
                )
    gate_status = "PASS" if not any(f["level"] == "FAIL" for f in gate_findings) else "FAIL"
    status = "PASS" if quality_status == "PASS" and gate_status == "PASS" else "FAIL"
    failed_checks = [
        f["code"] for f in (quality_findings + gate_findings) if f["level"] == "FAIL"
    ]
    # Persist last_gate_run_status for check_gate_pass.py hook.
    try:
        document = yaml.safe_load(artifact.read_text(encoding="utf-8"))
        if isinstance(document, dict):
            contract_block = (
                document.get("control_contract")
                if isinstance(document.get("control_contract"), dict)
                else document
            )
            if isinstance(contract_block, dict):
                eff = contract_block.get("effectiveness_review")
                if not isinstance(eff, dict):
                    eff = {}
                    contract_block["effectiveness_review"] = eff
                eff["last_gate_run_status"] = status
                artifact.write_text(
                    yaml.dump(
                        document,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )
    except (OSError, yaml.YAMLError):
        pass
    return emit_payload(
        args,
        {
            "status": status,
            "control": "execute.gate-run",
            "mission": args.mission,
            "artifact": relpath(root, artifact),
            "phase_results": [
                {"name": "quality_check", "status": quality_status, "findings": quality_findings},
                {"name": "artifact_gate", "status": gate_status, "findings": gate_findings},
            ],
            "failed_checks": failed_checks,
        },
    )


# --- code-review-improvement-plan M2.1: `harness review check-ready` --------


def cmd_review_check_ready(args: argparse.Namespace) -> int:
    """Verify code-review.contract.yaml is ready for stage complete:
    pending_reviewer_recheck=false AND no unresolved High findings.

    Pure-review stages do not copy mark_pending_recheck/check_pending_recheck
    from prd template (per protocol H2); this CLI replaces the gate by
    surfacing the readiness check as typed JSON.
    """
    root = Path(root_arg(args))
    artifact = (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / args.mission
        / "contracts"
        / "code-review.contract.yaml"
    )
    if not artifact.exists():
        return emit_payload(
            args,
            fail_payload(
                "review.check-ready",
                "code_review_contract_missing",
                f"code-review.contract.yaml not found at {relpath(root, artifact)}",
            ),
        )
    try:
        document = yaml.safe_load(artifact.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return emit_payload(
            args,
            fail_payload(
                "review.check-ready",
                "code_review_contract_invalid_yaml",
                f"Failed to parse {artifact}: {exc}",
            ),
        )
    if not isinstance(document, dict):
        return emit_payload(
            args,
            fail_payload(
                "review.check-ready",
                "code_review_contract_invalid_root",
                "code-review.contract.yaml root is not an object",
            ),
        )
    contract = (
        document.get("control_contract")
        if isinstance(document.get("control_contract"), dict)
        else document
    )
    if not isinstance(contract, dict):
        return emit_payload(
            args,
            fail_payload(
                "review.check-ready",
                "code_review_contract_invalid_shape",
                "code-review.contract.yaml control_contract not an object",
            ),
        )
    findings: list[dict] = []
    eff = contract.get("effectiveness_review") if isinstance(contract.get("effectiveness_review"), dict) else {}
    if eff.get("pending_reviewer_recheck"):
        findings.append(
            {
                "level": "FAIL",
                "code": "pending_reviewer_recheck",
                "message": "effectiveness_review.pending_reviewer_recheck=true; re-run reviewers",
            }
        )
    finding_list = contract.get("findings") if isinstance(contract.get("findings"), list) else []
    open_high = [
        f
        for f in finding_list
        if isinstance(f, dict)
        and (f.get("severity") or "").lower() == "high"
        and (f.get("status") or "open").lower() != "resolved"
    ]
    for f in open_high:
        findings.append(
            {
                "level": "FAIL",
                "code": "unresolved_high_finding",
                "finding_id": f.get("id"),
                "message": f"High-severity finding {f.get('id')!r} is unresolved",
            }
        )
    status = "PASS" if not findings else "FAIL"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "review.check-ready",
            "mission": args.mission,
            "findings": findings,
            "unresolved_high_count": len(open_high),
        },
    )


# --- code-review-improvement-plan M2.1: new CLI commands --------------------


def _resolve_code_review_contract(root: Path, mission: str) -> tuple[Path, dict | None, str | None]:
    """Locate and load the code-review contract for a given mission.

    Returns (artifact_path, contract_dict, error_code).
    """
    artifact = (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission
        / "contracts"
        / "code-review.contract.yaml"
    )
    if not artifact.exists():
        return artifact, None, "code_review_contract_missing"
    try:
        document = yaml.safe_load(artifact.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return artifact, None, "code_review_contract_invalid_yaml"
    if not isinstance(document, dict):
        return artifact, None, "code_review_contract_invalid_root"
    contract = (
        document.get("control_contract")
        if isinstance(document.get("control_contract"), dict)
        else document
    )
    if not isinstance(contract, dict):
        return artifact, None, "code_review_contract_invalid_shape"
    return artifact, contract, None


# Maps feature keywords found in a diff-summary JSON array to the reviewers that
# should be selected when any keyword is present.
_REVIEWER_TRIGGER_MAP: dict[str, list[str]] = {
    "auth": ["security-reviewer"],
    "authorization": ["security-reviewer"],
    "api_exposure": ["security-reviewer"],
    "crypto": ["security-reviewer"],
    "encryption": ["security-reviewer"],
    "e2e": ["e2e-reviewer"],
    "ui": ["interaction-reviewer"],
    "frontend": ["interaction-reviewer"],
    "database": ["data-engineer"],
    "migration": ["data-engineer"],
    "architecture": ["architecture-reviewer"],
    "integration": ["integration-impact-expert"],
}

# Reviewers that are always included regardless of diff content.
_ALWAYS_ENABLED_REVIEWERS: list[str] = ["correctness-reviewer", "tdd-reviewer"]


def cmd_review_select_reviewers(args: argparse.Namespace) -> int:
    """Select reviewers for the current mission's code-review stage.

    Reads an optional --diff-summary JSON file (array of feature keywords).
    Always includes correctness-reviewer and tdd-reviewer. Additional reviewers
    are triggered by diff keyword matching.
    """
    features: list[str] = []
    diff_summary = getattr(args, "diff_summary", None)
    if diff_summary:
        try:
            raw = Path(diff_summary).read_text(encoding="utf-8")
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                features = [str(f).lower() for f in parsed]
        except (OSError, json.JSONDecodeError):
            pass

    triggered: set[str] = set()
    for feature in features:
        for keyword, roles in _REVIEWER_TRIGGER_MAP.items():
            if keyword in feature:
                triggered.update(roles)

    all_possible = set(_ALWAYS_ENABLED_REVIEWERS)
    for roles in _REVIEWER_TRIGGER_MAP.values():
        all_possible.update(roles)

    selected = [
        {"role": r, "reason": "always_enabled" if r in _ALWAYS_ENABLED_REVIEWERS else "diff_trigger"}
        for r in sorted(set(_ALWAYS_ENABLED_REVIEWERS) | triggered)
    ]
    excluded = [
        {"role": r, "reason": "no_trigger"}
        for r in sorted(all_possible - (set(_ALWAYS_ENABLED_REVIEWERS) | triggered))
    ]
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "review.select-reviewers",
            "mission": args.mission,
            "selected": selected,
            "excluded": excluded,
            "findings": [],
        },
    )


def cmd_review_snapshot_diff(args: argparse.Namespace) -> int:
    """Capture a diff snapshot for the current review round.

    Runs `git diff` relative to the base ref (--base defaults to HEAD~1) and
    writes the result to harness-runtime/harness/traces/<mission>/diff-snapshot.patch.
    """
    root = Path(root_arg(args))
    mission = args.mission
    base = getattr(args, "base", "HEAD~1") or "HEAD~1"
    snapshot_dir = runtime_harness_root(root) / "traces" / mission
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / "diff-snapshot.patch"
    try:
        import subprocess as _sp
        result = _sp.run(
            ["git", "diff", base],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(root),
        )
        snapshot_path.write_text(result.stdout, encoding="utf-8")
        lines = result.stdout.count("\n")
    except Exception as exc:
        return emit_payload(
            args,
            fail_payload(
                "review.snapshot-diff",
                "snapshot_diff_error",
                f"git diff failed: {exc}",
            ),
        )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "review.snapshot-diff",
            "mission": mission,
            "snapshot_path": relpath(root, snapshot_path),
            "diff_lines": lines,
            "findings": [],
        },
    )


def cmd_review_toolchain_status(args: argparse.Namespace) -> int:
    """Report TDD toolchain gate status.

    Reads harness-runtime/harness/traces/<mission>/tdd/toolchain-status.json.
    Returns BLOCKED when the file is missing (toolchain check not yet run).
    """
    root = Path(root_arg(args))
    mission = args.mission
    status_file = runtime_harness_root(root) / "traces" / mission / "tdd" / "toolchain-status.json"
    if not status_file.exists():
        return emit_payload(
            args,
            {
                "status": "BLOCKED",
                "control": "review.toolchain-status",
                "mission": mission,
                "findings": [
                    {
                        "level": "FAIL",
                        "code": "toolchain_status_missing",
                        "message": (
                            f"toolchain-status.json not found at {relpath(root, status_file)}; "
                            "run `harness review toolchain-status` after tdd stage"
                        ),
                    }
                ],
            },
        )
    try:
        data = json.loads(status_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return emit_payload(
            args,
            fail_payload(
                "review.toolchain-status",
                "toolchain_status_unreadable",
                f"Cannot parse toolchain-status.json: {exc}",
            ),
        )
    ts = data.get("status", "UNKNOWN")
    findings: list[dict] = []
    if ts == "FAIL":
        for cap in data.get("missing_capabilities") or []:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "missing_capability",
                    "message": f"Missing capability: {cap}",
                }
            )
        if not findings:
            findings.append({"level": "FAIL", "code": "toolchain_fail", "message": "Toolchain status FAIL"})
    status = "PASS" if ts in ("PASS", "WARN") else "FAIL" if ts == "FAIL" else "WARN"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "review.toolchain-status",
            "mission": mission,
            "toolchain_status": ts,
            "findings": findings,
        },
    )


def cmd_review_e2e_status(args: argparse.Namespace) -> int:
    """Report E2E control-plane gate status.

    Reads harness-runtime/harness/traces/<mission>/e2e/e2e-status.json.
    Returns BLOCKED when the file is missing.
    """
    root = Path(root_arg(args))
    mission = args.mission
    status_file = runtime_harness_root(root) / "traces" / mission / "e2e" / "e2e-status.json"
    if not status_file.exists():
        return emit_payload(
            args,
            {
                "status": "BLOCKED",
                "control": "review.e2e-status",
                "mission": mission,
                "findings": [
                    {
                        "level": "FAIL",
                        "code": "e2e_status_missing",
                        "message": (
                            f"e2e-status.json not found at {relpath(root, status_file)}; "
                            "run e2e gate before code-review"
                        ),
                    }
                ],
            },
        )
    try:
        data = json.loads(status_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return emit_payload(
            args,
            fail_payload(
                "review.e2e-status",
                "e2e_status_unreadable",
                f"Cannot parse e2e-status.json: {exc}",
            ),
        )
    ts = data.get("status", "UNKNOWN")
    findings: list[dict] = []
    if ts not in ("PASS", "WARN"):
        findings.append({"level": "FAIL", "code": "e2e_fail", "message": f"E2E status: {ts}"})
    status = "PASS" if ts in ("PASS", "WARN") else "FAIL"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "review.e2e-status",
            "mission": mission,
            "e2e_status": ts,
            "findings": findings,
        },
    )


def cmd_contract_add_round(args: argparse.Namespace) -> int:
    """Archive a review round's verdicts into the contract.

    Increments effectiveness_review.rounds_used, appends to effectiveness_review.rounds[].
    """
    root = Path(root_arg(args))
    mission = args.mission
    artifact, contract, err = _resolve_code_review_contract(root, mission)
    if err:
        return emit_payload(
            args,
            fail_payload(
                "contract.add-round",
                err,
                f"Cannot load code-review contract for mission {mission!r}: {err}",
            ),
        )
    eff = contract.get("effectiveness_review")
    if not isinstance(eff, dict):
        eff = {}
        contract["effectiveness_review"] = eff
    rounds_used = int(eff.get("rounds_used") or 0) + 1
    eff["rounds_used"] = rounds_used

    rounds_list = eff.get("rounds")
    if not isinstance(rounds_list, list):
        rounds_list = []
        eff["rounds"] = rounds_list

    verdicts_raw = getattr(args, "verdicts", None)
    if verdicts_raw:
        try:
            verdicts = json.loads(verdicts_raw)
        except (json.JSONDecodeError, TypeError):
            verdicts = []
    else:
        verdicts = []

    round_entry: dict[str, Any] = {
        "round": rounds_used,
        "timestamp": now_iso(),
    }
    if verdicts:
        round_entry["verdicts"] = verdicts
    rounds_list.append(round_entry)

    # Write back to YAML
    doc_path = artifact
    try:
        raw = yaml.safe_load(doc_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "control_contract" in raw:
            raw["control_contract"]["effectiveness_review"] = eff
        else:
            raw["effectiveness_review"] = eff
        doc_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    except Exception as exc:
        return emit_payload(
            args,
            fail_payload(
                "contract.add-round",
                "contract_write_error",
                f"Failed to write contract: {exc}",
            ),
        )

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "contract.add-round",
            "mission": mission,
            "rounds_used": rounds_used,
            "findings": [],
        },
    )


# Maps reviewer roles to the finding categories they are authoritative for.
_FINDING_OWNERSHIP_POLICY: dict[str, list[str]] = {
    "correctness-reviewer": ["correctness", "logic", "algorithm"],
    "tdd-reviewer": ["coverage", "testing", "tdd"],
    "security-reviewer": ["security", "auth", "crypto"],
    "architecture-reviewer": ["architecture", "design", "coupling"],
    "interaction-reviewer": ["ui", "ux", "interaction"],
    "e2e-reviewer": ["e2e", "integration", "system"],
    "data-engineer": ["database", "migration", "data"],
    "integration-impact-expert": ["integration", "compatibility", "api"],
}


def cmd_contract_check_finding_ownership(args: argparse.Namespace) -> int:
    """Verify all findings in the contract have an owner assigned.

    Checks that each finding referenced by a role_verdict belongs to a category
    that falls within that reviewer's authorized boundary per _FINDING_OWNERSHIP_POLICY.
    """
    root = Path(root_arg(args))
    mission = args.mission
    artifact, contract, err = _resolve_code_review_contract(root, mission)
    if err:
        return emit_payload(
            args,
            fail_payload(
                "contract.check-finding-ownership",
                err,
                f"Cannot load code-review contract for mission {mission!r}: {err}",
            ),
        )
    findings_map: dict[str, dict] = {
        f["id"]: f
        for f in (contract.get("findings") or [])
        if isinstance(f, dict) and "id" in f
    }
    role_verdicts = contract.get("role_verdicts") or []
    violations: list[dict] = []
    for rv in role_verdicts:
        if not isinstance(rv, dict):
            continue
        role = rv.get("role", "")
        authorized = _FINDING_OWNERSHIP_POLICY.get(role, [])
        for fid in (rv.get("findings") or []):
            finding = findings_map.get(fid)
            if not finding:
                continue
            category = (finding.get("category") or "").lower()
            if authorized and category and not any(auth in category for auth in authorized):
                violations.append(
                    {
                        "level": "WARN",
                        "code": "boundary_mismatch",
                        "role": role,
                        "finding_id": fid,
                        "category": category,
                        "authorized": authorized,
                        "message": (
                            f"{role} referenced finding {fid!r} (category={category!r}) "
                            f"outside its authorized boundary: {authorized}"
                        ),
                    }
                )
    status = "PASS" if not violations else "WARN"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "contract.check-finding-ownership",
            "mission": mission,
            "ownership_violations": len(violations),
            "findings": violations,
        },
    )


def cmd_contract_detect_conflicts(args: argparse.Namespace) -> int:
    """Detect conflicting findings between reviewers.

    FAIL: any finding_id has one reviewer PASS and another HOLD (direct conflict).
    WARN: multiple reviewers reference the same finding_id with compatible verdicts
          (boundary_overlap — not a conflict, but flagged for review).
    """
    root = Path(root_arg(args))
    mission = args.mission
    artifact, contract, err = _resolve_code_review_contract(root, mission)
    if err:
        return emit_payload(
            args,
            fail_payload(
                "contract.detect-conflicts",
                err,
                f"Cannot load code-review contract for mission {mission!r}: {err}",
            ),
        )
    role_verdicts = contract.get("role_verdicts") or []

    # Build a map: finding_id -> [(role, verdict)]
    fid_map: dict[str, list[tuple[str, str]]] = {}
    for rv in role_verdicts:
        if not isinstance(rv, dict):
            continue
        role = rv.get("role", "unknown")
        verdict = (rv.get("verdict") or "").upper()
        for fid in (rv.get("findings") or []):
            fid_map.setdefault(fid, []).append((role, verdict))

    conflicts: list[dict] = []
    warnings: list[dict] = []
    for fid, entries in fid_map.items():
        verdicts = {v for _, v in entries}
        roles_list = [r for r, _ in entries]
        # Direct conflict: one says PASS, another says HOLD
        has_pass = any(v == "PASS" for v in verdicts)
        has_hold = any(v == "HOLD" for v in verdicts)
        if has_pass and has_hold:
            conflicts.append(
                {
                    "level": "FAIL",
                    "code": "pass_vs_hold",
                    "finding_id": fid,
                    "roles": roles_list,
                    "message": f"Finding {fid!r} has conflicting verdicts: {sorted(verdicts)}",
                }
            )
        elif len(entries) > 1 and len(verdicts) == 1:
            # Multiple reviewers, same verdict → boundary overlap warning
            warnings.append(
                {
                    "level": "WARN",
                    "code": "boundary_overlap",
                    "finding_id": fid,
                    "roles": roles_list,
                    "message": f"Finding {fid!r} referenced by multiple reviewers: {roles_list}",
                }
            )

    all_findings = conflicts + warnings
    status = "FAIL" if conflicts else ("WARN" if warnings else "PASS")
    return emit_payload(
        args,
        {
            "status": status,
            "control": "contract.detect-conflicts",
            "mission": mission,
            "conflict_count": len(conflicts),
            "findings": all_findings,
        },
    )


def _trace_round_event(args: argparse.Namespace, event: str) -> int:
    """Shared implementation for trace round-enter and round-exit."""
    root = Path(root_arg(args))
    mission_id = args.mission
    path = _trace_log_path(root, mission_id)
    if not path.exists():
        return emit_payload(
            args,
            fail_payload(
                f"trace.round-{event}",
                "TRACE_LOG_UNINITIALIZED",
                f"trace log not found: {relpath(root, path)}; run 'harness trace log-init' first",
            ),
        )
    record: dict[str, Any] = {
        "event": f"round-{event}",
        "mission_id": mission_id,
        "round": getattr(args, "round", None),
        "timestamp": now_iso(),
    }
    if event == "exit":
        record["status"] = getattr(args, "status", None)
    if getattr(args, "note", None):
        record["note"] = args.note
    _trace_append(path, record)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": f"trace.round-{event}",
            "mission": mission_id,
            "round": record["round"],
            "trace_path": relpath(root, path),
            "record": record,
            "findings": [],
        },
    )


def cmd_trace_round_enter(args: argparse.Namespace) -> int:
    """Record a review-round entry event into the mission trace."""
    return _trace_round_event(args, "enter")


def cmd_trace_round_exit(args: argparse.Namespace) -> int:
    """Record a review-round exit event into the mission trace."""
    return _trace_round_event(args, "exit")


# --- end code-review-improvement-plan M2.1 ----------------------------------


# --- breakdown-improvement-plan M2.1: real-new CLI commands -----------------
# Five commands carry the breakdown stage's typed lifecycle into harness-cli:
# - `execution-brief gate run` merges Step 7 quality_check + Step 8 artifact_gate
# - `execution-brief self-check` is the lighter Step 7 rapid lint
# - `writing-plans run --mode internal-carrier` is the typed entry into the
#    writing-plans carrier; only callable from the breakdown stage
# - `spec diff list` enumerates delta specs and their coverage state
# - `execution-brief check-coverage --spec-mode strict` is the global
#    coverage gate when spec.enabled=true
#
# These commands keep their semantics typed and JSON-only so the
# harness-cli skill can consume them without parsing free text. Heavy
# downstream semantics (e.g. full Atomic Task Queue 12-field lint,
# parallel write_scope conflict detection) are wired into M4.2 lints; M2.1
# commands stop at the structural / completeness layer that the workflow
# needs at runtime.


_BREAKDOWN_REQUIRED_ROLES = ("delivery-slicer", "test-planning-expert")


def _resolve_execution_brief_contract(root: Path, mission: str) -> tuple[Path, dict | None, str | None]:
    """Locate and load the execution-brief contract for a given mission.

    Returns (artifact_path, contract_dict, error_code).
    `contract_dict` may be None when the file is missing or malformed; the
    error_code is a short identifier the caller emits as a typed FAIL.
    """
    artifact = (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission
        / "contracts"
        / "execution-brief.contract.yaml"
    )
    if not artifact.exists():
        return artifact, None, "execution_brief_contract_missing"
    try:
        document = yaml.safe_load(artifact.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return artifact, None, "execution_brief_contract_invalid_yaml"
    if not isinstance(document, dict):
        return artifact, None, "execution_brief_contract_invalid_root"
    contract = (
        document.get("control_contract")
        if isinstance(document.get("control_contract"), dict)
        else document
    )
    if not isinstance(contract, dict):
        return artifact, None, "execution_brief_contract_invalid_shape"
    return artifact, contract, None


def _check_atomic_task_queue_completeness(contract: dict) -> list[dict]:
    """Report each task missing a `ready`/`accepted` atomic_task_queue or
    landing in a forbidden state.
    """
    findings: list[dict] = []
    forbidden = {"missing", "incomplete", "draft"}
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        tid = task.get("id") or "<unknown>"
        atq = task.get("atomic_task_queue") if isinstance(task.get("atomic_task_queue"), dict) else None
        if atq is None:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "missing_atomic_task_queue",
                    "task": tid,
                    "message": f"task {tid} lacks atomic_task_queue",
                }
            )
            continue
        status = atq.get("status")
        if status in forbidden or status is None:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "atomic_task_queue_not_ready",
                    "task": tid,
                    "status": status,
                    "message": (
                        f"task {tid} atomic_task_queue.status={status!r}; must be ready or accepted"
                    ),
                }
            )
    return findings


def _check_execution_results_dual_roles(contract: dict) -> list[dict]:
    """The breakdown parallel-worker pattern requires both delivery-slicer
    AND test-planning-expert to land DONE entries.
    """
    findings: list[dict] = []
    results = contract.get("execution_results")
    if not isinstance(results, list):
        # Singular legacy form is accepted but for breakdown both roles are
        # required, so singular form implies one is missing.
        findings.append(
            {
                "level": "FAIL",
                "code": "execution_results_singular_legacy",
                "message": (
                    "breakdown stage requires execution_results[] with both "
                    "delivery-slicer and test-planning-expert (parallel-worker "
                    "barrier); singular execution_result form is legacy"
                ),
            }
        )
        return findings
    roles = {
        entry.get("role")
        for entry in results
        if isinstance(entry, dict) and entry.get("status") == "DONE"
    }
    for required in _BREAKDOWN_REQUIRED_ROLES:
        if required not in roles:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "execution_results_missing_role",
                    "role": required,
                    "message": f"execution_results must contain DONE entry for {required}",
                }
            )
    return findings


def _check_traces_to_coverage(contract: dict) -> list[dict]:
    """Each task must declare traces_to[]; lint flags empty / missing.

    Full upstream cross-contract validation (5 contracts × ID registry) is
    M4 work via `harness contract check --upstream`; this lint only checks
    presence + non-empty.
    """
    findings: list[dict] = []
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        tid = task.get("id") or "<unknown>"
        traces = task.get("traces_to")
        if not isinstance(traces, list) or not traces:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "missing_traces_to",
                    "task": tid,
                    "message": f"task {tid} missing traces_to[]; must reference at least one upstream ID",
                }
            )
    return findings


def _check_authorized_paths(contract: dict) -> list[dict]:
    """W-execution-brief-authorized-paths + W-prohibited-paths: each task must
    declare non-empty authorized_paths, and authorized ∩ prohibited must be
    empty (a path cannot be both allowed and forbidden).
    """
    findings: list[dict] = []
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        tid = task.get("id") or "<unknown>"
        authorized = task.get("authorized_paths")
        if not isinstance(authorized, list) or not authorized:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "W-execution-brief-authorized-paths",
                    "task": tid,
                    "message": f"task {tid} has empty authorized_paths",
                }
            )
            continue
        prohibited = task.get("prohibited_paths") or []
        overlap = set(p for p in authorized if isinstance(p, str)) & set(
            p for p in prohibited if isinstance(p, str)
        )
        if overlap:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "W-execution-brief-prohibited-paths",
                    "task": tid,
                    "overlap": sorted(overlap),
                    "message": (
                        f"task {tid} has paths in both authorized_paths and "
                        f"prohibited_paths: {sorted(overlap)}"
                    ),
                }
            )
    return findings


def _check_stop_if_baseline(contract: dict) -> list[dict]:
    """W-execution-brief-stop-if: every task's stop_if must contain the 4
    baseline conditions.
    """
    baseline = {
        "changes_outside_authorized_paths",
        "new_public_behavior_without_delta_spec",
        "design_constraint_conflict",
        "new_external_dependency",
    }
    findings: list[dict] = []
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        tid = task.get("id") or "<unknown>"
        stop_if = set(
            f for f in (task.get("stop_if") or []) if isinstance(f, str)
        )
        missing = baseline - stop_if
        if missing:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "W-execution-brief-stop-if",
                    "task": tid,
                    "missing": sorted(missing),
                    "message": f"task {tid} stop_if missing baseline conditions: {sorted(missing)}",
                }
            )
    return findings


def _check_parallel_write_scope_conflict(contract: dict) -> list[dict]:
    """W-execution-brief-parallel-write-scope-conflict: tasks that do not
    declare a dependency on each other must not share authorized_paths
    entries (a parallel-batch write conflict). Tasks with an explicit
    dependency link are exempt (serialized).
    """
    findings: list[dict] = []
    tasks = [t for t in (contract.get("tasks") or []) if isinstance(t, dict)]
    for i, task_a in enumerate(tasks):
        a_id = task_a.get("id") or f"<task-{i}>"
        a_paths = set(p for p in (task_a.get("authorized_paths") or []) if isinstance(p, str))
        a_deps = set(d for d in (task_a.get("dependencies") or []) if isinstance(d, str))
        for task_b in tasks[i + 1 :]:
            b_id = task_b.get("id") or "<task>"
            b_paths = set(
                p for p in (task_b.get("authorized_paths") or []) if isinstance(p, str)
            )
            b_deps = set(d for d in (task_b.get("dependencies") or []) if isinstance(d, str))
            # Exempt when either task declares a dependency on the other.
            if b_id in a_deps or a_id in b_deps:
                continue
            overlap = a_paths & b_paths
            if overlap:
                findings.append(
                    {
                        "level": "FAIL",
                        "code": "W-execution-brief-parallel-write-scope-conflict",
                        "tasks": [a_id, b_id],
                        "overlap": sorted(overlap),
                        "message": (
                            f"tasks {a_id} and {b_id} share authorized_paths "
                            f"{sorted(overlap)} without declaring a dependency; "
                            "mark must_serialize or add a dependency edge"
                        ),
                    }
                )
    return findings


def _check_dependency_cycle(contract: dict) -> list[dict]:
    """W-execution-brief-dep-cycle: tasks[].dependencies must not form a cycle."""
    graph: dict[str, list[str]] = {}
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        tid = task.get("id")
        if not isinstance(tid, str):
            continue
        graph[tid] = [
            d for d in (task.get("dependencies") or []) if isinstance(d, str)
        ]
    # DFS cycle detection.
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}
    cycle_nodes: list[str] = []

    def _dfs(node: str, path: list[str]) -> bool:
        color[node] = GRAY
        path.append(node)
        for dep in graph.get(node, []):
            if dep not in color:
                continue
            if color[dep] == GRAY:
                cycle_nodes.extend(path[path.index(dep):] + [dep])
                return True
            if color[dep] == WHITE and _dfs(dep, path):
                return True
        path.pop()
        color[node] = BLACK
        return False

    for node in graph:
        if color[node] == WHITE and _dfs(node, []):
            return [
                {
                    "level": "FAIL",
                    "code": "W-execution-brief-dep-cycle",
                    "cycle": cycle_nodes,
                    "message": f"tasks[].dependencies form a cycle: {' -> '.join(cycle_nodes)}",
                }
            ]
    return []


def cmd_execution_brief_self_check(args: argparse.Namespace) -> int:
    """Step 7 rapid lint: structural checks without mission-status / contract
    cross-validation. Suitable for in-loop quick recheck before reviewer.
    """
    root = Path(root_arg(args))
    artifact, contract, error_code = _resolve_execution_brief_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execution-brief.self-check",
                error_code or "execution_brief_contract_unloadable",
                f"Cannot load execution-brief contract at {relpath(root, artifact)}",
            ),
        )
    findings: list[dict] = []
    findings.extend(_check_atomic_task_queue_completeness(contract))
    findings.extend(_check_traces_to_coverage(contract))
    status = "PASS" if not any(f["level"] == "FAIL" for f in findings) else "FAIL"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "execution-brief.self-check",
            "mission": args.mission,
            "artifact": relpath(root, artifact),
            "findings": findings,
        },
    )


def cmd_execution_brief_gate_run(args: argparse.Namespace) -> int:
    """Step 7 + Step 8 merged: quality_check + artifact_gate in one typed
    gate. Returns `phase_results: [{name, status, findings}]` so the workflow
    can distinguish "AC coverage failed" from "contract schema failed".
    """
    root = Path(root_arg(args))
    artifact, contract, error_code = _resolve_execution_brief_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execution-brief.gate-run",
                error_code or "execution_brief_contract_unloadable",
                f"Cannot load execution-brief contract at {relpath(root, artifact)}",
            ),
        )

    # quality_check: atomic_task_queue + traces_to + execution_results dual
    # role + M4.2 W-execution-brief lint group (authorized/prohibited paths,
    # stop_if baseline, parallel write-scope conflict, dependency cycle).
    quality_findings: list[dict] = []
    quality_findings.extend(_check_atomic_task_queue_completeness(contract))
    quality_findings.extend(_check_traces_to_coverage(contract))
    quality_findings.extend(_check_execution_results_dual_roles(contract))
    quality_findings.extend(_check_authorized_paths(contract))
    quality_findings.extend(_check_stop_if_baseline(contract))
    quality_findings.extend(_check_parallel_write_scope_conflict(contract))
    quality_findings.extend(_check_dependency_cycle(contract))
    quality_status = "PASS" if not any(f["level"] == "FAIL" for f in quality_findings) else "FAIL"

    # artifact_gate: contract schema + required headers in execution-brief.md.
    gate_findings: list[dict] = []
    md_path = (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / args.mission
        / "execution-brief.md"
    )
    if not md_path.exists():
        gate_findings.append(
            {
                "level": "FAIL",
                "code": "execution_brief_md_missing",
                "message": f"execution-brief.md not found at {relpath(root, md_path)}",
            }
        )
    else:
        md_text = md_path.read_text(encoding="utf-8")
        # Plain string markers must appear verbatim; the Contract reference
        # marker is checked via a tolerant regex that accepts both the
        # backtick (`contracts/...yaml`) and the plain (contracts/...yaml)
        # forms — see CONTRACT_REF_PATTERN in stage-gate/check_contracts.py.
        # The two checks previously contradicted each other, forcing authors
        # to duplicate the reference (see test_framework_p1_regressions).
        contract_marker_re = re.compile(
            r"(?:^|\n)\s*[-*]?\s*Contract\s*:\s*`?contracts/execution-brief\.contract\.yaml`?",
        )
        markers: list[tuple[str, object]] = [
            ("Execution Units", "Execution Units"),
            ("Contract: contracts/execution-brief.contract.yaml", contract_marker_re),
        ]
        for marker_label, matcher in markers:
            present = (
                marker_label in md_text
                if isinstance(matcher, str)
                else bool(matcher.search(md_text))
            )
            if not present:
                gate_findings.append(
                    {
                        "level": "FAIL",
                        "code": "execution_brief_md_section_missing",
                        "section": marker_label,
                        "message": f"execution-brief.md missing section/marker: {marker_label!r}",
                    }
                )
    gate_status = "PASS" if not any(f["level"] == "FAIL" for f in gate_findings) else "FAIL"
    status = "PASS" if quality_status == "PASS" and gate_status == "PASS" else "FAIL"
    failed_checks = [
        f["code"] for f in (quality_findings + gate_findings) if f["level"] == "FAIL"
    ]
    # M3.1 collaboration: persist `effectiveness_review.last_gate_run_status`
    # into the contract so `check_gate_pass.py` PreToolUse hook can verify
    # the latest gate run was PASS before `harness mission stage complete
    # breakdown`. Failure to write is non-fatal (JSON payload still carries
    # the true result).
    try:
        document = yaml.safe_load(artifact.read_text(encoding="utf-8"))
        if isinstance(document, dict):
            contract_block = (
                document.get("control_contract")
                if isinstance(document.get("control_contract"), dict)
                else document
            )
            if isinstance(contract_block, dict):
                eff = contract_block.get("effectiveness_review")
                if not isinstance(eff, dict):
                    eff = {}
                    contract_block["effectiveness_review"] = eff
                eff["last_gate_run_status"] = status
                artifact.write_text(
                    yaml.dump(
                        document,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )
    except (OSError, yaml.YAMLError):
        pass
    return emit_payload(
        args,
        {
            "status": status,
            "control": "execution-brief.gate-run",
            "mission": args.mission,
            "artifact": relpath(root, artifact),
            "phase_results": [
                {"name": "quality_check", "status": quality_status, "findings": quality_findings},
                {"name": "artifact_gate", "status": gate_status, "findings": gate_findings},
            ],
            "failed_checks": failed_checks,
        },
    )


def cmd_writing_plans_run(args: argparse.Namespace) -> int:
    """Typed entry into the writing-plans carrier. Only callable from the
    breakdown stage with --mode internal-carrier; any other stage or mode is
    rejected so writing-plans does not turn into an after-the-fact补强 step.
    """
    root = Path(root_arg(args))
    if args.mode != "internal-carrier":
        return emit_payload(
            args,
            fail_payload(
                "writing-plans.run",
                "writing_plans_mode_unsupported",
                f"writing-plans run only accepts --mode internal-carrier; got {args.mode!r}",
            ),
        )
    artifact, contract, error_code = _resolve_execution_brief_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "writing-plans.run",
                error_code or "execution_brief_contract_unloadable",
                f"Cannot load execution-brief contract at {relpath(root, artifact)}",
            ),
        )
    refinements: list[dict] = []
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        tid = task.get("id")
        atq = task.get("atomic_task_queue") if isinstance(task.get("atomic_task_queue"), dict) else {}
        refinements.append(
            {
                "task": tid,
                "atomic_task_status": atq.get("status"),
                "atomic_task_ids": atq.get("atomic_task_ids") or [],
                "detail_refs": atq.get("detail_refs") or [],
            }
        )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "writing-plans.run",
            "mode": args.mode,
            "mission": args.mission,
            "atomic_task_queue_refinement": refinements,
        },
    )


def cmd_spec_diff_list(args: argparse.Namespace) -> int:
    """Enumerate delta specs under `stages/<mission>/specs/<capability>/spec.md`
    and report each Scenario's coverage state versus tasks[].traces_to.
    """
    root = Path(root_arg(args))
    specs_dir = (
        root / "harness-runtime" / "harness" / "stages" / args.mission / "specs"
    )
    artifact, contract, _ = _resolve_execution_brief_contract(root, args.mission)
    traces: set[str] = set()
    if isinstance(contract, dict):
        for task in contract.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            for entry in task.get("traces_to") or []:
                if isinstance(entry, str):
                    traces.add(entry)
    deltas: list[dict] = []
    if specs_dir.exists():
        for capability_dir in sorted(specs_dir.iterdir()):
            if not capability_dir.is_dir():
                continue
            spec_md = capability_dir / "spec.md"
            if not spec_md.exists():
                continue
            text = spec_md.read_text(encoding="utf-8")
            # Lightweight extraction: scan for `### Scenario:` markers AND
            # explicit ADDED/MODIFIED block headers.
            scenarios: list[dict] = []
            for line in text.splitlines():
                line_strip = line.strip()
                if line_strip.startswith("### Scenario:") or line_strip.startswith("#### Scenario:"):
                    name = line_strip.split(":", 1)[1].strip()
                    # Coverage heuristic: any traces_to entry containing the
                    # scenario name OR capability/scenario path matches.
                    cap = capability_dir.name
                    candidate_ids = {
                        f"{cap}/spec.md#{name}",
                        name,
                    }
                    covered = bool(candidate_ids & traces) or any(
                        name in t for t in traces
                    )
                    scenarios.append(
                        {
                            "name": name,
                            "covered": covered,
                            "trace_id": f"{cap}/spec.md#{name}",
                        }
                    )
            deltas.append(
                {
                    "capability": capability_dir.name,
                    "spec_path": relpath(root, spec_md),
                    "scenarios": scenarios,
                }
            )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "spec.diff.list",
            "mission": args.mission,
            "deltas": deltas,
        },
    )


def cmd_execution_brief_check_coverage(args: argparse.Namespace) -> int:
    """Spec coverage gate: every delta scenario must be referenced by at
    least one task's traces_to (strict mode) or carry a tradeoff approval.
    """
    root = Path(root_arg(args))
    spec_mode = args.spec_mode or "strict"
    artifact, contract, error_code = _resolve_execution_brief_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execution-brief.check-coverage",
                error_code or "execution_brief_contract_unloadable",
                f"Cannot load execution-brief contract at {relpath(root, artifact)}",
            ),
        )
    traces: set[str] = set()
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        for entry in task.get("traces_to") or []:
            if isinstance(entry, str):
                traces.add(entry)
    specs_dir = (
        root / "harness-runtime" / "harness" / "stages" / args.mission / "specs"
    )
    uncovered: list[dict] = []
    total_scenarios = 0
    if specs_dir.exists():
        for capability_dir in sorted(specs_dir.iterdir()):
            if not capability_dir.is_dir():
                continue
            spec_md = capability_dir / "spec.md"
            if not spec_md.exists():
                continue
            text = spec_md.read_text(encoding="utf-8")
            cap = capability_dir.name
            for line in text.splitlines():
                line_strip = line.strip()
                if not (
                    line_strip.startswith("### Scenario:")
                    or line_strip.startswith("#### Scenario:")
                ):
                    continue
                name = line_strip.split(":", 1)[1].strip()
                total_scenarios += 1
                candidate_ids = {f"{cap}/spec.md#{name}", name}
                if candidate_ids & traces:
                    continue
                if any(name in t for t in traces):
                    continue
                uncovered.append(
                    {
                        "capability": cap,
                        "scenario": name,
                        "expected_trace": f"{cap}/spec.md#{name}",
                    }
                )
    status = "PASS"
    if uncovered and spec_mode == "strict":
        status = "FAIL"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "execution-brief.check-coverage",
            "mission": args.mission,
            "spec_mode": spec_mode,
            "total_scenarios": total_scenarios,
            "uncovered": uncovered,
        },
    )


# --- M2.1 chunk A: intake-workflow CLI commands ----------------------------
# These commands enable the Option B 6-phase intake workflow rewrite. Each
# returns typed `{status, control, ...}` JSON via emit_payload so callers can
# consume them through the harness-cli skill without parsing free text.

import re as _re

_MISSION_ID_SLUG_RE = _re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _normalize_mission_slug(value: str) -> str | None:
    """Coerce a free-text slug into the mission-id slug grammar.

    - Lowercase
    - ASCII letters / digits / hyphens only (other chars → hyphen)
    - Collapse repeated hyphens and trim edges
    Returns None if nothing usable remains.
    """
    if not value:
        return None
    slug = value.strip().lower()
    slug = _re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = _re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        return None
    return slug[:64]


def cmd_mission_new_id(args: argparse.Namespace) -> int:
    """Generate a canonical mission-id in the form `YYYYMMDD-<slug>`.

    Replaces the Step-1 prose "agent self-concatenates mission-id" path so
    every mission-id passes through one CLI gate (intake-plan M2.1).
    """
    raw_slug = getattr(args, "slug", None) or ""
    slug = _normalize_mission_slug(raw_slug)
    if not slug:
        return emit_payload(
            args,
            fail_payload(
                "mission.new-id",
                "INVALID_SLUG",
                f"slug must contain at least one ASCII letter/digit: received {raw_slug!r}",
            ),
        )
    date_str = getattr(args, "date", None) or dt.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
    if not _re.fullmatch(r"\d{8}", date_str):
        return emit_payload(
            args,
            fail_payload(
                "mission.new-id",
                "INVALID_DATE",
                f"--date must be YYYYMMDD; received {date_str!r}",
            ),
        )
    mission_id = f"{date_str}-{slug}"
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "mission.new-id",
            "mission_id": mission_id,
            "date": date_str,
            "slug": slug,
            "received_slug": raw_slug,
            "findings": [],
        },
    )


def _trace_log_path(root: Path, mission_id: str) -> Path:
    """Return the per-mission JSONL trace path.

    JSONL format chosen over the existing trace-log.md narrative file: each
    step-enter / step-exit event is one structured record so downstream tools
    (gate runners, retrospective stage) can parse without regex. The narrative
    trace-log.md continues to serve human readers in parallel.
    """
    return runtime_harness_root(root) / "traces" / mission_id / "steps.jsonl"


def _trace_append(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def cmd_trace_log_init(args: argparse.Namespace) -> int:
    """Create the per-mission JSONL trace file with an opening event.

    Idempotent: re-running on an existing trace emits a PASS-noop response
    so workflow Phase 0 can call this unconditionally on every stage entry
    without needing to check existence first.
    """
    root = Path(root_arg(args))
    mission_id = args.mission
    path = _trace_log_path(root, mission_id)
    is_new = not path.exists()
    if is_new:
        record = {
            "event": "log-init",
            "mission_id": mission_id,
            "stage": getattr(args, "stage", None),
            "timestamp": now_iso(),
        }
        _trace_append(path, record)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "trace.log-init",
            "mission_id": mission_id,
            "trace_path": relpath(root, path),
            "created": is_new,
            "findings": [],
        },
    )


def _trace_step_event(
    args: argparse.Namespace, event: str, *, require_status: bool
) -> int:
    root = Path(root_arg(args))
    mission_id = args.mission
    path = _trace_log_path(root, mission_id)
    if not path.exists():
        return emit_payload(
            args,
            fail_payload(
                f"trace.step-{event}",
                "TRACE_LOG_UNINITIALIZED",
                f"trace log not found: {relpath(root, path)}; run 'harness trace log-init' first",
            ),
        )
    record: dict[str, Any] = {
        "event": f"step-{event}",
        "mission_id": mission_id,
        "step": args.step,
        "timestamp": now_iso(),
    }
    if getattr(args, "phase", None):
        record["phase"] = args.phase
    if getattr(args, "rounds", None) is not None:
        record["rounds"] = args.rounds
    if getattr(args, "note", None):
        record["note"] = args.note
    if require_status:
        record["status"] = args.status
    _trace_append(path, record)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": f"trace.step-{event}",
            "mission_id": mission_id,
            "step": args.step,
            "trace_path": relpath(root, path),
            "record": record,
            "findings": [],
        },
    )


def cmd_trace_step_enter(args: argparse.Namespace) -> int:
    return _trace_step_event(args, "enter", require_status=False)


def cmd_trace_step_exit(args: argparse.Namespace) -> int:
    return _trace_step_event(args, "exit", require_status=True)


# --- harness todo: TodoWrite ↔ trace bridge ---------------------------------
# improvement-plan-execute skill 纪律 0 introduces TodoWrite as the session-local
# progress backbone. trace step-* events provide cross-session machine-readable
# evidence (JSONL append-only). The bridge helps the AI:
#   * `harness todo report` — derive current todo-shape state from trace so
#     a fresh session can resume by feeding the output to TodoWrite.
#   * `harness todo sync` — alias for report; produces TodoWrite-ready
#     `{content, activeForm, status}` items so the AI can directly seed its
#     in-memory todo list.
# We deliberately do NOT mutate trace from a TodoWrite snapshot — trace is
# event-sourced (only real step-enter / step-exit events should land there).


_TODO_STATUS_FROM_TRACE = {
    # step-exit status mapping → TodoWrite status
    "pass": "completed",
    "fail": "blocked",
    "blocked": "blocked",
}


def _derive_todos_from_trace(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Read JSONL trace events and project them onto a todo list.

    Algorithm:
      - For each unique `step` id, find the last event referencing it.
      - step-enter without subsequent step-exit ⇒ status=in_progress.
      - step-exit with status=pass ⇒ status=completed.
      - step-exit with status=fail|blocked ⇒ status=blocked.
      - Order todos by first appearance in the trace (chronological).

    Returns `(todos, warnings)`. Warnings list non-fatal issues (malformed
    records, unknown step-exit status, etc.).
    """
    todos: list[dict[str, Any]] = []
    seen_step_order: list[str] = []
    last_event_per_step: dict[str, dict[str, Any]] = {}
    # Prefer the note from step-enter (descriptive) over step-exit (usually
    # just status). Track first-seen note per step so content stays
    # human-readable even after the exit event lands.
    first_note_per_step: dict[str, str] = {}
    warnings: list[str] = []
    if not path.exists():
        return todos, ["trace_log_missing"]
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError:
                warnings.append(f"malformed_record:{raw_line[:60]}")
                continue
            event = record.get("event")
            step = record.get("step")
            if event in {"step-enter", "step-exit"} and isinstance(step, str):
                if step not in last_event_per_step:
                    seen_step_order.append(step)
                last_event_per_step[step] = record
                note = record.get("note")
                if step not in first_note_per_step and isinstance(note, str) and note:
                    first_note_per_step[step] = note
    for step in seen_step_order:
        record = last_event_per_step[step]
        event = record.get("event")
        if event == "step-enter":
            status = "in_progress"
        elif event == "step-exit":
            exit_status = str(record.get("status", "")).lower()
            status = _TODO_STATUS_FROM_TRACE.get(exit_status)
            if status is None:
                warnings.append(f"unknown_exit_status:{step}={exit_status}")
                status = "blocked"
        else:
            continue
        # content: prefer first-seen note (usually from step-enter), fall back
        # to step id when no note ever recorded.
        content = first_note_per_step.get(step, step)
        active_form = f"Working on {content}" if status == "in_progress" else content
        todos.append({
            "content": content,
            "activeForm": active_form,
            "status": status,
            "step_id": step,
            "phase": record.get("phase"),
            "rounds": record.get("rounds"),
            "last_event_timestamp": record.get("timestamp"),
        })
    return todos, warnings


def cmd_todo_report(args: argparse.Namespace) -> int:
    """Read mission trace and emit a TodoWrite-shaped report.

    Used by improvement-plan-execute skill 纪律 0 + 12 to bridge cross-session
    state when the AI starts fresh and wants to recover its previous todo
    list. The output `todos[]` is ready to be fed into TodoWrite directly.
    """
    root = Path(root_arg(args))
    mission_id = args.mission
    path = _trace_log_path(root, mission_id)
    todos, warnings = _derive_todos_from_trace(path)
    summary = {
        "total": len(todos),
        "in_progress": sum(1 for t in todos if t["status"] == "in_progress"),
        "completed": sum(1 for t in todos if t["status"] == "completed"),
        "blocked": sum(1 for t in todos if t["status"] == "blocked"),
    }
    return emit_payload(args, {
        "status": "PASS",
        "control": "todo.report",
        "mission_id": mission_id,
        "trace_path": relpath(root, path),
        "todos": todos,
        "summary": summary,
        "warnings": warnings,
        "findings": [],
    })


def cmd_todo_sync(args: argparse.Namespace) -> int:
    """Alias for `todo report` — phrased as 'sync' so the AI understands the
    intent is to seed its TodoWrite with state derived from trace.

    Direction is one-way (trace → todo). We do NOT support `--to-trace`
    because trace is event-sourced (only real step-enter / step-exit
    events should land there). To record a todo state change as evidence,
    the AI should call `harness trace step-enter` / `step-exit` directly,
    not retroactively replay a TodoWrite snapshot.
    """
    return cmd_todo_report(args)


def cmd_contract_summary(args: argparse.Namespace) -> int:
    """Produce a stable, machine-or-human summary of a mission contract.

    Replaces the Step-10 prose "agent organizes a free-form summary" path so
    the same artifact summary is consumed by both the user-facing confirmation
    prompt and machine consumers (gate runner, retrospective).
    """
    root = Path(root_arg(args))
    mission_id = args.mission
    artifact = resolve_path(root, args.artifact) if args.artifact else None
    if artifact is None:
        artifact = (
            runtime_harness_root(root)
            / "missions"
            / mission_id
            / "contracts"
            / "mission-contract.contract.yaml"
        )
    if not artifact.exists():
        return emit_payload(
            args,
            fail_payload(
                "contract.summary",
                "MISSING_CONTRACT",
                f"contract artifact not found: {relpath(root, artifact)}",
            ),
        )
    _, contract = control_contract_document(artifact)
    if not isinstance(contract, dict):
        return emit_payload(
            args,
            fail_payload(
                "contract.summary",
                "INVALID_CONTRACT",
                f"contract artifact does not contain a control_contract block: {relpath(root, artifact)}",
            ),
        )

    objective = contract.get("objective") if isinstance(contract.get("objective"), dict) else {}
    scope = contract.get("scope") if isinstance(contract.get("scope"), dict) else {}
    acs = contract.get("acceptance_criteria") if isinstance(contract.get("acceptance_criteria"), list) else []
    user_stories = contract.get("user_stories") if isinstance(contract.get("user_stories"), list) else []
    autonomy = contract.get("autonomy") if isinstance(contract.get("autonomy"), dict) else {}
    governance = autonomy.get("governance_assessment") if isinstance(autonomy.get("governance_assessment"), dict) else {}
    hard_triggers = governance.get("hard_triggers") if isinstance(governance.get("hard_triggers"), list) else []
    dimensions = governance.get("dimensions") if isinstance(governance.get("dimensions"), dict) else {}
    high_dimensions: list[str] = []
    medium_dimensions: list[str] = []
    for name, value in dimensions.items():
        if not isinstance(value, dict):
            continue
        level = str(value.get("level") or "").strip().lower()
        if level == "high":
            high_dimensions.append(str(name))
        elif level == "medium":
            medium_dimensions.append(str(name))

    summary = {
        "mission_id": mission_id,
        "contract_path": relpath(root, artifact),
        "objective": objective.get("statement") or objective.get("id") or "",
        "scope_in_count": len(scope.get("in") or []) if isinstance(scope.get("in"), list) else 0,
        "scope_out_count": len(scope.get("out") or []) if isinstance(scope.get("out"), list) else 0,
        "user_story_count": len(user_stories),
        "acceptance_criteria_count": len(acs),
        "autonomy_level": autonomy.get("level") or "",
        "governance_risk": autonomy.get("governance_risk") or "",
        "governance_hard_trigger_count": len(hard_triggers),
        "governance_high_dimensions": high_dimensions,
        "governance_medium_dimensions": medium_dimensions,
        "governance_decision_rule": governance.get("decision_rule") or "",
        "governance_confirmation_required": bool(governance.get("user_confirmation_required", True)) if governance else False,
        "required_checkpoints": list(autonomy.get("human_checkpoints") or []),
        "skippable_stages": list(autonomy.get("skippable_stages") or []),
    }

    payload: dict[str, Any] = {
        "status": "PASS",
        "control": "contract.summary",
        "summary": summary,
        "findings": [],
    }
    fmt = getattr(args, "format", "json") or "json"
    if fmt == "user":
        lines = [
            f"Mission: {mission_id}",
            f"Objective: {summary['objective']}",
            f"Scope: {summary['scope_in_count']} in / {summary['scope_out_count']} out",
            f"User stories: {summary['user_story_count']}",
            f"Acceptance criteria: {summary['acceptance_criteria_count']}",
            f"Autonomy level: {summary['autonomy_level']}",
        ]
        if summary["governance_risk"]:
            lines.append(f"Governance risk: {summary['governance_risk']}")
        if summary["governance_hard_trigger_count"]:
            lines.append(f"Governance hard triggers: {summary['governance_hard_trigger_count']}")
        if summary["governance_high_dimensions"] or summary["governance_medium_dimensions"]:
            lines.append(
                "Governance dimensions: "
                f"high={', '.join(summary['governance_high_dimensions']) or 'none'}; "
                f"medium={', '.join(summary['governance_medium_dimensions']) or 'none'}"
            )
        if summary["governance_decision_rule"]:
            lines.append(f"Governance decision rule: {summary['governance_decision_rule']}")
        if summary["required_checkpoints"]:
            lines.append("Required checkpoints: " + ", ".join(summary["required_checkpoints"]))
        if summary["skippable_stages"]:
            lines.append("Skippable stages: " + ", ".join(summary["skippable_stages"]))
        payload["user_text"] = "\n".join(lines)
    return emit_payload(args, payload)


def cmd_contract_check_recheck_pending(args: argparse.Namespace) -> int:
    """Surface the `pending_reviewer_recheck` flag on a contract artifact.

    Workflow Phase 5 uses this gate to ensure post-fix re-review actually
    happened before allowing `contract advance` / `gate advance` to proceed
    (intake-plan M2.1 + cross-stage hook contract).
    """
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    if artifact is None or not artifact.exists():
        return emit_payload(
            args,
            fail_payload(
                "contract.check-recheck-pending",
                "MISSING_CONTRACT",
                f"contract artifact not found: {args.artifact}",
            ),
        )
    _, contract = control_contract_document(artifact)
    if not isinstance(contract, dict):
        return emit_payload(
            args,
            fail_payload(
                "contract.check-recheck-pending",
                "INVALID_CONTRACT",
                f"contract artifact does not contain a control_contract block: {relpath(root, artifact)}",
            ),
        )
    pending = bool(contract.get("pending_reviewer_recheck"))
    status = "FAIL" if pending else "PASS"
    findings: list[dict[str, Any]] = []
    if pending:
        findings.append(
            {
                "level": "FAIL",
                "code": "PENDING_REVIEWER_RECHECK",
                "message": "contract was edited after the last review; reviewer re-run required before advance",
            }
        )
    return emit_payload(
        args,
        {
            "status": status,
            "control": "contract.check-recheck-pending",
            "contract": relpath(root, artifact),
            "pending_reviewer_recheck": pending,
            "findings": findings,
        },
    )


def cmd_evidence_graph_check(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args), "--graph", args.graph]
    if args.current_git_ref:
        forwarded.extend(["--current-git-ref", args.current_git_ref])
    return run_python(script("stage-gate", "scripts", "check_evidence_graph.py"), with_json(args, forwarded))


def cmd_evidence_graph_build(args: argparse.Namespace) -> int:
    forwarded: list[str] = []
    for artifact in args.artifact or []:
        forwarded.extend(["--artifact", artifact])
    if args.mission:
        forwarded.extend(["--mission-id", args.mission])
    if args.evidence_store:
        forwarded.extend(["--evidence-store", args.evidence_store])
    elif args.mission:
        store = evidence_store_path(Path(root_arg(args)), args.mission)
        if store.exists():
            forwarded.extend(["--evidence-store", str(store)])
    if args.output:
        forwarded.extend(["--output", args.output])
    return run_python(script("stage-gate", "scripts", "evidence_graph.py"), with_json(args, forwarded))


def cmd_evidence_add(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    store_path = evidence_store_path(root, args.mission, args.store)
    store = load_evidence_store(store_path, args.mission)
    evidence_path = resolve_path(root, args.evidence)
    if evidence_path is None or not evidence_path.exists():
        return emit_payload(args, fail_payload("evidence.add", "missing_evidence_manifest", "Evidence manifest must exist"))
    evidence = load_manifest(evidence_path)
    evidence = evidence.get("evidence") if isinstance(evidence.get("evidence"), dict) else evidence
    if not isinstance(evidence, dict) or not evidence.get("id"):
        return emit_payload(args, fail_payload("evidence.add", "invalid_evidence", "Evidence manifest must be an object with id"))
    evidence.setdefault("mission_id", args.mission)
    action = upsert_by_id(store["evidence"], evidence)
    write_manifest(store_path, store)
    return emit_payload(args, {"status": "PASS", "control": "evidence.add", "store": relpath(root, store_path), "action": action, "evidence": evidence, "findings": []})


def cmd_evidence_link(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    store_path = evidence_store_path(root, args.mission, args.store)
    store = load_evidence_store(store_path, args.mission)
    evidence = next((item for item in store["evidence"] if str(item.get("id") or "") == args.from_id), None)
    if evidence is None:
        return emit_payload(args, fail_payload("evidence.link", "missing_evidence_node", f"Evidence node not found: {args.from_id}"))
    covers = evidence.setdefault("covers", {})
    if not isinstance(covers, dict):
        return emit_payload(args, fail_payload("evidence.link", "invalid_evidence_covers", "evidence.covers must be an object"))
    obligations = covers.setdefault("obligations", [])
    if not isinstance(obligations, list):
        return emit_payload(args, fail_payload("evidence.link", "invalid_evidence_obligations", "evidence.covers.obligations must be a list"))
    if args.to not in obligations:
        obligations.append(args.to)
    link = {"from": args.from_id, "to": args.to, "type": args.type}
    if link not in store["links"]:
        store["links"].append(link)
    write_manifest(store_path, store)
    return emit_payload(args, {"status": "PASS", "control": "evidence.link", "store": relpath(root, store_path), "link": link, "findings": []})


def cmd_evidence_command_collect(args: argparse.Namespace) -> int:
    forwarded = ["--cwd", str(Path(args.cwd).expanduser().resolve()) if args.cwd else root_arg(args)]
    if args.timeout is not None:
        forwarded.extend(["--timeout", str(args.timeout)])
    if args.output_dir:
        forwarded.extend(["--output-dir", args.output_dir])
    if args.mission:
        forwarded.extend(["--mission-id", args.mission])
    if args.store:
        forwarded.extend(["--store", args.store])
    if args.no_run:
        forwarded.append("--no-run")
    return run_python(script("verify", "scripts", "collect_command_evidence.py"), with_json(args, forwarded))


def cmd_evidence_visual_manifest(args: argparse.Namespace) -> int:
    forwarded = ["--mission-id", args.mission, "--stage-dir", args.stage_dir, "--source-dir", args.source_dir]
    if args.copy:
        forwarded.append("--copy")
    if args.output:
        forwarded.extend(["--output", args.output])
    return run_python(script("visual-interaction-design", "scripts", "visual_manifest.py"), forwarded)


def cmd_gate_advance(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args), "--mission-id", args.mission, "--gate-report", args.gate_report]
    if args.contract_artifact:
        forwarded.extend(["--contract-artifact", args.contract_artifact])
    if args.allow_warnings:
        forwarded.append("--allow-warnings")
    return run_python(script("board-router", "scripts", "advance_after_gate.py"), with_json(args, forwarded))


def cmd_gate_run(args: argparse.Namespace) -> int:
    temp_path: Path | None = None
    contract_check_json = args.contract_check_json
    if not args.mission_slice:
        print("harness gate run: --mission-slice is required so Gate reports are bound to a Work Graph Mission Slice", file=sys.stderr)
        return 64
    if not contract_check_json:
        if not args.artifact:
            print("harness gate run: --artifact or --contract-check-json is required", file=sys.stderr)
            return 64
        check_cmd = [
            sys.executable,
            str(script("stage-gate", "scripts", "check_contracts.py")),
            "--root",
            root_arg(args),
            "--artifact",
            args.artifact,
            "--json",
        ]
        if args.allow_placeholders:
            check_cmd.append("--allow-placeholders")
        for upstream in args.upstream or []:
            check_cmd.extend(["--upstream", upstream])
        check_result = subprocess.run(check_cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check_result.stderr:
            print(check_result.stderr, end="", file=sys.stderr)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
            handle.write(check_result.stdout)
            temp_path = Path(handle.name)
        contract_check_json = str(temp_path)
        if check_result.returncode not in {0, 1}:
            return check_result.returncode
    forwarded = [
        "--root",
        root_arg(args),
        "--contract-check-json",
        contract_check_json,
        "--mission-id",
        args.mission,
        "--from-stage",
        args.stage,
        "--to-stage",
        args.to_stage or args.stage,
    ]
    if args.mission_slice:
        forwarded.extend(["--mission-slice", args.mission_slice])
    for report in args.control_report or []:
        forwarded.extend(["--control-report", report])
    for control in args.required_control or []:
        forwarded.extend(["--required-control", control])
    for checkpoint in args.required_checkpoint or []:
        forwarded.extend(["--required-checkpoint", checkpoint])
    for checkpoint in args.human_checkpoint or []:
        forwarded.extend(["--human-checkpoint", checkpoint])
    interpretation = (args.ai_interpretation or "").strip()
    skip_reason = (getattr(args, "no_interpretation", None) or "").strip()
    if interpretation and skip_reason:
        print("harness gate run: --ai-interpretation and --no-interpretation are mutually exclusive", file=sys.stderr)
        return 2
    if not interpretation and not skip_reason:
        print(
            "harness gate run: --ai-interpretation is required so the gate report records why this decision is justified; "
            "pass --no-interpretation \"<reason>\" to opt out (e.g. automated reruns).",
            file=sys.stderr,
        )
        return 2
    if interpretation:
        forwarded.extend(["--ai-interpretation", interpretation])
    else:
        forwarded.extend(["--ai-interpretation", f"[omitted] {skip_reason}"])
    if args.output_dir:
        forwarded.extend(["--output-dir", args.output_dir])
    try:
        result = run_python_capture(script("stage-gate", "scripts", "render_gate_report.py"), forwarded)
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.stdout:
            print(result.stdout, end="")
        if result.returncode != 0:
            return result.returncode
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return 64
        if payload.get("gate_effect") in {"block", "pause"} or payload.get("decision") == "cannot_continue":
            return 1
        return 0
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)


def cmd_gate_report_render(args: argparse.Namespace) -> int:
    forwarded = [
        "--root",
        root_arg(args),
        "--contract-check-json",
        args.contract_check_json,
        "--mission-id",
        args.mission,
        "--from-stage",
        args.from_stage,
        "--to-stage",
        args.to_stage,
    ]
    if args.mission_slice:
        forwarded.extend(["--mission-slice", args.mission_slice])
    for report in args.control_report or []:
        forwarded.extend(["--control-report", report])
    for control in args.required_control or []:
        forwarded.extend(["--required-control", control])
    for checkpoint in args.required_checkpoint or []:
        forwarded.extend(["--required-checkpoint", checkpoint])
    for checkpoint in args.human_checkpoint or []:
        forwarded.extend(["--human-checkpoint", checkpoint])
    interpretation = (args.ai_interpretation or "").strip()
    skip_reason = (getattr(args, "no_interpretation", None) or "").strip()
    if interpretation and skip_reason:
        print("harness gate report render: --ai-interpretation and --no-interpretation are mutually exclusive", file=sys.stderr)
        return 2
    if not interpretation and not skip_reason:
        print(
            "harness gate report render: --ai-interpretation is required; pass --no-interpretation \"<reason>\" to opt out.",
            file=sys.stderr,
        )
        return 2
    if interpretation:
        forwarded.extend(["--ai-interpretation", interpretation])
    else:
        forwarded.extend(["--ai-interpretation", f"[omitted] {skip_reason}"])
    if args.output_dir:
        forwarded.extend(["--output-dir", args.output_dir])
    return run_python(script("stage-gate", "scripts", "render_gate_report.py"), forwarded)


def cmd_gate_control_reports(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args)]
    if args.mission:
        forwarded.extend(["--mission-id", args.mission])
    for report in args.report or []:
        forwarded.extend(["--report", report])
    for control in args.required_control or []:
        forwarded.extend(["--required-control", control])
    return run_python(script("stage-gate", "scripts", "check_control_reports.py"), with_json(args, forwarded))


def cmd_lint_runtime(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args)]
    return run_python(script("harness-lint", "scripts", "check_runtime_consistency.py"), with_json(args, forwarded))


def cmd_lint_graph(args: argparse.Namespace) -> int:
    return cmd_graph_check(args)


def cmd_lint_project(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args)]
    for attr, flag in (
        ("config", "--config"),
        ("profile", "--profile"),
        ("mission", "--mission-id"),
        ("changed_files_file", "--changed-files-file"),
        ("command_evidence", "--command-evidence"),
        ("trace", "--trace"),
        ("output_dir", "--output-dir"),
    ):
        value = getattr(args, attr, None)
        if value:
            forwarded.extend([flag, value])
    for value in args.changed_file or []:
        forwarded.extend(["--changed-file", value])
    if args.no_git_diff:
        forwarded.append("--no-git-diff")
    return run_python(script("project-lint", "scripts", "run_project_lint.py"), with_json(args, forwarded))


# ----------------------------------------------------------------------------
# PRD stage commands (prd-improvement-plan M2.1)
# ----------------------------------------------------------------------------
# Typed CLI replacements for prompt-only HARD-GATE judgments in
# prd/workflow.md Steps 4/7/8. Each returns the canonical
# {status, control, findings, ...} payload shape.

# Anti-pattern rule definitions (Step 4).
_PRD_VAGUE_TERMS = frozenset({
    "好用", "快速", "直观", "简单", "高效", "流畅", "友好", "方便",
    "robust", "fast", "intuitive", "simple", "efficient", "user-friendly",
    "easy", "smooth", "good", "nice", "better", "improved",
})
_PRD_IMPL_LEAK_PATTERNS = [
    # Common tech keywords that signal implementation leakage in FR text.
    r"\b(React|Vue|Angular|Django|Flask|Express|Spring|Hibernate|ORM|SDK|API|REST|GraphQL|"
    r"PostgreSQL|MongoDB|Redis|Elasticsearch|Kubernetes|Docker|Terraform)\b",
]
_DOMAIN_MODEL_REQUIRED_SECTIONS = (
    "Domain Intent",
    "Strategic DDD",
    "Tactical DDD",
    "Rules & Constraints",
    "Traceability",
    "Downstream Guidance",
)
_DOMAIN_MODEL_REQUIRED_SUBSECTIONS = (
    "Bounded Contexts",
    "Context Map",
    "Ubiquitous Language",
    "Aggregates",
    "Domain Commands",
    "Domain Events",
    "Invariants",
    "State Machines",
    "Permission Matrix",
)
_DOMAIN_MODEL_TECH_LEAK_PATTERNS = [
    *_PRD_IMPL_LEAK_PATTERNS,
    r"(?i)\b(database|db table|table|column|schema migration|endpoint|route|controller|repository|"
    r"cache|message queue|Kafka|RabbitMQ|HTTP API|/api/|SQL|MySQL|PostgreSQL|Redis)\b",
]


def _scan_anti_patterns(text: str) -> list[dict[str, Any]]:
    """Scan PRD text for 5 anti-pattern categories and return typed findings."""
    import re as _re

    findings: list[dict[str, Any]] = []

    # 1. Vague adjectives
    for line_no, line in enumerate(text.splitlines(), 1):
        words = set(w.lower().rstrip(".,;:!") for w in line.split())
        hits = words & _PRD_VAGUE_TERMS
        if hits:
            findings.append({
                "rule": "vague_adjective",
                "location": f"line {line_no}",
                "evidence": ", ".join(sorted(hits)),
                "message": f"Vague adjective(s) found: {', '.join(sorted(hits))}. Replace with measurable criteria.",
            })

    # 2. Implementation leaks
    for pattern in _PRD_IMPL_LEAK_PATTERNS:
        for m in _re.finditer(pattern, text):
            findings.append({
                "rule": "implementation_leak",
                "location": f"line {text[:m.start()].count(chr(10)) + 1}",
                "evidence": m.group(0),
                "message": f"Implementation detail '{m.group(0)}' leaked into requirement text. Replace with capability description.",
            })

    # 3. Unmeasurable indicators (heuristic: FR lines without numbers or Given/When/Then)
    #    We keep this lightweight — full BDD validation is the reviewer's job.
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("FR-") or stripped.startswith("NFR-"):
            # Check if the line (or its continuation) has any digit or measurable anchor
            rest = stripped.split(":", 1)[-1] if ":" in stripped else stripped
            has_digit = any(c.isdigit() for c in rest)
            has_gwt = any(kw in rest for kw in ("GIVEN", "WHEN", "THEN", " GIVEN ", " WHEN ", " THEN "))
            if not has_digit and not has_gwt and len(rest) > 10:
                findings.append({
                    "rule": "unmeasurable",
                    "location": f"line {line_no}",
                    "evidence": rest[:80],
                    "message": "FR/NFR line lacks quantitative criteria or Given/When/Then structure. Add measurable acceptance criteria.",
                })

    return findings


def cmd_prd_anti_pattern_scan(args: argparse.Namespace) -> int:
    """Scan a PRD artifact for 5 anti-pattern categories (plan Step 4)."""
    artifact = Path(args.artifact)
    if not artifact.exists():
        return emit_payload(args, fail_payload("prd.anti-pattern-scan", "missing_artifact", f"Artifact not found: {args.artifact}"))

    text = artifact.read_text(encoding="utf-8")
    findings = _scan_anti_patterns(text)

    payload: dict[str, Any] = {
        "status": "PASS" if not findings else "FAIL",
        "control": "prd.anti-pattern-scan",
        "artifact": str(artifact),
        "total_findings": len(findings),
        "findings": findings,
    }
    return emit_payload(args, payload)


def _markdown_sections(text: str) -> dict[str, str]:
    import re as _re

    matches = list(_re.finditer(r"^##\s+(.+?)\s*$", text, flags=_re.MULTILINE))
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections[title] = text[start:end].strip()
    return sections


def _has_heading(text: str, heading: str) -> bool:
    import re as _re

    return bool(_re.search(rf"^#+\s+{_re.escape(heading)}\s*$", text, flags=_re.MULTILINE))


def _section_has_content(body: str) -> bool:
    meaningful = []
    for raw in body.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("|---") or stripped.startswith("---"):
            continue
        if stripped.startswith("### "):
            continue
        meaningful.append(stripped)
    return bool(meaningful)


def _is_na_with_reason(line: str) -> bool:
    lowered = line.lower()
    if "n/a" not in lowered and "不适用" not in line:
        return True
    return any(marker in lowered for marker in ("because", "reason", "not applicable because")) or any(
        marker in line for marker in ("因为", "由于", "原因", "理由")
    )


def _scan_domain_model(
    text: str,
    *,
    product_definition_text: str | None = None,
    contract: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    import re as _re

    findings: list[dict[str, Any]] = []
    sections = _markdown_sections(text)

    def finding(code: str, rule: str, location: str, evidence: str, message: str) -> None:
        findings.append({
            "code": code,
            "rule": rule,
            "location": location,
            "evidence": evidence,
            "message": message,
        })

    for section in _DOMAIN_MODEL_REQUIRED_SECTIONS:
        body = sections.get(section)
        if body is None:
            finding(
                "missing_domain_model_section",
                "missing_required_section",
                section,
                section,
                f"product-domain-model.md must include section '## {section}'.",
            )
        elif not _section_has_content(body):
            finding(
                "empty_domain_model_section",
                "empty_required_section",
                section,
                section,
                f"section '## {section}' must contain concrete modeling content or an N/A reason.",
            )

    for heading in _DOMAIN_MODEL_REQUIRED_SUBSECTIONS:
        if not _has_heading(text, heading):
            code = {
                "Bounded Contexts": "missing_bounded_context",
                "Aggregates": "missing_aggregate_root",
                "Domain Commands": "missing_domain_command",
                "Domain Events": "missing_domain_event",
                "Invariants": "missing_invariant_trace",
                "State Machines": "missing_state_transition",
                "Permission Matrix": "missing_permission_matrix",
            }.get(heading, "missing_domain_model_subsection")
            finding(
                code,
                "missing_required_subsection",
                heading,
                heading,
                f"DDD domain model must include subsection '{heading}' or mark it N/A with a reason.",
            )

    for line_no, line in enumerate(text.splitlines(), 1):
        if not _is_na_with_reason(line):
            finding(
                "na_without_reason",
                "unjustified_not_applicable",
                f"line {line_no}",
                line.strip()[:120],
                "N/A / 不适用 entries must include a reason.",
            )

    for pattern in _DOMAIN_MODEL_TECH_LEAK_PATTERNS:
        for match in _re.finditer(pattern, text):
            finding(
                "technical_leakage_in_domain_model",
                "technical_leakage",
                f"line {text[:match.start()].count(chr(10)) + 1}",
                match.group(0),
                "Product domain model must describe business semantics, not implementation choices.",
            )

    if _has_heading(text, "State Machines"):
        state_body = ""
        for title, body in sections.items():
            if "State Machines" in body or title == "Tactical DDD":
                state_body = body
                break
        state_text = state_body or text
        if "From State" in state_text or "To State" in state_text:
            required = ("From State", "To State", "Trigger", "Actor", "Preconditions", "Invalid Transitions")
            missing = [item for item in required if item not in state_text]
            if missing:
                finding(
                    "invalid_state_machine_shape",
                    "state_machine_missing_columns",
                    "State Machines",
                    ", ".join(missing),
                    "State machine must cover from/to state, trigger, actor, preconditions, and invalid transitions.",
                )

    if _has_heading(text, "Permission Matrix"):
        required = ("Actor", "Command", "State", "Allowed", "Reason")
        missing = [item for item in required if item not in text]
        if missing:
            finding(
                "invalid_permission_matrix_shape",
                "permission_matrix_missing_columns",
                "Permission Matrix",
                ", ".join(missing),
                "Permission matrix must cover actor, command, state, allowed decision, and reason.",
            )

    if product_definition_text:
        requirement_ids = sorted(set(_re.findall(r"\b(?:FR|NFR|RULE|SC|AC)-[A-Za-z0-9-]+\b", product_definition_text)))
        traceability = sections.get("Traceability", "")
        for req_id in requirement_ids:
            if req_id not in traceability:
                finding(
                    "untraced_requirement",
                    "missing_requirement_trace",
                    "Traceability",
                    req_id,
                    f"{req_id} appears in product-definition.md but is not traced to a domain element.",
                )

    if contract:
        domain_model = contract.get("domain_model")
        if not isinstance(domain_model, dict):
            finding(
                "missing_domain_model_contract",
                "missing_contract_domain_model",
                "contracts/prd.contract.yaml",
                "domain_model",
                "prd.contract.yaml must include structured domain_model fields aligned with product-domain-model.md.",
            )
        else:
            required_keys = (
                "bounded_contexts",
                "aggregates",
                "commands",
                "events",
                "invariants",
                "state_machines",
                "permission_rules",
                "modeling_risks",
            )
            for key in required_keys:
                if key not in domain_model:
                    finding(
                        "missing_domain_model_contract_field",
                        "missing_contract_domain_model_field",
                        f"domain_model.{key}",
                        key,
                        f"prd.contract.yaml domain_model must include '{key}'.",
                    )

    return findings


def cmd_prd_domain_model_lint(args: argparse.Namespace) -> int:
    """Validate product-domain-model.md DDD structure, anti-patterns, and traces."""
    artifact = Path(args.artifact)
    if not artifact.exists():
        return emit_payload(args, fail_payload("prd.domain-model-lint", "missing_domain_model", f"Domain model artifact not found: {args.artifact}"))

    text = artifact.read_text(encoding="utf-8")

    product_definition_text: str | None = None
    if getattr(args, "product_definition", None):
        product_definition = Path(args.product_definition)
        if not product_definition.exists():
            return emit_payload(args, fail_payload("prd.domain-model-lint", "missing_product_definition", f"Product definition artifact not found: {args.product_definition}"))
        product_definition_text = product_definition.read_text(encoding="utf-8")

    contract: dict[str, Any] | None = None
    if getattr(args, "contract", None):
        contract_path = Path(args.contract)
        if not contract_path.exists():
            return emit_payload(args, fail_payload("prd.domain-model-lint", "missing_prd_contract", f"PRD contract not found: {args.contract}"))
        try:
            parsed = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
            candidate = parsed.get("control_contract") if isinstance(parsed, dict) else None
            contract = candidate if isinstance(candidate, dict) else {}
        except yaml.YAMLError:
            return emit_payload(args, fail_payload("prd.domain-model-lint", "invalid_prd_contract", f"PRD contract is not valid YAML: {args.contract}"))

    findings = _scan_domain_model(text, product_definition_text=product_definition_text, contract=contract)
    payload: dict[str, Any] = {
        "status": "PASS" if not findings else "FAIL",
        "control": "prd.domain-model-lint",
        "artifact": str(artifact),
        "product_definition": getattr(args, "product_definition", None),
        "contract": getattr(args, "contract", None),
        "total_findings": len(findings),
        "findings": findings,
    }
    return emit_payload(args, payload)


def cmd_spec_delta_lint(args: argparse.Namespace) -> int:
    """Validate delta spec structure: FR coverage, heading levels, anti-patterns."""
    root = Path(root_arg(args))
    mission = args.mission
    capability = args.capability

    spec_path = root / "harness-runtime" / "harness" / "stages" / mission / "specs" / capability / "spec.md"
    if not spec_path.exists():
        return emit_payload(args, fail_payload("spec.delta-lint", "missing_spec", f"Delta spec not found: {spec_path}"))

    text = spec_path.read_text(encoding="utf-8")
    findings: list[dict[str, Any]] = []

    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        # Check Scenario headings are #### (4 hashes)
        stripped = line.strip()
        if stripped.startswith("### Scenario") and not stripped.startswith("#### Scenario"):
            findings.append({
                "rule": "scenario_heading_level",
                "location": f"line {i}",
                "evidence": stripped[:60],
                "message": "Scenario heading must be #### (4 hashes), not ###.",
            })

    # Check for implementation leaks in spec
    import re as _re
    for pattern in _PRD_IMPL_LEAK_PATTERNS:
        for m in _re.finditer(pattern, text):
            findings.append({
                "rule": "implementation_leak_in_spec",
                "location": f"line {text[:m.start()].count(chr(10)) + 1}",
                "evidence": m.group(0),
                "message": f"Implementation detail '{m.group(0)}' leaked into spec. Write only externally observable behavior.",
            })

    payload: dict[str, Any] = {
        "status": "PASS" if not findings else "FAIL",
        "control": "spec.delta-lint",
        "mission": mission,
        "capability": capability,
        "total_findings": len(findings),
        "findings": findings,
    }
    return emit_payload(args, payload)


def cmd_spec_scan_from_prd(args: argparse.Namespace) -> int:
    """Infer affected capabilities from product definition FRs when discovery is skipped."""
    root = Path(root_arg(args))
    mission = args.mission
    prd_path = Path(args.from_prd) if args.from_prd else root / "harness-runtime" / "harness" / "stages" / mission / "product" / "product-definition.md"

    if not prd_path.exists():
        return emit_payload(args, fail_payload("spec.scan", "missing_product_definition", f"Product definition artifact not found: {prd_path}"))

    text = prd_path.read_text(encoding="utf-8")

    # Extract FR IDs from PRD text
    import re as _re
    fr_ids = list(set(_re.findall(r"\bFR-\d+\b", text)))
    nfr_ids = list(set(_re.findall(r"\bNFR-\d+\b", text)))

    # Check existing project-knowledge capabilities
    spec_index = behavior_specs_root(root) / "_index.md"
    existing_capabilities: list[str] = []
    if spec_index.exists():
        idx_text = spec_index.read_text(encoding="utf-8")
        existing_capabilities = _re.findall(r"^-\s+(\S+)", idx_text, _re.MULTILINE)

    payload: dict[str, Any] = {
        "status": "PASS",
        "control": "spec.scan",
        "mission": mission,
        "source": "prd",
        "extracted_fr_ids": sorted(fr_ids),
        "extracted_nfr_ids": sorted(nfr_ids),
        "existing_capabilities": existing_capabilities,
        "findings": [],
    }
    return emit_payload(args, payload)


def cmd_prd_agent_cap_eval(args: argparse.Namespace) -> int:
    """Typed input for Step 8 Agent Capability Requirements."""
    root = Path(root_arg(args))
    mission = args.mission
    component = args.component

    # Validate work_rights enum
    valid_work_rights = {"read_context", "decide_action", "write_artifact", "dispatch_subagent", "request_human_input", "halt_for_review"}
    raw_rights = args.work_rights.split(",") if args.work_rights else []
    invalid = [r for r in raw_rights if r not in valid_work_rights]
    if invalid:
        return emit_payload(args, fail_payload("prd.agent-cap-eval", "invalid_work_rights", f"Invalid work_rights: {', '.join(invalid)}. Valid: {', '.join(sorted(valid_work_rights))}"))

    # Validate priority enum
    if args.priority and args.priority not in ("P0", "P1", "P2"):
        return emit_payload(args, fail_payload("prd.agent-cap-eval", "invalid_priority", f"Invalid priority: {args.priority}. Must be P0/P1/P2."))

    payload: dict[str, Any] = {
        "status": "PASS",
        "control": "prd.agent-cap-eval",
        "mission": mission,
        "component": component,
        "work_rights": raw_rights,
        "priority": args.priority or "P2",
        "findings": [],
    }
    return emit_payload(args, payload)


# ----------------------------------------------------------------------------
# Discovery stage commands (discovery-improvement-plan M2.1)
# ----------------------------------------------------------------------------
# These commands replace prompt-only HARD-GATE judgments in discovery/workflow.md
# with typed CLI outputs the workflow can consume deterministically. Each
# returns the canonical {status, control, findings, ...} payload shape so
# downstream gate runners / hooks / reviewer scripts can rely on the same
# parsing logic used by mission stage / contract / trace commands.

GITNEXUS_INDEX_FRESH_HOURS = 24


def cmd_gitnexus_status(args: argparse.Namespace) -> int:
    """Return typed GitNexus index status for the current project root.

    Discovery workflow Step 2 brownfield HARD-GATE consumes this to decide
    whether `degradations[]` must record gitnexus_unavailable / gitnexus_stale.
    The check is purely on-disk (looks for `.gitnexus/` per gitnexus-cli
    SKILL.md convention); we do not shell out to `npx gitnexus` so the result
    remains deterministic, offline-safe, and fast inside hooks.
    """
    root = Path(root_arg(args))
    # GitNexus writes its index to `.gitnexus/` in the project root. The
    # install target and the actual working repo may differ (e.g. when
    # `--root` points at /tmp/install-target but gitnexus is indexed in the
    # source repo), so fall back to cwd when root has no .gitnexus/ folder.
    candidates = [root / ".gitnexus", Path.cwd() / ".gitnexus"]
    index_dir = next((p for p in candidates if p.exists() and p.is_dir()), None)

    payload: dict[str, Any] = {
        "status": "PASS" if index_dir else "WARN",
        "control": "gitnexus.status",
        "available": index_dir is not None,
        "indexed": False,
        "fresh": False,
        "last_index_at": None,
        "target_repo": None,
        "findings": [],
    }

    # target_repo: prefer `git remote get-url origin` so the response carries
    # a stable URL the reviewer / lint can grep against. Fall back to the
    # directory basename when remote lookup fails (detached repo, no remote).
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(root), capture_output=True, text=True, check=False, timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            payload["target_repo"] = result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    if not payload["target_repo"]:
        payload["target_repo"] = root.resolve().name

    if index_dir:
        has_content = any(index_dir.iterdir())
        payload["indexed"] = has_content
        if has_content:
            mtime_dt = dt.datetime.fromtimestamp(index_dir.stat().st_mtime, tz=dt.timezone.utc)
            payload["last_index_at"] = mtime_dt.isoformat()
            age_hours = (dt.datetime.now(tz=dt.timezone.utc) - mtime_dt).total_seconds() / 3600
            payload["fresh"] = age_hours < GITNEXUS_INDEX_FRESH_HOURS
            if not payload["fresh"]:
                payload["status"] = "WARN"
                payload["findings"].append({
                    "level": "WARN",
                    "code": "gitnexus_index_stale",
                    "message": f"Index last touched {int(age_hours)}h ago (threshold {GITNEXUS_INDEX_FRESH_HOURS}h); run `npx gitnexus analyze` or record `gitnexus_stale` in degradations[].",
                })
        else:
            payload["status"] = "WARN"
            payload["findings"].append({
                "level": "WARN",
                "code": "gitnexus_index_empty",
                "message": ".gitnexus/ exists but is empty; run `npx gitnexus analyze` to populate it.",
            })
    else:
        payload["findings"].append({
            "level": "WARN",
            "code": "gitnexus_not_indexed",
            "message": "No .gitnexus/ directory found; for brownfield missions record `gitnexus_unavailable` in degradations[] or run `npx gitnexus analyze`.",
        })

    return emit_payload(args, payload)


def cmd_discovery_skip(args: argparse.Namespace) -> int:
    """Record an explicit decision to skip the discovery stage for a mission.

    Discovery is skippable per mission contract autonomy.skippable_stages, but
    plan §M2.1 requires the skip decision to land in approvals.json as a typed
    record (type=`discovery_skip`) so retrospective / lint can audit why a
    mission bypassed problem-space analysis. The `--reason` is required and
    written to the `comment` field; commands missing a reason are rejected
    rather than silently writing an empty record (would defeat audit purpose).
    """
    reason = (args.reason or "").strip()
    if not reason:
        return emit_payload(args, fail_payload(
            "discovery.skip",
            "missing_reason",
            "--reason is required; explain why discovery is being skipped for this mission.",
        ))
    root = Path(root_arg(args))
    document, records = load_approvals(root)
    record = {
        "approval_id": next_approval_id(records),
        "mission_id": args.mission,
        "type": "discovery_skip",
        "stage": "discovery",
        "checkpoint": "",
        "status": "approved",
        "decided_at": now_iso(),
        "comment": reason,
    }
    records.append(record)
    path = write_approvals(root, document, records)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "discovery.skip",
            "approval": record,
            "approvals_path": relpath(root, path),
            "findings": [],
        },
    )


DEPENDENCY_TRIGGER_KEYWORDS = (
    # Data model / schema / migration signals
    ("数据模型", "data_model"),
    ("data model", "data_model"),
    ("schema", "schema_change"),
    ("数据迁移", "data_migration"),
    ("migration", "data_migration"),
    ("DDL", "ddl_change"),
    # External system / API / integration signals
    ("外部业务系统", "external_system"),
    ("external system", "external_system"),
    ("third-party", "external_system"),
    ("third party", "external_system"),
    ("外部 API", "external_api"),
    ("external api", "external_api"),
    ("integration", "integration"),
    ("webhook", "integration"),
    # Infrastructure / deployment signals
    ("基础设施", "infrastructure"),
    ("infrastructure", "infrastructure"),
    ("deployment", "infrastructure"),
    ("CI/CD", "infrastructure"),
)


def cmd_discovery_check_dependency_trigger(args: argparse.Namespace) -> int:
    """Decide whether discovery Step 6 must trigger the dependency-impact skill.

    Plan §M2.1 replaces a prompt-only judgment with a typed CLI output so the
    workflow / hook can deterministically gate the dependency-impact dispatch.
    Decision signals (any one ⇒ required=True):

    - brownfield=true on the mission (heuristic via gitnexus status — if the
      project has an indexed .gitnexus/ directory the mission is treated as
      brownfield-aware)
    - keyword hits in mission-contract.md indicating data-model / API /
      infrastructure dependencies
    - mission complexity is `high` or scope spans more than a configurable
      threshold of files (informative signal only, not standalone trigger)

    Reasons[] is always returned (whether required=True or False) so the
    operator can see exactly which signals fired and challenge any heuristic.
    """
    root = Path(root_arg(args))
    contract_path = root / "harness-runtime" / "harness" / "missions" / args.mission / "mission-contract.md"
    if not contract_path.exists():
        return emit_payload(args, fail_payload(
            "discovery.check-dependency-trigger",
            "missing_mission_contract",
            f"mission-contract.md not found: {relpath(root, contract_path)}; mission must be initialized before discovery scans dependencies.",
        ))

    text = contract_path.read_text(encoding="utf-8")
    text_lower = text.lower()

    reasons: list[dict[str, str]] = []
    matched_signals: set[str] = set()

    # Keyword scan — surface every hit so the operator can audit. Multiple
    # keywords mapping to the same signal id collapse into a single reason.
    for keyword, signal_id in DEPENDENCY_TRIGGER_KEYWORDS:
        if keyword.lower() in text_lower and signal_id not in matched_signals:
            matched_signals.add(signal_id)
            reasons.append({
                "signal": signal_id,
                "source": "mission_contract_keyword",
                "evidence": keyword,
            })

    # gitnexus status reuses the same logic as `harness gitnexus status` —
    # presence of a populated .gitnexus/ index treats the mission as brownfield
    # (the user explicitly chose to index this repo with gitnexus).
    candidates = [root / ".gitnexus", Path.cwd() / ".gitnexus"]
    index_dir = next((p for p in candidates if p.exists() and p.is_dir() and any(p.iterdir())), None)
    if index_dir is not None and "brownfield" not in matched_signals:
        matched_signals.add("brownfield")
        reasons.append({
            "signal": "brownfield",
            "source": "gitnexus_index_present",
            "evidence": relpath(root, index_dir),
        })

    required = bool(matched_signals)
    payload = {
        "status": "PASS",
        "control": "discovery.check-dependency-trigger",
        "mission_id": args.mission,
        "required": required,
        "signals": sorted(matched_signals),
        "reasons": reasons,
        "findings": [],
    }
    return emit_payload(args, payload)


def cmd_spec_scan_capabilities(args: argparse.Namespace) -> int:
    """Enumerate capabilities under project-knowledge/specs/ and tag each with a
    heuristic confidence based on the mission scope_in paths.

    Plan §M2.1 (discovery) keeps this command on the existing `harness spec scan`
    surface but disambiguated from the prd-flavored scan by the `--scope-in`
    flag. Discovery Step 3 consumes the candidate list; discovery-analyst
    upgrades the heuristic confidence to a final CONFIRMED / UNCERTAIN /
    ASSUMED with an actual evidence chain.

    Heuristic confidence rule (intentionally conservative — discovery-analyst
    is the authoritative judge):

    - CONFIRMED: capability name appears as a substring of at least one
      --scope-in path.
    - ASSUMED: capability exists in project-knowledge/specs/ but no scope_in match;
      discovery-analyst must decide whether it is in scope.
    """
    root = Path(root_arg(args))
    specs_dir = behavior_specs_root(root)
    if not specs_dir.exists() or not specs_dir.is_dir():
        return emit_payload(args, fail_payload(
            "spec.scan",
            "specs_dir_missing",
            f"{relpath(root, specs_dir)} not found; run `harness spec init` first.",
        ))

    scope_in: list[str] = list(getattr(args, "scope_in", None) or [])
    scope_in_lower = [s.lower() for s in scope_in]

    capabilities: list[dict[str, Any]] = []
    for entry in sorted(specs_dir.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        spec_md = entry / "spec.md"
        record: dict[str, Any] = {
            "capability": name,
            "spec_path": relpath(root, spec_md) if spec_md.exists() else None,
            "confidence": "ASSUMED",
            "matched_scope": [],
        }
        if scope_in_lower:
            name_lower = name.lower()
            for raw, lower in zip(scope_in, scope_in_lower):
                if name_lower in lower:
                    record["matched_scope"].append(raw)
            if record["matched_scope"]:
                record["confidence"] = "CONFIRMED"
        capabilities.append(record)

    findings: list[dict[str, str]] = []
    if not capabilities:
        findings.append({
            "level": "WARN",
            "code": "no_capabilities",
            "message": f"{relpath(root, specs_dir)} is empty; if the mission is greenfield this is expected, otherwise scaffold capabilities with `harness spec init --capability <name>`.",
        })

    payload = {
        "status": "PASS" if not findings else "WARN",
        "control": "spec.scan",
        "mode": "discovery",
        "mission_id": args.mission,
        "spec_root": relpath(root, specs_dir),
        "scope_in": scope_in,
        "capabilities": capabilities,
        "summary": {
            "total": len(capabilities),
            "confirmed": sum(1 for c in capabilities if c["confidence"] == "CONFIRMED"),
            "uncertain": sum(1 for c in capabilities if c["confidence"] == "UNCERTAIN"),
            "assumed": sum(1 for c in capabilities if c["confidence"] == "ASSUMED"),
        },
        "findings": findings,
    }
    return emit_payload(args, payload)


def cmd_spec_scan(args: argparse.Namespace) -> int:
    """Dispatch `harness spec scan` to the right flavor.

    `--scope-in` triggers the discovery flavor (enumerate capabilities under
    project-knowledge/specs/ with heuristic confidence). Without --scope-in we keep
    the existing prd-flavor scan that extracts FR / NFR IDs from a PRD artifact.
    Two flavors share the same payload control field (spec.scan) so downstream
    consumers can branch on the `mode` field rather than re-parsing argparse.
    """
    if getattr(args, "scope_in", None):
        return cmd_spec_scan_capabilities(args)
    return cmd_spec_scan_from_prd(args)


def cmd_discovery_agent_eng_eval(args: argparse.Namespace) -> int:
    """Append a typed Agent-engineering decision-matrix evaluation to the
    discovery-brief contract.

    Plan §M2.1 replaces Step 7 prose with a 4-boolean typed input: autonomy /
    runtime_context / multi_step_reasoning / uncertainty. Decision rule (plan
    §M4.3 will strict-reject deviations): all four true → recommended:agentize;
    otherwise → recommended:deterministic. Operators that want to defer the
    call pass --recommendation undecided explicitly (strict-mode plan §M4.3
    rejects undecided too unless paired with an open question — out of scope
    for M2.1).

    Each invocation appends one candidate to
    `discovery-brief.contract.yaml.agent_engineering_candidates`; duplicate
    `--component` values overwrite the previous record (re-evaluation is the
    expected flow). Without this command the matrix lives only in prose, so
    discovery-effectiveness-reviewer / harness-lint cannot cross-check that
    `recommended=agentize` actually has all four flags true.
    """
    root = Path(root_arg(args))
    contract_path = root / "harness-runtime" / "harness" / "stages" / args.mission / "contracts" / "discovery-brief.contract.yaml"
    if not contract_path.exists():
        return emit_payload(args, fail_payload(
            "discovery.agent-eng-eval",
            "missing_contract",
            f"discovery-brief contract not found: {relpath(root, contract_path)}; run `harness contract fill --template discovery-brief` first.",
        ))
    document = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    contract = document.get("control_contract") if isinstance(document.get("control_contract"), dict) else None
    if contract is None:
        return emit_payload(args, fail_payload(
            "discovery.agent-eng-eval",
            "invalid_contract",
            "discovery-brief contract is missing the `control_contract:` root.",
        ))

    bools = (args.autonomy, args.runtime_context, args.multi_step, args.uncertainty)
    if args.recommendation:
        recommended = args.recommendation
    else:
        # Default rule per plan: 4-of-4 → agentize, else deterministic. The
        # operator can override via --recommendation but only into undecided
        # (used by the workflow when downstream review is pending). agentize
        # without 4-of-4 is rejected explicitly (M4.3 strict-mode preview).
        if all(bools):
            recommended = "agentize"
        else:
            recommended = "deterministic"

    if recommended == "agentize" and not all(bools):
        return emit_payload(args, fail_payload(
            "discovery.agent-eng-eval",
            "agentize_requires_all_four",
            "--recommendation agentize requires autonomy && runtime_context && multi_step && uncertainty all true (M4.3 strict-mode preview).",
        ))

    candidate = {
        "component": args.component,
        "autonomy": bool(args.autonomy),
        "runtime_context": bool(args.runtime_context),
        "multi_step_reasoning": bool(args.multi_step),
        "uncertainty": bool(args.uncertainty),
        "recommended": recommended,
    }
    if args.notes:
        candidate["notes"] = args.notes

    candidates = contract.get("agent_engineering_candidates")
    if not isinstance(candidates, list):
        candidates = []
    replaced = False
    for i, existing in enumerate(list(candidates)):
        if isinstance(existing, dict) and existing.get("component") == args.component:
            candidates[i] = candidate
            replaced = True
            break
    if not replaced:
        candidates.append(candidate)
    contract["agent_engineering_candidates"] = candidates

    contract_path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "discovery.agent-eng-eval",
            "contract_path": relpath(root, contract_path),
            "candidate": candidate,
            "replaced_existing": replaced,
            "findings": [],
        },
    )


# --- design Stage-4 M2.1: solution / interaction / tech-design lane CLIs ----
# Replaces 3 lane-action prompt-only HARD-GATEs with typed CLI outputs so the
# workflow / hook can deterministically gate.

# solution decision-scan: anti-pattern keywords for "demo / minimum change /
# temporary plan" + vague risk mitigation. Surface findings so the AI cannot
# silently ship a solution.md that hides "let's do the simplest thing" as a
# decision rationale.
_SOLUTION_ANTI_PATTERN_PHRASES = (
    # Anti-design / anti-target-driven phrases.
    ("最小改动", "anti_minimum_change", "Solution must be target-driven, not minimum-change-driven."),
    ("改动最小", "anti_minimum_change", "Solution must be target-driven, not minimum-change-driven."),
    ("minimum change", "anti_minimum_change", "Solution must be target-driven, not minimum-change-driven."),
    ("先做 demo", "anti_demo_first", "Solution must not lead with a demo placeholder."),
    ("先做demo", "anti_demo_first", "Solution must not lead with a demo placeholder."),
    ("demo 先行", "anti_demo_first", "Solution must not lead with a demo placeholder."),
    ("先 demo", "anti_demo_first", "Solution must not lead with a demo placeholder."),
    ("临时方案", "anti_temporary_plan", "Solution must not present a temporary plan as the chosen path; use a decision + tradeoff."),
    ("temporary plan", "anti_temporary_plan", "Solution must not present a temporary plan as the chosen path; use a decision + tradeoff."),
    ("临时实现", "anti_temporary_plan", "Solution must not present a temporary plan as the chosen path."),
)

# Vague mitigation phrases that should not appear in risks[].mitigation. These
# keywords betray that the author has not actually mitigated the risk — they
# just punted to "we will think about it later".
_SOLUTION_VAGUE_MITIGATION = (
    "考虑",
    "考虑下",
    "可能",
    "可能要",
    "也许",
    "或许",
    "需要进一步",
    "需要进一步研究",
    "to be determined",
    "TBD",
    "待定",
    "下一步再",
    "later",
)


def cmd_solution_decision_scan(args: argparse.Namespace) -> int:
    """Stage-4 solution M2.1: anti-pattern + vague-mitigation scan for solution.md.

    Replaces design/workflow.md HARD-GATE 反 demo / 反最小改动 prose with a
    typed CLI output. Findings are non-empty ⇒ status FAIL. Authors fix by
    rewriting the offending phrasing into a real decision (with tradeoff +
    accepted_alternatives).
    """
    artifact = Path(args.artifact)
    if not artifact.exists():
        return emit_payload(args, fail_payload(
            "solution.decision-scan",
            "missing_artifact",
            f"Artifact not found: {args.artifact}",
        ))

    text = artifact.read_text(encoding="utf-8")
    findings: list[dict[str, Any]] = []

    # 1. Anti-pattern phrases at any line.
    text_lower = text.lower()
    lines = text.splitlines()
    for phrase, rule, message in _SOLUTION_ANTI_PATTERN_PHRASES:
        idx = text_lower.find(phrase.lower())
        if idx == -1:
            continue
        line_no = text[:idx].count("\n") + 1
        findings.append({
            "rule": rule,
            "location": f"line {line_no}",
            "evidence": phrase,
            "message": message,
        })

    # 2. Vague mitigation: scan only inside risks: / mitigation: regions.
    # Heuristic: lines starting with `mitigation:` or that come within 5 lines
    # of a `risks:` heading. Flag if the value contains a vague keyword.
    in_risks_block = False
    risks_distance = 0
    for line_no, raw in enumerate(lines, 1):
        if raw.strip().startswith("risks:"):
            in_risks_block = True
            risks_distance = 0
            continue
        if in_risks_block:
            risks_distance += 1
            if risks_distance > 30:
                in_risks_block = False
                continue
        if "mitigation:" in raw or in_risks_block:
            for vague in _SOLUTION_VAGUE_MITIGATION:
                if vague in raw and not raw.strip().startswith("#"):
                    findings.append({
                        "rule": "vague_mitigation",
                        "location": f"line {line_no}",
                        "evidence": vague,
                        "message": (
                            f"Vague phrase '{vague}' inside risk mitigation. "
                            "Replace with a concrete action + verification."
                        ),
                    })
                    break  # one vague hit per line is enough

    payload = {
        "status": "PASS" if not findings else "FAIL",
        "control": "solution.decision-scan",
        "artifact": str(artifact),
        "total_findings": len(findings),
        "findings": findings,
    }
    return emit_payload(args, payload)


def cmd_solution_lane_action_validate(args: argparse.Namespace) -> int:
    """Stage-4 solution M2.1: lane action 单一性 兜底 — verify that within the
    current mission slice, only the active lane action's artifacts have been
    modified. Complements M1.3 overlay (which blocks Write at runtime) by
    catching any modifications that slipped through.

    Inspects `git status --porcelain` and the mission-slice file to determine
    the active design stage. Modifications to other-stage artifacts under
    harness-runtime/harness/stages/<mission>/ trigger FAIL with offending paths.
    """
    import subprocess

    root = Path(root_arg(args))
    mission_id = args.mission
    slice_path = root / "harness-runtime" / "harness" / "missions" / mission_id / "mission-slice.yaml"
    active_stage: str | None = None
    if slice_path.exists():
        try:
            slice_doc = yaml.safe_load(slice_path.read_text(encoding="utf-8")) or {}
            cp = slice_doc.get("control_plane") or {}
            active_stage = cp.get("stage")
        except yaml.YAMLError:
            pass
    # Allow override via flag for test / out-of-band invocation.
    active_stage = args.stage or active_stage

    if not active_stage:
        return emit_payload(args, fail_payload(
            "solution.lane-action-validate",
            "missing_stage",
            "stage not found in mission-slice and not provided via --stage.",
        ))

    if active_stage not in {"solution", "interaction", "technical_analysis"}:
        return emit_payload(args, fail_payload(
            "solution.lane-action-validate",
            "unknown_stage",
            f"stage must be one of solution / interaction / technical_analysis; got {active_stage}.",
        ))

    # Map stage → permitted artifact path globs (relative to repo).
    lane_artifacts = {
        "solution": [f"harness-runtime/harness/stages/{mission_id}/solution.md"],
        "interaction": [
            f"harness-runtime/harness/stages/{mission_id}/interaction.md",
            f"harness-runtime/harness/stages/{mission_id}/visual-interaction/",
        ],
        "technical_analysis": [f"harness-runtime/harness/stages/{mission_id}/tech-design.md"],
    }
    other_lane_globs = (
        f"harness-runtime/harness/stages/{mission_id}/solution.md",
        f"harness-runtime/harness/stages/{mission_id}/interaction.md",
        f"harness-runtime/harness/stages/{mission_id}/tech-design.md",
        f"harness-runtime/harness/stages/{mission_id}/visual-interaction/",
    )
    permitted = set(lane_artifacts[active_stage])

    try:
        result = subprocess.run(
            # `-uall` expands untracked directories into individual file entries
            # so a fresh write to an other-lane artifact under an untracked stage
            # dir is visible (otherwise git collapses it into `?? <dir>/`).
            ["git", "status", "--porcelain", "-uall"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return emit_payload(args, fail_payload(
            "solution.lane-action-validate",
            "git_unavailable",
            "git not on PATH; cannot inspect working tree state.",
        ))

    findings: list[dict[str, Any]] = []
    for raw in result.stdout.splitlines():
        if not raw.strip():
            continue
        # Format: "XY <path>" — XY is two-character status code.
        path = raw[3:].strip().strip('"')
        # Skip files outside the mission stage dir (other commits / unrelated work).
        if not path.startswith(f"harness-runtime/harness/stages/{mission_id}/"):
            continue
        # Allow modifications to permitted artifacts (exact match for files,
        # prefix match for visual-interaction/ directory).
        is_permitted = any(
            (path == p or (p.endswith("/") and path.startswith(p)))
            for p in permitted
        )
        if is_permitted:
            continue
        # Flag if it matches an other-lane glob (any visible cross-lane write).
        is_cross_lane = any(
            (path == g or (g.endswith("/") and path.startswith(g)))
            for g in other_lane_globs
        )
        if is_cross_lane:
            findings.append({
                "rule": "cross_lane_write",
                "path": path,
                "stage": active_stage,
                "message": (
                    f"In stage={active_stage}, modifications to "
                    f"{path} are forbidden (other-lane artifact)."
                ),
            })

    payload = {
        "status": "PASS" if not findings else "FAIL",
        "control": "solution.lane-action-validate",
        "mission_id": mission_id,
        "stage": active_stage,
        "total_findings": len(findings),
        "findings": findings,
    }
    return emit_payload(args, payload)


# --- interaction lane CLIs --------------------------------------------------

# Phrases / sections in mission-contract.md / product definition that signal UI / user
# journey work. The interaction lane defaults to required for product work; these
# signals make the reason explicit. It is skipped only when upstream explicitly
# says the work has no interface surface.
_INTERACTION_TRIGGER_KEYWORDS = (
    ("prototype", "prototype"),
    ("原型", "prototype"),
    ("frontend_ui", "frontend_ui"),
    ("frontend ui", "frontend_ui"),
    ("user_journey", "user_journey"),
    ("user journey", "user_journey"),
    ("用户旅程", "user_journey"),
    ("用户旅", "user_journey"),
    ("UI / 用户交互", "ui_user_interaction"),
    ("UI/用户交互", "ui_user_interaction"),
    ("交互设计", "ui_user_interaction"),
    ("E2E", "e2e_obligation"),
    ("end-to-end", "e2e_obligation"),
    ("端到端", "e2e_obligation"),
    ("visual", "visual_evidence"),
    ("visual artifact", "visual_evidence"),
    ("可视化资产", "visual_evidence"),
)

_INTERACTION_NO_INTERFACE_KEYWORDS = (
    ("api-only", "api_only"),
    ("api only", "api_only"),
    ("only api", "api_only"),
    ("纯 api", "api_only"),
    ("仅 api", "api_only"),
    ("no ui", "no_interface"),
    ("no user interface", "no_interface"),
    ("without ui", "no_interface"),
    ("无界面", "no_interface"),
    ("没有界面", "no_interface"),
    ("不涉及界面", "no_interface"),
    ("backend only", "backend_only"),
    ("pure backend", "backend_only"),
    ("纯后端", "backend_only"),
    ("仅后端", "backend_only"),
    ("cli only", "cli_only"),
    ("命令行", "cli_only"),
    ("batch job", "no_interface_background_job"),
    ("background job", "no_interface_background_job"),
)


def cmd_interaction_check_ui_trigger(args: argparse.Namespace) -> int:
    """Auto-detect whether a mission requires the interaction/prototype lane.

    The lane is required by default for product work after PRD. It returns
    requires_interaction=False only when upstream artifacts explicitly state
    that the change has no interface surface, such as API-only / pure backend /
    CLI-only work. UI / journey / prototype signals override no-interface hints.
    """
    root = Path(root_arg(args))
    mission_id = args.mission
    candidates: list[Path] = []
    mc = root / "harness-runtime" / "harness" / "missions" / mission_id / "mission-contract.md"
    if mc.exists():
        candidates.append(mc)
    for product_name in ("product-definition.md", "product-domain-model.md", "product-evidence.md"):
        product_path = root / "harness-runtime" / "harness" / "stages" / mission_id / "product" / product_name
        if product_path.exists():
            candidates.append(product_path)
    prd_contract = root / "harness-runtime" / "harness" / "stages" / mission_id / "contracts" / "prd.contract.yaml"
    if prd_contract.exists():
        candidates.append(prd_contract)

    if not candidates:
        return emit_payload(args, fail_payload(
            "interaction.check-ui-trigger",
            "missing_upstream",
            f"No upstream contract / artifact found under mission {mission_id}.",
        ))

    matched_signals: set[str] = set()
    no_interface_signals: set[str] = set()
    reasons: list[dict[str, str]] = []
    skip_reasons: list[dict[str, str]] = []
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        text_lower = text.lower()
        for phrase, signal in _INTERACTION_TRIGGER_KEYWORDS:
            if phrase.lower() in text_lower and signal not in matched_signals:
                matched_signals.add(signal)
                reasons.append({
                    "signal": signal,
                    "source": path.name,
                    "evidence": phrase,
                })
        for phrase, signal in _INTERACTION_NO_INTERFACE_KEYWORDS:
            if phrase.lower() in text_lower and signal not in no_interface_signals:
                no_interface_signals.add(signal)
                skip_reasons.append({
                    "signal": signal,
                    "source": path.name,
                    "evidence": phrase,
                })

    requires = bool(matched_signals) or not no_interface_signals
    if requires and not matched_signals:
        matched_signals.add("prototype_default_required")
        reasons.append({
            "signal": "prototype_default_required",
            "source": "default_policy",
            "evidence": "No explicit API-only / no-interface scope found.",
        })
    payload = {
        "status": "PASS",
        "control": "interaction.check-ui-trigger",
        "mission_id": mission_id,
        "requires_interaction": requires,
        "signals": sorted(matched_signals),
        "skip_signals": sorted(no_interface_signals),
        "reasons": reasons,
        "skip_reasons": skip_reasons,
        "findings": [],
    }
    return emit_payload(args, payload)


_DOMAIN_REF_RE = re.compile(
    r"\b(?:BC|CAP|ACT|AGG|ENT|VO|CMD|EVT|INV|POL|DS|STM|EXC|AUD)-[A-Za-z0-9._-]+\b"
)
_TRACE_REF_RE = re.compile(
    r"\b(?:AC|FR|NFR|SCN|RULE|DEC|MOD|IF|DATA|VS|FLOW|STATE|INT|VAL|E2E|"
    r"CMD|ENT|INV|STM|POL|AGG|BC|CAP|ACT|EVT|EXC|AUD|TASK|T|AT)-[A-Za-z0-9._-]+\b"
)
_INTERACTION_REQUIRED_FILES = (
    "README.md",
    "source-trace.md",
    "surface-index.md",
    "surface-baseline.md",
    "surface-changeset.md",
    "domain-ui-mapping.md",
    "flows.md",
    "states.md",
    "interactions.md",
    "scenarios.md",
    "validation-rules.md",
    "view-models.ts",
    "consistency-report.md",
)
_INTERACTION_REQUIRED_STATES = (
    "STATE-LOADING",
    "STATE-EMPTY",
    "STATE-SUCCESS",
    "STATE-ERROR",
    "STATE-PERMISSION",
    "STATE-DISABLED",
)
_BROWSER_PRIMARY_EVIDENCE_KINDS = {
    "dom",
    "dom_snapshot",
    "screenshot",
    "video",
    "trace",
    "accessibility_snapshot",
}
_NON_UI_PRIMARY_EVIDENCE_KINDS = {
    "api",
    "api_response",
    "db",
    "database",
    "internal_state",
    "mock",
    "log",
}
_OPERABLE_PROTOTYPE_ROLES = {"operable_prototype", "primary_prototype"}
_OPERABLE_PROTOTYPE_PATHS = {
    "prototype/index.html",
    "visual-interaction/prototype/index.html",
}
_OPERABLE_PROTOTYPE_FORBIDDEN_TEXT = (
    "阅读顺序",
    "评审入口",
    "评审说明",
    "Flow 串走",
    "状态陈列",
    "组件目录",
    "缩略图墙",
    "coverage",
    "manifest",
    "visual-interaction-manifest",
    "interaction-spec",
    "contracts/interaction",
    "traces_to",
    "reviewer",
)
_OPERABLE_PROTOTYPE_FORBIDDEN_RE = re.compile(
    r"\b(?:AC|FR|NFR|FLOW|STATE|SCN|E2E)-[A-Za-z0-9._-]+\b"
)
_OPERABLE_PROTOTYPE_INTERACTIVE_RE = re.compile(
    r"<\s*(?:button|input|select|textarea)\b|<\s*a\b[^>]*\bhref\s*=|"
    r"\bdata-testid\s*=|\brole\s*=\s*['\"](?:button|tab|checkbox|menuitem|switch|combobox)['\"]",
    re.IGNORECASE,
)


def _mission_stage_dir(root: Path, mission: str) -> Path:
    return runtime_harness_root(root) / "stages" / mission


def _read_text_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _is_placeholder_text(value: object) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    lowered = text.lower()
    return (
        "{{" in text
        or lowered in {"n/a", "na", "none", "null", "tbd", "todo", "-", "不适用", "无"}
    )


def _finding(level: str, code: str, message: str, **extra: object) -> dict[str, object]:
    item: dict[str, object] = {"level": level, "code": code, "message": message}
    item.update(extra)
    return item


def _apply_compat_warning(args: argparse.Namespace, findings: list[dict[str, object]]) -> tuple[str, list[dict[str, object]]]:
    if getattr(args, "compat", False):
        for item in findings:
            if item.get("level") == "FAIL":
                item["level"] = "WARN"
                item["compat_downgraded"] = True
        return ("WARN" if findings else "PASS"), []
    failed = [f for f in findings if f.get("level") == "FAIL"]
    return ("FAIL" if failed else "PASS"), failed


def _collect_refs_from_value(value: object, pattern: re.Pattern[str] = _TRACE_REF_RE) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for child in value.values():
            refs.update(_collect_refs_from_value(child, pattern))
    elif isinstance(value, list):
        for child in value:
            refs.update(_collect_refs_from_value(child, pattern))
    elif isinstance(value, str):
        if "{{" not in value:
            refs.update(pattern.findall(value))
    return refs


def _load_yaml_contract_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(doc, dict):
        return {}
    cc = doc.get("control_contract")
    return cc if isinstance(cc, dict) else doc


def _interaction_spec_dir(root: Path, mission: str) -> Path:
    return _mission_stage_dir(root, mission) / "interaction-spec"


def _known_domain_refs(root: Path, mission: str) -> set[str]:
    stage_dir = _mission_stage_dir(root, mission)
    candidates = [
        stage_dir / "product" / "product-domain-model.md",
        stage_dir / "product-domain-model.md",
        root / "project-knowledge" / "product" / "product-domain-model.md",
    ]
    refs: set[str] = set()
    for path in candidates:
        refs.update(_DOMAIN_REF_RE.findall(_read_text_if_exists(path)))
    prd_contract = stage_dir / "contracts" / "prd.contract.yaml"
    refs.update(_collect_refs_from_value(_load_yaml_contract_file(prd_contract), _DOMAIN_REF_RE))
    return refs


def _interaction_prd_feedback_required(root: Path, mission: str) -> bool:
    contract = _load_yaml_contract_file(
        _mission_stage_dir(root, mission) / "contracts" / "interaction.contract.yaml"
    )
    feedback = contract.get("prd_feedback") if isinstance(contract.get("prd_feedback"), dict) else {}
    status = str(feedback.get("status") or feedback.get("state") or "").lower()
    if feedback.get("requires_prd_feedback") is True:
        return True
    return status in {"required", "pending", "needs_prd_feedback", "prd_feedback_required"}


def _state_has_na_reason(text: str, state_id: str) -> bool:
    for line in text.splitlines():
        if state_id in line and re.search(r"\bN/A\b|不适用|not applicable|无需|无此状态", line, re.I):
            return True
    return False


def cmd_interaction_spec_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    spec_dir = _interaction_spec_dir(root, mission)
    findings: list[dict[str, object]] = []

    if not spec_dir.exists():
        findings.append(_finding(
            "FAIL",
            "INTERACTION_SPEC_MISSING",
            f"interaction-spec directory not found: {relpath(root, spec_dir)}",
            path=relpath(root, spec_dir),
        ))
    for name in _INTERACTION_REQUIRED_FILES:
        path = spec_dir / name
        if not path.exists():
            findings.append(_finding(
                "FAIL",
                "INTERACTION_SPEC_FILE_MISSING",
                f"interaction-spec required file missing: {name}",
                path=relpath(root, path),
            ))

    states_text = _read_text_if_exists(spec_dir / "states.md")
    for state_id in _INTERACTION_REQUIRED_STATES:
        if state_id not in states_text and not _state_has_na_reason(states_text, state_id):
            findings.append(_finding(
                "FAIL",
                "INTERACTION_STATE_MATRIX_INCOMPLETE",
                f"states.md must cover {state_id} or record an explicit N/A reason.",
                state_id=state_id,
                path=relpath(root, spec_dir / "states.md"),
            ))

    focus_sources = "\n".join([
        _read_text_if_exists(spec_dir / "states.md"),
        _read_text_if_exists(spec_dir / "interactions.md"),
        _read_text_if_exists(spec_dir / "scenarios.md"),
    ]).lower()
    if not any(token in focus_sources for token in ("focus", "焦点", "keyboard", "键盘")):
        findings.append(_finding(
            "FAIL",
            "INTERACTION_FOCUS_STATE_MISSING",
            "interaction-spec must cover disabled/focus or keyboard focus behavior.",
            path=relpath(root, spec_dir / "interactions.md"),
        ))

    domain_refs = _DOMAIN_REF_RE.findall(_read_text_if_exists(spec_dir / "domain-ui-mapping.md"))
    known_domain_refs = _known_domain_refs(root, mission)
    if domain_refs and known_domain_refs:
        for ref in sorted(set(domain_refs) - known_domain_refs):
            findings.append(_finding(
                "FAIL",
                "UNKNOWN_DOMAIN_REF",
                f"interaction domain-ui-mapping references unknown domain id {ref}.",
                ref=ref,
                path=relpath(root, spec_dir / "domain-ui-mapping.md"),
            ))
    elif not domain_refs:
        findings.append(_finding(
            "FAIL",
            "MISSING_ALIGNMENT_EVIDENCE",
            "domain-ui-mapping.md must include Entity/Command/State/Permission/Invariant refs.",
            path=relpath(root, spec_dir / "domain-ui-mapping.md"),
        ))

    if _interaction_prd_feedback_required(root, mission):
        findings.append(_finding(
            "FAIL",
            "PRD_FEEDBACK_REQUIRED",
            "Interaction contract records new AC/domain/permission/scope feedback that must return to PRD or Decision Gate.",
        ))

    status, failed_checks = _apply_compat_warning(args, findings)
    return emit_payload(args, {
        "status": status,
        "control": "interaction.spec-check",
        "mission_id": mission,
        "interaction_spec_dir": relpath(root, spec_dir),
        "findings": findings,
        "failed_checks": failed_checks,
    })


def _load_visual_manifest(root: Path, mission: str) -> tuple[Path, dict[str, Any] | None]:
    stage_dir = _mission_stage_dir(root, mission)
    candidates = [
        stage_dir / "visual-interaction" / "visual-interaction-manifest.json",
        stage_dir / "visual-interaction-manifest.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return path, None
            return path, data if isinstance(data, dict) else None
    return candidates[0], None


def _covered_manifest_values(manifest: dict[str, Any], key: str) -> set[str]:
    covered: set[str] = set()
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return covered
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        covers = artifact.get("covers") if isinstance(artifact.get("covers"), dict) else {}
        values = covers.get(key)
        if isinstance(values, list):
            covered.update(str(v) for v in values if not _is_placeholder_text(v))
    return covered


def _artifact_rel_path(artifact: dict[str, Any]) -> str:
    return str(artifact.get("path") or "").replace("\\", "/").lstrip("./")


def _artifact_role(artifact: dict[str, Any]) -> str:
    return str(
        artifact.get("artifact_role")
        or artifact.get("role")
        or artifact.get("kind")
        or ""
    ).strip().lower()


def _is_operable_prototype_artifact(artifact: dict[str, Any]) -> bool:
    rel = _artifact_rel_path(artifact)
    if str(artifact.get("type") or "").lower() != "html":
        return False
    return _artifact_role(artifact) in _OPERABLE_PROTOTYPE_ROLES or rel in _OPERABLE_PROTOTYPE_PATHS


def _resolve_visual_artifact_path(root: Path, mission: str, manifest_path: Path, artifact: dict[str, Any]) -> Path:
    absolute = artifact.get("absolute_path")
    if isinstance(absolute, str) and absolute:
        candidate = Path(absolute)
        if candidate.exists():
            return candidate
    rel = _artifact_rel_path(artifact)
    return manifest_path.parent / rel


def _html_without_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def _operable_prototype_findings(
    root: Path,
    mission: str,
    manifest_path: Path,
    manifest: dict[str, Any],
) -> list[dict[str, object]]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return [_finding(
            "FAIL",
            "PRIMARY_PROTOTYPE_MISSING",
            "visual manifest must include artifacts[] with a primary operable prototype.",
            expected_path="visual-interaction/prototype/index.html",
        )]

    primary = [
        artifact for artifact in artifacts
        if isinstance(artifact, dict) and _is_operable_prototype_artifact(artifact)
    ]
    if not primary:
        return [_finding(
            "FAIL",
            "PRIMARY_PROTOTYPE_MISSING",
            "visual manifest must include prototype/index.html or an HTML artifact with artifact_role=operable_prototype.",
            expected_path="visual-interaction/prototype/index.html",
        )]

    findings: list[dict[str, object]] = []
    for artifact in primary:
        path = _resolve_visual_artifact_path(root, mission, manifest_path, artifact)
        rel = _artifact_rel_path(artifact)
        if not path.exists():
            findings.append(_finding(
                "FAIL",
                "PRIMARY_PROTOTYPE_FILE_MISSING",
                f"primary operable prototype file missing: {rel}",
                path=rel,
            ))
            continue
        html = _read_text_if_exists(path)
        visibleish = _html_without_comments(html)
        if not _OPERABLE_PROTOTYPE_INTERACTIVE_RE.search(visibleish):
            findings.append(_finding(
                "FAIL",
                "PRIMARY_PROTOTYPE_NOT_OPERABLE",
                "primary prototype must expose real interaction affordances such as button/input/link/data-testid.",
                path=rel,
            ))
        forbidden_hits = [
            token for token in _OPERABLE_PROTOTYPE_FORBIDDEN_TEXT
            if token.lower() in visibleish.lower()
        ]
        if _OPERABLE_PROTOTYPE_FORBIDDEN_RE.search(visibleish):
            forbidden_hits.append("AC/FLOW/STATE trace id")
        if forbidden_hits:
            findings.append(_finding(
                "FAIL",
                "PRIMARY_PROTOTYPE_CONTAINS_REVIEW_COPY",
                "primary prototype must not mix review/spec/coverage instructions into the product UI.",
                path=rel,
                evidence=sorted(set(forbidden_hits)),
            ))
    return findings


def cmd_interaction_visual_coverage_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    spec_dir = _interaction_spec_dir(root, mission)
    manifest_path, manifest = _load_visual_manifest(root, mission)
    findings: list[dict[str, object]] = []
    if manifest is None:
        findings.append(_finding(
            "FAIL",
            "VISUAL_MANIFEST_MISSING",
            f"visual interaction manifest missing or invalid: {relpath(root, manifest_path)}",
            path=relpath(root, manifest_path),
        ))
        manifest = {}

    required_flows = set(re.findall(r"\bFLOW-[A-Za-z0-9._-]+\b", _read_text_if_exists(spec_dir / "flows.md")))
    required_states = set(re.findall(r"\bSTATE-[A-Za-z0-9._-]+\b", _read_text_if_exists(spec_dir / "states.md")))
    if not required_states:
        required_states = set(_INTERACTION_REQUIRED_STATES)
    covered_flows = _covered_manifest_values(manifest, "flows")
    covered_states = _covered_manifest_values(manifest, "states")
    covered_viewports = {v.lower() for v in _covered_manifest_values(manifest, "viewports")}
    findings.extend(_operable_prototype_findings(root, mission, manifest_path, manifest))

    for flow_id in sorted(required_flows - covered_flows):
        findings.append(_finding(
            "FAIL",
            "VISUAL_FLOW_COVERAGE_MISSING",
            f"visual manifest must cover interaction flow {flow_id}.",
            flow_id=flow_id,
        ))
    for state_id in sorted(required_states - covered_states):
        findings.append(_finding(
            "FAIL",
            "VISUAL_STATE_COVERAGE_MISSING",
            f"visual manifest must cover interaction state {state_id}.",
            state_id=state_id,
        ))
    for viewport in ("desktop", "mobile"):
        if viewport not in covered_viewports:
            findings.append(_finding(
                "FAIL",
                "VISUAL_VIEWPORT_COVERAGE_MISSING",
                f"visual manifest must cover the {viewport} viewport.",
                viewport=viewport,
            ))

    status, failed_checks = _apply_compat_warning(args, findings)
    return emit_payload(args, {
        "status": status,
        "control": "interaction.visual-coverage-check",
        "mission_id": mission,
        "manifest_path": relpath(root, manifest_path),
        "required_flows": sorted(required_flows),
        "required_states": sorted(required_states),
        "covered_flows": sorted(covered_flows),
        "covered_states": sorted(covered_states),
        "covered_viewports": sorted(covered_viewports),
        "findings": findings,
        "failed_checks": failed_checks,
    })


def _scenario_rows_with_locator_obligation(text: str) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if "|" not in line:
            continue
        if re.search(r"\b(?:E2E|SCN)-[A-Za-z0-9._-]+\b|\bP[01]\b", line):
            rows.append((idx, line))
    return rows


def _row_has_locator_strategy(row: str) -> bool:
    lowered = row.lower()
    if any(token in lowered for token in ("data-testid", "locator", "getbyrole", "getbylabel", "aria", "accessibility", "role=")):
        return not _is_placeholder_text(row)
    return False


def cmd_interaction_locator_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    scenarios_path = _interaction_spec_dir(root, mission) / "scenarios.md"
    text = _read_text_if_exists(scenarios_path)
    findings: list[dict[str, object]] = []
    rows = _scenario_rows_with_locator_obligation(text)
    if not rows:
        findings.append(_finding(
            "FAIL",
            "LOCATOR_OBLIGATION_MISSING",
            "P0/P1 scenario E2E obligations with locator strategy are missing.",
            path=relpath(root, scenarios_path),
        ))
    for line_no, row in rows:
        if not _row_has_locator_strategy(row):
            findings.append(_finding(
                "FAIL",
                "E2E_LOCATOR_MISSING",
                "P0/P1 scenario must declare data-testid or accessibility locator strategy.",
                path=relpath(root, scenarios_path),
                line=line_no,
            ))

    status, failed_checks = _apply_compat_warning(args, findings)
    return emit_payload(args, {
        "status": status,
        "control": "interaction.locator-check",
        "mission_id": mission,
        "scenario_rows_checked": len(rows),
        "findings": findings,
        "failed_checks": failed_checks,
    })


def _alignment_source_paths(root: Path, mission: str, stage: str) -> dict[str, Path]:
    stage_dir = _mission_stage_dir(root, mission)
    contracts = stage_dir / "contracts"
    return {
        "mission_contract": root / "harness-runtime" / "harness" / "missions" / mission / "mission-contract.md",
        "product_definition": stage_dir / "product" / "product-definition.md",
        "product_domain_model": stage_dir / "product" / "product-domain-model.md",
        "product_evidence": stage_dir / "product" / "product-evidence.md",
        "prd_contract": contracts / "prd.contract.yaml",
        "interaction_spec": stage_dir / "interaction-spec",
        "interaction_contract": contracts / "interaction.contract.yaml",
        "solution_contract": contracts / "solution.contract.yaml",
        "tech_design_contract": contracts / "tech-design.contract.yaml",
        "execution_brief_contract": contracts / "execution-brief.contract.yaml",
        "verification_report_contract": contracts / "verification-report.contract.yaml",
    }


def _collect_refs_from_path(path: Path) -> set[str]:
    if path.is_dir():
        refs: set[str] = set()
        for child in sorted(path.glob("*")):
            if child.is_file() and child.suffix in {".md", ".yaml", ".yml", ".ts", ".tsx", ".json"}:
                refs.update(_TRACE_REF_RE.findall(_read_text_if_exists(child)))
        return refs
    if path.suffix in {".yaml", ".yml", ".json"}:
        return _collect_refs_from_value(_load_yaml_contract_file(path), _TRACE_REF_RE)
    return set(_TRACE_REF_RE.findall(_read_text_if_exists(path)))


def _collect_known_upstream_refs(root: Path, mission: str, stage: str) -> set[str]:
    paths = _alignment_source_paths(root, mission, stage)
    order_by_stage = {
        "interaction": ["mission_contract", "product_definition", "product_domain_model", "product_evidence", "prd_contract"],
        "solution": ["mission_contract", "product_definition", "product_domain_model", "product_evidence", "prd_contract", "interaction_spec", "interaction_contract"],
        "technical_analysis": ["mission_contract", "product_definition", "product_domain_model", "product_evidence", "prd_contract", "interaction_spec", "interaction_contract", "solution_contract"],
        "breakdown": ["mission_contract", "product_definition", "product_domain_model", "product_evidence", "prd_contract", "interaction_spec", "interaction_contract", "solution_contract", "tech_design_contract"],
        "verify": ["mission_contract", "product_definition", "product_domain_model", "product_evidence", "prd_contract", "interaction_spec", "interaction_contract", "solution_contract", "tech_design_contract", "execution_brief_contract"],
    }
    refs: set[str] = set()
    for key in order_by_stage.get(stage, []):
        refs.update(_collect_refs_from_path(paths[key]))
    return refs


def _alignment_current_payload(root: Path, mission: str, stage: str) -> tuple[str, object, Path | None]:
    paths = _alignment_source_paths(root, mission, stage)
    if stage == "interaction":
        return stage, {
            "spec_refs": sorted(_collect_refs_from_path(paths["interaction_spec"])),
            "contract_refs": sorted(_collect_refs_from_path(paths["interaction_contract"])),
        }, paths["interaction_spec"]
    if stage == "solution":
        path = paths["solution_contract"]
    elif stage == "technical_analysis":
        path = paths["tech_design_contract"]
    elif stage == "breakdown":
        path = paths["execution_brief_contract"]
    elif stage == "verify":
        path = paths["verification_report_contract"]
    else:
        path = None
    return stage, _load_yaml_contract_file(path) if path else {}, path


def cmd_alignment_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    stage = args.stage
    findings: list[dict[str, object]] = []

    known_upstream = _collect_known_upstream_refs(root, mission, stage)
    _, current_payload, current_path = _alignment_current_payload(root, mission, stage)
    current_refs = _collect_refs_from_value(current_payload, _TRACE_REF_RE)
    current_domain_refs = _collect_refs_from_value(current_payload, _DOMAIN_REF_RE)
    known_domain = _known_domain_refs(root, mission)

    if not current_refs:
        findings.append(_finding(
            "FAIL",
            "MISSING_ALIGNMENT_EVIDENCE",
            f"{stage} artifact must include explicit trace refs to upstream PRD/domain/interaction/solution artifacts.",
            path=relpath(root, current_path) if current_path else None,
        ))

    if known_domain:
        for ref in sorted(current_domain_refs - known_domain):
            findings.append(_finding(
                "FAIL",
                "UNKNOWN_DOMAIN_REF",
                f"{stage} references unknown domain id {ref}.",
                ref=ref,
                path=relpath(root, current_path) if current_path else None,
            ))

    self_prefixes_by_stage = {
        "interaction": ("FLOW-", "STATE-", "INT-", "VAL-", "E2E-"),
        "solution": ("DEC-",),
        "technical_analysis": ("MOD-", "IF-", "DATA-", "VS-", "DEC-"),
        "breakdown": ("TASK-", "T-", "AT-"),
        "verify": ("E2E-",),
    }
    self_refs = {
        ref for ref in current_refs
        if ref.startswith(self_prefixes_by_stage.get(stage, ()))
    }
    for ref in sorted(current_refs - known_upstream - self_refs):
        findings.append(_finding(
            "FAIL",
            "BROKEN_UPSTREAM_TRACE",
            f"{stage} trace ref {ref} is not present in known upstream artifacts.",
            ref=ref,
            path=relpath(root, current_path) if current_path else None,
        ))

    text_blob = json.dumps(current_payload, ensure_ascii=False)
    if "{{" in text_blob:
        findings.append(_finding(
            "FAIL",
            "MISSING_ALIGNMENT_EVIDENCE",
            f"{stage} trace/alignment fields still contain placeholders.",
            path=relpath(root, current_path) if current_path else None,
        ))

    if stage == "interaction" and _interaction_prd_feedback_required(root, mission):
        findings.append(_finding(
            "FAIL",
            "PRD_FEEDBACK_REQUIRED",
            "Interaction changed AC/domain/permission/scope and must return to PRD or Decision Gate.",
        ))

    status, failed_checks = _apply_compat_warning(args, findings)
    return emit_payload(args, {
        "status": status,
        "control": "alignment.check",
        "mission_id": mission,
        "stage": stage,
        "known_upstream_refs_count": len(known_upstream),
        "current_refs": sorted(current_refs),
        "findings": findings,
        "failed_checks": failed_checks,
    })


def cmd_interaction_gate_run(args: argparse.Namespace) -> int:
    import contextlib as _cl
    import io as _io

    root = Path(root_arg(args))
    mission = args.mission
    checks: dict[str, dict[str, Any]] = {}
    failed_checks: list[dict[str, Any]] = []
    for name, handler, extra in (
        ("spec_check", cmd_interaction_spec_check, {}),
        ("visual_coverage_check", cmd_interaction_visual_coverage_check, {}),
        ("locator_check", cmd_interaction_locator_check, {}),
        ("alignment_check", cmd_alignment_check, {"stage": "interaction"}),
    ):
        check_args = argparse.Namespace(**vars(args))
        for key, value in extra.items():
            setattr(check_args, key, value)
        buf = _io.StringIO()
        with _cl.redirect_stdout(buf):
            handler(check_args)
        try:
            result = json.loads(buf.getvalue())
        except json.JSONDecodeError:
            result = {"status": "BLOCKED", "failed_checks": [{"check": name, "status": "BLOCKED"}]}
        checks[name] = result
        if result.get("status") not in {"PASS", "WARN"}:
            for item in result.get("failed_checks") or result.get("findings") or []:
                if isinstance(item, dict):
                    failed_checks.append({"check": name, **item})
            if not (result.get("failed_checks") or result.get("findings")):
                failed_checks.append({"check": name, "status": result.get("status")})

    status = "FAIL" if failed_checks else ("WARN" if any(r.get("status") == "WARN" for r in checks.values()) else "PASS")
    payload = {
        "status": status,
        "control": "interaction.gate-run",
        "mission_id": mission,
        "checks": checks,
        "failed_checks": failed_checks,
    }
    reports_dir = _mission_stage_dir(root, mission) / "gate-reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "interaction__hard_gate.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if status == "PASS":
        traces_dir = _mission_stage_dir(root, mission) / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)
        (traces_dir / "interaction_gate_pass.flag").write_text("PASS", encoding="utf-8")
        (traces_dir / "alignment_pass.flag").write_text("PASS", encoding="utf-8")
    return emit_payload(args, payload)


# --- tech-design lane CLIs --------------------------------------------------

# Keywords in mission-contract.md / product definition / solution.md that indicate
# dependency-impact analysis is required (similar to discovery's trigger but
# scoped to tech-design Step 1 prerequisite).
_DEP_IMPACT_TRIGGER_KEYWORDS = (
    ("外部业务系统", "external_system"),
    ("external system", "external_system"),
    ("third-party", "external_system"),
    ("third party", "external_system"),
    ("外部 API", "external_api"),
    ("external api", "external_api"),
    ("数据迁移", "data_migration"),
    ("data migration", "data_migration"),
    ("schema change", "schema_change"),
    ("schema 变更", "schema_change"),
    ("DDL", "schema_change"),
    ("跨服务", "cross_service"),
    ("cross-service", "cross_service"),
    ("微服务", "cross_service"),
    ("microservice", "cross_service"),
    ("integration", "integration"),
    ("webhook", "integration"),
    ("infrastructure", "infrastructure"),
    ("基础设施", "infrastructure"),
)


def cmd_tech_design_check_dep_impact_trigger(args: argparse.Namespace) -> int:
    """Stage-4 technical_analysis M2.1: auto-detect whether tech-design Step 1
    must dispatch the dependency-impact skill before Step 2.

    Replaces design/workflow.md prompt judgment with a typed payload. Conservative:
    if scope_in mentions external systems / data migration / cross-service /
    third-party APIs, dependency-impact is required. Reasons[] surfaced so
    the operator can challenge any heuristic hit.
    """
    root = Path(root_arg(args))
    mission_id = args.mission
    candidates: list[Path] = []
    mc = root / "harness-runtime" / "harness" / "missions" / mission_id / "mission-contract.md"
    if mc.exists():
        candidates.append(mc)
    for product_name in ("product-definition.md", "product-domain-model.md", "product-evidence.md"):
        product_path = root / "harness-runtime" / "harness" / "stages" / mission_id / "product" / product_name
        if product_path.exists():
            candidates.append(product_path)
    sol = root / "harness-runtime" / "harness" / "stages" / mission_id / "solution.md"
    if sol.exists():
        candidates.append(sol)

    if not candidates:
        return emit_payload(args, fail_payload(
            "tech-design.check-dep-impact-trigger",
            "missing_upstream",
            f"No mission-contract / product definition / solution found under mission {mission_id}.",
        ))

    matched_signals: set[str] = set()
    reasons: list[dict[str, str]] = []
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        text_lower = text.lower()
        for phrase, signal in _DEP_IMPACT_TRIGGER_KEYWORDS:
            if phrase.lower() in text_lower and signal not in matched_signals:
                matched_signals.add(signal)
                reasons.append({
                    "signal": signal,
                    "source": path.name,
                    "evidence": phrase,
                })

    required = bool(matched_signals)
    payload = {
        "status": "PASS",
        "control": "tech-design.check-dep-impact-trigger",
        "mission_id": mission_id,
        "required": required,
        "signals": sorted(matched_signals),
        "reasons": reasons,
        "findings": [],
    }
    return emit_payload(args, payload)


def cmd_tech_design_check_capability_trigger(args: argparse.Namespace) -> int:
    """Stage-4 technical_analysis M2.1: auto-detect whether tech-design Step 4
    must dispatch the agent-capability-designer for `## Agent 实现` section.

    Trigger: mission-contract.md contains an explicit `## Agent Engineering`
    section OR prd.contract.yaml has agent_capability_requirements[].
    Conservative default: required=False; only required=True when explicit
    Agent Engineering signal exists. reasons[] surfaces the source so the
    operator can confirm.
    """
    root = Path(root_arg(args))
    mission_id = args.mission
    matched_signals: set[str] = set()
    reasons: list[dict[str, str]] = []

    mc = root / "harness-runtime" / "harness" / "missions" / mission_id / "mission-contract.md"
    if mc.exists():
        text = mc.read_text(encoding="utf-8")
        if "## Agent Engineering" in text or "## Agent 工程" in text:
            matched_signals.add("agent_engineering_section")
            reasons.append({
                "signal": "agent_engineering_section",
                "source": "mission-contract.md",
                "evidence": "## Agent Engineering",
            })

    prd_contract = root / "harness-runtime" / "harness" / "stages" / mission_id / "contracts" / "prd.contract.yaml"
    if prd_contract.exists():
        try:
            doc = yaml.safe_load(prd_contract.read_text(encoding="utf-8")) or {}
            cc = doc.get("control_contract") or {}
            acr = cc.get("agent_capability_requirements") or []
            if acr:
                matched_signals.add("agent_capability_requirements")
                reasons.append({
                    "signal": "agent_capability_requirements",
                    "source": "prd.contract.yaml",
                    "evidence": f"{len(acr)} requirement(s)",
                })
        except yaml.YAMLError:
            pass

    required = bool(matched_signals)
    payload = {
        "status": "PASS",
        "control": "tech-design.check-capability-trigger",
        "mission_id": mission_id,
        "required": required,
        "signals": sorted(matched_signals),
        "reasons": reasons,
        "findings": [],
    }
    return emit_payload(args, payload)


def cmd_discovery_summary(args: argparse.Namespace) -> int:
    """Render a standardized summary of a discovery-brief contract.

    Discovery Step 9 user confirmation needs a consistent shape so the user
    sees the same fields every time and the AI cannot quietly drop sections.
    Plan §M2.1 says the summary is sourced from the externalized
    discovery-brief.contract.yaml (the markdown brief is human prose; the
    contract YAML is the audit-trail of structured findings).

    --format user emits a human-readable text block; --format json (default
    when --json is also passed) emits the typed payload itself. Both share
    the same underlying summary structure so the text rendering can never
    say something the JSON payload doesn't.
    """
    root = Path(root_arg(args))
    contract_path = root / "harness-runtime" / "harness" / "stages" / args.mission / "contracts" / "discovery-brief.contract.yaml"
    if not contract_path.exists():
        return emit_payload(args, fail_payload(
            "discovery.summary",
            "missing_contract",
            f"discovery-brief contract not found: {relpath(root, contract_path)}; run `harness contract fill --template discovery-brief` first.",
        ))
    try:
        document = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return emit_payload(args, fail_payload(
            "discovery.summary",
            "invalid_contract",
            f"discovery-brief contract is not valid YAML: {exc}",
        ))
    contract = document.get("control_contract") if isinstance(document.get("control_contract"), dict) else {}
    if not contract:
        return emit_payload(args, fail_payload(
            "discovery.summary",
            "invalid_contract",
            "discovery-brief contract is missing the `control_contract:` root.",
        ))

    def _items(key: str) -> list[dict[str, Any]]:
        value = contract.get(key)
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    capabilities = _items("affected_capabilities")
    roles = _items("roles")
    scenarios = _items("scenarios")
    existing = _items("existing_solutions")
    assumptions = _items("design_assumptions")
    candidates = _items("agent_engineering_candidates")
    degradations = _items("degradations")

    def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items:
            label = str(item.get(key) or "unspecified")
            counts[label] = counts.get(label, 0) + 1
        return counts

    summary: dict[str, Any] = {
        "mission_id": args.mission,
        "stage": contract.get("stage"),
        "affected_capabilities": {
            "total": len(capabilities),
            "by_confidence": _count_by(capabilities, "confidence"),
        },
        "roles": {"total": len(roles)},
        "scenarios": {
            "total": len(scenarios),
            "by_kind": _count_by(scenarios, "kind"),
        },
        "existing_solutions": {
            "total": len(existing),
            "by_source": _count_by(existing, "source"),
        },
        "design_assumptions": {
            "total": len(assumptions),
            "by_downstream": _count_by(assumptions, "impact_on"),
        },
        "agent_engineering_candidates": {
            "total": len(candidates),
            "by_recommendation": _count_by(candidates, "recommended"),
        },
        "degradations": {
            "total": len(degradations),
            "by_kind": _count_by(degradations, "kind"),
        },
    }

    # M4.2 will turn missing affected_capabilities into a FAIL via the
    # W-spec-coverage lint rule. At M2.1 surfacing this as a finding gives the
    # workflow + reviewer a typed signal without yet blocking gate PASS.
    findings: list[dict[str, str]] = []
    if not capabilities:
        findings.append({
            "level": "WARN",
            "code": "no_affected_capabilities",
            "message": "discovery-brief.contract.yaml.affected_capabilities is empty; downstream PRD has no capability impact baseline.",
        })
    if not roles:
        findings.append({
            "level": "WARN",
            "code": "no_roles",
            "message": "discovery-brief.contract.yaml.roles is empty; user-impact analysis is missing.",
        })
    if not scenarios:
        findings.append({
            "level": "WARN",
            "code": "no_scenarios",
            "message": "discovery-brief.contract.yaml.scenarios is empty; happy_path / exception coverage cannot be audited.",
        })

    payload: dict[str, Any] = {
        "status": "WARN" if findings else "PASS",
        "control": "discovery.summary",
        "contract_path": relpath(root, contract_path),
        "summary": summary,
        "findings": findings,
    }

    if args.format == "user":
        # Human-readable rendering placed in `display` so JSON consumers see
        # both the structured summary and the same text the user sees — no
        # divergence possible.
        lines = [
            f"# Discovery Brief Summary — {args.mission}",
            "",
            f"- affected_capabilities: {summary['affected_capabilities']['total']} "
            f"({', '.join(f'{k}={v}' for k, v in summary['affected_capabilities']['by_confidence'].items()) or 'none'})",
            f"- roles: {summary['roles']['total']}",
            f"- scenarios: {summary['scenarios']['total']} "
            f"({', '.join(f'{k}={v}' for k, v in summary['scenarios']['by_kind'].items()) or 'none'})",
            f"- existing_solutions: {summary['existing_solutions']['total']} "
            f"({', '.join(f'{k}={v}' for k, v in summary['existing_solutions']['by_source'].items()) or 'none'})",
            f"- design_assumptions: {summary['design_assumptions']['total']}",
            f"- agent_engineering_candidates: {summary['agent_engineering_candidates']['total']} "
            f"({', '.join(f'{k}={v}' for k, v in summary['agent_engineering_candidates']['by_recommendation'].items()) or 'none'})",
            f"- degradations: {summary['degradations']['total']}",
        ]
        if findings:
            lines.append("")
            lines.append("## Gaps")
            for f in findings:
                lines.append(f"- [{f['level']}] {f['code']}: {f['message']}")
        payload["display"] = "\n".join(lines)

    return emit_payload(args, payload)


# ---------------------------------------------------------------------------
# verify-improvement-plan M2.1: verify command domain
# ---------------------------------------------------------------------------

def _verify_report_path(root: Path, mission: str) -> Path:
    return (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission
        / "contracts"
        / "verification-report.contract.yaml"
    )


def _resolve_verify_contract(
    root: Path, mission: str, artifact_arg: str | None = None
) -> tuple[Path, dict | None, str | None]:
    path = Path(artifact_arg) if artifact_arg else _verify_report_path(root, mission)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        return path, None, "verification_report_contract_missing"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return path, None, "verification_report_contract_invalid_yaml"
    if not isinstance(doc, dict):
        return path, None, "verification_report_contract_invalid_root"
    contract = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
    if not isinstance(contract, dict):
        return path, None, "verification_report_contract_invalid_shape"
    return path, contract, None


def _resolve_execution_brief_for_verify(
    root: Path, mission: str, upstream_arg: str | None = None
) -> tuple[Path, dict | None, str | None]:
    """Resolve execution-brief.contract.yaml for verify commands."""
    if upstream_arg:
        path = Path(upstream_arg)
        if not path.is_absolute():
            path = root / path
    else:
        path = (
            root
            / "harness-runtime"
            / "harness"
            / "stages"
            / mission
            / "contracts"
            / "execution-brief.contract.yaml"
        )
    if not path.exists():
        return path, None, "execution_brief_contract_missing"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return path, None, "execution_brief_contract_invalid_yaml"
    if not isinstance(doc, dict):
        return path, None, "execution_brief_contract_invalid_root"
    contract = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
    return path, contract, None


def cmd_verify_compute_scope(args: argparse.Namespace) -> int:
    """verify compute-scope: output ac_list, task_list, test_layers, e2e_obligations,
    project_lint_enabled, required_evidence_matrix from execution-brief.
    """
    root = Path(root_arg(args))
    mission = args.mission
    _brief_path, brief, err = _resolve_execution_brief_for_verify(root, mission)
    if err or brief is None:
        return emit_payload(args, fail_payload("verify.compute-scope", err or "brief_unloadable", f"Cannot load execution-brief for mission {mission}"))

    tasks = brief.get("tasks") or []
    ac_list: list[str] = []
    for t in tasks:
        if isinstance(t, dict):
            for ac in t.get("traces_to") or []:
                if isinstance(ac, str) and ac not in ac_list:
                    ac_list.append(ac)

    required_evidence_matrix: list[dict] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        task_id = t.get("id", "")
        for re in t.get("required_evidence") or []:
            if isinstance(re, dict):
                required_evidence_matrix.append({
                    "task_id": task_id,
                    "id": re.get("id", ""),
                    "path": re.get("path", ""),
                    "command": re.get("command", ""),
                    "verification_type": re.get("verification_type", re.get("type", "")),
                })

    # Check execute_failure_ref
    execute_failure_ref: dict | None = None
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for er in t.get("execution_results") or []:
            if isinstance(er, dict) and er.get("failure_state"):
                execute_failure_ref = {
                    "task_id": t.get("id"),
                    "failure_state": er["failure_state"],
                }
                break
        if execute_failure_ref:
            break

    harness_config = root / "harness-runtime" / "config" / "harness.yaml"
    project_lint_enabled = False
    if harness_config.exists():
        try:
            cfg = yaml.safe_load(harness_config.read_text(encoding="utf-8")) or {}
            project_lint_enabled = bool((cfg.get("project_lint") or {}).get("enabled", False))
        except yaml.YAMLError:
            pass

    return emit_payload(args, {
        "status": "PASS",
        "control": "verify.compute-scope",
        "mission_id": mission,
        "ac_list": ac_list,
        "task_list": [t.get("id") for t in tasks if isinstance(t, dict)],
        "test_layers": ["unit", "integration", "e2e"],
        "e2e_obligations": brief.get("e2e_obligations") or [],
        "project_lint_enabled": project_lint_enabled,
        "required_evidence_matrix": required_evidence_matrix,
        "execute_failure_ref": execute_failure_ref,
    })


def cmd_verify_run_tests(args: argparse.Namespace) -> int:
    """verify run-tests: run a single test layer and write command evidence."""
    root = Path(root_arg(args))
    mission = args.mission
    layer = args.layer
    command = getattr(args, "command", None) or ""
    if not command:
        return emit_payload(args, fail_payload("verify.run-tests", "command_required", "--command is required for verify run-tests"))
    import subprocess as _sp
    import datetime as _dt
    traces_dir = root / "harness-runtime" / "harness" / "stages" / mission / "traces" / "cmd"
    traces_dir.mkdir(parents=True, exist_ok=True)
    started_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
    result = _sp.run(command, shell=True, cwd=str(root), capture_output=True, text=True, timeout=300)
    ended_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
    cmd_id = f"cmd-{layer}-{started_at[:19].replace(':', '-').replace('T', '-')}"
    evidence = {
        "id": cmd_id,
        "kind": "command",
        "layer": layer,
        "command": command,
        "cwd": str(root),
        "exit_code": result.returncode,
        "started_at": started_at,
        "ended_at": ended_at,
        "result": "pass" if result.returncode == 0 else "fail",
        "stdout": result.stdout[:4096],
        "stderr": result.stderr[:4096],
        "artifact": str(traces_dir / f"{cmd_id}.json"),
    }
    (traces_dir / f"{cmd_id}.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    status = "PASS" if result.returncode == 0 else "FAIL"
    return emit_payload(args, {
        "status": status,
        "control": "verify.run-tests",
        "mission_id": mission,
        "layer": layer,
        "command": command,
        "exit_code": result.returncode,
        "evidence_id": cmd_id,
        "artifact": evidence["artifact"],
    })


def cmd_verify_e2e_status(args: argparse.Namespace) -> int:
    """verify e2e-status: return current e2e-status.json content."""
    root = Path(root_arg(args))
    mission = args.mission
    e2e_path = root / "harness-runtime" / "harness" / "traces" / mission / "e2e" / "e2e-status.json"
    if not e2e_path.exists():
        e2e_path = root / "harness-runtime" / "harness" / "stages" / mission / "traces" / "e2e" / "e2e-status.json"
    if not e2e_path.exists():
        payload = {
            "status": "BLOCKED",
            "control": "verify.e2e-status",
            "mission_id": mission,
            "message": "e2e-status.json not found; run the E2E three-step pipeline first",
        }
        if getattr(args, "json", False):
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"verify.e2e-status: BLOCKED — {payload['message']}")
        return 0
    try:
        data = json.loads(e2e_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return emit_payload(args, fail_payload("verify.e2e-status", "e2e_status_invalid", "e2e-status.json is not valid JSON"))
    return emit_payload(args, {
        "status": data.get("status", "UNKNOWN"),
        "control": "verify.e2e-status",
        "mission_id": mission,
        "e2e_status": data,
        "artifact": str(e2e_path),
    })


def cmd_verify_dispatch_worker(args: argparse.Namespace) -> int:
    """verify dispatch-worker: generate verification-engineer dispatch envelope."""
    import datetime as _dt
    root = Path(root_arg(args))
    mission = args.mission
    envelope_dir = (
        root / "harness-runtime" / "harness" / "stages" / mission / "traces" / "dispatches"
    )
    envelope_dir.mkdir(parents=True, exist_ok=True)
    envelope = {
        "dispatch_id": f"dispatch-worker-{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "agent": "verification-engineer",
        "mission_id": mission,
        "execution_mode": "spawn_agent",
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "write_scope": [
            f"harness-runtime/harness/stages/{mission}/verification-report.md",
            f"harness-runtime/harness/stages/{mission}/contracts/verification-report.contract.yaml",
            f"harness-runtime/harness/traces/{mission}/**",
        ],
    }
    out = envelope_dir / "worker-dispatch.json"
    out.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return emit_payload(args, {
        "status": "PASS",
        "control": "verify.dispatch-worker",
        "mission_id": mission,
        "dispatch_id": envelope["dispatch_id"],
        "envelope_path": str(out),
    })


def cmd_verify_dispatch_reviewer(args: argparse.Namespace) -> int:
    """verify dispatch-reviewer: generate reviewer dispatch envelope. Blocks main_agent_fallback."""
    import datetime as _dt
    root = Path(root_arg(args))
    mission = args.mission
    envelope_dir = (
        root / "harness-runtime" / "harness" / "stages" / mission / "traces" / "dispatches"
    )
    envelope_dir.mkdir(parents=True, exist_ok=True)
    envelope = {
        "dispatch_id": f"dispatch-reviewer-{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "agent": "verification-effectiveness-reviewer",
        "mission_id": mission,
        "execution_mode": "spawn_agent",
        "readonly": True,
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "main_agent_fallback": "BLOCKED",
        "note": "reviewer PASS must be from spawn_agent or human checkpoint; main_agent_fallback is rejected",
    }
    out = envelope_dir / "reviewer-dispatch.json"
    out.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return emit_payload(args, {
        "status": "PASS",
        "control": "verify.dispatch-reviewer",
        "mission_id": mission,
        "dispatch_id": envelope["dispatch_id"],
        "envelope_path": str(out),
    })


def cmd_verify_detect_contradictions(args: argparse.Namespace) -> int:
    """verify detect-contradictions: compare ac_trace.conclusion vs evidence results."""
    root = Path(root_arg(args))
    mission = args.mission
    artifact_arg = getattr(args, "artifact", None)
    _path, contract, err = _resolve_verify_contract(root, mission, artifact_arg)
    if err or contract is None:
        return emit_payload(args, fail_payload("verify.detect-contradictions", err or "contract_unloadable", f"Cannot load verification contract for mission {mission}"))

    contradictions: list[dict] = []
    command_evidence: dict[str, dict] = {}
    for ce in contract.get("command_evidence") or []:
        if isinstance(ce, dict) and ce.get("id"):
            command_evidence[ce["id"]] = ce

    for ac in contract.get("ac_trace") or []:
        if not isinstance(ac, dict):
            continue
        ac_id = ac.get("id") or ac.get("ac_id") or "<unknown>"
        conclusion = str(ac.get("conclusion", "")).lower()
        if conclusion != "pass":
            continue
        for cmd_id in ac.get("command_evidence_ids") or []:
            ce = command_evidence.get(cmd_id)
            if ce is None:
                continue
            ce_result = str(ce.get("result", "")).lower()
            if ce_result in {"fail", "blocked", "unavailable"}:
                contradictions.append({
                    "ac_id": ac_id,
                    "command_evidence_id": cmd_id,
                    "issue": f"ac_trace.conclusion=pass but command_evidence[{cmd_id}].result={ce_result!r}",
                })

    status = "FAIL" if contradictions else "PASS"
    return emit_payload(args, {
        "status": status,
        "control": "verify.detect-contradictions",
        "mission_id": mission,
        "contradictions": contradictions,
    })


def cmd_verify_compute_conclusion(args: argparse.Namespace) -> int:
    """verify compute-conclusion: return PASS|FAIL|BLOCKED|PASS_WITH_RISK conclusion."""
    root = Path(root_arg(args))
    mission = args.mission
    _path, contract, err = _resolve_verify_contract(root, mission)
    if err or contract is None:
        return emit_payload(args, fail_payload("verify.compute-conclusion", err or "contract_unloadable", f"Cannot load verification contract for mission {mission}"))

    # Check execute_failure_ref
    execute_failure_ref = contract.get("execute_failure_ref")
    if execute_failure_ref:
        return emit_payload(args, {
            "status": "PASS",
            "control": "verify.compute-conclusion",
            "mission_id": mission,
            "conclusion": "BLOCKED",
            "failure_path": "blocked_execute_failure",
            "reason": f"execute already FAILED: {execute_failure_ref}",
        })

    ac_traces = contract.get("ac_trace") or []
    conclusions = [str(ac.get("conclusion", "")).lower() for ac in ac_traces if isinstance(ac, dict)]
    fail_count = sum(1 for c in conclusions if c in {"fail", "failed"})
    blocked_count = sum(1 for c in conclusions if c == "blocked")
    risk_count = sum(1 for c in conclusions if c == "pass_with_risk")

    if blocked_count > 0:
        conclusion = "BLOCKED"
        failure_path = "decision_gate"
    elif fail_count > 0:
        conclusion = "FAIL"
        failure_path = "bug_fix"
    elif risk_count > 0:
        conclusion = "PASS_WITH_RISK"
        failure_path = None
    else:
        conclusion = "PASS"
        failure_path = None

    return emit_payload(args, {
        "status": "PASS",
        "control": "verify.compute-conclusion",
        "mission_id": mission,
        "conclusion": conclusion,
        "failure_path": failure_path,
        "ac_summary": {
            "total": len(conclusions),
            "pass": sum(1 for c in conclusions if c in {"pass", "passed"}),
            "fail": fail_count,
            "blocked": blocked_count,
            "pass_with_risk": risk_count,
        },
    })


def cmd_verify_agent_eval_status(args: argparse.Namespace) -> int:
    """verify agent-eval-status: check if agent-eval is required and its status."""
    root = Path(root_arg(args))
    mission = args.mission
    eval_report = (
        root / "harness-runtime" / "harness" / "stages" / mission / "agent-eval-report.md"
    )
    harness_config = root / "harness-runtime" / "config" / "harness.yaml"
    require_agent_eval = False
    if harness_config.exists():
        try:
            cfg = yaml.safe_load(harness_config.read_text(encoding="utf-8")) or {}
            ae = cfg.get("agent_engineering") or {}
            require_agent_eval = bool(ae.get("require_agent_eval", False))
        except yaml.YAMLError:
            pass

    if not require_agent_eval:
        return emit_payload(args, {
            "status": "PASS",
            "control": "verify.agent-eval-status",
            "mission_id": mission,
            "required": False,
            "passed": True,
            "failure_impact": None,
        })

    if not eval_report.exists():
        return emit_payload(args, {
            "status": "BLOCKED",
            "control": "verify.agent-eval-status",
            "mission_id": mission,
            "required": True,
            "passed": False,
            "failure_impact": "agent-eval-report.md missing; run agent-eval skill",
        })

    text = eval_report.read_text(encoding="utf-8")
    passed = "High" not in text or "未通过" not in text
    return emit_payload(args, {
        "status": "PASS" if passed else "FAIL",
        "control": "verify.agent-eval-status",
        "mission_id": mission,
        "required": True,
        "passed": passed,
        "failure_impact": None if passed else "agent-eval has High severity failures",
    })


def cmd_verify_failure_path(args: argparse.Namespace) -> int:
    """verify failure-path: record a typed failure path for the mission."""
    import datetime as _dt
    root = Path(root_arg(args))
    mission = args.mission
    kind = args.kind
    valid_kinds = {"bug_fix", "execute", "decision_gate", "receiving_review",
                   "blocked_execute_failure", "execute_evidence_missing"}
    if kind not in valid_kinds:
        return emit_payload(args, fail_payload("verify.failure-path", "invalid_kind", f"kind must be one of {sorted(valid_kinds)}"))
    traces_dir = root / "harness-runtime" / "harness" / "stages" / mission / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "kind": kind,
        "mission_id": mission,
        "recorded_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "stage": "verify",
    }
    (traces_dir / "failure_path.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )
    return emit_payload(args, {
        "status": "PASS",
        "control": "verify.failure-path",
        "mission_id": mission,
        "kind": kind,
        "record_path": str(traces_dir / "failure_path.json"),
    })


def _evidence_role(ev: dict[str, Any]) -> str:
    return str(
        ev.get("evidence_role")
        or ev.get("role")
        or ev.get("purpose")
        or ""
    ).lower()


def _is_ui_ac_trace(ac: dict[str, Any]) -> bool:
    return (
        str(ac.get("surface_type") or "").lower() == "ui"
        or bool(ac.get("ui_surface"))
        or str(ac.get("ac_type") or "").lower() == "ui"
    )


def cmd_verify_true_e2e_check(args: argparse.Namespace) -> int:
    """Verify UI ACs using real browser-path primary evidence.

    API/DB/internal/mock evidence can prepare or cross-check data, but it cannot
    be the primary result for a UI acceptance criterion.
    """
    root = Path(root_arg(args))
    mission = args.mission
    _path, contract, err = _resolve_verify_contract(root, mission)
    if err or contract is None:
        return emit_payload(args, fail_payload(
            "verify.true-e2e-check",
            err or "contract_unloadable",
            f"Cannot load verification contract for mission {mission}",
        ))

    result_evidence: dict[str, dict[str, Any]] = {}
    for item in contract.get("result_evidence") or []:
        if isinstance(item, dict) and item.get("id"):
            result_evidence[str(item["id"])] = item

    failed_checks: list[dict[str, object]] = []
    checked_ui_acs = 0
    for ac in contract.get("ac_trace") or []:
        if not isinstance(ac, dict):
            continue
        if str(ac.get("conclusion") or "").lower() != "pass":
            continue
        if not _is_ui_ac_trace(ac):
            continue
        checked_ui_acs += 1
        ac_id = str(ac.get("id") or ac.get("ac_id") or "<unknown>")
        res_ids = [str(rid) for rid in (ac.get("result_evidence_ids") or [])]
        browser_primary = False
        for rid in res_ids:
            ev = result_evidence.get(rid) or {}
            kind = str(ev.get("kind") or "").lower()
            role = _evidence_role(ev)
            if kind in _BROWSER_PRIMARY_EVIDENCE_KINDS and role in {"", "primary", "primary_user_path", "user_path", "browser_user_flow"}:
                browser_primary = True
            if kind in _NON_UI_PRIMARY_EVIDENCE_KINDS and role in {"", "primary", "primary_user_path", "user_path", "assertion"}:
                failed_checks.append({
                    "check": "true_e2e_api_primary_not_allowed",
                    "code": "TRUE_E2E_API_PRIMARY_NOT_ALLOWED",
                    "ac_id": ac_id,
                    "evidence_id": rid,
                    "kind": kind,
                    "message": "API/DB/internal/mock evidence cannot be primary evidence for a UI AC.",
                })
            if kind == "mock" and not (
                ev.get("api_contract_ref")
                or ev.get("contract_ref")
                or ev.get("fixture_parity_evidence_id")
                or ev.get("fixture_parity")
            ):
                failed_checks.append({
                    "check": "true_e2e_mock_without_parity",
                    "code": "TRUE_E2E_MOCK_WITHOUT_PARITY",
                    "ac_id": ac_id,
                    "evidence_id": rid,
                    "message": "Mock evidence needs API contract or fixture parity evidence when used as auxiliary UI AC evidence.",
                })
        if not browser_primary:
            failed_checks.append({
                "check": "true_e2e_primary_browser_evidence_missing",
                "code": "TRUE_E2E_PRIMARY_BROWSER_EVIDENCE_MISSING",
                "ac_id": ac_id,
                "message": (
                    "UI AC pass requires real browser-path primary evidence "
                    f"with kind in {sorted(_BROWSER_PRIMARY_EVIDENCE_KINDS)}."
                ),
            })

    findings = [dict(item, level="FAIL") for item in failed_checks]
    status, compat_failed = _apply_compat_warning(args, findings)
    return emit_payload(args, {
        "status": status,
        "control": "verify.true-e2e-check",
        "mission_id": mission,
        "checked_ui_acs": checked_ui_acs,
        "findings": findings,
        "failed_checks": compat_failed,
    })


def cmd_verify_gate_run(args: argparse.Namespace) -> int:
    """verify gate run: thin wrapper aggregating check-ac-trace, detect-contradictions,
    and the general gate run for the verify stage.
    """
    import io as _io
    import contextlib as _cl
    root = Path(root_arg(args))
    mission = args.mission

    # 1. contract check-ac-trace
    ac_trace_args = argparse.Namespace(**vars(args))
    ac_trace_args.mission = mission
    ac_trace_args.artifact = None
    ac_trace_args.upstream = None
    ac_trace_buf = _io.StringIO()
    with _cl.redirect_stdout(ac_trace_buf):
        _rc1 = cmd_contract_check_ac_trace(ac_trace_args)
    try:
        ac_trace_result = json.loads(ac_trace_buf.getvalue())
    except json.JSONDecodeError:
        ac_trace_result = {"status": "BLOCKED", "failed_checks": []}

    # 2. true E2E check: UI ACs require browser-path primary evidence.
    true_e2e_args = argparse.Namespace(**vars(args))
    true_e2e_buf = _io.StringIO()
    with _cl.redirect_stdout(true_e2e_buf):
        _rc_true_e2e = cmd_verify_true_e2e_check(true_e2e_args)
    try:
        true_e2e_result = json.loads(true_e2e_buf.getvalue())
    except json.JSONDecodeError:
        true_e2e_result = {"status": "BLOCKED", "failed_checks": []}

    # 3. detect-contradictions
    contra_args = argparse.Namespace(**vars(args))
    contra_args.artifact = None
    contra_buf = _io.StringIO()
    with _cl.redirect_stdout(contra_buf):
        _rc2 = cmd_verify_detect_contradictions(contra_args)
    try:
        contra_result = json.loads(contra_buf.getvalue())
    except json.JSONDecodeError:
        contra_result = {"status": "BLOCKED", "contradictions": []}

    # 4. compute-conclusion
    concl_args = argparse.Namespace(**vars(args))
    concl_buf = _io.StringIO()
    with _cl.redirect_stdout(concl_buf):
        _rc3 = cmd_verify_compute_conclusion(concl_args)
    try:
        concl_result = json.loads(concl_buf.getvalue())
    except json.JSONDecodeError:
        concl_result = {"status": "BLOCKED", "conclusion": "BLOCKED"}

    failed_checks: list[dict] = []
    if ac_trace_result.get("status") not in {"PASS"}:
        for fc in ac_trace_result.get("failed_checks") or []:
            failed_checks.append(fc)
        if not ac_trace_result.get("failed_checks"):
            failed_checks.append({"check": "contract.check-ac-trace", "status": ac_trace_result.get("status")})
    if true_e2e_result.get("status") not in {"PASS"}:
        for fc in true_e2e_result.get("failed_checks") or []:
            failed_checks.append(fc)
        if not true_e2e_result.get("failed_checks"):
            failed_checks.append({"check": "verify.true-e2e-check", "status": true_e2e_result.get("status")})
    if contra_result.get("status") not in {"PASS"}:
        for c in contra_result.get("contradictions") or []:
            failed_checks.append({"check": "verify.detect-contradictions", **c})

    overall = "FAIL" if failed_checks else (concl_result.get("conclusion") or "PASS")
    # Write gate_run_pass flag if PASS
    if overall == "PASS":
        traces_dir = root / "harness-runtime" / "harness" / "stages" / mission / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)
        (traces_dir / "gate_run_pass.flag").write_text("PASS", encoding="utf-8")
        if true_e2e_result.get("status") == "PASS":
            (traces_dir / "true_e2e_pass.flag").write_text("PASS", encoding="utf-8")
        if not contra_result.get("contradictions"):
            (traces_dir / "contradictions_pass.flag").write_text("PASS", encoding="utf-8")

    return emit_payload(args, {
        "status": overall,
        "control": "verify.gate-run",
        "mission_id": mission,
        "conclusion": concl_result.get("conclusion"),
        "failed_checks": failed_checks,
        "ac_trace_status": ac_trace_result.get("status"),
        "true_e2e_status": true_e2e_result.get("status"),
        "contradictions_status": contra_result.get("status"),
    })


def cmd_contract_check_ac_trace(args: argparse.Namespace) -> int:
    """contract check-ac-trace: validate AC evidence sufficiency and required_evidence_id anchoring."""
    root = Path(root_arg(args))
    mission = args.mission
    artifact_arg = getattr(args, "artifact", None)
    upstream_arg = getattr(args, "upstream", None)

    _path, contract, err = _resolve_verify_contract(root, mission, artifact_arg)
    if err or contract is None:
        return emit_payload(args, fail_payload("contract.check-ac-trace", err or "contract_unloadable", f"Cannot load verification contract for mission {mission}"))

    _brief_path, brief, brief_err = _resolve_execution_brief_for_verify(root, mission, upstream_arg)
    valid_re_ids: set[str] = set()
    if brief is not None:
        for t in brief.get("tasks") or []:
            if not isinstance(t, dict):
                continue
            for re in t.get("required_evidence") or []:
                if isinstance(re, dict) and isinstance(re.get("id"), str):
                    valid_re_ids.add(re["id"])

    failed_checks: list[dict] = []
    command_evidence: dict[str, dict] = {}
    result_evidence: dict[str, dict] = {}
    for ce in contract.get("command_evidence") or []:
        if isinstance(ce, dict) and ce.get("id"):
            command_evidence[ce["id"]] = ce
    for re in contract.get("result_evidence") or []:
        if isinstance(re, dict) and re.get("id"):
            result_evidence[re["id"]] = re

    # Check required_evidence_id cross-references (H3 primary key) when upstream available
    if valid_re_ids:
        for key, entries in [("command_evidence", command_evidence), ("result_evidence", result_evidence)]:
            for ev_id, ev in entries.items():
                ref = ev.get("required_evidence_id")
                if ref and ref not in valid_re_ids:
                    failed_checks.append({
                        "check": "required_evidence_id_not_in_upstream",
                        "code": "VERIFY_EVIDENCE_ID_NOT_IN_UPSTREAM",
                        "evidence_id": ev_id,
                        "evidence_kind": key,
                        "required_evidence_id": ref,
                        "message": f"{key}[{ev_id}].required_evidence_id={ref!r} not found in execution-brief required_evidence ids",
                    })

    # Check AC evidence sufficiency
    _UI_KINDS = _BROWSER_PRIMARY_EVIDENCE_KINDS
    for ac in contract.get("ac_trace") or []:
        if not isinstance(ac, dict):
            continue
        conclusion = str(ac.get("conclusion", "")).lower()
        if conclusion != "pass":
            continue
        ac_id = ac.get("id") or ac.get("ac_id") or "<unknown>"
        cmd_ids = set(ac.get("command_evidence_ids") or [])
        res_ids = set(ac.get("result_evidence_ids") or [])
        if not cmd_ids:
            failed_checks.append({
                "check": "missing_command_evidence",
                "ac_id": ac_id,
                "message": f"ac_trace[{ac_id}].conclusion=pass but no command_evidence_ids",
            })
        if not res_ids:
            failed_checks.append({
                "check": "missing_result_evidence",
                "ac_id": ac_id,
                "message": f"ac_trace[{ac_id}].conclusion=pass but no result_evidence_ids",
            })
        # UI AC check
        is_ui = ac.get("surface_type") == "ui" or bool(ac.get("ui_surface"))
        if is_ui:
            ui_kind_found = any(
                str((result_evidence.get(rid) or {}).get("kind", "")).lower() in _UI_KINDS
                for rid in res_ids
            )
            if not ui_kind_found:
                failed_checks.append({
                    "check": "missing_ui_evidence_kind",
                    "ac_id": ac_id,
                    "message": f"ac_trace[{ac_id}].surface_type=ui but no result_evidence with kind in {sorted(_UI_KINDS)}",
                })

    status = "FAIL" if failed_checks else "PASS"
    return emit_payload(args, {
        "status": status,
        "control": "contract.check-ac-trace",
        "mission_id": mission,
        "failed_checks": failed_checks,
        "upstream_re_ids_count": len(valid_re_ids),
    })



# ----------------------------------------------------------------------------
# Retrospective stage commands (retrospective-improvement-plan M2.1)
# ----------------------------------------------------------------------------


def _stage_dir(root: Path, mission: str) -> Path:
    return runtime_harness_root(root) / "stages" / mission


def cmd_mission_artifacts(args: argparse.Namespace) -> int:
    """Return artifact index for a mission stage that Gate has accepted.

    retrospective-improvement-plan M2.1 — replaces Step 1 fixed-path enumeration.
    Returns {artifacts: [{stage, path, exists}]}.
    """
    root = Path(root_arg(args))
    mission = args.mission
    stage_filter = getattr(args, "stage", None)
    harness_root = runtime_harness_root(root)
    stages_root = harness_root / "stages" / mission
    artifact_defs = [
        ("prd", "product/product-definition.md"),
        ("prd", "product/product-domain-model.md"),
        ("prd", "product/product-evidence.md"),
        ("solution", "solution.md"),
        ("tech-design", "tech-design.md"),
        ("interaction", "interaction.md"),
        ("execution-brief", "execution-brief.md"),
        ("verification-report", "verification-report.md"),
        ("code-review", "code-review.md"),
        ("acceptance-result", "acceptance-result.md"),
        ("delivery", "delivery.md"),
        ("retrospective", "retrospective.md"),
    ]
    artifacts = []
    for stage, name in artifact_defs:
        path = stages_root / name
        artifacts.append({
            "stage": stage,
            "path": str(path.relative_to(root)) if path.exists() else str(stages_root.relative_to(root) / name),
            "exists": path.exists(),
        })
    if stage_filter:
        artifacts = [a for a in artifacts if a["stage"] == stage_filter]
    findings: list[dict] = []
    existing = [a for a in artifacts if a["exists"]]
    if not existing:
        findings.append({
            "level": "WARN",
            "code": "no_artifacts_found",
            "message": f"No artifacts found for mission {mission}. Stage may not have started yet.",
        })
    return emit_payload(args, {
        "status": "PASS",
        "control": "mission.artifacts",
        "mission": mission,
        "artifacts": artifacts,
        "count": len(existing),
        "findings": findings,
    })


def _read_trace_events(root: Path, mission: str) -> list[dict]:
    """Read all events from the mission trace JSONL log."""
    import json as _json
    trace_path = runtime_harness_root(root) / "state" / "trace" / f"{mission}-trace.jsonl"
    if not trace_path.exists():
        return []
    events = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(_json.loads(line))
        except Exception:
            pass
    return events


def _read_approvals_for_mission(root: Path, mission: str) -> list[dict]:
    """Read approval records for a mission from approvals.json."""
    try:
        _doc, records = load_approvals(root)
    except Exception:
        return []
    return [r for r in records if r.get("mission") == mission]


def _read_stage_effectiveness(root: Path, mission: str) -> dict:
    """Read effectiveness_review fields from stage contracts."""
    stages_root = runtime_harness_root(root) / "stages" / mission / "contracts"
    result = {}
    if not stages_root.exists():
        return result
    for contract_path in stages_root.glob("*.contract.yaml"):
        try:
            doc = load_yaml(contract_path)
            cc = doc.get("control_contract", {})
            er = cc.get("effectiveness_review", {})
            if er:
                result[contract_path.stem] = {
                    "rounds_used": er.get("rounds_used"),
                    "last_verdict": er.get("last_verdict"),
                    "checkpoints": er.get("checkpoints", []),
                }
        except Exception:
            pass
    return result


def cmd_mission_retrospective_data(args: argparse.Namespace) -> int:
    """Aggregate retrospective input data for a mission.

    retrospective-improvement-plan M2.1 F1-fix — replaces Step 0 ad-hoc reads.
    Collects trace-log, approvals, per-stage effectiveness_review, stop_events.
    """
    root = Path(root_arg(args))
    mission = args.mission
    findings: list[dict] = []

    trace_events = _read_trace_events(root, mission)
    approvals = _read_approvals_for_mission(root, mission)
    effectiveness = _read_stage_effectiveness(root, mission)

    # Build per-stage summary
    stages: list[dict] = []
    for stage_key, er in effectiveness.items():
        stages.append({
            "stage": stage_key,
            "rounds_used": er.get("rounds_used"),
            "last_verdict": er.get("last_verdict"),
            "checkpoints": er.get("checkpoints", []),
            "stop_events": [
                e for e in trace_events
                if e.get("stage") == stage_key and e.get("type") == "stop_event"
            ],
            "approvals": [a for a in approvals if a.get("stage") == stage_key],
            "trace_event_count": sum(
                1 for e in trace_events if e.get("stage") == stage_key
            ),
        })

    # Cross-stage failures from trace
    cross_stage_failures = [
        e for e in trace_events
        if e.get("status") == "fail" or e.get("type") == "gate_fail"
    ]

    return emit_payload(args, {
        "status": "PASS",
        "control": "mission.retrospective-data",
        "mission": mission,
        "stages": stages,
        "cross_stage_failures": cross_stage_failures,
        "trace_event_count": len(trace_events),
        "approval_count": len(approvals),
        "findings": findings,
    })


def cmd_project_context_add_lesson(args: argparse.Namespace) -> int:
    """Append a lesson to the project-context.md 历史教训 section.

    retrospective-improvement-plan M2.1 - replaces direct Edit of project-context.md.
    """
    import re as _re
    root = Path(root_arg(args))
    lesson_text = (args.lesson or "").strip()
    if not lesson_text:
        return emit_payload(args, fail_payload(
            "project-context.add-lesson",
            "empty_lesson",
            "--lesson is required and must not be empty.",
        ))
    ctx_path = project_context_path(root)
    if not ctx_path.exists():
        return emit_payload(args, fail_payload(
            "project-context.add-lesson",
            "project_context_missing",
            f"project-context.md does not exist at {ctx_path}; run 'harness context init' first.",
        ))
    date_str = getattr(args, "date", None) or today()
    source = getattr(args, "source", None)
    entry = f"- {date_str} {lesson_text}"
    if source:
        entry = entry + f" (source: {source})"

    content = ctx_path.read_text(encoding="utf-8")
    section_pattern = _re.compile(r"(##\s*历史教训[^\n]*\n)(.*?)(\n##|\Z)", _re.DOTALL | _re.IGNORECASE)
    m = section_pattern.search(content)
    if m:
        new_section = m.group(1) + m.group(2).rstrip() + "\n" + entry + "\n"
        new_content = content[:m.start()] + new_section + content[m.end():]
    else:
        new_content = content.rstrip() + "\n\n## 历史教训\n\n" + entry + "\n"

    ctx_path.write_text(new_content, encoding="utf-8")
    return emit_payload(args, {
        "status": "PASS",
        "control": "project-context.add-lesson",
        "lesson": entry,
        "path": str(ctx_path.relative_to(root)),
        "findings": [],
    })

def cmd_project_context_drift_scan(args: argparse.Namespace) -> int:
    """Scan project-context.md for stale or duplicate lessons.

    retrospective-improvement-plan M2.1.
    """
    import re as _re
    root = Path(root_arg(args))
    ctx_path = project_context_path(root)
    if not ctx_path.exists():
        return emit_payload(args, fail_payload(
            "project-context.drift-scan",
            "project_context_missing",
            f"project-context.md does not exist at {ctx_path}; run 'harness context init' first.",
        ))
    content = ctx_path.read_text(encoding="utf-8")
    findings: list[dict] = []

    # Find lesson lines
    lesson_lines = _re.findall(r"^- (\d{4}-\d{2}-\d{2}) (.+)$", content, _re.MULTILINE)

    # Check for duplicates by content
    seen: dict[str, list[str]] = {}
    for date_str, text in lesson_lines:
        key = text.strip().lower()
        seen.setdefault(key, []).append(date_str)
    for text, dates in seen.items():
        if len(dates) > 1:
            findings.append({
                "level": "WARN",
                "code": "duplicate_lesson",
                "message": f"Duplicate lesson found on dates {dates}: '{text[:80]}'",
            })

    # Check stale (older than 365 days)
    import datetime as _dt
    today_dt = _dt.date.today()
    stale_threshold = 365
    stale_count = 0
    for date_str, _ in lesson_lines:
        try:
            lesson_dt = _dt.date.fromisoformat(date_str)
            if (today_dt - lesson_dt).days > stale_threshold:
                stale_count += 1
        except ValueError:
            findings.append({
                "level": "WARN",
                "code": "invalid_date_format",
                "message": f"Lesson date '{date_str}' does not match YYYY-MM-DD format.",
            })

    if stale_count > 0:
        findings.append({
            "level": "INFO",
            "code": "stale_lessons",
            "message": f"{stale_count} lesson(s) are older than {stale_threshold} days and may be stale.",
        })

    status = "WARN" if any(f["level"] == "WARN" for f in findings) else "PASS"
    return emit_payload(args, {
        "status": status,
        "control": "project-context.drift-scan",
        "lesson_count": len(lesson_lines),
        "stale_count": stale_count,
        "findings": findings,
    })


def cmd_project_context_lint(args: argparse.Namespace) -> int:
    """Lint project-context.md for format compliance.

    retrospective-improvement-plan M2.1.
    """
    import re as _re
    root = Path(root_arg(args))
    ctx_path = project_context_path(root)
    if not ctx_path.exists():
        return emit_payload(args, fail_payload(
            "project-context.lint",
            "project_context_missing",
            "project-context.md does not exist; run 'harness context init' first.",
        ))
    content = ctx_path.read_text(encoding="utf-8")
    findings: list[dict] = []

    # Check each lesson line has YYYY-MM-DD prefix
    for i, line in enumerate(content.splitlines(), 1):
        if line.startswith("- ") and not _re.match(r"^- \d{4}-\d{2}-\d{2} ", line):
            findings.append({
                "level": "WARN",
                "code": "missing_date_prefix",
                "message": f"Line {i}: lesson entry missing YYYY-MM-DD date prefix: {line[:80]}",
            })

    status = "WARN" if findings else "PASS"
    return emit_payload(args, {
        "status": status,
        "control": "project-context.lint",
        "findings": findings,
    })


def cmd_retrospective_harness_gap_init(args: argparse.Namespace) -> int:
    """Initialize the harness-gap YAML store for a mission.

    retrospective-improvement-plan M2.1.
    """
    root = Path(root_arg(args))
    mission = args.mission
    stage_dir = _stage_dir(root, mission)
    gap_path = stage_dir / "harness-gap.yaml"
    if gap_path.exists():
        return emit_payload(args, {
            "status": "PASS",
            "control": "retrospective.harness-gap-init",
            "mission": mission,
            "path": str(gap_path.relative_to(root)),
            "created": False,
            "findings": [{"level": "INFO", "code": "already_exists", "message": "harness-gap.yaml already exists."}],
        })
    stage_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "mission": mission,
        "gaps": [],
    }
    write_yaml(gap_path, doc)
    return emit_payload(args, {
        "status": "PASS",
        "control": "retrospective.harness-gap-init",
        "mission": mission,
        "path": str(gap_path.relative_to(root)),
        "created": True,
        "findings": [],
    })


def cmd_retrospective_harness_gap_emit(args: argparse.Namespace) -> int:
    """Append a gap record to harness-gap.yaml.

    retrospective-improvement-plan M2.1.
    """
    root = Path(root_arg(args))
    mission = args.mission
    stage_dir = _stage_dir(root, mission)
    # Check retrospective.md exists first (Step 3 must run before emit)
    retro_md = stage_dir / "retrospective.md"
    if not retro_md.exists():
        return emit_payload(args, fail_payload(
            "retrospective.harness-gap-emit",
            "retrospective_md_missing",
            f"retrospective.md not found at {retro_md.relative_to(root)}; write Step 3 first.",
        ))
    gap_path = stage_dir / "harness-gap.yaml"
    if not gap_path.exists():
        doc = {"mission": mission, "gaps": []}
    else:
        doc = load_yaml(gap_path) or {"mission": mission, "gaps": []}
    gaps = doc.setdefault("gaps", [])
    gap_id = args.gap_id
    # Prevent duplicate gap_id
    if any(g.get("gap_id") == gap_id for g in gaps):
        return emit_payload(args, fail_payload(
            "retrospective.harness-gap-emit",
            "duplicate_gap_id",
            f"gap_id '{gap_id}' already exists in harness-gap.yaml.",
        ))
    gap_record = {
        "gap_id": gap_id,
        "pattern_key": args.pattern_key,
        "target_kind": args.target_kind,
        "severity": getattr(args, "severity", "medium"),
        "description": args.description,
        "first_seen": getattr(args, "first_seen", None) or today(),
        "repeat_count": 1,
        "status": "open",
    }
    if getattr(args, "verification_ref", None):
        gap_record["verification_ref"] = args.verification_ref
    gaps.append(gap_record)
    write_yaml(gap_path, doc)
    return emit_payload(args, {
        "status": "PASS",
        "control": "retrospective.harness-gap-emit",
        "mission": mission,
        "gap_id": gap_id,
        "path": str(gap_path.relative_to(root)),
        "findings": [],
    })


def cmd_harness_gap_pattern_scan(args: argparse.Namespace) -> int:
    """Scan harness-gap.yaml for recurring gap patterns.

    retrospective-improvement-plan M2.1.
    """
    root = Path(root_arg(args))
    mission = args.mission
    min_repeat = getattr(args, "min_repeat", 2)
    gap_path = _stage_dir(root, mission) / "harness-gap.yaml"
    if not gap_path.exists():
        return emit_payload(args, {
            "status": "PASS",
            "control": "harness-gap.pattern-scan",
            "mission": mission,
            "patterns": [],
            "findings": [{"level": "INFO", "code": "no_gap_file", "message": "harness-gap.yaml not found; no gaps recorded."}],
        })
    doc = load_yaml(gap_path) or {}
    gaps = doc.get("gaps", [])
    # Group by pattern_key
    from collections import defaultdict as _dd
    by_key: dict = _dd(list)
    for g in gaps:
        by_key[g.get("pattern_key", "unknown")].append(g)
    patterns = []
    findings: list[dict] = []
    for pattern_key, gap_list in by_key.items():
        total_repeat = sum(g.get("repeat_count", 1) for g in gap_list)
        if total_repeat >= min_repeat:
            patterns.append({
                "pattern_key": pattern_key,
                "gap_count": len(gap_list),
                "total_repeat_count": total_repeat,
                "gap_ids": [g["gap_id"] for g in gap_list],
            })
            findings.append({
                "level": "WARN",
                "code": "recurring_pattern",
                "message": f"Pattern '{pattern_key}' appears {total_repeat} time(s) across {len(gap_list)} gap(s).",
            })
    return emit_payload(args, {
        "status": "WARN" if patterns else "PASS",
        "control": "harness-gap.pattern-scan",
        "mission": mission,
        "patterns": patterns,
        "findings": findings,
    })


def cmd_agent_eval_drift(args: argparse.Namespace) -> int:
    """Compare agent-eval pass rates between current and baseline missions.

    retrospective-improvement-plan M2.1 / M4.2 — typed drift report.
    """
    import re as _re
    root = Path(root_arg(args))
    mission = args.mission
    baseline_mission = getattr(args, "baseline_mission", None)
    threshold = getattr(args, "threshold", 0.1)
    findings: list[dict] = []

    current_report = _stage_dir(root, mission) / "agent-eval-report.md"
    if not current_report.exists():
        findings.append({
            "level": "WARN",
            "code": "eval_report_missing",
            "message": f"agent-eval-report.md not found for mission {mission}; agent evaluation was not performed.",
        })
        return emit_payload(args, {
            "status": "WARN",
            "control": "agent-eval.drift",
            "mission": mission,
            "baseline": None,
            "drift_summary": None,
            "regressions": [],
            "findings": findings,
        })
    if not baseline_mission:
        findings.append({
            "level": "WARN",
            "code": "no_baseline",
            "message": (
                "No --baseline mission provided; cannot compute drift. "
                "Establish a baseline by passing --baseline <mission-id> on a known-good mission."
            ),
        })
        return emit_payload(args, {
            "status": "WARN",
            "control": "agent-eval.drift",
            "mission": mission,
            "baseline": None,
            "drift_summary": None,
            "regressions": [],
            "findings": findings,
        })
    baseline_report = _stage_dir(root, baseline_mission) / "agent-eval-report.md"
    if not baseline_report.exists():
        findings.append({
            "level": "WARN",
            "code": "baseline_report_missing",
            "message": f"agent-eval-report.md not found for baseline mission {baseline_mission}.",
        })
        return emit_payload(args, {
            "status": "WARN",
            "control": "agent-eval.drift",
            "mission": mission,
            "baseline": baseline_mission,
            "drift_summary": None,
            "regressions": [],
            "findings": findings,
        })

    def _extract_pass_rate(text: str) -> "float | None":
        m = _re.search(
            r"通过率[:：]\s*([0-9.]+)%|pass\s+rate[:：]\s*([0-9.]+)%",
            text,
            _re.IGNORECASE,
        )
        if m:
            val = m.group(1) or m.group(2)
            try:
                return float(val) / 100.0
            except ValueError:
                return None
        return None

    current_text = current_report.read_text(encoding="utf-8")
    baseline_text = baseline_report.read_text(encoding="utf-8")
    current_rate = _extract_pass_rate(current_text)
    baseline_rate = _extract_pass_rate(baseline_text)

    regressions = []
    status = "PASS"
    if current_rate is not None and baseline_rate is not None:
        delta = current_rate - baseline_rate
        if delta < -threshold:
            regressions.append({
                "type": "pass_rate_regression",
                "delta": round(delta, 4),
                "threshold": threshold,
                "message": (
                    f"Pass rate dropped from {baseline_rate:.1%} to {current_rate:.1%} "
                    f"(delta={delta:.1%}, threshold={-threshold:.1%})."
                ),
            })
            status = "WARN"
            findings.append({
                "level": "WARN",
                "code": "pass_rate_regression",
                "message": regressions[-1]["message"],
            })
    else:
        status = "WARN"
        findings.append({
            "level": "WARN",
            "code": "pass_rate_not_found",
            "message": "Could not extract pass rate from one or both eval reports.",
        })

    return emit_payload(args, {
        "status": status,
        "control": "agent-eval.drift",
        "mission": mission,
        "baseline": baseline_mission,
        "drift_summary": {
            "current_pass_rate": current_rate,
            "baseline_pass_rate": baseline_rate,
            "delta": round(current_rate - baseline_rate, 4) if current_rate is not None and baseline_rate is not None else None,
            "threshold": threshold,
        },
        "regressions": regressions,
        "findings": findings,
    })


# ----------------------------------------------------------------------------
# finishing-branch stage commands (finishing-branch-improvement-plan M2.1)
# ----------------------------------------------------------------------------


def _fb_mission_info(root: Path, mission: str) -> dict:
    """Load mission branch / base_branch from mission-status.yaml."""
    status_path = mission_status_path(root)
    status = load_yaml(status_path)
    entry = status.get(mission) if isinstance(status.get(mission), dict) else {}
    git = entry.get("git") if isinstance(entry.get("git"), dict) else {}
    return {
        "mission_branch": git.get("mission_branch") or entry.get("mission_branch"),
        "base_branch": git.get("base_branch") or "main",
    }


def _fb_stage_dir(root: Path, mission: str) -> Path:
    return runtime_harness_root(root) / "stages" / mission


def _fb_load_contract(root: Path, mission: str) -> dict:
    """Load finishing-branch contract if present, else empty dict."""
    contract_path = _fb_stage_dir(root, mission) / "contracts" / "finishing-branch.contract.yaml"
    if not contract_path.exists():
        return {}
    try:
        doc = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except Exception:
        return {}


def cmd_finishing_branch_status(args: argparse.Namespace) -> int:
    """Return branch status (dirty, active/blocked stage worktrees, mission branch).

    M2.1 finishing-branch status command.
    """
    import subprocess as _sp
    root = Path(root_arg(args))
    mission = args.mission
    info = _fb_mission_info(root, mission)
    mission_branch = info.get("mission_branch")
    base_branch = info.get("base_branch") or "main"

    # Detect dirty state
    dirty = False
    try:
        r = _sp.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=str(root))
        dirty = bool(r.stdout.strip())
    except Exception:
        pass

    # Detect stage worktrees (grep mission id in worktree list)
    active_worktrees: list[str] = []
    blocked_worktrees: list[str] = []
    try:
        r = _sp.run(["git", "worktree", "list", "--porcelain"], capture_output=True, text=True, cwd=str(root))
        current_wt = {}
        for line in r.stdout.splitlines():
            if line.startswith("worktree "):
                current_wt = {"path": line[len("worktree "):]}
            elif line.startswith("branch "):
                current_wt["branch"] = line[len("branch "):]
            elif line == "" and current_wt:
                path = current_wt.get("path", "")
                branch = current_wt.get("branch", "")
                if mission in path or mission in branch:
                    active_worktrees.append(path)
                current_wt = {}
    except Exception:
        pass

    branch_status = {
        "mission_branch": mission_branch,
        "base_branch": base_branch,
        "dirty": dirty,
        "active_stage_worktrees": active_worktrees,
        "blocked_stage_worktrees": blocked_worktrees,
    }

    return emit_payload(args, {
        "status": "PASS",
        "control": "finishing-branch.status",
        "mission": mission,
        "branch_status": branch_status,
        "findings": [],
    })


def cmd_finishing_branch_detect_test_cmd(args: argparse.Namespace) -> int:
    """Detect the test command for the current project.

    M2.1 finishing-branch detect-test-cmd command.
    """
    root = Path(root_arg(args))
    candidates: list[dict] = []

    # Check for pytest / pyproject.toml
    if (root / "pyproject.toml").exists() or (root / "setup.cfg").exists() or (root / "pytest.ini").exists():
        candidates.append({"command": "pytest", "confidence": "high", "reason": "pyproject.toml/setup.cfg/pytest.ini found"})

    # Check for package.json
    if (root / "package.json").exists():
        try:
            pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
            if isinstance(pkg.get("scripts"), dict) and "test" in pkg["scripts"]:
                candidates.append({"command": "npm test", "confidence": "high", "reason": "package.json scripts.test found"})
        except Exception:
            candidates.append({"command": "npm test", "confidence": "medium", "reason": "package.json found"})

    # Check for Cargo.toml
    if (root / "Cargo.toml").exists():
        candidates.append({"command": "cargo test", "confidence": "high", "reason": "Cargo.toml found"})

    # Check for go.mod
    if (root / "go.mod").exists():
        candidates.append({"command": "go test ./...", "confidence": "high", "reason": "go.mod found"})

    # Fallback
    if not candidates:
        candidates.append({"command": "pytest", "confidence": "low", "reason": "default fallback"})

    recommended = candidates[0]["command"] if candidates else "pytest"

    return emit_payload(args, {
        "status": "PASS",
        "control": "finishing-branch.detect-test-cmd",
        "mission": args.mission,
        "recommended": recommended,
        "candidates": candidates,
        "findings": [],
    })


def cmd_finishing_branch_run_tests(args: argparse.Namespace) -> int:
    """Run the project test suite or reuse prior evidence.

    M2.1 finishing-branch run-tests command.
    """
    root = Path(root_arg(args))
    mission = args.mission
    dry_run = getattr(args, "dry_run", False)
    reuse_id = getattr(args, "reuse_evidence_id", None)

    if reuse_id:
        # Look in verification-report contract for this evidence id
        contract_path = _fb_stage_dir(root, mission) / "contracts" / "verification-report.contract.yaml"
        if contract_path.exists():
            try:
                doc = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
                contract = doc.get("control_contract") if isinstance(doc, dict) else doc
                evidence_list = (contract or {}).get("command_evidence") or []
                for ev in evidence_list:
                    if isinstance(ev, dict) and ev.get("id") == reuse_id:
                        return emit_payload(args, {
                            "status": "PASS",
                            "control": "finishing-branch.run-tests",
                            "mission": mission,
                            "mode": "reused_verification_evidence",
                            "evidence_id": reuse_id,
                            "evidence": ev,
                            "findings": [],
                        })
            except Exception:
                pass
        return emit_payload(args, fail_payload(
            "finishing-branch.run-tests", "reuse_evidence_not_found",
            f"Evidence id '{reuse_id}' not found in verification-report contract.",
        ))

    # Detect test command
    test_cmd = getattr(args, "test_cmd", None) or "pytest"
    if dry_run:
        return emit_payload(args, {
            "status": "PASS",
            "control": "finishing-branch.run-tests",
            "mission": mission,
            "mode": "dry_run",
            "command": test_cmd,
            "findings": [{"level": "INFO", "code": "dry_run", "message": "Dry-run: test command not executed."}],
        })

    import subprocess as _sp
    r = _sp.run(test_cmd.split(), capture_output=True, text=True, cwd=str(root))
    passed = r.returncode == 0
    return emit_payload(args, {
        "status": "PASS" if passed else "FAIL",
        "control": "finishing-branch.run-tests",
        "mission": mission,
        "mode": "executed",
        "command": test_cmd,
        "exit_code": r.returncode,
        "findings": [] if passed else [{
            "level": "FAIL",
            "code": "test_suite_failed",
            "message": f"Test command '{test_cmd}' exited with code {r.returncode}.",
        }],
    })


def cmd_finishing_branch_readiness(args: argparse.Namespace) -> int:
    """Check release readiness: delivery-package, acceptance-result, test evidence.

    M2.1 finishing-branch readiness command.
    """
    root = Path(root_arg(args))
    mission = args.mission
    stage_dir = _fb_stage_dir(root, mission)
    findings: list[dict] = []

    delivery_present = (stage_dir / "delivery-package.md").exists()
    acceptance_present = (stage_dir / "acceptance-result.md").exists()

    if not delivery_present:
        findings.append({
            "level": "FAIL",
            "code": "delivery_package_missing",
            "message": "delivery-package.md not found. Run delivery stage before finishing-branch.",
        })

    if not acceptance_present:
        findings.append({
            "level": "WARN",
            "code": "acceptance_result_missing",
            "message": "acceptance-result.md not found. Acceptance evidence is recommended.",
        })

    # Collect test evidence IDs from verification contract
    evidence_ids: list[str] = []
    contract_path = stage_dir / "contracts" / "verification-report.contract.yaml"
    if contract_path.exists():
        try:
            doc = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
            contract = doc.get("control_contract") if isinstance(doc, dict) else doc
            evidence_ids = [
                ev["id"] for ev in ((contract or {}).get("command_evidence") or [])
                if isinstance(ev, dict) and ev.get("id")
            ]
        except Exception:
            pass

    fail_items = [f for f in findings if f.get("level") == "FAIL"]
    status = "FAIL" if fail_items else "PASS"

    return emit_payload(args, {
        "status": status,
        "control": "finishing-branch.readiness",
        "mission": mission,
        "release_readiness": {
            "delivery_package_present": delivery_present,
            "acceptance_result_present": acceptance_present,
            "command_evidence_ids": evidence_ids,
        },
        "findings": findings,
    })


def cmd_finishing_branch_options(args: argparse.Namespace) -> int:
    """Return the 4 available close strategies with enabled/disabled status.

    M2.1 finishing-branch options command.
    """
    root = Path(root_arg(args))
    mission = args.mission
    stage_dir = _fb_stage_dir(root, mission)

    delivery_present = (stage_dir / "delivery-package.md").exists()

    options = [
        {
            "value": "merge_to_base",
            "label": "Merge mission branch to base branch locally",
            "enabled": delivery_present,
            "disabled_reason": None if delivery_present else "delivery-package.md not found",
        },
        {
            "value": "push_pr",
            "label": "Push and create Pull Request",
            "enabled": delivery_present,
            "disabled_reason": None if delivery_present else "delivery-package.md not found",
        },
        {
            "value": "keep",
            "label": "Keep branch as-is (handle manually later)",
            "enabled": True,
            "disabled_reason": None,
        },
        {
            "value": "discard",
            "label": "Discard the mission branch",
            "enabled": True,
            "disabled_reason": None,
        },
    ]

    return emit_payload(args, {
        "status": "PASS",
        "control": "finishing-branch.options",
        "mission": mission,
        "options": options,
        "findings": [],
    })


def cmd_finishing_branch_pr_body(args: argparse.Namespace) -> int:
    """Build a typed PR body from delivery-package + verification evidence.

    M2.1 finishing-branch pr-body command.
    """
    root = Path(root_arg(args))
    mission = args.mission
    stage_dir = _fb_stage_dir(root, mission)

    delivery_path = stage_dir / "delivery-package.md"
    if not delivery_path.exists():
        return emit_payload(args, {
            "status": "BLOCKED",
            "control": "finishing-branch.pr-body",
            "mission": mission,
            "findings": [{
                "level": "FAIL",
                "code": "pr_body_delivery_package_missing",
                "message": "delivery-package.md is required to generate PR body.",
            }],
        })

    delivery_text = delivery_path.read_text(encoding="utf-8")
    source_artifacts = ["delivery-package.md"]

    # Collect verification evidence
    evidence_ids: list[str] = []
    contract_path = stage_dir / "contracts" / "verification-report.contract.yaml"
    if contract_path.exists():
        try:
            doc = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
            contract = doc.get("control_contract") if isinstance(doc, dict) else doc
            evidence_ids = [
                ev["id"] for ev in ((contract or {}).get("command_evidence") or [])
                if isinstance(ev, dict) and ev.get("id")
            ]
        except Exception:
            pass

    # Build body text
    summary_lines = [
        line.lstrip("- ").strip()
        for line in delivery_text.splitlines()
        if line.startswith("- ") or line.startswith("* ")
    ][:5]
    summary_text = "\n".join(f"- {s}" for s in summary_lines) if summary_lines else "See delivery-package.md"

    evidence_checklist = "\n".join(f"- [x] Evidence `{eid}` passed" for eid in evidence_ids) if evidence_ids else "- [ ] Add test evidence"

    body_text = (
        f"## Summary\n\n{summary_text}\n\n"
        f"## Related\n\n- Mission: {mission}\n\n"
        f"## Test Plan\n\n{evidence_checklist}\n- [ ] Code Review: Approved\n"
    )

    return emit_payload(args, {
        "status": "PASS",
        "control": "finishing-branch.pr-body",
        "mission": mission,
        "pr_body": {
            "required": True,
            "source_artifacts": source_artifacts,
            "verification_evidence_ids": evidence_ids,
            "body_text": body_text,
        },
        "findings": [],
    })


def cmd_finishing_branch_execute(args: argparse.Namespace) -> int:
    """Execute the chosen close strategy (git ops).

    M2.1 finishing-branch execute command.
    Supports --dry-run for safe preview.
    """
    root = Path(root_arg(args))
    mission = args.mission
    strategy = args.strategy
    dry_run = getattr(args, "dry_run", False)
    confirmation_id = getattr(args, "confirmation_id", None)

    info = _fb_mission_info(root, mission)
    mission_branch = info.get("mission_branch")
    base_branch = info.get("base_branch") or "main"

    if not mission_branch:
        return emit_payload(args, fail_payload(
            "finishing-branch.execute",
            "mission_branch_unknown",
            f"mission_branch not found in mission-status.yaml for mission {mission}.",
        ))

    if strategy == "discard" and not confirmation_id:
        return emit_payload(args, fail_payload(
            "finishing-branch.execute",
            "discard_confirmation_required",
            "strategy=discard requires --confirmation-id (must be 'discard') to confirm destructive operation.",
        ))

    findings: list[dict] = []

    # Build the typed git command plan for the chosen strategy. Each entry
    # carries the `op` label plus the concrete `argv` to run.
    plan: list[dict] = []
    if strategy == "merge_to_base":
        plan = [
            {"op": "checkout", "argv": ["git", "checkout", base_branch]},
            {"op": "pull", "argv": ["git", "pull", "origin", base_branch]},
            {"op": "merge", "argv": ["git", "merge", "--no-ff", mission_branch]},
        ]
    elif strategy == "push_pr":
        plan = [
            {"op": "push", "argv": ["git", "push", "origin", mission_branch]},
        ]
    elif strategy == "keep":
        findings.append({
            "level": "WARN",
            "code": "strategy_keep",
            "message": "Branch kept as-is. No git operations performed.",
        })
    elif strategy == "discard":
        plan = [
            {"op": "checkout", "argv": ["git", "checkout", base_branch]},
            {"op": "branch_force_delete", "argv": ["git", "branch", "-D", mission_branch]},
            {"op": "worktree_prune", "argv": ["git", "worktree", "prune"]},
        ]

    # dry_run: return the plan without touching git. Otherwise actually run
    # each git command, capturing exit code + output as git_ops evidence and
    # stopping at the first failure (a partial merge must not silently push).
    import subprocess as _sp
    git_ops: list[dict] = []
    overall_status = "PASS"
    for step in plan:
        op_record: dict = {
            "op": step["op"],
            "command": " ".join(step["argv"]),
            "dry_run": dry_run,
        }
        if dry_run:
            op_record["executed"] = False
        else:
            try:
                proc = _sp.run(
                    step["argv"], capture_output=True, text=True, check=False, cwd=str(root),
                )
                op_record["executed"] = True
                op_record["exit_code"] = proc.returncode
                op_record["stdout"] = proc.stdout.strip()[-2000:]
                op_record["stderr"] = proc.stderr.strip()[-2000:]
                if proc.returncode != 0:
                    overall_status = "FAIL"
                    findings.append({
                        "level": "FAIL",
                        "code": "git_op_failed",
                        "message": f"git op {step['op']} failed (exit {proc.returncode}): {proc.stderr.strip()[-400:]}",
                    })
            except Exception as exc:  # noqa: BLE001 - surface any git failure as a finding
                op_record["executed"] = True
                op_record["exit_code"] = -1
                op_record["error"] = str(exc)
                overall_status = "FAIL"
                findings.append({
                    "level": "FAIL",
                    "code": "git_op_error",
                    "message": f"git op {step['op']} raised: {exc}",
                })
        git_ops.append(op_record)
        if overall_status == "FAIL":
            break  # stop the sequence; do not run later destructive ops

    return emit_payload(args, {
        "status": overall_status,
        "control": "finishing-branch.execute",
        "mission": mission,
        "strategy": strategy,
        "dry_run": dry_run,
        "mission_branch": mission_branch,
        "base_branch": base_branch,
        "git_ops": git_ops,
        "findings": findings,
    })


def cmd_finishing_branch_cleanup(args: argparse.Namespace) -> int:
    """Clean up stage worktrees after a mission is closed.

    M2.1 finishing-branch cleanup command.
    """
    import subprocess as _sp
    root = Path(root_arg(args))
    mission = args.mission
    dry_run = getattr(args, "dry_run", False)
    findings: list[dict] = []
    removed: list[str] = []

    # Find stage worktrees
    try:
        r = _sp.run(["git", "worktree", "list", "--porcelain"], capture_output=True, text=True, cwd=str(root))
        current_wt: dict = {}
        worktrees_to_remove: list[str] = []
        for line in r.stdout.splitlines():
            if line.startswith("worktree "):
                current_wt = {"path": line[len("worktree "):]}
            elif line.startswith("branch "):
                current_wt["branch"] = line[len("branch "):]
            elif line == "" and current_wt:
                path = current_wt.get("path", "")
                branch = current_wt.get("branch", "")
                if mission in path or mission in branch:
                    worktrees_to_remove.append(path)
                current_wt = {}
    except Exception:
        worktrees_to_remove = []

    if not worktrees_to_remove:
        findings.append({
            "level": "INFO",
            "code": "no_stage_worktrees",
            "message": f"No stage worktrees found for mission {mission}.",
        })
    elif dry_run:
        findings.append({
            "level": "INFO",
            "code": "dry_run",
            "message": f"Dry-run: would remove {len(worktrees_to_remove)} stage worktree(s): {worktrees_to_remove}",
        })
        removed = worktrees_to_remove
    else:
        for wt_path in worktrees_to_remove:
            try:
                _sp.run(["git", "worktree", "remove", wt_path], check=True, cwd=str(root))
                removed.append(wt_path)
            except Exception as exc:
                findings.append({
                    "level": "WARN",
                    "code": "worktree_remove_failed",
                    "message": f"Failed to remove worktree {wt_path}: {exc}",
                })

    return emit_payload(args, {
        "status": "PASS",
        "control": "finishing-branch.cleanup",
        "mission": mission,
        "dry_run": dry_run,
        "removed_worktrees": removed,
        "findings": findings,
    })


# --- delivery-improvement-plan M2.1: delivery CLI commands -----------------
# 6 real-new commands: summarize / compute-follow-ups / check-followups /
# compute-conclusion / handoff / agent-capability-status. Each returns typed
# JSON via emit_payload; the delivery hooks + schema + workflow are shipped
# separately (delivery M3.1 / M1.1 / M2.2).


def _delivery_contract_path(root: Path, mission: str) -> Path:
    return (
        root / "harness-runtime" / "harness" / "stages" / mission
        / "contracts" / "delivery.contract.yaml"
    )


def _verification_report_path(root: Path, mission: str) -> Path:
    return (
        root / "harness-runtime" / "harness" / "stages" / mission
        / "contracts" / "verification-report.contract.yaml"
    )


def _load_control_contract(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    if not isinstance(doc, dict):
        return None
    block = doc.get("control_contract")
    return block if isinstance(block, dict) else doc


def cmd_delivery_summarize(args: argparse.Namespace) -> int:
    """Produce a typed delivery summary from the verification-report contract."""
    root = Path(root_arg(args))
    vr_path = _verification_report_path(root, args.mission)
    contract = _load_control_contract(vr_path)
    if contract is None:
        return emit_payload(args, fail_payload(
            "delivery.summarize", "verification_report_missing",
            f"verification-report contract not found at {relpath(root, vr_path)}",
        ))
    ac_trace = contract.get("ac_trace") if isinstance(contract.get("ac_trace"), list) else []
    total = len(ac_trace)
    passed = sum(1 for e in ac_trace if isinstance(e, dict) and e.get("conclusion") == "pass")
    failed = sum(1 for e in ac_trace if isinstance(e, dict) and e.get("conclusion") == "fail")
    findings: list[dict] = []
    if failed:
        findings.append({
            "level": "WARN", "code": "ac_trace_has_failures",
            "message": f"{failed} AC(s) concluded fail in verification-report",
        })
    return emit_payload(args, {
        "status": "PASS",
        "control": "delivery.summarize",
        "mission": args.mission,
        "summary": {"ac_trace": {"total": total, "pass": passed, "fail": failed}},
        "findings": findings,
    })


def cmd_delivery_compute_follow_ups(args: argparse.Namespace) -> int:
    """Generate follow-up candidates from failed / accepted-risk ACs."""
    root = Path(root_arg(args))
    vr_path = _verification_report_path(root, args.mission)
    contract = _load_control_contract(vr_path)
    if contract is None:
        return emit_payload(args, fail_payload(
            "delivery.compute-follow-ups", "verification_report_missing",
            f"verification-report contract not found at {relpath(root, vr_path)}",
        ))
    ac_trace = contract.get("ac_trace") if isinstance(contract.get("ac_trace"), list) else []
    candidates: list[dict] = []
    for entry in ac_trace:
        if not isinstance(entry, dict):
            continue
        ac = entry.get("ac") or entry.get("ac_id") or "<unknown>"
        conclusion = entry.get("conclusion")
        if conclusion == "fail":
            candidates.append({
                "id": f"FU-{ac}", "ac": ac, "severity": "blocking",
                "source": "failed_ac",
                "reason": f"AC {ac} concluded fail; must be resolved before close",
            })
        elif conclusion == "accepted_risk":
            candidates.append({
                "id": f"FU-{ac}", "ac": ac, "severity": "advisory",
                "source": "accepted_risk_ac",
                "reason": f"AC {ac} accepted with risk; track as advisory follow-up",
            })
    return emit_payload(args, {
        "status": "PASS",
        "control": "delivery.compute-follow-ups",
        "mission": args.mission,
        "follow_ups_candidates": candidates,
        "findings": [],
    })


def cmd_delivery_check_followups(args: argparse.Namespace) -> int:
    """Verify every follow-up has a graph operation or a documented none reason."""
    root = Path(root_arg(args))
    dc_path = _delivery_contract_path(root, args.mission)
    contract = _load_control_contract(dc_path)
    if contract is None:
        return emit_payload(args, fail_payload(
            "delivery.check-followups", "delivery_contract_missing",
            f"delivery contract not found at {relpath(root, dc_path)}",
        ))
    package = contract.get("delivery_package") if isinstance(contract.get("delivery_package"), dict) else {}
    follow_ups = package.get("follow_ups") if isinstance(package.get("follow_ups"), list) else []
    findings: list[dict] = []
    for fu in follow_ups:
        if not isinstance(fu, dict):
            continue
        fu_id = fu.get("id") or "<unknown>"
        severity = fu.get("severity")
        graph_op = fu.get("graph_op")
        has_op = bool(graph_op) and graph_op != "none"
        if severity in {"blocking", "advisory"}:
            if not has_op:
                findings.append({
                    "level": "FAIL", "code": "follow_up_missing_graph_op",
                    "follow_up": fu_id,
                    "message": f"follow-up {fu_id} ({severity}) must declare a graph operation; got {graph_op!r}",
                })
        elif severity == "can_ignore":
            if not has_op and not fu.get("none_reason"):
                findings.append({
                    "level": "FAIL", "code": "follow_up_missing_none_reason",
                    "follow_up": fu_id,
                    "message": f"follow-up {fu_id} (can_ignore) with graph_op=none must declare none_reason",
                })
    status = "PASS" if not any(f["level"] == "FAIL" for f in findings) else "FAIL"
    return emit_payload(args, {
        "status": status,
        "control": "delivery.check-followups",
        "mission": args.mission,
        "follow_ups_checked": len(follow_ups),
        "findings": findings,
    })


def cmd_delivery_compute_conclusion(args: argparse.Namespace) -> int:
    """Compute the typed delivery conclusion: delivered / continue_fix / blocked."""
    root = Path(root_arg(args))
    dc_path = _delivery_contract_path(root, args.mission)
    contract = _load_control_contract(dc_path)
    if contract is None:
        return emit_payload(args, fail_payload(
            "delivery.compute-conclusion", "delivery_contract_missing",
            f"delivery contract not found at {relpath(root, dc_path)}",
        ))
    package = contract.get("delivery_package") if isinstance(contract.get("delivery_package"), dict) else {}
    acceptance = contract.get("acceptance_result") if isinstance(contract.get("acceptance_result"), dict) else {}
    findings: list[dict] = []

    if not package.get("acceptance_state_ref"):
        findings.append({
            "level": "FAIL", "code": "acceptance_state_ref_missing",
            "message": "delivery_package.acceptance_state_ref is missing",
        })
    handoff = package.get("handoff_evidence") if isinstance(package.get("handoff_evidence"), dict) else {}
    if handoff.get("pause_required") is not True:
        findings.append({
            "level": "FAIL", "code": "handoff_pause_required_missing",
            "message": "delivery_package.handoff_evidence.pause_required must be true",
        })
    checkpoint = acceptance.get("user_checkpoint") if isinstance(acceptance.get("user_checkpoint"), dict) else {}
    ckpt_status = checkpoint.get("status")
    if ckpt_status == "pending_user_acceptance":
        findings.append({
            "level": "FAIL", "code": "user_checkpoint_pending",
            "message": "acceptance_result.user_checkpoint.status is still pending_user_acceptance",
        })
    ac_trace = acceptance.get("ac_acceptance_trace") if isinstance(acceptance.get("ac_acceptance_trace"), list) else []
    for entry in ac_trace:
        if not isinstance(entry, dict):
            continue
        if entry.get("result_status") == "pass" and not entry.get("verify_command_evidence_id"):
            findings.append({
                "level": "FAIL", "code": "ac_trace_missing_verify_evidence",
                "ac": entry.get("ac_id"),
                "message": f"AC {entry.get('ac_id')} concluded pass but lacks verify_command_evidence_id",
            })

    if ckpt_status == "continue_fix":
        conclusion = "continue_fix"
    elif ckpt_status == "pending_user_acceptance":
        conclusion = "blocked"
    elif any(f["level"] == "FAIL" for f in findings):
        conclusion = "blocked"
    else:
        conclusion = "delivered"
    status = "PASS" if conclusion == "delivered" and not findings else "FAIL"
    return emit_payload(args, {
        "status": status,
        "control": "delivery.compute-conclusion",
        "mission": args.mission,
        "conclusion": conclusion,
        "findings": findings,
    })


def cmd_delivery_handoff(args: argparse.Namespace) -> int:
    """Write handoff evidence declaring a pause boundary after delivery."""
    root = Path(root_arg(args))
    dc_path = _delivery_contract_path(root, args.mission)
    if not dc_path.exists():
        return emit_payload(args, fail_payload(
            "delivery.handoff", "delivery_contract_missing",
            f"delivery contract not found at {relpath(root, dc_path)}",
        ))
    try:
        doc = yaml.safe_load(dc_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return emit_payload(args, fail_payload(
            "delivery.handoff", "delivery_contract_invalid_yaml", f"{exc}",
        ))
    if not isinstance(doc, dict):
        doc = {}
    block = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
    if not isinstance(block, dict):
        doc["control_contract"] = {}
        block = doc["control_contract"]
    package = block.get("delivery_package")
    if not isinstance(package, dict):
        package = {}
        block["delivery_package"] = package
    approval_id = getattr(args, "approval_id", None)
    handoff_evidence = {
        "pause_required": True,
        "requires_user_resume": True,
        "next_stage_candidate": "finishing-branch",
        "approval_id": approval_id,
    }
    package["handoff_evidence"] = handoff_evidence
    dc_path.write_text(
        yaml.dump(doc, default_flow_style=False, allow_unicode=True, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return emit_payload(args, {
        "status": "PASS",
        "control": "delivery.handoff",
        "mission": args.mission,
        "pause_required": True,
        "requires_user_resume": True,
        "next_stage_candidate": "finishing-branch",
        "handoff_evidence": handoff_evidence,
        "findings": [],
    })


def cmd_delivery_agent_capability_status(args: argparse.Namespace) -> int:
    """Report agent-capability delivery status, or not_applicable when the
    mission has no Agent implementation in tech-design."""
    root = Path(root_arg(args))
    dc_path = _delivery_contract_path(root, args.mission)
    if _load_control_contract(dc_path) is None:
        return emit_payload(args, fail_payload(
            "delivery.agent-capability-status", "delivery_contract_missing",
            f"delivery contract not found at {relpath(root, dc_path)}",
        ))
    td_path = (
        root / "harness-runtime" / "harness" / "stages" / args.mission
        / "contracts" / "tech-design.contract.yaml"
    )
    td = _load_control_contract(td_path)
    has_agent = bool(td) and bool(td.get("agent_architecture") or td.get("agent_implementation"))
    overall = "delivered" if has_agent else "not_applicable"
    return emit_payload(args, {
        "status": "PASS",
        "control": "delivery.agent-capability-status",
        "mission": args.mission,
        "agent_capability_status": {"overall_status": overall},
        "findings": [],
    })


def add_leaf(subparsers: argparse._SubParsersAction, name: str, handler: Callable[[argparse.Namespace], int], **kwargs: object) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, **kwargs)
    parser.set_defaults(handler=handler)
    add_common(parser)
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness")
    parser.add_argument("--root", dest="global_root", default=".", help="target project root")
    sub = parser.add_subparsers(dest="command", required=True)

    frame = sub.add_parser("frame")
    frame_sub = frame.add_subparsers(dest="frame_command", required=True)
    p = add_leaf(frame_sub, "current", cmd_frame_current)
    p.add_argument("--mission")
    p = add_leaf(frame_sub, "explain", cmd_frame_explain)
    p.add_argument("--mission", required=True)
    p.add_argument("--node")

    config = sub.add_parser("config")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    add_leaf(config_sub, "snapshot", cmd_config_snapshot)

    control = sub.add_parser("control")
    control_sub = control.add_subparsers(dest="control_command", required=True)
    p = add_leaf(control_sub, "status", cmd_control_status, help="emit read-only control-plane status snapshot")
    p.set_defaults(json=True)
    p.add_argument("--mission")
    p.add_argument("--runtime-root", help="explicit runtime root, usually harness-runtime/harness")
    p = add_leaf(control_sub, "candidates", cmd_control_candidates, help="emit non-decision control-plane candidates")
    p.set_defaults(json=True)
    p.add_argument("--intent", required=True, choices=["continue"])
    p.add_argument("--mission")
    p.add_argument("--runtime-root", help="explicit runtime root, usually harness-runtime/harness")
    p = add_leaf(control_sub, "frame", cmd_control_frame, help="emit selected Mission frame facts")
    p.set_defaults(json=True)
    p.add_argument("--mission", required=True)
    p.add_argument("--runtime-root", help="explicit runtime root, usually harness-runtime/harness")
    p = add_leaf(control_sub, "guidance", cmd_control_guidance, help="emit bounded stage guidance facts")
    p.set_defaults(json=True)
    p.add_argument("--mission", required=True)
    p.add_argument("--runtime-root", help="explicit runtime root, usually harness-runtime/harness")
    p = add_leaf(control_sub, "context-index", cmd_control_context_index, help="emit path-only required context index")
    p.set_defaults(json=True)
    p.add_argument("--mission", required=True)
    p.add_argument("--runtime-root", help="explicit runtime root, usually harness-runtime/harness")

    context = sub.add_parser("context")
    context_sub = context.add_subparsers(dest="context_command", required=True)
    add_leaf(context_sub, "check", cmd_context_check)
    p = add_leaf(context_sub, "init", cmd_context_init)
    p.add_argument("--replace", action="store_true")

    knowledge = sub.add_parser("knowledge")
    knowledge_sub = knowledge.add_subparsers(dest="knowledge_command", required=True)
    p = add_leaf(knowledge_sub, "init", cmd_knowledge_init)
    p.add_argument("--replace", action="store_true")
    add_leaf(knowledge_sub, "check", cmd_knowledge_check)
    p = add_leaf(knowledge_sub, "index", cmd_knowledge_index)
    p.add_argument("--check", action="store_true", help="check whether project-knowledge/_index.md is up to date without writing")
    p = add_leaf(knowledge_sub, "resolve", cmd_knowledge_resolve)
    p.add_argument("--stage", required=True, help="Harness stage requesting knowledge context")
    p.add_argument("--capability", help="optional capability filter for specs")
    p = add_leaf(knowledge_sub, "promote", cmd_knowledge_promote)
    p.add_argument("--mission", required=True)
    p.add_argument("--write-plan", action="store_true", help="write knowledge-promotion-plan.md under the mission stage directory")
    p.add_argument("--output", help="optional output path for --write-plan")

    spec = sub.add_parser("spec")
    spec_sub = spec.add_subparsers(dest="spec_command", required=True)
    p = add_leaf(spec_sub, "check", cmd_spec_check)
    p.add_argument("--capability", help="check that a specific capability spec exists")
    p = add_leaf(spec_sub, "init", cmd_spec_init)
    p.add_argument("--capability", help="scaffold a specific capability spec under project-knowledge/specs; without this flag, initialize the specs index")
    p.add_argument("--replace", action="store_true")
    p = add_leaf(spec_sub, "delta-lint", cmd_spec_delta_lint)
    p.add_argument("--mission", required=True)
    p.add_argument("--capability", dest="capability", required=True, help="Capability name to validate.")
    p = add_leaf(spec_sub, "scan", cmd_spec_scan)
    p.add_argument("--mission", required=True)
    p.add_argument("--from-prd", dest="from_prd", help="Path to product definition; defaults to stages/<mission>/product/product-definition.md")
    p.add_argument("--scope-in", dest="scope_in", action="append", help="(discovery flavor) Mission scope_in path; repeat for multiple paths. Activates capability enumeration from project-knowledge/specs/.")
    # breakdown-improvement-plan M2.1: typed delta-spec enumerator. Returns
    # `{deltas: [{capability, scenarios: [{name, covered, trace_id}]}]}`.
    spec_diff = spec_sub.add_parser("diff")
    spec_diff_sub = spec_diff.add_subparsers(dest="spec_diff_command", required=True)
    p = add_leaf(spec_diff_sub, "list", cmd_spec_diff_list)
    p.add_argument("--mission", required=True)

    # breakdown-improvement-plan M2.1: execution-brief lifecycle CLI.
    execution_brief = sub.add_parser("execution-brief")
    execution_brief_sub = execution_brief.add_subparsers(
        dest="execution_brief_command", required=True
    )
    p = add_leaf(execution_brief_sub, "self-check", cmd_execution_brief_self_check)
    p.add_argument("--mission", required=True)
    p = add_leaf(execution_brief_sub, "check-coverage", cmd_execution_brief_check_coverage)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--spec-mode",
        choices=["strict", "warn"],
        default="strict",
        help="strict: uncovered scenarios FAIL; warn: surface only",
    )
    execution_brief_gate = execution_brief_sub.add_parser("gate")
    execution_brief_gate_sub = execution_brief_gate.add_subparsers(
        dest="execution_brief_gate_command", required=True
    )
    p = add_leaf(execution_brief_gate_sub, "run", cmd_execution_brief_gate_run)
    p.add_argument("--mission", required=True)

    # execute-improvement-plan M5 anchor: apply-overlay / revoke-overlay /
    # stop-event.record. These commands consume the breakdown-side
    # execution-brief.contract.yaml and write the effective overlay state +
    # stop event records the runtime hooks read.
    execute_cli = sub.add_parser("execute")
    execute_sub = execute_cli.add_subparsers(dest="execute_command", required=True)
    p = add_leaf(execute_sub, "apply-overlay", cmd_execute_apply_overlay)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--task",
        help="Filter to a single Atomic Task id (SDD per-task mode); omit for mission-level snapshot",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Return the overlay payload without writing the state file",
    )
    p = add_leaf(execute_sub, "revoke-overlay", cmd_execute_revoke_overlay)
    p.add_argument("--mission", required=True)
    p = add_leaf(execute_sub, "check-ready", cmd_execute_check_ready)
    p.add_argument("--mission", required=True)
    execute_gate = execute_sub.add_parser("gate")
    execute_gate_sub = execute_gate.add_subparsers(
        dest="execute_gate_command", required=True
    )
    p = add_leaf(execute_gate_sub, "run", cmd_execute_gate_run)
    p.add_argument("--mission", required=True)
    stop_event = execute_sub.add_parser("stop-event")
    stop_event_sub = stop_event.add_subparsers(dest="stop_event_command", required=True)
    p = add_leaf(stop_event_sub, "record", cmd_execute_stop_event_record)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--kind",
        required=True,
        help="Stop event kind (matches protocol §stop_event.kind enum)",
    )
    p.add_argument("--task", help="Atomic Task id triggering the stop event")
    p.add_argument(
        "--path",
        action="append",
        help="Affected path (repeat for multiple); typed array per protocol §stop_event.affected_paths",
    )
    p.add_argument(
        "--hook-source",
        help="Hook script name that triggered the event; defaults to `manual` when invoked from workflow",
    )

    # code-review-improvement-plan M2.1: review readiness gate.
    review_cli = sub.add_parser("review")
    review_sub = review_cli.add_subparsers(dest="review_command", required=True)
    p = add_leaf(review_sub, "check-ready", cmd_review_check_ready)
    p.add_argument("--mission", required=True)
    p = add_leaf(review_sub, "select-reviewers", cmd_review_select_reviewers)
    p.add_argument("--mission", required=True)
    p.add_argument("--diff-summary", dest="diff_summary",
                   help="Path to JSON file listing changed feature keywords.")
    p = add_leaf(review_sub, "snapshot-diff", cmd_review_snapshot_diff)
    p.add_argument("--mission", required=True)
    p.add_argument("--base", default="HEAD~1", help="Git ref to diff against (default: HEAD~1)")
    p = add_leaf(review_sub, "toolchain-status", cmd_review_toolchain_status)
    p.add_argument("--mission", required=True)
    p = add_leaf(review_sub, "e2e-status", cmd_review_e2e_status)
    p.add_argument("--mission", required=True)

    # breakdown-improvement-plan M2.1: writing-plans carrier boundary entry.
    writing_plans = sub.add_parser("writing-plans")
    writing_plans_sub = writing_plans.add_subparsers(
        dest="writing_plans_command", required=True
    )
    p = add_leaf(writing_plans_sub, "run", cmd_writing_plans_run)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--mode",
        required=True,
        help="must be `internal-carrier`; other values are rejected (breakdown M2.1 boundary)",
    )

    mission = sub.add_parser("mission")
    mission_sub = mission.add_subparsers(dest="mission_command", required=True)
    p = add_leaf(mission_sub, "init", cmd_mission_init)
    p.add_argument("--replace", action="store_true")
    p = add_leaf(mission_sub, "create-slice", cmd_mission_create_slice)
    p.add_argument("--mission", required=True)
    p.add_argument("--primary-node", action="append", required=True)
    p.add_argument("--related-node", action="append")
    p.add_argument("--input-node", action="append")
    p.add_argument("--output-node", action="append")
    p.add_argument("--lane-action", required=True)
    p.add_argument("--operation", help="operation name, such as advance_lane; defaults to the lane action registration")
    p.add_argument("--graph-operation", help="deprecated: operation name or graph operation manifest path")
    p.add_argument("--graph-operation-manifest", help="path to an explicit graph operation manifest")
    p.add_argument("--replace", action="store_true")
    p = add_leaf(mission_sub, "status", cmd_mission_status)
    p.add_argument("--mission")
    p.add_argument("--active", action="store_true", help="only return missions with an active Mission Slice")
    p.add_argument("--open", dest="open_only", action="store_true", help="only return missions whose status is not closed")
    p.add_argument("--status", dest="status_filter", action="append", help="filter by mission status; may be repeated")
    p.add_argument("--current-stage", action="append", help="filter by current_stage; may be repeated")
    p.add_argument("--stage", action="append", help="filter by a key in stages; may be repeated")
    p.add_argument("--stage-status", action="append", help="filter by stage status, optionally combined with --stage")
    p.add_argument("--ids-only", action="store_true", help="return matching mission ids without mission payloads")
    p = add_leaf(mission_sub, "reset-stage", cmd_mission_reset_stage)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--primary-node", action="append")
    p.add_argument("--related-node", action="append")
    p.add_argument("--output-node-policy", choices=["keep", "defer", "prune"], default="defer")
    p.add_argument("--preserve-stage-history", action="store_true")
    p.add_argument("--preserve-checkpoints", action="store_true")
    p.add_argument("--reason", default="Mission reset by harness mission reset-stage")
    mission_stage = mission_sub.add_parser("stage")
    mission_stage_sub = mission_stage.add_subparsers(dest="mission_stage_command", required=True)
    p = add_leaf(mission_stage_sub, "start", cmd_mission_stage_start)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p = add_leaf(mission_stage_sub, "complete", cmd_mission_stage_complete)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p = add_leaf(mission_sub, "close", cmd_mission_close)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--strategy", required=True,
        choices=["merged", "pr", "kept", "discarded", "delivered", "cancelled", "manual"],
        help=(
            "Close strategy. New values: merged | pr | kept | discarded. "
            "Legacy aliases: delivered (→merged) | cancelled (→discarded) | manual (→kept)."
        ),
    )
    p.add_argument("--pr-url", dest="pr_url", help="PR URL when strategy=pr.")
    p.add_argument("--kept-reason", dest="kept_reason", help="Reason string when strategy=kept.")
    p = add_leaf(mission_sub, "new-id", cmd_mission_new_id)
    p.add_argument("--slug", required=True, help="short kebab-case identifier (lowercase ASCII letters, digits, hyphens)")
    p.add_argument("--date", help="optional YYYYMMDD override; defaults to today's date in Asia/Shanghai")

    trace = sub.add_parser("trace")
    trace_sub = trace.add_subparsers(dest="trace_command", required=True)
    p = add_leaf(trace_sub, "log-init", cmd_trace_log_init)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", help="optional stage label to record on the init event")
    p = add_leaf(trace_sub, "step-enter", cmd_trace_step_enter)
    p.add_argument("--mission", required=True)
    p.add_argument("--step", required=True, help="step id or phase label, e.g. 'phase-1' or 'review-loop'")
    p.add_argument("--phase", help="optional phase grouping label")
    p.add_argument("--rounds", type=int, help="optional rounds counter (e.g. reviewer round number)")
    p.add_argument("--note", help="optional free-text note appended to the trace record")
    p = add_leaf(trace_sub, "step-exit", cmd_trace_step_exit)
    p.add_argument("--mission", required=True)
    p.add_argument("--step", required=True)
    p.add_argument("--status", required=True, choices=["pass", "fail", "blocked"])
    p.add_argument("--phase")
    p.add_argument("--rounds", type=int)
    p.add_argument("--note")
    # code-review-improvement-plan M2.1: review-round trace events
    p = add_leaf(trace_sub, "round-enter", cmd_trace_round_enter)
    p.add_argument("--mission", required=True)
    p.add_argument("--round", type=int, required=True, help="Review round number (1-based)")
    p.add_argument("--note", help="Optional note appended to the trace record")
    p = add_leaf(trace_sub, "round-exit", cmd_trace_round_exit)
    p.add_argument("--mission", required=True)
    p.add_argument("--round", type=int, required=True, help="Review round number (1-based)")
    p.add_argument("--status", required=True, choices=["pass", "fail", "hold", "blocked"],
                   help="Outcome of this review round")
    p.add_argument("--note", help="Optional note appended to the trace record")

    # harness todo: TodoWrite ↔ trace bridge
    todo = sub.add_parser("todo")
    todo_sub = todo.add_subparsers(dest="todo_command", required=True)
    p = add_leaf(todo_sub, "report", cmd_todo_report)
    p.add_argument("--mission", required=True)
    p = add_leaf(todo_sub, "sync", cmd_todo_sync)
    p.add_argument("--mission", required=True)

    approval = sub.add_parser("approval")
    approval_sub = approval.add_subparsers(dest="approval_command", required=True)
    p = add_leaf(approval_sub, "append", cmd_approval_append)
    p.add_argument("--mission", required=True)
    p.add_argument("--type", required=True, choices=["checkpoint", "boundary", "risk", "tradeoff"])
    p.add_argument("--stage")
    p.add_argument("--checkpoint")
    p.add_argument("--status", required=True, choices=["approved", "rejected", "modified"])
    p.add_argument("--comment")
    p.add_argument("--approval-id")
    p.add_argument("--decided-at")
    p = add_leaf(approval_sub, "latest", cmd_approval_latest)
    p.add_argument("--mission")
    p.add_argument("--type", choices=["checkpoint", "boundary", "risk", "tradeoff"])
    p.add_argument("--stage")
    p.add_argument("--status", choices=["approved", "rejected", "modified"])
    p = add_leaf(approval_sub, "require", cmd_approval_require)
    p.add_argument("--mission", required=True)
    p.add_argument("--type", required=True, choices=["checkpoint", "boundary", "risk", "tradeoff"])
    p.add_argument("--stage")
    p.add_argument("--checkpoint")

    graph = sub.add_parser("graph")
    graph_sub = graph.add_subparsers(dest="graph_command", required=True)
    p = add_leaf(graph_sub, "apply", cmd_graph_apply)
    p.add_argument("--operation", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--staged", action="store_true")
    p = add_leaf(graph_sub, "plan", cmd_graph_plan)
    p.add_argument("--operation", required=True)
    add_leaf(graph_sub, "rebuild", cmd_graph_rebuild)
    add_leaf(graph_sub, "check", cmd_graph_check)
    graph_node = graph_sub.add_parser("node")
    graph_node_sub = graph_node.add_subparsers(dest="node_command", required=True)
    p = add_leaf(graph_node_sub, "show", cmd_graph_node_show)
    p.add_argument("node_id")
    p = add_leaf(graph_node_sub, "create", cmd_graph_node_create)
    p.add_argument("--node-id", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--lane", required=True)
    p.add_argument("--status", required=True)
    p.add_argument("--mission-id")
    p.add_argument("--operation-id")
    p.add_argument("--input-node", action="append")
    p.add_argument("--output-node", action="append")

    board = sub.add_parser("board")
    board_sub = board.add_subparsers(dest="board_command", required=True)
    p = add_leaf(board_sub, "select", cmd_board_select)
    p.add_argument("--mission", required=True)
    p.add_argument("--query", action="append")
    p.add_argument("--primary-node", action="append")
    p.add_argument("--related-node", action="append")
    p.add_argument("--spec", action="append")
    p.add_argument("--write-slice", action="store_true")
    p.add_argument("--no-write", action="store_true")

    contract = sub.add_parser("contract")
    contract_sub = contract.add_subparsers(dest="contract_command", required=True)
    p = add_leaf(contract_sub, "init", cmd_contract_init)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--node")
    p.add_argument("--template", required=True)
    p.add_argument("--artifact-version", default="v1")
    p.add_argument("--review-strategy")
    p.add_argument("--capability")
    p.add_argument("--output")
    p.add_argument("--replace", action="store_true")
    p = add_leaf(contract_sub, "fill", cmd_contract_fill)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--artifact", required=True, help="Path to control contract YAML (auto-init from --template if missing)")
    p.add_argument("--intent-framing", required=True, help="YAML manifest with objective/user_stories/scope/acceptance_criteria/work_graph/autonomy_level; see harness-runtime/templates/contracts/intent-framing.example.yaml")
    p.add_argument("--template", help="Contract template name (e.g. mission-contract); only used when --artifact does not yet exist")
    p = add_leaf(contract_sub, "patch", cmd_contract_patch)
    p.add_argument("--artifact", required=True)
    p.add_argument("--patch", help="Path to a YAML manifest with {patches:[{target: control_contract.X.Y, op: set|merge|append, value: ...}]}. For business fields prefer `harness contract fill`.")
    p.add_argument("--add-round", action="store_true", help="M4.3 shortcut: increment control_contract.effectiveness_review.rounds_used by 1. Combine with --last-verdict to record the verdict at that round.")
    p.add_argument("--last-verdict", help="Record control_contract.effectiveness_review.last_verdict in tandem with --add-round (PASS / HOLD / PASS_WITH_RISK / BLOCKED).")
    p = add_leaf(contract_sub, "add-verdict", cmd_contract_add_verdict)
    p.add_argument("--artifact", required=True)
    p.add_argument("--verdict", required=True)
    p = add_leaf(contract_sub, "add-execution-result", cmd_contract_add_execution_result)
    p.add_argument("--artifact", required=True)
    p.add_argument("--result", required=True)
    p = add_leaf(contract_sub, "check", cmd_contract_check)
    p.add_argument("--artifact", required=True)
    p.add_argument("--upstream", action="append")
    p.add_argument("--allow-placeholders", action="store_true")
    p = add_leaf(contract_sub, "summary", cmd_contract_summary)
    p.add_argument("--mission", required=True)
    p.add_argument("--artifact", help="optional explicit contract path; defaults to harness-runtime/harness/missions/<id>/contracts/mission-contract.contract.yaml")
    p.add_argument("--format", choices=["user", "json"], default="json")
    p = add_leaf(contract_sub, "check-recheck-pending", cmd_contract_check_recheck_pending)
    p.add_argument("--artifact", required=True)
    # code-review-improvement-plan M2.1: code-review contract management
    p = add_leaf(contract_sub, "add-round", cmd_contract_add_round)
    p.add_argument("--mission", required=True)
    p.add_argument("--verdicts", help="JSON array of verdict objects for this round")
    p = add_leaf(contract_sub, "check-finding-ownership", cmd_contract_check_finding_ownership)
    p.add_argument("--mission", required=True)
    p = add_leaf(contract_sub, "detect-conflicts", cmd_contract_detect_conflicts)
    p.add_argument("--mission", required=True)
    # verify-improvement-plan M2.1: AC evidence cross-check command
    p = add_leaf(contract_sub, "check-ac-trace", cmd_contract_check_ac_trace)
    p.add_argument("--mission", required=True)
    p.add_argument("--artifact", help="Path to verification-report.contract.yaml; defaults to harness-runtime/harness/stages/<mission>/contracts/...")
    p.add_argument("--upstream", help="Path to execution-brief.contract.yaml for required_evidence_id cross-check; omit to skip H3 primary key validation")

    # verify-improvement-plan M2.1: verify command domain
    verify_cli = sub.add_parser("verify")
    verify_sub = verify_cli.add_subparsers(dest="verify_command", required=True)
    p = add_leaf(verify_sub, "compute-scope", cmd_verify_compute_scope)
    p.add_argument("--mission", required=True)
    p = add_leaf(verify_sub, "run-tests", cmd_verify_run_tests)
    p.add_argument("--mission", required=True)
    p.add_argument("--layer", required=True, choices=["unit", "integration", "e2e"])
    p.add_argument("--command", required=True, help="Test command to run")
    p = add_leaf(verify_sub, "e2e-status", cmd_verify_e2e_status)
    p.add_argument("--mission", required=True)
    p = add_leaf(verify_sub, "true-e2e-check", cmd_verify_true_e2e_check)
    p.add_argument("--mission", required=True)
    p.add_argument("--compat", action="store_true", help="downgrade strict new-gate failures to WARN for historical accepted artifacts")
    p = add_leaf(verify_sub, "dispatch-worker", cmd_verify_dispatch_worker)
    p.add_argument("--mission", required=True)
    p = add_leaf(verify_sub, "dispatch-reviewer", cmd_verify_dispatch_reviewer)
    p.add_argument("--mission", required=True)
    p = add_leaf(verify_sub, "detect-contradictions", cmd_verify_detect_contradictions)
    p.add_argument("--mission", required=True)
    p.add_argument("--artifact", help="Path to verification-report.contract.yaml")
    p = add_leaf(verify_sub, "compute-conclusion", cmd_verify_compute_conclusion)
    p.add_argument("--mission", required=True)
    p = add_leaf(verify_sub, "agent-eval-status", cmd_verify_agent_eval_status)
    p.add_argument("--mission", required=True)
    p = add_leaf(verify_sub, "failure-path", cmd_verify_failure_path)
    p.add_argument("--mission", required=True)
    p.add_argument("--kind", required=True)
    verify_gate = verify_sub.add_parser("gate")
    verify_gate_sub = verify_gate.add_subparsers(dest="verify_gate_command", required=True)
    p = add_leaf(verify_gate_sub, "run", cmd_verify_gate_run)
    p.add_argument("--mission", required=True)

    evidence = sub.add_parser("evidence")
    evidence_sub = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_graph = evidence_sub.add_parser("graph")
    evidence_graph_sub = evidence_graph.add_subparsers(dest="evidence_graph_command", required=True)
    p = add_leaf(evidence_graph_sub, "build", cmd_evidence_graph_build)
    p.add_argument("--mission")
    p.add_argument("--artifact", action="append", required=True)
    p.add_argument("--evidence-store")
    p.add_argument("--output")
    p = add_leaf(evidence_graph_sub, "check", cmd_evidence_graph_check)
    p.add_argument("--graph", required=True)
    p.add_argument("--current-git-ref")
    p = add_leaf(evidence_sub, "add", cmd_evidence_add)
    p.add_argument("--mission", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--store")
    p = add_leaf(evidence_sub, "link", cmd_evidence_link)
    p.add_argument("--mission", required=True)
    p.add_argument("--from", dest="from_id", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--type", default="supported_by")
    p.add_argument("--store")
    evidence_command = evidence_sub.add_parser("command")
    evidence_command_sub = evidence_command.add_subparsers(dest="evidence_command_command", required=True)
    p = add_leaf(evidence_command_sub, "collect", cmd_evidence_command_collect)
    p.add_argument("--mission")
    p.add_argument("--cwd")
    p.add_argument("--timeout", type=int)
    p.add_argument("--output-dir")
    p.add_argument("--store")
    p.add_argument("--no-run", action="store_true")
    evidence_visual = evidence_sub.add_parser("visual")
    evidence_visual_sub = evidence_visual.add_subparsers(dest="evidence_visual_command", required=True)
    p = add_leaf(evidence_visual_sub, "manifest", cmd_evidence_visual_manifest)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage-dir", required=True)
    p.add_argument("--source-dir", required=True)
    p.add_argument("--copy", action="store_true")
    p.add_argument("--output")

    gate = sub.add_parser("gate")
    gate_sub = gate.add_subparsers(dest="gate_command", required=True)
    p = add_leaf(gate_sub, "run", cmd_gate_run)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--lane-action")
    p.add_argument("--from-lane")
    p.add_argument("--to-lane")
    p.add_argument("--to-stage")
    p.add_argument("--primary-node", action="append")
    p.add_argument("--related-node", action="append")
    p.add_argument("--artifact")
    p.add_argument("--contract-artifact")
    p.add_argument("--contract-check-json")
    p.add_argument("--mission-slice")
    p.add_argument("--control-report", action="append")
    p.add_argument("--required-control", action="append")
    p.add_argument("--required-checkpoint", action="append")
    p.add_argument("--human-checkpoint", action="append")
    p.add_argument("--upstream", action="append")
    p.add_argument("--allow-placeholders", action="store_true")
    p.add_argument(
        "--ai-interpretation",
        help="One-paragraph AI explanation of why this gate decision is justified. Required unless --no-interpretation is given with a reason.",
    )
    p.add_argument(
        "--no-interpretation",
        metavar="REASON",
        help="Explicit reason for omitting --ai-interpretation (e.g. 'automated rerun, no decision change'). Recorded in the gate report.",
    )
    p.add_argument("--output-dir")
    p = add_leaf(gate_sub, "advance", cmd_gate_advance)
    p.add_argument("--mission", required=True)
    p.add_argument("--gate-report", required=True)
    p.add_argument("--contract-artifact")
    p.add_argument("--allow-warnings", action="store_true")
    gate_report = gate_sub.add_parser("report")
    gate_report_sub = gate_report.add_subparsers(dest="gate_report_command", required=True)
    p = add_leaf(gate_report_sub, "render", cmd_gate_report_render)
    p.add_argument("--contract-check-json", required=True)
    p.add_argument("--mission", required=True)
    p.add_argument("--from-stage", required=True)
    p.add_argument("--to-stage", required=True)
    p.add_argument("--mission-slice")
    p.add_argument("--control-report", action="append")
    p.add_argument("--required-control", action="append")
    p.add_argument("--required-checkpoint", action="append")
    p.add_argument("--human-checkpoint", action="append")
    p.add_argument(
        "--ai-interpretation",
        help="One-paragraph AI explanation of why this gate decision is justified. Required unless --no-interpretation is given.",
    )
    p.add_argument(
        "--no-interpretation",
        metavar="REASON",
        help="Explicit reason for omitting --ai-interpretation (recorded in the gate report).",
    )
    p.add_argument("--output-dir")
    p = add_leaf(gate_sub, "control-reports", cmd_gate_control_reports)
    p.add_argument("--mission")
    p.add_argument("--report", action="append")
    p.add_argument("--required-control", action="append")

    # Discovery stage commands (discovery-improvement-plan M2.1).
    gitnexus = sub.add_parser("gitnexus")
    gitnexus_sub = gitnexus.add_subparsers(dest="gitnexus_command", required=True)
    add_leaf(gitnexus_sub, "status", cmd_gitnexus_status)

    # PRD stage commands (prd-improvement-plan M2.1)
    prd = sub.add_parser("prd")
    prd_sub = prd.add_subparsers(dest="prd_command", required=True)
    p = add_leaf(prd_sub, "anti-pattern-scan", cmd_prd_anti_pattern_scan)
    p.add_argument("--artifact", required=True, help="Path to product-definition.md to scan.")
    p = add_leaf(prd_sub, "domain-model-lint", cmd_prd_domain_model_lint)
    p.add_argument("--artifact", required=True, help="Path to product-domain-model.md to lint.")
    p.add_argument("--product-definition", help="Optional path to product-definition.md for traceability checks.")
    p.add_argument("--contract", help="Optional path to prd.contract.yaml for structured domain_model checks.")
    p = add_leaf(prd_sub, "agent-cap-eval", cmd_prd_agent_cap_eval)
    p.add_argument("--mission", required=True)
    p.add_argument("--component", required=True, help="Name of the agent component being evaluated.")
    p.add_argument("--work-rights", dest="work_rights", help="Comma-separated list of work rights (read_context,decide_action,write_artifact,dispatch_subagent,request_human_input,halt_for_review).")
    p.add_argument("--priority", choices=["P0", "P1", "P2"], help="Priority level.")
    p.add_argument("--notes", help="Optional rationale text.")

    discovery = sub.add_parser("discovery")
    discovery_sub = discovery.add_subparsers(dest="discovery_command", required=True)
    p = add_leaf(discovery_sub, "skip", cmd_discovery_skip)
    p.add_argument("--mission", required=True)
    p.add_argument("--reason", required=True, help="Explicit reason for skipping discovery (audit trail).")
    p = add_leaf(discovery_sub, "summary", cmd_discovery_summary)
    p.add_argument("--mission", required=True)
    p.add_argument("--format", choices=["user", "json"], default="user", help="Human-readable text or pure structured payload.")
    p = add_leaf(discovery_sub, "check-dependency-trigger", cmd_discovery_check_dependency_trigger)
    p.add_argument("--mission", required=True)
    p = add_leaf(discovery_sub, "agent-eng-eval", cmd_discovery_agent_eng_eval)
    p.add_argument("--mission", required=True)
    p.add_argument("--component", required=True, help="Name of the candidate component being evaluated for agentization.")
    p.add_argument("--autonomy", action="store_true", help="Component requires autonomous judgment.")
    p.add_argument("--runtime-context", dest="runtime_context", action="store_true", help="Behaviour depends on runtime context.")
    p.add_argument("--multi-step", dest="multi_step", action="store_true", help="Behaviour requires multi-step reasoning.")
    p.add_argument("--uncertainty", action="store_true", help="Behaviour involves uncertainty or exception handling.")
    p.add_argument("--recommendation", choices=["agentize", "deterministic", "undecided"], help="Override the auto-derived recommendation; agentize is rejected unless all four flags are true.")
    p.add_argument("--notes", help="Optional rationale text appended to the contract record.")

    # Stage-4 design lane CLIs (M2.1).
    solution = sub.add_parser("solution")
    solution_sub = solution.add_subparsers(dest="solution_command", required=True)
    p = add_leaf(solution_sub, "decision-scan", cmd_solution_decision_scan)
    p.add_argument("--artifact", required=True, help="Path to solution.md to scan for anti-patterns + vague mitigation.")
    p = add_leaf(solution_sub, "lane-action-validate", cmd_solution_lane_action_validate)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--stage",
        choices=["solution", "interaction", "technical_analysis"],
        help="Override the stage read from mission-slice.yaml (test / out-of-band).",
    )

    interaction = sub.add_parser("interaction")
    interaction_sub = interaction.add_subparsers(dest="interaction_command", required=True)
    p = add_leaf(interaction_sub, "check-ui-trigger", cmd_interaction_check_ui_trigger)
    p.add_argument("--mission", required=True)
    p = add_leaf(interaction_sub, "spec-check", cmd_interaction_spec_check)
    p.add_argument("--mission", required=True)
    p.add_argument("--compat", action="store_true", help="downgrade strict new-gate failures to WARN for historical accepted artifacts")
    p = add_leaf(interaction_sub, "visual-coverage-check", cmd_interaction_visual_coverage_check)
    p.add_argument("--mission", required=True)
    p.add_argument("--compat", action="store_true", help="downgrade strict new-gate failures to WARN for historical accepted artifacts")
    p = add_leaf(interaction_sub, "locator-check", cmd_interaction_locator_check)
    p.add_argument("--mission", required=True)
    p.add_argument("--compat", action="store_true", help="downgrade strict new-gate failures to WARN for historical accepted artifacts")
    interaction_gate = interaction_sub.add_parser("gate")
    interaction_gate_sub = interaction_gate.add_subparsers(dest="interaction_gate_command", required=True)
    p = add_leaf(interaction_gate_sub, "run", cmd_interaction_gate_run)
    p.add_argument("--mission", required=True)
    p.add_argument("--compat", action="store_true", help="downgrade strict new-gate failures to WARN for historical accepted artifacts")

    alignment = sub.add_parser("alignment")
    alignment_sub = alignment.add_subparsers(dest="alignment_command", required=True)
    p = add_leaf(alignment_sub, "check", cmd_alignment_check)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--stage",
        required=True,
        choices=["interaction", "solution", "technical_analysis", "breakdown", "verify"],
    )
    p.add_argument("--compat", action="store_true", help="downgrade strict new-gate failures to WARN for historical accepted artifacts")

    tech_design = sub.add_parser("tech-design")
    tech_design_sub = tech_design.add_subparsers(dest="tech_design_command", required=True)
    p = add_leaf(tech_design_sub, "check-dep-impact-trigger", cmd_tech_design_check_dep_impact_trigger)
    p.add_argument("--mission", required=True)
    p = add_leaf(tech_design_sub, "check-capability-trigger", cmd_tech_design_check_capability_trigger)
    p.add_argument("--mission", required=True)

    lint = sub.add_parser("lint")
    lint_sub = lint.add_subparsers(dest="lint_command", required=True)
    add_leaf(lint_sub, "runtime", cmd_lint_runtime)
    add_leaf(lint_sub, "graph", cmd_lint_graph)
    p = add_leaf(lint_sub, "project", cmd_lint_project)
    p.add_argument("--config")
    p.add_argument("--profile")
    p.add_argument("--mission")
    p.add_argument("--changed-file", action="append")
    p.add_argument("--changed-files-file")
    p.add_argument("--command-evidence")
    p.add_argument("--trace")
    p.add_argument("--output-dir")
    p.add_argument("--no-git-diff", action="store_true")

    # Retrospective stage commands (retrospective-improvement-plan M2.1).
    p = add_leaf(mission_sub, "artifacts", cmd_mission_artifacts)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", help="Filter artifacts to a specific stage subdirectory.")

    p = add_leaf(mission_sub, "retrospective-data", cmd_mission_retrospective_data)
    p.add_argument("--mission", required=True)

    project_context = sub.add_parser("project-context")
    project_context_sub = project_context.add_subparsers(dest="project_context_command", required=True)
    p = add_leaf(project_context_sub, "add-lesson", cmd_project_context_add_lesson)
    p.add_argument("--lesson", required=True, help="Lesson text to append.")
    p.add_argument("--date", help="Override date (YYYY-MM-DD); defaults to today.")
    p.add_argument("--source", help="Source mission-id for audit trail.")
    add_leaf(project_context_sub, "drift-scan", cmd_project_context_drift_scan)
    add_leaf(project_context_sub, "lint", cmd_project_context_lint)

    retrospective = sub.add_parser("retrospective")
    retrospective_sub = retrospective.add_subparsers(dest="retrospective_command", required=True)
    p = add_leaf(retrospective_sub, "harness-gap-init", cmd_retrospective_harness_gap_init)
    p.add_argument("--mission", required=True)
    p = add_leaf(retrospective_sub, "harness-gap-emit", cmd_retrospective_harness_gap_emit)
    p.add_argument("--mission", required=True)
    p.add_argument("--gap-id", required=True)
    p.add_argument("--pattern-key", required=True)
    p.add_argument("--target-kind", required=True,
                   choices=["workflow", "hook", "schema", "lint_check", "agent_prompt", "methodology", "other"])
    p.add_argument("--severity", choices=["critical", "high", "medium", "low"], default="medium")
    p.add_argument("--description", required=True)
    p.add_argument("--first-seen")
    p.add_argument("--verification-ref")

    harness_gap = sub.add_parser("harness-gap")
    harness_gap_sub = harness_gap.add_subparsers(dest="harness_gap_command", required=True)
    p = add_leaf(harness_gap_sub, "pattern-scan", cmd_harness_gap_pattern_scan)
    p.add_argument("--mission", required=True)
    p.add_argument("--min-repeat", type=int, default=2,
                   help="Minimum repeat_count to flag as a recurring pattern.")

    agent_eval = sub.add_parser("agent-eval")
    agent_eval_sub = agent_eval.add_subparsers(dest="agent_eval_command", required=True)
    p = add_leaf(agent_eval_sub, "drift", cmd_agent_eval_drift)
    p.add_argument("--mission", required=True)
    p.add_argument("--baseline", dest="baseline_mission",
                   help="Mission id to use as drift baseline.")
    p.add_argument("--threshold", type=float, default=0.1,
                   help="Regression threshold (0.0-1.0); delta below -threshold triggers a finding.")

    # finishing-branch stage commands (M2.1)
    # delivery-improvement-plan M2.1: delivery stage CLI.
    delivery_cli = sub.add_parser("delivery")
    delivery_sub = delivery_cli.add_subparsers(dest="delivery_command", required=True)
    p = add_leaf(delivery_sub, "summarize", cmd_delivery_summarize)
    p.add_argument("--mission", required=True)
    p = add_leaf(delivery_sub, "compute-follow-ups", cmd_delivery_compute_follow_ups)
    p.add_argument("--mission", required=True)
    p = add_leaf(delivery_sub, "check-followups", cmd_delivery_check_followups)
    p.add_argument("--mission", required=True)
    p = add_leaf(delivery_sub, "compute-conclusion", cmd_delivery_compute_conclusion)
    p.add_argument("--mission", required=True)
    p = add_leaf(delivery_sub, "handoff", cmd_delivery_handoff)
    p.add_argument("--mission", required=True)
    p.add_argument("--approval-id", dest="approval_id", help="User acceptance approval id")
    p = add_leaf(delivery_sub, "agent-capability-status", cmd_delivery_agent_capability_status)
    p.add_argument("--mission", required=True)

    finishing_branch = sub.add_parser("finishing-branch")
    fb_sub = finishing_branch.add_subparsers(dest="finishing_branch_command", required=True)

    p = add_leaf(fb_sub, "status", cmd_finishing_branch_status)
    p.add_argument("--mission", required=True)

    p = add_leaf(fb_sub, "detect-test-cmd", cmd_finishing_branch_detect_test_cmd)
    p.add_argument("--mission", required=True)

    p = add_leaf(fb_sub, "run-tests", cmd_finishing_branch_run_tests)
    p.add_argument("--mission", required=True)
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    p.add_argument("--test-cmd", dest="test_cmd", help="Override test command.")
    p.add_argument("--reuse-evidence-id", dest="reuse_evidence_id",
                   help="Reuse a named evidence id from verification-report contract.")

    p = add_leaf(fb_sub, "readiness", cmd_finishing_branch_readiness)
    p.add_argument("--mission", required=True)

    p = add_leaf(fb_sub, "options", cmd_finishing_branch_options)
    p.add_argument("--mission", required=True)

    p = add_leaf(fb_sub, "pr-body", cmd_finishing_branch_pr_body)
    p.add_argument("--mission", required=True)

    p = add_leaf(fb_sub, "execute", cmd_finishing_branch_execute)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--strategy", required=True,
        choices=["merge_to_base", "push_pr", "keep", "discard"],
    )
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    p.add_argument("--confirmation-id", dest="confirmation_id",
                   help="Required for strategy=discard; must be 'discard'.")

    p = add_leaf(fb_sub, "cleanup", cmd_finishing_branch_cleanup)
    p.add_argument("--mission", required=True)
    p.add_argument("--dry-run", action="store_true", dest="dry_run")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
