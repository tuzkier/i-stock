"""Stage hook checks: retrospective."""

from __future__ import annotations

from context import HookContext
from entry import BASH, TASK, WRITE, HookEntry
from result import HookResult
from lib import commands, runtime


# --- PreToolUse: write guards ----------------------------------------------
_ALLOWED_TARGETS = (
    "/retrospective.md",
    "/project-context.md",
)
_FORBIDDEN_MARKERS = (
    "/mission-status.yaml",
    "/work-graph/",
    "/contracts/",
)


def check_data_producer_zero_write(ctx: HookContext) -> HookResult:
    """Enforce retrospective-stage zero-write: only retrospective.md +
    project-context.md are writable."""
    file_path = ctx.file_path or ""
    if any(marker in file_path for marker in _ALLOWED_TARGETS):
        return HookResult.ok()
    for marker in _FORBIDDEN_MARKERS:
        if marker in file_path:
            return HookResult.block(
                "HarnessV2 retrospective hook BLOCKED: retrospective stage "
                f"may not mutate {file_path!r}. Lessons land in "
                "project-context.md; analysis lands in retrospective.md."
            )
    return HookResult.ok()


_FORBIDDEN_SECTIONS = (
    "## memory_update_contract",
    "## execution_result",
    "## role_verdicts",
)
_FORBIDDEN_YAML_KEYS = (
    "memory_update_contract:",
    "execution_result:",
    "role_verdicts:",
    "control_contract:",
)


def _contains_forbidden_content(text: str) -> str | None:
    """Description of forbidden content in retrospective.md text, or None."""
    for section in _FORBIDDEN_SECTIONS:
        if section in text:
            return f"forbidden section heading {section!r}"
    in_fence = False
    fence_content: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_fence:
                block = "\n".join(fence_content)
                for key in _FORBIDDEN_YAML_KEYS:
                    if key in block:
                        return f"fenced YAML block contains forbidden key {key!r}"
                fence_content = []
                in_fence = False
            else:
                lang = stripped[3:].strip().lower()
                if lang in {"yaml", "yml", ""}:
                    in_fence = True
        elif in_fence:
            fence_content.append(line)
    return None


def check_retrospective_markdown(ctx: HookContext) -> HookResult:
    """Deny fenced YAML contract blocks / forbidden headings in retrospective.md."""
    file_path = ctx.file_path or ""
    if "retrospective.md" not in file_path:
        return HookResult.ok()
    reason = _contains_forbidden_content(ctx.content)
    if reason:
        return HookResult.block(
            f"HarnessV2 retrospective hook BLOCKED: {reason} detected in "
            f"{file_path}. retrospective.md must not embed control YAML — "
            "write structured data to contracts/retrospective.contract.yaml "
            "via `harness contract init/patch --json`."
        )
    return HookResult.ok()


def deny_direct_contract_edit(ctx: HookContext) -> HookResult:
    """Block direct Write/Edit of retrospective.contract.yaml."""
    if "retrospective.contract.yaml" in (ctx.file_path or ""):
        return HookResult.block(
            "HarnessV2 retrospective hook BLOCKED: direct Write/Edit of "
            "retrospective.contract.yaml is forbidden. Use "
            "`harness contract init --stage retrospective` or "
            "`harness contract patch --artifact ... --json` to ensure "
            "schema validation and round bookkeeping remain intact."
        )
    return HookResult.ok()


def deny_direct_project_context_edit(ctx: HookContext) -> HookResult:
    """Block direct Write/Edit of project-context.md."""
    file_path = ctx.file_path or ""
    if file_path.endswith("project-context.md") or "/project-context.md" in file_path:
        return HookResult.block(
            "HarnessV2 retrospective hook BLOCKED: direct Write/Edit of "
            "project-context.md is forbidden during retrospective stage. "
            "Use `harness project-context add-lesson --content \"<lesson>\" --json` "
            "to append lessons with deduplication and source-mission tracking."
        )
    return HookResult.ok()


_FORBIDDEN_TEMPLATE_MARKERS = (
    ".harness/common/rules/",
    ".harness/common/skills/",
    ".harness/common/agents/",
    ".harness/common/schemas/",
    "harness-runtime/templates/",
    ".harness/common/rules/",
    ".harness/common/skills/",
    ".harness/common/agents/",
    ".harness/common/schemas/",
)


def deny_direct_template_mutation(ctx: HookContext) -> HookResult:
    """Block direct mutation of Harness template source paths."""
    file_path = (ctx.file_path or "").replace("\\", "/")
    for marker in _FORBIDDEN_TEMPLATE_MARKERS:
        if marker in file_path:
            return HookResult.block(
                f"HarnessV2 retrospective hook BLOCKED: direct mutation of "
                f"{file_path!r} is forbidden during retrospective stage. "
                "Retrospective may only produce typed learning proposals via "
                "`harness retrospective harness-gap-emit`. Template source changes "
                "require human approval and must run in a follow-up mission."
            )
    return HookResult.ok()


# --- PreToolUse: bash guard ------------------------------------------------
def require_retrospective_gate_evidence(ctx: HookContext) -> HookResult:
    """Advisory: warn when no Step 5 contract-check PASS evidence is found
    before `harness mission stage complete --stage retrospective`."""
    try:
        command = ctx.command or ""
        if not (commands.is_stage_complete(command) and "retrospective" in command):
            return HookResult.ok()

        mission_id = commands.mission_id(command) or ctx.mission_id
        if mission_id and _check_trace_evidence(ctx, mission_id):
            return HookResult.ok()

        return HookResult.advise(
            "HarnessV2 retrospective hook WARNING: no Step 5 contract-check PASS "
            "evidence found in trace log for this retrospective. Ensure "
            "`harness gate run --stage retrospective` or "
            "`harness contract check --artifact ...` returned PASS before calling "
            "stage complete."
        )
    except Exception:
        return HookResult.ok()


def _check_trace_evidence(ctx: HookContext, mission_id: str) -> bool:
    """True when traces/<mission_id>/steps.jsonl shows step5_contract_check pass."""
    import json

    trace_path = ctx.runtime_root / "traces" / mission_id / "steps.jsonl"
    if not trace_path.exists():
        return False
    try:
        lines = trace_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(record, dict)
            and record.get("step") in {"step5_contract_check", "step5", "gate_run"}
            and str(record.get("status") or "").lower() == "pass"
        ):
            return True
    return False


# --- PostToolUse: record sensor --------------------------------------------
def record_planning_analyst_dispatch(ctx: HookContext) -> HookResult:
    """Record planning-analyst dispatch in trace JSONL; BLOCK when the dispatch
    returned BLOCKED (no main-agent substitution allowed)."""
    try:
        tool_input = ctx.tool_input or {}
        command = str(tool_input.get("command") or "") + str(tool_input.get("prompt") or "")
        if "planning-analyst" not in command:
            return HookResult.ok()

        mission_id = commands.mission_id(command) or ctx.mission_id
        if not mission_id:
            return HookResult.ok()

        tool_response = ctx.tool_response or {}
        response_text = str(tool_response.get("output") or tool_response.get("content") or "")
        exit_code = ctx.raw.get("exit_code", 0)
        is_blocked = "BLOCKED" in response_text.upper() or exit_code not in {0, None}

        record = {
            "event": "planning_analyst_dispatch",
            "tool_name": ctx.tool_name,
            "status": "BLOCKED" if is_blocked else "dispatched",
            "mission_id": mission_id,
        }
        runtime.append_trace(ctx.cwd, f"traces/{mission_id}/steps.jsonl", record)

        if is_blocked:
            return HookResult.block(
                "HarnessV2 retrospective hook BLOCKED: planning-analyst dispatch "
                "returned BLOCKED. retrospective Stage 2 cannot proceed without a "
                "successful sub-agent dispatch. Investigate the dispatch failure "
                "before continuing."
            )
    except Exception:
        return HookResult.ok()
    return HookResult.ok()


ENTRIES: list[HookEntry] = [
    HookEntry(id="retrospective-check-data-producer-zero-write", event="PreToolUse", check=check_data_producer_zero_write, tools=WRITE),
    HookEntry(id="retrospective-check-markdown-structure", event="PreToolUse", check=check_retrospective_markdown, tools=WRITE),
    HookEntry(id="retrospective-deny-direct-contract-edit", event="PreToolUse", check=deny_direct_contract_edit, tools=WRITE),
    HookEntry(id="retrospective-deny-direct-project-context-edit", event="PreToolUse", check=deny_direct_project_context_edit, tools=WRITE),
    HookEntry(id="retrospective-deny-direct-template-mutation", event="PreToolUse", check=deny_direct_template_mutation, tools=WRITE),
    HookEntry(id="retrospective-require-gate-evidence", event="PreToolUse", check=require_retrospective_gate_evidence, tools=BASH),
    HookEntry(id="retrospective-record-planning-analyst-dispatch", event="PostToolUse", check=record_planning_analyst_dispatch, tools=TASK),
]
