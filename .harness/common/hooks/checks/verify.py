"""Stage hook checks: verify.

Migrated from .harness/common/runtime-overlay/hooks/verify/ — 8 PreToolUse
checks + 4 PostToolUse sensors. The dispatcher already filters by event +
tools and only invokes these on the resolved `verify` stage, so checks
below do finer filtering (file_path / command / role / payload) only.
"""

from __future__ import annotations

import json
import re
import shlex
from datetime import datetime, timezone
from pathlib import Path

from context import HookContext
from entry import BASH, READ, TASK, WRITE, HookEntry
from result import HookResult
from lib import commands, contracts, paths, roles, runtime

_CONTRACT_MARKER = "verification-report.contract.yaml"
_CONTRACT_FILENAME = "verification-report.contract.yaml"
_BRIEF_FILENAME = "execution-brief.contract.yaml"

_UI_SURFACE_KINDS = {"screenshot", "video", "dom", "dom_snapshot"}

_PATCH_AC_PASS_RE = re.compile(
    r"\bharness\s+contract\s+patch\b.*\bacceptance_trace\b.*\bconclusion\b.*\bpass\b",
    re.IGNORECASE | re.DOTALL,
)
_PATCH_OR_RESULT_RE = re.compile(
    r"\bharness\s+contract\s+(?:patch|add-execution-result)\b",
    re.IGNORECASE,
)
_COLLECT_RE = re.compile(
    r"\bharness\s+(?:evidence\s+command\s+collect|verify\s+run-tests)\b",
    re.IGNORECASE,
)

_E2E_PATTERNS = [
    re.compile(r"\bnpx\s+playwright\s+(test|run)\b", re.IGNORECASE),
    re.compile(r"\bnpm\s+run\s+e2e\b", re.IGNORECASE),
    re.compile(r"\byarn\s+e2e\b", re.IGNORECASE),
    re.compile(r"\bpnpm\s+e2e\b", re.IGNORECASE),
    re.compile(r"\bpytest\s+.*\s+-m\s+e2e\b", re.IGNORECASE),
    re.compile(r"\bpython\s+.*pytest\b.*\be2e\b", re.IGNORECASE),
    re.compile(r"\bcypress\s+run\b", re.IGNORECASE),
]

_DEFAULT_ALLOWED_WRITE = [
    "harness-runtime/harness/artifacts/*/verify/verification-report.md",
    "harness-runtime/harness/stages/*/contracts/verification-report.contract.yaml",
    "harness-runtime/harness/traces/**",
    "harness-runtime/harness/approvals.json",
    "harness-runtime/harness/stages/*/contracts/",
]
_ALWAYS_ALLOWED_PREFIXES = (".harness/", ".claude/", ".cursor/", "/tmp/", "tmp/")

_PROTECTED_SRC_PATTERNS = ["src/**", "tests/**", "test/**", "lib/**", "app/**"]
_ALLOWED_FAILURE_KINDS = {"bug_fix", "execute", "decision_gate", "receiving_review"}

_CONTEXT_FILE_MARKERS = [
    "mission-contract.md",
    "execution-brief.md",
    "execution-brief.contract.yaml",
    "code-review.md",
    "code-review.contract.yaml",
    "project-context.md",
    "project-knowledge/specs",
]
_MISSION_PATH_RE = re.compile(r"harness-runtime[/\\]harness[/\\]stages[/\\]([^/\\]+)")


# --- check_contract_via_cli ------------------------------------------------
def check_contract_via_cli(ctx: HookContext) -> HookResult:
    file_path = ctx.file_path or ""
    if _CONTRACT_MARKER not in file_path:
        return HookResult.ok()
    return HookResult.block(
        "HarnessV2 verify hook BLOCKED: direct Write/Edit of "
        f"{_CONTRACT_MARKER} is forbidden. Use `harness contract fill/patch/"
        "add-verdict --json`."
    )


# --- check_evidence_id_referenced ------------------------------------------
def check_evidence_id_referenced(ctx: HookContext) -> HookResult:
    command = ctx.command or ""
    if not commands.is_stage_complete(command, "verify"):
        return HookResult.ok()
    mission_id = commands.mission_id(command) or ctx.mission_id
    if not mission_id:
        return HookResult.ok()
    brief = contracts.load_contract(
        contracts.stage_contract_path(ctx.cwd, mission_id, _BRIEF_FILENAME)
    )
    report = contracts.load_contract(
        contracts.stage_contract_path(ctx.cwd, mission_id, _CONTRACT_FILENAME)
    )
    if not brief or not report:
        # Cannot enforce without both contracts — let other hooks decide.
        return HookResult.ok()
    valid_ids: set[str] = set()
    for task in brief.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        for ev in task.get("required_evidence") or []:
            if isinstance(ev, dict) and isinstance(ev.get("id"), str):
                valid_ids.add(ev["id"])
    missing_refs: list[str] = []
    for key in ("command_evidence", "result_evidence"):
        entries = report.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            ref = entry.get("required_evidence_id")
            if not ref:
                missing_refs.append(f"{key}.{entry.get('id', '<unknown>')}=<missing>")
            elif ref not in valid_ids:
                missing_refs.append(
                    f"{key}.{entry.get('id', '<unknown>')}={ref!r} not in execution-brief"
                )
    if missing_refs:
        return HookResult.block(
            "HarnessV2 verify hook BLOCKED (VERIFY_EVIDENCE_ID_NOT_IN_UPSTREAM): "
            "verification-report.contract.yaml carries evidence entries that "
            "do not reference a valid breakdown required_evidence[].id. "
            f"Offending entries: {missing_refs}. "
            "Anchor each command/result_evidence to a typed upstream id; "
            "verify does not invent IDs."
        )
    return HookResult.ok()


# --- deny_reviewer_write ---------------------------------------------------
def deny_reviewer_write(ctx: HookContext) -> HookResult:
    if not _is_reviewer_context(ctx):
        return HookResult.ok()
    file_path = ctx.file_path or ""
    return HookResult.block(
        "HarnessV2 verify hook BLOCKED (REVIEWER_WRITE_DENIED): "
        "verification-effectiveness-reviewer is readonly and must not "
        f"Edit/Write files (attempted: {file_path!r}). "
        "Reviewer may only read artifacts and record a verdict via "
        "`harness contract add-verdict --json`."
    )


# --- check_worker_write_scope ----------------------------------------------
def check_worker_write_scope(ctx: HookContext) -> HookResult:
    file_path = ctx.file_path or ""
    if not file_path:
        return HookResult.ok()
    if not _is_worker_context(ctx):
        return HookResult.ok()
    norm_fp = file_path.lstrip("./")
    for prefix in _ALWAYS_ALLOWED_PREFIXES:
        if norm_fp.startswith(prefix.lstrip("./")):
            return HookResult.ok()
    allowed = _DEFAULT_ALLOWED_WRITE + _load_extra_allowed_write(ctx.cwd)
    if _match_write_scope(file_path, allowed):
        return HookResult.ok()
    return HookResult.block(
        "HarnessV2 verify hook BLOCKED (WORKER_WRITE_SCOPE_VIOLATION): "
        f"verification-engineer is not permitted to write {file_path!r}. "
        "Allowed paths: verification-report.md, verification-report.contract.yaml, "
        "traces/**, approvals.json, and evidence_path_lock.allowed_write_paths. "
        "If a code fix is needed, record a failure_path via "
        "`harness verify failure-path --kind bug_fix --json` first."
    )


# --- deny_direct_e2e -------------------------------------------------------
def deny_direct_e2e(ctx: HookContext) -> HookResult:
    command = ctx.command or ""
    if not any(pat.search(command) for pat in _E2E_PATTERNS):
        return HookResult.ok()
    if _e2e_enabled(ctx.cwd) is not True:
        return HookResult.ok()
    return HookResult.block(
        "HarnessV2 verify hook BLOCKED (DIRECT_E2E_DENIED): "
        "e2e.enabled=true in the verification contract. "
        "Direct E2E commands are not permitted during verify; use "
        "`harness verify e2e-status --mission <id> --json` to run the "
        "normalised e2e_resolver / e2e_runner / normalise three-step suite. "
        f"Blocked command: {command[:200]!r}"
    )


# --- check_verify_prereqs --------------------------------------------------
def check_verify_prereqs(ctx: HookContext) -> HookResult:
    command = ctx.command or ""
    if not commands.is_advance(command):
        return HookResult.ok()
    mission_id = commands.mission_id(command) or ctx.mission_id
    if not mission_id:
        return HookResult.ok()
    unmet = _check_prereqs(ctx.cwd, mission_id)
    if not unmet:
        return HookResult.ok()
    return HookResult.block(
        "HarnessV2 verify hook BLOCKED (VERIFY_PREREQS_NOT_MET): "
        "cannot advance verify gate until all prerequisites are satisfied. "
        f"Unmet: [{'; '.join(unmet)}]. "
        "Complete the required steps before running `harness gate advance`."
    )


# --- check_ac_evidence -----------------------------------------------------
def check_ac_evidence(ctx: HookContext) -> HookResult:
    violations: list[str] = []
    if ctx.tool_name == "Bash":
        command = ctx.command or ""
        if not _PATCH_AC_PASS_RE.search(command):
            return HookResult.ok()
        violations = _check_bash_patch_acs(command)
    elif ctx.is_write_tool:
        if _CONTRACT_MARKER not in (ctx.file_path or ""):
            return HookResult.ok()
        content = ctx.content
        if not content or "conclusion" not in content or "pass" not in content:
            return HookResult.ok()
        doc = _safe_yaml(content)
        if not isinstance(doc, dict):
            return HookResult.ok()
        violations = _check_contract_acs(doc)
    else:
        return HookResult.ok()
    if not violations:
        return HookResult.ok()
    return HookResult.block(
        "HarnessV2 verify hook BLOCKED (AC_EVIDENCE_INSUFFICIENT): "
        "cannot set acceptance_trace[*].conclusion=pass without both command evidence "
        "and result evidence. UI acceptance scenarios additionally require screenshot/video/dom kind. "
        f"Violations: [{'; '.join(violations)}]. "
        "Collect required evidence via `harness evidence command collect` and "
        "`harness contract add-execution-result` before marking acceptance scenarios as pass."
    )


# --- require_failure_path --------------------------------------------------
def require_failure_path(ctx: HookContext) -> HookResult:
    file_path = ctx.file_path or ""
    if not file_path:
        return HookResult.ok()
    norm = file_path.lstrip("./")
    if not any(paths.match(norm, pat) for pat in _PROTECTED_SRC_PATTERNS):
        return HookResult.ok()
    if _failure_path_recorded(ctx.cwd):
        return HookResult.ok()
    return HookResult.block(
        "HarnessV2 verify hook BLOCKED (FAILURE_PATH_REQUIRED): "
        f"verify stage must not edit implementation files ({file_path!r}) directly. "
        "Record a typed failure path first: "
        "`harness verify failure-path --mission <id> "
        "--kind bug_fix|execute|decision_gate|receiving_review --json`. "
        "Then the defect fix must happen in the designated bug-fix / execute stage."
    )


# --- PostToolUse sensors ---------------------------------------------------
def record_context_reads(ctx: HookContext) -> HookResult:
    file_path = ctx.file_path or ""
    norm = file_path.replace("\\", "/")
    if not any(marker in norm for marker in _CONTEXT_FILE_MARKERS):
        return HookResult.ok()
    mission_id = _mission_from_path(file_path) or _latest_mission(ctx.cwd)
    if not mission_id:
        return HookResult.ok()
    runtime.append_trace(
        ctx.cwd,
        f"stages/{mission_id}/traces/context_reads.jsonl",
        {
            "event": "context_read",
            "file_path": file_path,
            "tool_name": "Read",
            "mission_id": mission_id,
            "timestamp": _now(),
        },
    )
    return HookResult.ok()


def record_dispatch(ctx: HookContext) -> HookResult:
    agent_id = (
        ctx.tool_input.get("subagent_type")
        or ctx.tool_input.get("agent_id")
        or ctx.tool_input.get("agent")
        or ""
    )
    if not agent_id:
        return HookResult.ok()
    mission_id = ctx.mission_id or _latest_mission(ctx.cwd)
    if not mission_id:
        return HookResult.ok()
    is_reviewer = roles.is_reviewer(agent_id)
    is_worker = roles.is_worker(agent_id)
    runtime.append_trace(
        ctx.cwd,
        f"stages/{mission_id}/traces/dispatches.jsonl",
        {
            "event": "dispatch",
            "agent_id": agent_id,
            "is_reviewer": is_reviewer,
            "is_worker": is_worker,
            "mission_id": mission_id,
            "timestamp": _now(),
        },
    )
    traces_dir = runtime.runtime_root(ctx.cwd) / "stages" / mission_id / "traces"
    try:
        traces_dir.mkdir(parents=True, exist_ok=True)
        if is_reviewer:
            (traces_dir / "reviewer_turn.flag").write_text(_now(), encoding="utf-8")
        elif is_worker:
            (traces_dir / "worker_turn.flag").write_text(_now(), encoding="utf-8")
    except OSError:
        pass
    return HookResult.ok()


def record_command_flag(ctx: HookContext) -> HookResult:
    command = ctx.command or ""
    if not _COLLECT_RE.search(command):
        return HookResult.ok()
    exit_code = ctx.tool_response.get("exit_code")
    if exit_code is None:
        result = ctx.raw.get("result") or ctx.raw.get("tool_result") or {}
        if isinstance(result, dict):
            exit_code = result.get("exit_code")
    # If exit_code unknown, write the flag optimistically (gate check is the
    # authoritative enforcer anyway).
    if exit_code is not None and exit_code != 0:
        return HookResult.ok()
    mission_id = commands.mission_id(command) or ctx.mission_id
    if not mission_id:
        return HookResult.ok()
    traces_dir = runtime.runtime_root(ctx.cwd) / "stages" / mission_id / "traces"
    try:
        traces_dir.mkdir(parents=True, exist_ok=True)
        (traces_dir / "command_evidence_collected.flag").write_text(
            _now(), encoding="utf-8"
        )
    except OSError:
        pass
    return HookResult.ok()


def mirror_evidence_graph(ctx: HookContext) -> HookResult:
    command = ctx.command or ""
    if not _PATCH_OR_RESULT_RE.search(command):
        return HookResult.ok()
    mission_id = commands.mission_id(command) or ctx.mission_id
    if not mission_id:
        return HookResult.ok()
    contract_path = contracts.stage_contract_path(
        ctx.cwd, mission_id, _CONTRACT_FILENAME
    )
    if not contract_path.exists():
        return HookResult.ok()
    doc = contracts.load_yaml(contract_path)
    if not isinstance(doc, dict):
        return HookResult.ok()
    graph = _build_evidence_graph(doc)
    traces_dir = runtime.runtime_root(ctx.cwd) / "stages" / mission_id / "traces"
    try:
        traces_dir.mkdir(parents=True, exist_ok=True)
        (traces_dir / "evidence_graph.json").write_text(
            json.dumps(graph, indent=2), encoding="utf-8"
        )
    except OSError:
        pass
    return HookResult.ok()


# --- private helpers -------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_yaml(text: str):
    if not contracts.HAVE_YAML:
        return None
    import yaml

    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return None


def _reviewer_flag_present(cwd: Path) -> bool:
    base = runtime.runtime_root(cwd) / "stages"
    return base.is_dir() and any(base.glob("*/traces/reviewer_turn.flag"))


def _worker_flag_present(cwd: Path) -> bool:
    base = runtime.runtime_root(cwd) / "stages"
    return base.is_dir() and any(base.glob("*/traces/worker_turn.flag"))


def _is_reviewer_context(ctx: HookContext) -> bool:
    if roles.is_reviewer(ctx.agent_role):
        return True
    return _reviewer_flag_present(ctx.cwd)


def _is_worker_context(ctx: HookContext) -> bool:
    role = ctx.agent_role
    if role:
        norm = role.replace("-", "").replace("_", "")
        if norm == "verificationengineer":
            return True
    return _worker_flag_present(ctx.cwd)


def _match_write_scope(file_path: str, patterns: list[str]) -> bool:
    norm = file_path.lstrip("./")
    for pat in patterns:
        pat_norm = pat.lstrip("./")
        if paths.match(norm, pat_norm) or paths.match(file_path, pat_norm):
            return True
        if norm.startswith("harness-runtime/"):
            stripped = norm[len("harness-runtime/"):]
            if paths.match(stripped, pat_norm):
                return True
    return False


def _load_extra_allowed_write(cwd: Path) -> list[str]:
    extra: list[str] = []
    base = runtime.runtime_root(cwd) / "stages"
    if not base.is_dir():
        return extra
    for contract_path in base.glob("*/contracts/verification-report.contract.yaml"):
        doc = contracts.load_contract(contract_path)
        lock = doc.get("evidence_path_lock")
        if not isinstance(lock, dict):
            continue
        for p in lock.get("allowed_write_paths") or []:
            if isinstance(p, str):
                extra.append(p)
    return extra


def _e2e_enabled(cwd: Path) -> bool | None:
    base = runtime.runtime_root(cwd) / "stages"
    if not base.is_dir():
        return None
    for contract_path in base.glob("*/contracts/verification-report.contract.yaml"):
        doc = contracts.load_contract(contract_path)
        if not doc:
            continue
        e2e = doc.get("e2e")
        if isinstance(e2e, dict):
            return bool(e2e.get("enabled", False))
        if isinstance(doc.get("e2e_enabled"), bool):
            return doc["e2e_enabled"]
    return None


def _check_prereqs(cwd: Path, mission_id: str) -> list[str]:
    contract = contracts.load_contract(
        contracts.stage_contract_path(cwd, mission_id, _CONTRACT_FILENAME)
    )
    traces = runtime.runtime_root(cwd) / "stages" / mission_id / "traces"
    failures: list[str] = []

    collected = (traces / "command_evidence_collected.flag").exists()
    if not collected and contract:
        gr = contract.get("gate_run")
        gr = gr if isinstance(gr, dict) else {}
        collected = bool(gr.get("command_evidence_collected", False)) or bool(
            contract.get("command_evidence_collected", False)
        )
    if not collected:
        failures.append(
            "command_evidence_collected=false (run `harness evidence command collect` "
            "or `harness verify run-tests` first)"
        )

    gate_pass = (traces / "gate_run_pass.flag").exists()
    if not gate_pass and contract:
        gr = contract.get("gate_run")
        gr = gr if isinstance(gr, dict) else {}
        status = gr.get("last_gate_run_status") or contract.get("last_gate_run_status")
        gate_pass = status == "PASS"
    if not gate_pass:
        failures.append(
            "last_gate_run_status != PASS (run `harness verify gate run --mission <id> --json`)"
        )

    true_e2e_pass = (traces / "true_e2e_pass.flag").exists()
    if not true_e2e_pass and contract:
        gr = contract.get("gate_run")
        gr = gr if isinstance(gr, dict) else {}
        status = gr.get("true_e2e_status") or contract.get("true_e2e_status")
        true_e2e_pass = status in {"PASS", "none", "N/A", "not_applicable"}
    if not true_e2e_pass:
        failures.append(
            "true_e2e_status != PASS (run "
            "`harness verify true-e2e-check --mission <id> --json` via "
            "`harness verify gate run --mission <id> --json`)"
        )

    contra_pass = (traces / "contradictions_pass.flag").exists()
    if not contra_pass and contract:
        gr = contract.get("gate_run")
        gr = gr if isinstance(gr, dict) else {}
        status = gr.get("contradictions_status") or contract.get("contradictions_status")
        contra_pass = status in {"PASS", "none"}
    if not contra_pass:
        failures.append(
            "contradictions_status != PASS (run "
            "`harness verify detect-contradictions --mission <id> --json`)"
        )
    return failures


def _has_sufficient_evidence(acceptance_id, trace_entry, result_evidence) -> tuple[bool, str]:
    cmd_ids = set(trace_entry.get("command_evidence_ids") or [])
    res_ids = set(trace_entry.get("result_evidence_ids") or [])
    if not cmd_ids:
        return False, f"acceptance_trace[{acceptance_id}].conclusion=pass but no command_evidence_ids"
    if not res_ids:
        return False, f"acceptance_trace[{acceptance_id}].conclusion=pass but no result_evidence_ids"
    is_ui = trace_entry.get("surface_type") == "ui" or bool(trace_entry.get("ui_surface"))
    if is_ui:
        res_ev_map = {e.get("id"): e for e in result_evidence if isinstance(e, dict)}
        ui_kind_found = any(
            str((res_ev_map.get(rid) or {}).get("kind") or "").lower()
            in _UI_SURFACE_KINDS
            for rid in res_ids
        )
        if not ui_kind_found:
            return (
                False,
                f"acceptance_trace[{acceptance_id}].surface_type=ui but no linked result_evidence "
                "with kind in [screenshot, video, dom]",
            )
    return True, ""


def _check_contract_acs(doc: dict) -> list[str]:
    inner = contracts.unwrap(doc)
    acceptance_traces = inner.get("acceptance_trace") or []
    result_evidence = inner.get("result_evidence") or []
    if not isinstance(acceptance_traces, list):
        return []
    violations: list[str] = []
    for entry in acceptance_traces:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("conclusion", "")).lower() != "pass":
            continue
        acceptance_id = entry.get("id") or entry.get("acceptance_id") or "<unknown>"
        ok, reason = _has_sufficient_evidence(acceptance_id, entry, result_evidence)
        if not ok:
            violations.append(reason)
    return violations


def _check_bash_patch_acs(command: str) -> list[str]:
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = []
    for index, part in enumerate(parts):
        if part != "--data" or index + 1 >= len(parts):
            continue
        raw_doc = parts[index + 1]
        try:
            doc = json.loads(raw_doc)
        except (json.JSONDecodeError, ValueError, TypeError):
            doc = _safe_yaml(raw_doc)
        if isinstance(doc, dict):
            return _check_contract_acs(doc)
    return []


def _failure_path_recorded(cwd: Path) -> bool:
    base = runtime.runtime_root(cwd) / "stages"
    if not base.is_dir():
        return False
    for trace_path in base.glob("*/traces/failure_path.json"):
        try:
            data = json.loads(trace_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("kind") in _ALLOWED_FAILURE_KINDS:
            return True
    for contract_path in base.glob("*/contracts/verification-report.contract.yaml"):
        doc = contracts.load_contract(contract_path)
        fp = doc.get("failure_path")
        if isinstance(fp, dict) and fp.get("kind") in _ALLOWED_FAILURE_KINDS:
            return True
        if isinstance(fp, str) and fp in _ALLOWED_FAILURE_KINDS:
            return True
    return False


def _build_evidence_graph(doc: dict) -> dict:
    inner = contracts.unwrap(doc)
    nodes: list[dict] = []
    edges: list[dict] = []
    node_ids: set[str] = set()

    def add_node(nid: str, ntype: str) -> None:
        if nid not in node_ids:
            nodes.append({"id": nid, "type": ntype})
            node_ids.add(nid)

    for ce in inner.get("command_evidence") or []:
        if isinstance(ce, dict) and ce.get("id"):
            add_node(ce["id"], "command_evidence")
    for re_ in inner.get("result_evidence") or []:
        if isinstance(re_, dict) and re_.get("id"):
            add_node(re_["id"], "result_evidence")
    for trace_entry in inner.get("acceptance_trace") or []:
        if not isinstance(trace_entry, dict):
            continue
        acceptance_id = trace_entry.get("id") or trace_entry.get("acceptance_id")
        if not acceptance_id:
            continue
        add_node(acceptance_id, "acceptance_trace")
        for cmd_id in trace_entry.get("command_evidence_ids") or []:
            if isinstance(cmd_id, str):
                add_node(cmd_id, "command_evidence")
                edges.append({"from": acceptance_id, "to": cmd_id, "rel": "commands"})
        for res_id in trace_entry.get("result_evidence_ids") or []:
            if isinstance(res_id, str):
                add_node(res_id, "result_evidence")
                edges.append({"from": acceptance_id, "to": res_id, "rel": "results"})
    return {"nodes": nodes, "edges": edges, "built_at": _now()}


def _mission_from_path(file_path: str) -> str | None:
    m = _MISSION_PATH_RE.search(file_path or "")
    return m.group(1) if m else None


def _latest_mission(cwd: Path) -> str | None:
    stages_dir = runtime.runtime_root(cwd) / "stages"
    if not stages_dir.is_dir():
        return None
    candidates = [p for p in stages_dir.iterdir() if p.is_dir()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0].name


ENTRIES: list[HookEntry] = [
    HookEntry(id="verify-check-contract-via-cli", event="PreToolUse",
              check=check_contract_via_cli, tools=WRITE),
    HookEntry(id="verify-check-evidence-id-referenced", event="PreToolUse",
              check=check_evidence_id_referenced, tools=BASH),
    HookEntry(id="verify-deny-reviewer-write", event="PreToolUse",
              check=deny_reviewer_write, tools=WRITE),
    HookEntry(id="verify-check-worker-write-scope", event="PreToolUse",
              check=check_worker_write_scope, tools=WRITE),
    HookEntry(id="verify-deny-direct-e2e", event="PreToolUse",
              check=deny_direct_e2e, tools=BASH),
    HookEntry(id="verify-check-prereqs", event="PreToolUse",
              check=check_verify_prereqs, tools=BASH),
    HookEntry(id="verify-check-ac-evidence", event="PreToolUse",
              check=check_ac_evidence, tools=BASH | WRITE),
    HookEntry(id="verify-require-failure-path", event="PreToolUse",
              check=require_failure_path, tools=WRITE),
    HookEntry(id="verify-record-context-reads", event="PostToolUse",
              check=record_context_reads, tools=READ),
    HookEntry(id="verify-record-dispatch", event="PostToolUse",
              check=record_dispatch, tools=TASK),
    HookEntry(id="verify-record-command-flag", event="PostToolUse",
              check=record_command_flag, tools=BASH),
    HookEntry(id="verify-mirror-evidence-graph", event="PostToolUse",
              check=mirror_evidence_graph, tools=BASH),
]
