from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


BREAKDOWN_REQUIRED_ROLES = ("delivery-slicer", "test-planning-expert")


def execution_brief_contract_path(root: Path, mission: str) -> Path:
    return root / "harness-runtime" / "harness" / "stages" / mission / "contracts" / "execution-brief.contract.yaml"


def execution_brief_markdown_path(root: Path, mission: str) -> Path:
    return root / "harness-runtime" / "harness" / "stages" / mission / "execution-brief.md"


def resolve_execution_brief_contract(root: Path, mission: str) -> tuple[Path, dict[str, Any] | None, str | None]:
    artifact = execution_brief_contract_path(root, mission)
    if not artifact.exists():
        return artifact, None, "execution_brief_contract_missing"
    try:
        document = yaml.safe_load(artifact.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return artifact, None, "execution_brief_contract_invalid_yaml"
    if not isinstance(document, dict):
        return artifact, None, "execution_brief_contract_invalid_root"
    contract = document.get("control_contract") if isinstance(document.get("control_contract"), dict) else document
    if not isinstance(contract, dict):
        return artifact, None, "execution_brief_contract_invalid_shape"
    return artifact, contract, None


def delta_spec_roots(root: Path, mission: str) -> list[Path]:
    """Return delta spec roots in current artifact layout order.

    Product delta specs live with product artifacts. Legacy artifact-store and
    pre-artifact-store stage paths are kept for backward compatibility.
    """
    harness_root = root / "harness-runtime" / "harness"
    candidates = [
        harness_root / "artifacts" / mission / "product" / "specs",
        harness_root / "artifacts" / mission / "legacy" / "specs",
        harness_root / "stages" / mission / "specs",
    ]
    return [path for path in candidates if path.exists()]


def delta_spec_files(root: Path, mission: str) -> list[Path]:
    seen: set[str] = set()
    files: list[Path] = []
    for specs_dir in delta_spec_roots(root, mission):
        for spec_md in sorted(specs_dir.rglob("spec.md")):
            capability = spec_md.parent.name
            source_key = f"{capability}:{spec_md}"
            if source_key in seen:
                continue
            seen.add(source_key)
            files.append(spec_md)
    return files


def find_delta_spec(root: Path, mission: str, capability: str) -> Path | None:
    for specs_dir in delta_spec_roots(root, mission):
        spec_md = specs_dir / capability / "spec.md"
        if spec_md.exists():
            return spec_md
    return None


def check_atomic_task_queue_completeness(contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    forbidden = {"missing", "incomplete", "draft"}
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        task_id = task.get("id") or "<unknown>"
        atq = task.get("atomic_task_queue") if isinstance(task.get("atomic_task_queue"), dict) else None
        if atq is None:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "missing_atomic_task_queue",
                    "task": task_id,
                    "message": f"task {task_id} lacks atomic_task_queue",
                }
            )
            continue
        status = atq.get("status")
        if status in forbidden or status is None:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "atomic_task_queue_not_ready",
                    "task": task_id,
                    "status": status,
                    "message": f"task {task_id} atomic_task_queue.status={status!r}; must be ready or accepted",
                }
            )
    return findings


def check_execution_results_dual_roles(contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    results = contract.get("execution_results")
    if not isinstance(results, list):
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
    roles = {entry.get("role") for entry in results if isinstance(entry, dict) and entry.get("status") == "DONE"}
    for required in BREAKDOWN_REQUIRED_ROLES:
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


def check_traces_to_coverage(contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        task_id = task.get("id") or "<unknown>"
        traces = task.get("traces_to")
        if not isinstance(traces, list) or not traces:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "missing_traces_to",
                    "task": task_id,
                    "message": f"task {task_id} missing traces_to[]; must reference at least one upstream ID",
                }
            )
    return findings


def check_authorized_paths(contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        task_id = task.get("id") or "<unknown>"
        authorized = task.get("authorized_paths")
        if not isinstance(authorized, list) or not authorized:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "W-execution-brief-authorized-paths",
                    "task": task_id,
                    "message": f"task {task_id} has empty authorized_paths",
                }
            )
            continue
        prohibited = task.get("prohibited_paths") or []
        overlap = set(path for path in authorized if isinstance(path, str)) & set(
            path for path in prohibited if isinstance(path, str)
        )
        if overlap:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "W-execution-brief-prohibited-paths",
                    "task": task_id,
                    "overlap": sorted(overlap),
                    "message": f"task {task_id} has paths in both authorized_paths and prohibited_paths: {sorted(overlap)}",
                }
            )
    return findings


def check_stop_if_baseline(contract: dict[str, Any]) -> list[dict[str, Any]]:
    baseline = {
        "changes_outside_authorized_paths",
        "new_public_behavior_without_delta_spec",
        "design_constraint_conflict",
        "new_external_dependency",
    }
    findings: list[dict[str, Any]] = []
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        task_id = task.get("id") or "<unknown>"
        stop_if = set(flag for flag in (task.get("stop_if") or []) if isinstance(flag, str))
        missing = baseline - stop_if
        if missing:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "W-execution-brief-stop-if",
                    "task": task_id,
                    "missing": sorted(missing),
                    "message": f"task {task_id} stop_if missing baseline conditions: {sorted(missing)}",
                }
            )
    return findings


def check_parallel_write_scope_conflict(contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    tasks = [task for task in (contract.get("tasks") or []) if isinstance(task, dict)]
    for index, task_a in enumerate(tasks):
        a_id = task_a.get("id") or f"<task-{index}>"
        a_paths = set(path for path in (task_a.get("authorized_paths") or []) if isinstance(path, str))
        a_deps = set(dep for dep in (task_a.get("dependencies") or []) if isinstance(dep, str))
        for task_b in tasks[index + 1 :]:
            b_id = task_b.get("id") or "<task>"
            b_paths = set(path for path in (task_b.get("authorized_paths") or []) if isinstance(path, str))
            b_deps = set(dep for dep in (task_b.get("dependencies") or []) if isinstance(dep, str))
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
                            f"tasks {a_id} and {b_id} share authorized_paths {sorted(overlap)} "
                            "without declaring a dependency; mark must_serialize or add a dependency edge"
                        ),
                    }
                )
    return findings


def check_dependency_cycle(contract: dict[str, Any]) -> list[dict[str, Any]]:
    graph: dict[str, list[str]] = {}
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        task_id = task.get("id")
        if isinstance(task_id, str):
            graph[task_id] = [dep for dep in (task.get("dependencies") or []) if isinstance(dep, str)]

    white, gray, black = 0, 1, 2
    color = {node: white for node in graph}
    cycle_nodes: list[str] = []

    def dfs(node: str, path: list[str]) -> bool:
        color[node] = gray
        path.append(node)
        for dep in graph.get(node, []):
            if dep not in color:
                continue
            if color[dep] == gray:
                cycle_nodes.extend(path[path.index(dep) :] + [dep])
                return True
            if color[dep] == white and dfs(dep, path):
                return True
        path.pop()
        color[node] = black
        return False

    for node in graph:
        if color[node] == white and dfs(node, []):
            return [
                {
                    "level": "FAIL",
                    "code": "W-execution-brief-dep-cycle",
                    "cycle": cycle_nodes,
                    "message": f"tasks[].dependencies form a cycle: {' -> '.join(cycle_nodes)}",
                }
            ]
    return []


def self_check_findings(contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    findings.extend(check_atomic_task_queue_completeness(contract))
    findings.extend(check_traces_to_coverage(contract))
    return findings


def quality_check_findings(contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    findings.extend(check_atomic_task_queue_completeness(contract))
    findings.extend(check_traces_to_coverage(contract))
    findings.extend(check_execution_results_dual_roles(contract))
    findings.extend(check_authorized_paths(contract))
    findings.extend(check_stop_if_baseline(contract))
    findings.extend(check_parallel_write_scope_conflict(contract))
    findings.extend(check_dependency_cycle(contract))
    return findings


def artifact_gate_findings(root: Path, mission: str, relpath_fn) -> list[dict[str, Any]]:
    md_path = execution_brief_markdown_path(root, mission)
    if not md_path.exists():
        return [
            {
                "level": "FAIL",
                "code": "execution_brief_md_missing",
                "message": f"execution-brief.md not found at {relpath_fn(root, md_path)}",
            }
        ]

    md_text = md_path.read_text(encoding="utf-8")
    contract_marker_re = re.compile(r"(?:^|\n)\s*[-*]?\s*Contract\s*:\s*`?contracts/execution-brief\.contract\.yaml`?")
    markers: list[tuple[str, object]] = [
        ("Execution Units", "Execution Units"),
        ("Contract: contracts/execution-brief.contract.yaml", contract_marker_re),
    ]
    findings: list[dict[str, Any]] = []
    for marker_label, matcher in markers:
        present = marker_label in md_text if isinstance(matcher, str) else bool(matcher.search(md_text))
        if not present:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "execution_brief_md_section_missing",
                    "section": marker_label,
                    "message": f"execution-brief.md missing section/marker: {marker_label!r}",
                }
            )
    return findings


def status_from_fail_findings(findings: list[dict[str, Any]]) -> str:
    return "PASS" if not any(finding.get("level") == "FAIL" for finding in findings) else "FAIL"


def persist_last_gate_run_status(artifact: Path, status: str) -> None:
    try:
        document = yaml.safe_load(artifact.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            return
        contract_block = document.get("control_contract") if isinstance(document.get("control_contract"), dict) else document
        if not isinstance(contract_block, dict):
            return
        effectiveness = contract_block.get("effectiveness_review")
        if not isinstance(effectiveness, dict):
            effectiveness = {}
            contract_block["effectiveness_review"] = effectiveness
        effectiveness["last_gate_run_status"] = status
        artifact.write_text(yaml.dump(document, default_flow_style=False, allow_unicode=True, sort_keys=False) + "\n", encoding="utf-8")
    except (OSError, yaml.YAMLError):
        return


def trace_ids_from_contract(contract: dict[str, Any]) -> set[str]:
    traces: set[str] = set()
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        for entry in task.get("traces_to") or []:
            if isinstance(entry, str):
                traces.add(entry)
    return traces


def delta_spec_scenarios(root: Path, mission: str, traces: set[str], relpath_fn) -> list[dict[str, Any]]:
    deltas: list[dict[str, Any]] = []
    for spec_md in delta_spec_files(root, mission):
        capability = spec_md.parent.name
        text = spec_md.read_text(encoding="utf-8")
        scenarios: list[dict[str, Any]] = []
        for line in text.splitlines():
            line_strip = line.strip()
            if line_strip.startswith("### Scenario:") or line_strip.startswith("#### Scenario:"):
                name = line_strip.split(":", 1)[1].strip()
                candidate_ids = {f"{capability}/spec.md#{name}", name}
                covered = bool(candidate_ids & traces) or any(name in trace for trace in traces)
                scenarios.append({"name": name, "covered": covered, "trace_id": f"{capability}/spec.md#{name}"})
        deltas.append({"capability": capability, "spec_path": relpath_fn(root, spec_md), "scenarios": scenarios})
    return deltas


def uncovered_delta_scenarios(root: Path, mission: str, traces: set[str]) -> tuple[int, list[dict[str, str]]]:
    uncovered: list[dict[str, str]] = []
    total_scenarios = 0
    for spec_md in delta_spec_files(root, mission):
        capability = spec_md.parent.name
        for line in spec_md.read_text(encoding="utf-8").splitlines():
            line_strip = line.strip()
            if not (line_strip.startswith("### Scenario:") or line_strip.startswith("#### Scenario:")):
                continue
            name = line_strip.split(":", 1)[1].strip()
            total_scenarios += 1
            candidate_ids = {f"{capability}/spec.md#{name}", name}
            if candidate_ids & traces:
                continue
            if any(name in trace for trace in traces):
                continue
            uncovered.append({"capability": capability, "scenario": name, "expected_trace": f"{capability}/spec.md#{name}"})
    return total_scenarios, uncovered


def writing_plans_refinements(contract: dict[str, Any]) -> list[dict[str, Any]]:
    refinements: list[dict[str, Any]] = []
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        atomic_task_queue = task.get("atomic_task_queue") if isinstance(task.get("atomic_task_queue"), dict) else {}
        refinements.append(
            {
                "task": task.get("id"),
                "atomic_task_status": atomic_task_queue.get("status"),
                "atomic_task_ids": atomic_task_queue.get("atomic_task_ids") or [],
                "detail_refs": atomic_task_queue.get("detail_refs") or [],
            }
        )
    return refinements
