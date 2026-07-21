"""Stage hook checks: prototype-as-frontend（interaction 阶段 frontend_engineering 路线）。

frontend_engineering 路线运行在 stage=interaction 下，但产物不是 interaction.md +
interaction.contract.yaml，而是真前端工程 surface patch + frontend-changeset.md +
contracts/prototype-as-frontend.contract.yaml，审查结论由 frontend-reviewer 通过
`harness contract record-review ... --verdict PASS` 写入。

interactive_prototype 路线（design.ENTRIES）改 interaction.md → 置脏
interaction.contract.yaml；本路线缺等价的"改代码→PASS 失效"门，导致改了前端代码
后可复用旧 frontend-reviewer PASS。本模块补两条 hook：

- mark_pending_recheck（PostToolUse）：改 frontend-changeset.md → 置脏
  prototype-as-frontend.contract.yaml 的 effectiveness_review.pending_reviewer_recheck。
  frontend-changeset.md 是本路线每轮代码改动的强制载体（workflow 步骤 5 要求每次
  surface 改动都更新变更清单并重入审查员），且路径内带 mission id，是可靠的置脏触发点。
- reject_pass_without_recheck（PreToolUse Bash）：当 contract 仍 pending=true 时，
  拦截 `harness contract record-review ... --verdict PASS` 写入 frontend-reviewer PASS。
  本路线 PASS 经 Bash record-review 落盘（非 Write 产物文件），故守卫挂在 Bash 上，
  与 code-review 的 reject_pass_without_recheck 同义。

两条 hook 只在路径/命令指向 prototype-as-frontend 产物时触发，对同样跑在
stage=interaction 的 interactive_prototype 路线无副作用。
"""

from __future__ import annotations

import re

from context import HookContext
from entry import BASH, HookEntry, WRITE
from result import HookResult
from lib import commands, contracts

_CONTRACT_FILENAME = "prototype-as-frontend.contract.yaml"
_RECHECK_FIELD = "effectiveness_review.pending_reviewer_recheck"

# frontend-changeset.md 落点：harness-runtime/harness/stages/<mission>/frontend-changeset.md
_CHANGESET_PATH_RE = re.compile(
    r"harness(?:-runtime)?/harness/stages/(?P<mission>[^/]+)/frontend-changeset\.md$"
)
# record-review --artifact 里携带的 contract 路径（含 mission id）。兼容三种写法：
#   harness-runtime/harness/stages/<mission>/contracts/...                （workflow record-review 用的短写）
#   harness-runtime/harness/stages/<mission>/contracts/... （全路径）
#   harness-runtime/harness/harness/stages/<mission>/contracts/...         （历史变体）
_REVIEW_ARTIFACT_MISSION_RE = re.compile(
    r"(?:harness-runtime/)?harness-runtime/harness/(?:harness-runtime/harness/)?stages/(?P<mission>[^/]+)/"
    r"contracts/prototype-as-frontend\.contract\.yaml"
)
_RECORD_REVIEW_RE = re.compile(r"\bharness\s+contract\s+record-review\b")
_VERDICT_PASS_RE = re.compile(r"--verdict[=\s]+PASS\b")


# --- mark-pending-recheck ---------------------------------------------------
def mark_pending_recheck(ctx: HookContext) -> HookResult:
    """PostToolUse: 改 frontend-changeset.md 后，置脏
    prototype-as-frontend.contract.yaml 的 pending_reviewer_recheck=true。"""
    try:
        target = ctx.file_path
        if target is None:
            return HookResult.ok()
        rel = ctx.rel_path(target)
        match = _CHANGESET_PATH_RE.search(rel)
        if not match:
            return HookResult.ok()
        mission = match.group("mission")
        contract_path = contracts.stage_contract_path(ctx.cwd, mission, _CONTRACT_FILENAME)
        if not contract_path.exists():
            return HookResult.ok()
        contracts.set_pending_recheck(contract_path, True, field_path=_RECHECK_FIELD)
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


# --- reject-pass-without-recheck --------------------------------------------
def reject_pass_without_recheck(ctx: HookContext) -> HookResult:
    """PreToolUse Bash: 当 prototype-as-frontend.contract.yaml 仍 pending=true 时，
    拦截 `harness contract record-review ... --verdict PASS`（写 frontend-reviewer
    PASS）。强制"改代码 → 旧 PASS 失效 → 必须重审才能再 PASS"。"""
    try:
        command = ctx.command
        if not command or not _RECORD_REVIEW_RE.search(command):
            return HookResult.ok()
        if not _VERDICT_PASS_RE.search(command):
            return HookResult.ok()
        match = _REVIEW_ARTIFACT_MISSION_RE.search(command.replace("\\", "/"))
        if match is None:
            return HookResult.ok()
        mission = match.group("mission")
        contract_path = contracts.stage_contract_path(ctx.cwd, mission, _CONTRACT_FILENAME)
        if contracts.pending_recheck(contract_path, field_path=_RECHECK_FIELD):
            return HookResult.block(
                f"HarnessV2 prototype-as-frontend hook BLOCKED: {_CONTRACT_FILENAME} "
                "has pending_reviewer_recheck=true. Recording a frontend-reviewer "
                "PASS is not allowed until the reviewer has re-examined the changed "
                "frontend code. Re-run frontend-reviewer and clear the recheck flag first."
            )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


ENTRIES: list[HookEntry] = [
    HookEntry(id="prototype-as-frontend-mark-pending-recheck", event="PostToolUse",
              check=mark_pending_recheck, tools=WRITE),
    HookEntry(id="prototype-as-frontend-reject-pass-without-recheck", event="PreToolUse",
              check=reject_pass_without_recheck, tools=BASH),
]
