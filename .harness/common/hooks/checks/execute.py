"""Stage hook checks: execute.

Migrated from .harness/common/runtime-overlay/hooks/execute/ — 7 PreToolUse
hooks. The dispatcher already filters by event + tools and only invokes
these when the resolved stage is `execute`, so checks below do finer
filtering only (file_path / command / stop_if).
"""

from __future__ import annotations

from pathlib import Path

from context import HookContext
from entry import BASH, WRITE, HookEntry
from result import HookResult
from lib import commands, contracts, paths, runtime

_CONTRACT_MARKER = "execution-result.contract.yaml"
_UPSTREAM_MARKERS = (
    "/execution-brief.md",
    "/execution-brief.contract.yaml",
)
_DEP_CONFIG = "harness-runtime/config/dependency-files.yaml"


# --- check_contract_via_cli ------------------------------------------------
def check_contract_via_cli(ctx: HookContext) -> HookResult:
    file_path = ctx.file_path or ""
    if _CONTRACT_MARKER not in file_path:
        return HookResult.ok()
    return HookResult.block(
        "HarnessV2 execute hook BLOCKED: direct Write/Edit of "
        f"{_CONTRACT_MARKER} is forbidden. Use `harness contract fill/patch/"
        "add-verdict/add-execution-result --json` so schema validation and "
        "reviewer bookkeeping stay intact."
    )


# --- check_upstream_artifact_readonly --------------------------------------
def check_upstream_artifact_readonly(ctx: HookContext) -> HookResult:
    file_path = ctx.file_path or ""
    for marker in _UPSTREAM_MARKERS:
        if marker in file_path:
            return HookResult.block(
                "HarnessV2 execute hook BLOCKED: upstream artifact "
                f"{marker.strip('/')} is read-only at the execute stage. "
                "If the upstream needs revision, BLOCKED the current "
                "mission and return to breakdown via Decision Gate; do "
                "not mutate the contract from execute."
            )
    return HookResult.ok()


# --- check_gate_pass -------------------------------------------------------
def check_gate_pass(ctx: HookContext) -> HookResult:
    command = ctx.command or ""
    if not commands.is_stage_complete(command, "execute"):
        return HookResult.ok()
    mission_id = commands.mission_id(command) or ctx.mission_id
    if not mission_id:
        return HookResult.ok()
    path = contracts.stage_contract_path(
        ctx.cwd, mission_id, "execution-result.contract.yaml"
    )
    contract = contracts.load_contract(path) if path.exists() else {}
    if not contract:
        return HookResult.block(
            "HarnessV2 execute hook BLOCKED: cannot verify gate run "
            "result (execution-result.contract.yaml unloadable). Run "
            "`harness execute gate run --json` (M2.1) and capture the "
            "PASS verdict before stage complete."
        )
    eff = contract.get("effectiveness_review")
    eff = eff if isinstance(eff, dict) else {}
    status = eff.get("last_gate_run_status")
    if status != "PASS":
        return HookResult.block(
            "HarnessV2 execute hook BLOCKED: effectiveness_review."
            f"last_gate_run_status={status!r}; must be 'PASS' before "
            "`harness mission stage complete execute`. Run "
            "`harness execute gate run --json` and record the PASS result."
        )
    return HookResult.ok()


# --- stop_if hooks (effective-overlay.json driven) -------------------------
def check_stop_changes_outside_authorized(ctx: HookContext) -> HookResult:
    file_path = ctx.file_path or ""
    if not file_path:
        return HookResult.ok()
    overlay = runtime.load_overlay(ctx.cwd)
    if overlay is None:
        return HookResult.ok()
    if "changes_outside_authorized_paths" not in (overlay.get("stop_if") or []):
        return HookResult.ok()
    authorized = overlay.get("authorized_paths") or []
    target = paths.strip_runtime_prefix(file_path)
    if paths.match_any(file_path, authorized) or paths.match_any(target, authorized):
        return HookResult.ok()
    return HookResult.block(
        "HarnessV2 execute stop_if BLOCKED (changes_outside_authorized_paths): "
        f"{file_path!r} is not in the current task's authorized_paths "
        f"{authorized!r}. Record a stop event via "
        "`harness execute stop-event record --kind changes_outside_authorized_paths` "
        "before expanding the boundary."
    )


def check_stop_new_external_dependency(ctx: HookContext) -> HookResult:
    file_path = ctx.file_path or ""
    if not file_path:
        return HookResult.ok()
    overlay = runtime.load_overlay(ctx.cwd)
    if overlay is None:
        return HookResult.ok()
    if "new_external_dependency" not in (overlay.get("stop_if") or []):
        return HookResult.ok()
    patterns = _load_dep_patterns(ctx.cwd)
    basename = Path(file_path).name
    if not any(
        basename == pat or file_path.endswith("/" + pat) for pat in patterns
    ):
        return HookResult.ok()
    return HookResult.block(
        "HarnessV2 execute stop_if BLOCKED (new_external_dependency): "
        f"{file_path!r} matches a project dependency file "
        f"({patterns!r}). Mutations require Decision Gate via "
        "`harness execute stop-event record --kind new_external_dependency`."
    )


def check_stop_design_constraint_conflict(ctx: HookContext) -> HookResult:
    file_path = ctx.file_path or ""
    if not file_path:
        return HookResult.ok()
    overlay = runtime.load_overlay(ctx.cwd)
    if overlay is None:
        return HookResult.ok()
    if "design_constraint_conflict" not in (overlay.get("stop_if") or []):
        return HookResult.ok()
    prohibited = overlay.get("prohibited_paths") or []
    target = paths.strip_runtime_prefix(file_path)
    matched = None
    for pat in prohibited:
        if paths.match(file_path, pat) or paths.match(target, pat):
            matched = pat
            break
    if matched is None:
        return HookResult.ok()
    return HookResult.block(
        "HarnessV2 execute stop_if BLOCKED (design_constraint_conflict): "
        f"{file_path!r} matches prohibited_paths pattern {matched!r}. "
        "This path is forbidden by upstream design constraints; record "
        "`harness execute stop-event record --kind design_constraint_conflict` "
        "and return to design via Decision Gate."
    )


def check_stop_new_public_behavior(ctx: HookContext) -> HookResult:
    file_path = ctx.file_path or ""
    if not file_path:
        return HookResult.ok()
    overlay = runtime.load_overlay(ctx.cwd)
    if overlay is None:
        return HookResult.ok()
    if "new_public_behavior_without_delta_spec" not in (overlay.get("stop_if") or []):
        return HookResult.ok()
    # If delta specs exist for this mission, trust breakdown's coverage gate.
    if _delta_specs_present(ctx.cwd):
        return HookResult.ok()
    if bool(overlay.get("strict_public_behavior")):
        return HookResult.block(
            "HarnessV2 execute stop_if BLOCKED "
            "(new_public_behavior_without_delta_spec, strict): "
            "no delta spec found under stages/*/specs/ for this mission, "
            "but the task allows new public behavior. Confirm spec coverage "
            "and record `harness execute stop-event record "
            "--kind new_public_behavior_without_delta_spec` if intentional."
        )
    return HookResult.advise(
        "HarnessV2 execute stop_if ADVISORY "
        "(new_public_behavior_without_delta_spec): the current task allows "
        "new public behavior but no delta spec is present. Confirm spec "
        "coverage before continuing."
    )


# --- private helpers -------------------------------------------------------
def _load_dep_patterns(cwd: Path) -> list[str]:
    doc = contracts.load_yaml(cwd / _DEP_CONFIG)
    if not isinstance(doc, dict):
        return []
    patterns: list[str] = []
    for entry in doc.get("dependency_files", []) or []:
        if isinstance(entry, dict) and isinstance(entry.get("pattern"), str):
            patterns.append(entry["pattern"])
    return patterns


def _delta_specs_present(cwd: Path) -> bool:
    base = runtime.runtime_root(cwd) / "stages"
    if not base.is_dir():
        return False
    for specs_dir in base.glob("*/specs"):
        if specs_dir.is_dir() and any(specs_dir.rglob("spec.md")):
            return True
    return False


ENTRIES: list[HookEntry] = [
    HookEntry(id="execute-check-contract-via-cli", event="PreToolUse",
              check=check_contract_via_cli, tools=WRITE),
    HookEntry(id="execute-check-upstream-artifact-readonly", event="PreToolUse",
              check=check_upstream_artifact_readonly, tools=WRITE),
    HookEntry(id="execute-check-gate-pass", event="PreToolUse",
              check=check_gate_pass, tools=BASH),
    HookEntry(id="execute-check-stop-changes-outside-authorized", event="PreToolUse",
              check=check_stop_changes_outside_authorized, tools=WRITE),
    HookEntry(id="execute-check-stop-new-external-dependency", event="PreToolUse",
              check=check_stop_new_external_dependency, tools=WRITE),
    HookEntry(id="execute-check-stop-design-constraint-conflict", event="PreToolUse",
              check=check_stop_design_constraint_conflict, tools=WRITE),
    HookEntry(id="execute-check-stop-new-public-behavior", event="PreToolUse",
              check=check_stop_new_public_behavior, tools=WRITE),
]
