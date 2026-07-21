---
name: harness-lint
description: '当需要检查 Harness 框架本身完整性、一致性、技能格式、阶段文档、配置或安装资产时使用。'
---

# Harness 自检 — 框架检查

## 概述

检查 HarnessV2 框架本身的健康状态：技能文件格式、配置一致性、阶段文档完整性。

## 何时使用

- 任务完成后自动触发
- 用户说"检查 harness"、"lint harness"
- 修改了 Harness 框架文件后

## 检查维度

| 维度 | 检查内容 |
|------|---------|
| SKILL.md 格式 | frontmatter 是否完整、description 是否症状驱动 |
| workflow.md 存在性 | 每个技能是否有对应的工作流 |
| 配置一致性 | harness.yaml 中的引用是否有效 |
| 阶段文档 | 当前任务的阶段文档是否齐全 |

按 `workflow.md` 执行详细步骤。
#!/usr/bin/env python3
"""Check Harness runtime asset consistency after control-plane wiring."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - optional runtime dependency
    yaml = None


TEMPLATE_CONTRACT_EXPECTATIONS = {
    "harness-runtime/templates/contracts/mission-contract.contract.yaml": ("intent_contract", None),
    "harness-runtime/templates/contracts/prd.contract.yaml": ("behaviour_contract", None),
    "harness-runtime/templates/contracts/delta-spec.contract.yaml": ("behaviour_contract", None),
    "harness-runtime/templates/contracts/execution-brief.contract.yaml": ("action_contract", None),
    "harness-runtime/templates/contracts/verification-report.contract.yaml": ("evidence_contract", "verification_evidence"),
    "harness-runtime/templates/contracts/solution.contract.yaml": ("guide_contract", "solution_guide"),
    "harness-runtime/templates/contracts/tech-design.contract.yaml": ("guide_contract", "technical_guide"),
    "harness-runtime/templates/contracts/interaction.contract.yaml": ("guide_contract", "interaction_guide"),
    "harness-runtime/templates/contracts/code-review.contract.yaml": ("evidence_contract", "review_evidence"),
    "harness-runtime/templates/contracts/retrospective.contract.yaml": ("memory_update_contract", None),
}

WORKFLOW_EXPECTATIONS = {
    ".harness/common/skills/stage-gate/workflow.md": {
        "must_reference_path": [
            "harness contract check",
            "harness evidence graph check",
            "harness gate control-reports",
            "harness gate run",
            "harness gate advance",
            "harness gate transition",
        ],
        "must_mention_concept": ["programmatic", "AI Interpretation", "Evidence Graph", "gate_effect"],
    },
    ".harness/common/skills/verify/workflow.md": {
        "must_reference_path": [
            "harness evidence command collect",
            "harness lint project",
            "harness verify true-e2e-check",
            "harness alignment check",
        ],
        "must_mention_concept": ["Verification Evidence Contract", "真实浏览器路径", "cross_check"],
    },
    ".harness/common/skills/interaction/workflow.md": {
        "must_reference_path": [
            "harness interaction spec-check",
            "harness interaction visual-coverage-check",
            "harness interaction locator-check",
            "harness interaction gate run",
            "harness alignment check",
        ],
        "must_mention_concept": ["interaction-spec", "domain model", "locator"],
    },
    ".harness/common/skills/solution/workflow.md": {
        "must_reference_path": ["harness alignment check"],
        "must_mention_concept": ["domain model", "interaction-spec"],
    },
    ".harness/common/skills/technical_analysis/workflow.md": {
        "must_reference_path": ["harness alignment check"],
        "must_mention_concept": ["交互用例实现、界面模型和路径 / 状态合同"],
    },
    ".harness/common/skills/breakdown/workflow.md": {
        "must_reference_path": ["harness alignment check"],
        "must_mention_concept": ["domain command", "state transition"],
    },
    ".harness/common/skills/code-review/workflow.md": {
        "must_reference_path": [
            ".harness/common/skills/code-review/scripts/toolchain_resolver.py",
            ".harness/common/skills/code-review/scripts/toolchain_runner.py",
            ".harness/common/skills/code-review/scripts/normalize_toolchain_status.py",
            ".harness/common/skills/code-review/scripts/e2e_obligation_policy.py",
            ".harness/common/skills/code-review/scripts/e2e_resolver.py",
            ".harness/common/skills/code-review/scripts/e2e_runner.py",
            ".harness/common/skills/code-review/scripts/normalize_e2e_status.py",
            ".harness/docs/e2e-effectiveness-reviewer-methodology.md",
            "harness review toolchain-status",
            "harness review e2e-status",
        ],
        "must_mention_concept": [
            "TDD Toolchain", "role_boundary", "E2E Control Plane", "e2e_status", "methodology_ref",
            "failure_paths", "ask-user", "harness-cli skill",
        ],
    },
    ".harness/common/skills/harness-lint/workflow.md": {
        "must_reference_path": [
            ".harness/common/skills/harness-lint/scripts/check_runtime_consistency.py",
            ".harness/common/skills/harness-lint/scripts/check_protocol_coverage.py",
            ".harness/common/skills/harness-lint/scripts/generate_drift_patch.py",
        ],
        "must_mention_concept": ["protocol", "schema"],
    },
    ".harness/common/skills/visual-interaction-design/workflow.md": {
        "must_reference_path": [
            "harness evidence visual manifest",
        ],
        "must_mention_concept": ["HTML", "visual-interaction-manifest.json", "interaction-reviewer"],
    },
    ".harness/common/skills/project-lint/workflow.md": {
        "must_reference_path": [
            "harness lint project",
            ".harness/common/skills/project-lint/scripts/bootstrap_project_lint.py",
            "project-knowledge/engineering/policies/project-lint.yaml",
        ],
        "must_mention_concept": ["command evidence", "trace lint", "project-lint-report.json", "gate_effect"],
    },
    ".harness/common/skills/skill-router/SKILL.md": {
        "must_reference_path": [".harness/common/protocols/README.md"],
        "must_mention_concept": ["quality-control", "bug-fix", "project-lint"],
    },
    ".harness/common/skills/work-graph/workflow.md": {
        "must_reference_path": [
            "harness graph apply",
            "harness graph rebuild",
            "harness graph check",
        ],
        "must_mention_concept": ["nodes/**/*.yaml", "board", "index", "tree"],
    },
    ".harness/common/skills/board-router/workflow.md": {
        "must_reference_path": [
            "harness-runtime/harness/work-graph/boards/main.yaml",
            "harness-runtime/harness/work-graph/_index.yaml",
            "harness board select",
            "harness gate advance",
        ],
        "must_mention_concept": ["Mission Slice", "graph operation"],
    },
}

CLI_COMMAND_EXPECTATIONS = [
    ["frame", "current"],
    ["frame", "explain"],
    ["graph", "apply"],
    ["graph", "plan"],
    ["graph", "rebuild"],
    ["graph", "check"],
    ["board", "select"],
    ["mission", "create-slice"],
    ["mission", "status"],
    ["mission", "stage", "start"],
    ["mission", "stage", "complete"],
    ["mission", "close"],
    ["approval", "append"],
    ["approval", "latest"],
    ["approval", "require"],
    ["contract", "init"],
    ["contract", "patch"],
    ["contract", "add-verdict"],
    ["contract", "record-review"],
    ["contract", "add-execution-result"],
    ["contract", "check"],
    ["evidence", "graph", "build"],
    ["evidence", "graph", "check"],
    ["evidence", "command", "collect"],
    ["evidence", "visual", "manifest"],
    ["evidence", "add"],
    ["evidence", "link"],
    ["gate", "run"],
    ["gate", "advance"],
    ["gate", "transition"],
    ["gate", "report", "render"],
    ["gate", "control-reports"],
    ["lint", "runtime"],
    ["lint", "graph"],
    ["lint", "project"],
    # code-review-improvement-plan M2.1: review/contract/trace commands
    ["review", "select-reviewers"],
    ["review", "snapshot-diff"],
    ["review", "toolchain-status"],
    ["review", "e2e-status"],
    ["interaction", "spec-check"],
    ["interaction", "visual-coverage-check"],
    ["interaction", "locator-check"],
    ["interaction", "gate", "run"],
    ["verify", "true-e2e-check"],
    ["alignment", "check"],
    ["contract", "add-round"],
    ["contract", "check-finding-ownership"],
    ["contract", "detect-conflicts"],
    ["trace", "report"],
    ["trace", "round-enter"],
    ["trace", "round-exit"],
]

REQUIRED_PATHS = [
    ".harness/common/cli/harness_cli.py",
    "harness-runtime/bin/harness",
    "harness-runtime/templates/mission-contract.md",
    "harness-runtime/templates/discovery-brief.md",
    "harness-runtime/templates/execution-brief.md",
    "harness-runtime/templates/acceptance-result.md",
    "harness-runtime/templates/verification-report.md",
    "harness-runtime/templates/delta-spec.md",
    "harness-runtime/templates/solution.md",
    "harness-runtime/templates/tech-design.md",
    "harness-runtime/templates/interaction.md",
    "harness-runtime/templates/code-review.md",
    "harness-runtime/templates/project-context.md",
    "harness-runtime/templates/agent-eval-report.md",
    "harness-runtime/templates/retrospective.md",
    ".harness/docs/workflow-authoring.md",
    ".harness/common/skills/stage-gate/scripts/check_contracts.py",
    ".harness/common/skills/stage-gate/scripts/check_evidence_graph.py",
    ".harness/common/skills/stage-gate/scripts/evidence_graph.py",
    ".harness/common/skills/stage-gate/scripts/obligation_policy.py",
    ".harness/common/skills/stage-gate/scripts/role_policy.py",
    ".harness/common/skills/stage-gate/scripts/render_gate_report.py",
    ".harness/common/skills/stage-gate/scripts/check_control_reports.py",
    ".harness/common/skills/code-review/scripts/toolchain_probe.py",
    ".harness/common/skills/code-review/scripts/test_obligation_policy.py",
    ".harness/common/skills/code-review/scripts/toolchain_resolver.py",
    ".harness/common/skills/code-review/scripts/toolchain_runner.py",
    ".harness/common/skills/code-review/scripts/normalize_toolchain_status.py",
    ".harness/common/skills/code-review/scripts/e2e_obligation_policy.py",
    ".harness/common/skills/code-review/scripts/e2e_resolver.py",
    ".harness/common/skills/code-review/scripts/e2e_runner.py",
    ".harness/common/skills/code-review/scripts/normalize_e2e_status.py",
    ".harness/docs/e2e-effectiveness-reviewer-methodology.md",
    ".harness/common/skills/execute/dispatch-plan.md",
    ".harness/common/skills/visual-interaction-design/SKILL.md",
    ".harness/common/skills/visual-interaction-design/workflow.md",
    ".harness/common/skills/visual-interaction-design/scripts/visual_manifest.py",
    ".harness/common/skills/project-lint/SKILL.md",
    ".harness/common/skills/project-lint/workflow.md",
    ".harness/common/skills/project-lint/scripts/run_project_lint.py",
    ".harness/common/skills/project-lint/scripts/bootstrap_project_lint.py",
    "project-knowledge/engineering/policies/project-lint.yaml",
    ".harness/common/skills/verify/scripts/collect_command_evidence.py",
    ".harness/common/skills/execute/scripts/execute_role_policy.py",
    ".harness/common/skills/harness-lint/scripts/check_runtime_consistency.py",
    ".harness/common/skills/harness-lint/scripts/build_trace_graph.py",
    ".harness/common/skills/harness-lint/scripts/check_protocol_coverage.py",
    ".harness/common/skills/harness-lint/scripts/generate_drift_patch.py",
    ".harness/common/schemas/control_contract.v1/common.yaml",
    ".harness/common/schemas/control_contract.v1/role_policy.yaml",
    ".harness/common/schemas/control_contract.v1/obligation.yaml",
    ".harness/common/schemas/control_contract.v1/evidence_graph.yaml",
    ".harness/common/schemas/control_contract.v1/gate_policy.yaml",
    ".harness/common/schemas/control_contract.v1/guide_contract.interaction_guide.yaml",
    ".harness/common/schemas/project_lint.v1/profile.yaml",
    ".harness/common/schemas/project_lint.v1/report.yaml",
    ".harness/common/agents/senior-product-expert.md",
    ".harness/common/agents/business-domain-modeler.md",
    ".harness/common/agents/acceptance-scenario-designer.md",
    ".harness/common/agents/product-scope-strategist.md",
    ".harness/common/agents/product-definition-reviewer.md",
    ".harness/common/agents/verification-engineer.md",
    ".harness/common/agents/verification-effectiveness-reviewer.md",
    ".harness/common/agents/mission-framing-expert.md",
    ".harness/common/agents/mission-contract-effectiveness-reviewer.md",
    ".harness/common/agents/solution-architect.md",
    ".harness/common/agents/solution-effectiveness-reviewer.md",
    ".harness/common/agents/technical-design-effectiveness-reviewer.md",
    ".harness/common/agents/agent-capability-designer.md",
    ".harness/common/agents/agent-capability-reviewer.md",
    ".harness/common/agents/interaction-designer.md",
    ".harness/common/agents/interaction-reviewer.md",
    ".harness/common/agents/delivery-slicer.md",
    ".harness/common/agents/test-planning-expert.md",
    ".harness/common/agents/execution-plan-effectiveness-reviewer.md",
    ".harness/common/agents/integration-impact-expert.md",
    ".harness/common/agents/dependency-validity-reviewer.md",
    ".harness/common/agents/release-readiness-expert.md",
    ".harness/common/agents/acceptance-package-reviewer.md",
    ".harness/common/agents/frontend-prototype-engineer.md",
    ".harness/common/agents/frontend-engineer.md",
    ".harness/common/agents/backend-engineer.md",
    ".harness/common/agents/client-engineer.md",
    ".harness/common/agents/security-engineer.md",
    ".harness/common/agents/test-engineer.md",
    ".harness/common/agents/debugging-expert.md",
    ".harness/common/agents/interaction-engineer.md",
    ".harness/common/agents/integration-engineer.md",
    ".harness/common/agents/data-engineer.md",
    ".harness/common/agents/refactoring-expert.md",
    ".harness/common/agents/data-migration-reviewer.md",
    ".harness/docs/tdd-toolchain.md",
    ".harness/common/protocols/README.md",
    ".harness/common/protocols/quality-control/PROTOCOL.md",
    ".harness/common/protocols/bug-fix/PROTOCOL.md",
    ".harness/common/skills/quality-control/SKILL.md",
    ".harness/common/skills/quality-control/workflow.md",
    ".harness/common/skills/bug-fix/SKILL.md",
    ".harness/common/skills/bug-fix/workflow.md",
    ".harness/common/skills/work-graph/SKILL.md",
    ".harness/common/skills/work-graph/workflow.md",
    ".harness/common/skills/work-graph/scripts/work_graph_lib.py",
    ".harness/common/skills/work-graph/scripts/rebuild_index.py",
    ".harness/common/skills/work-graph/scripts/check_graph_consistency.py",
    ".harness/common/skills/work-graph/scripts/apply_graph_operation.py",
    ".harness/common/skills/board-router/SKILL.md",
    ".harness/common/skills/board-router/workflow.md",
    ".harness/common/skills/board-router/scripts/select_next_node.py",
    ".harness/common/skills/board-router/scripts/advance_after_gate.py",
    ".harness/common/schemas/work_graph.v1/node.yaml",
    ".harness/common/schemas/work_graph.v1/graph_operation.yaml",
    ".harness/common/schemas/work_graph.v1/mission_slice.yaml",
    "harness-runtime/harness/work-graph/_index.yaml",
    "harness-runtime/harness/work-graph/boards/main.yaml",
    "harness-runtime/harness/work-graph/indexes/by-lane.yaml",
    "harness-runtime/harness/work-graph/indexes/by-kind.yaml",
    "harness-runtime/harness/work-graph/indexes/by-status.yaml",
    "harness-runtime/harness/work-graph/indexes/by-relation.yaml",
]

TEMPLATE_REFERENCE_RE = re.compile(r"harness-runtime/templates/[A-Za-z0-9_.-]+\.md")
IGNORED_TEMPLATE_REFS = {
    # Example placeholder in harness-lint docs, not a real runtime template.
    "harness-runtime/templates/xyz.md",
}
DESCRIPTION_TRIGGER_TERMS = ("当", "每次", "用户", "明确", "需要", "触发", "时", "Use when", "when", "needs", "wants")
DESCRIPTION_FORBIDDEN_SUMMARY_PATTERNS = (
    "包含",
    "Includes",
    "负责",
    "完整流程",
    "工作流",
    "comprehensive",
    "Comprehensive",
    "end-to-end",
)
FORBIDDEN_WORK_GRAPH_ROUTING_PATTERNS = (
    "work_graph.enabled",
    "Work Graph enabled",
    "Legacy stage mode",
    "legacy stage",
    "任务契约初稿",
    "dependency-impact 阶段",
    "任务接入 → git-workflow(prepare)",
    "缺 prd →",
    "缺 solution →",
    "旧 Harness 的主线是生命周期",
    "code-review → 验证 → 交付 → retrospective",
    "交付 → retrospective → close 是正确顺序",
    "work_graph.enabled=true",
    "继续下一阶段直到交付",
    "动作：commit-artifact 后进入下一阶段",
    "阶段链路从接入到收尾",
    "按阶段链路",
)
LEGACY_STAGE_QUEUE_MARKERS = (
    'mission-contract: "done"',
    'dependency-impact: "pending"',
    'execution-brief: "pending"',
    'implementation: "pending"',
    'delivery-package: "pending"',
)
WORKFLOW_DECIMAL_STEP_RE = re.compile(
    r'(?mi)^\s*(?:#{1,6}\s*)?Step\s+([0-9]+\.[0-9]+)\b'
    r'|^\s*<step\s+[^>]*\bn="([0-9]+\.[0-9]+)"'
)
WORKFLOW_LEGACY_ROOT_RE = re.compile(r"<工作流\b")
WORKFLOW_REQUIRED_ROOT_RE = re.compile(r"<workflow\b")
WORKFLOW_DENSE_TAG_RE = re.compile(
    r"<(?:action|invariant|condition|criterion|deny|allow|ask|input|artifact|"
    r"subagent|enforced_by|write_scope|package_path|disallowed_tools|validator|"
    r"call|check|loop|branch|case|hard_gate|hard-gate|user_checkpoint|"
    r"description|question|answers|answer|round_start|failure|recovery|"
    r"stage_transition|decided_by|typical_next|next)\b",
    re.IGNORECASE,
)
LEGACY_STATUS_UPDATE_RE = re.compile(
    r"更新[^\n]*(?:mission-status|`harness-runtime/harness/mission-status\.yaml`)[^\n]*`stages\."
    r"(solution|tech-design|interaction|execution-brief|implementation|verification|delivery-package):"
)


def finding(level: str, code: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "message": message}


def installed_candidates(rel: str) -> list[str]:
    candidates = [rel]
    if rel.startswith(".harness/common/"):
        candidates.append(".harness/common/" + rel.removeprefix(".harness/common/"))
    if rel.startswith("harness-runtime/"):
        candidates.append("harness-runtime/" + rel.removeprefix("harness-runtime/"))
    if rel.startswith(".harness/docs/"):
        candidates.append(".harness/docs/" + rel.removeprefix(".harness/docs/"))
    if rel.startswith("project-knowledge/"):
        candidates.append("project-knowledge/" + rel.removeprefix("project-knowledge/"))
    if rel == ".harness/workflow-map.html":
        candidates.append(".harness/workflow-map.html")
    return list(dict.fromkeys(candidates))


def existing_path(root: Path, rel: str) -> Path | None:
    for candidate in installed_candidates(rel):
        path = root / candidate
        if path.exists():
            return path
    return None


def template_reference_candidates(ref: str) -> list[str]:
    candidates = [ref]
    if ref.startswith("harness-runtime/templates/"):
        candidates.append(f"harness-runtime/{ref}")
        candidates.append(f"harness-runtime/{ref}")
    if not ref.startswith("package/"):
        candidates.append(f"package/{ref}")
    if not ref.startswith("harness-runtime/"):
        candidates.append(f"harness-runtime/{ref}")
    if ref.startswith(".harness/common/"):
        candidates.append(".harness/common/" + ref.removeprefix(".harness/common/"))
    if ref.startswith(".harness/docs/"):
        candidates.append(".harness/docs/" + ref.removeprefix(".harness/docs/"))
    return list(dict.fromkeys(candidates))


def has_contract_ref(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return bool(re.search(r"(?:Contract|Control Contract): `contracts/[^`]+\.ya?ml`", text))


def workflow_reference_variants(ref: str) -> list[str]:
    """Return source/install path spellings that are equivalent in workflows."""
    if ref.startswith((".harness/common/", ".harness/docs/")):
        return installed_candidates(ref)
    return [ref]


def parse_control_contract(path: Path) -> dict[str, Any] | None:
    if yaml is None or not path.exists():
        return None
    parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(parsed, dict):
        return None
    contract = parsed.get("control_contract")
    return contract if isinstance(contract, dict) else None


def extract_frontmatter_description(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    frontmatter = text[4:end]
    if yaml is not None:
        parsed = yaml.safe_load(frontmatter) or {}
        if isinstance(parsed, dict) and parsed.get("description") is not None:
            return str(parsed["description"]).strip()
    for line in frontmatter.splitlines():
        if line.startswith("description:"):
            value = line.removeprefix("description:").strip()
            return value.strip("'\"")
    return None


def extract_frontmatter(path: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    frontmatter = text[4:end]
    if yaml is None:
        return {}
    parsed = yaml.safe_load(frontmatter) or {}
    return parsed if isinstance(parsed, dict) else None


def check_skill_descriptions(root: Path, results: list[dict[str, str]]) -> None:
    skill_roots = [root / ".harness/common/skills", root / ".harness/common/skills"]
    for skill_root in skill_roots:
        if not skill_root.exists():
            continue
        for path in sorted(skill_root.rglob("SKILL.md")):
            description = extract_frontmatter_description(path)
            if description is None:
                results.append(finding("FAIL", "skill_description_missing", f"{path.relative_to(root)} missing frontmatter description"))
                continue
            if not any(term in description for term in DESCRIPTION_TRIGGER_TERMS):
                results.append(finding("FAIL", "skill_description_trigger_drift", f"{path.relative_to(root)} description must describe trigger conditions"))
                continue
            if any(pattern in description for pattern in DESCRIPTION_FORBIDDEN_SUMMARY_PATTERNS):
                results.append(finding("FAIL", "skill_description_summary_drift", f"{path.relative_to(root)} description appears to summarize workflow instead of trigger conditions"))
            else:
                results.append(finding("PASS", "skill_description_trigger_only", str(path.relative_to(root))))


def check_agent_frontmatter(root: Path, results: list[dict[str, str]]) -> None:
    agent_roots = [root / ".harness/common/agents", root / ".harness/common/agents"]
    for agent_root in agent_roots:
        if not agent_root.exists():
            continue
        for path in sorted(agent_root.glob("*.md")):
            frontmatter = extract_frontmatter(path)
            if frontmatter is None:
                results.append(finding("FAIL", "agent_frontmatter_missing", f"{path.relative_to(root)} missing YAML frontmatter"))
                continue
            expected = path.stem
            actual = frontmatter.get("name")
            if actual != expected:
                results.append(finding("FAIL", "agent_frontmatter_name_drift", f"{path.relative_to(root)} name must be {expected!r}, got {actual!r}"))
            else:
                results.append(finding("PASS", "agent_frontmatter_name", str(path.relative_to(root))))


def cli_path(root: Path) -> Path | None:
    return existing_path(root, ".harness/common/cli/harness_cli.py")


def shim_path(root: Path) -> Path | None:
    return existing_path(root, "harness-runtime/bin/harness")


def check_cli_command(cli: Path, tokens: list[str]) -> tuple[bool, str]:
    completed = subprocess.run(
        [sys.executable, str(cli), *tokens, "--help"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    output = completed.stdout + completed.stderr
    return completed.returncode == 0, output.strip().splitlines()[0] if output.strip() else ""


def check_cli_assets(root: Path, results: list[dict[str, str]]) -> None:
    cli = cli_path(root)
    shim = shim_path(root)
    if cli and cli.exists():
        results.append(finding("PASS", "harness_cli_exists", str(cli.relative_to(root))))
    else:
        results.append(finding("FAIL", "missing_harness_cli", "missing .harness/common/cli/harness_cli.py or .harness/common/cli/harness_cli.py"))
        return
    if shim and shim.exists():
        results.append(finding("PASS", "harness_cli_shim_exists", str(shim.relative_to(root))))
        if os.access(shim, os.X_OK):
            results.append(finding("PASS", "harness_cli_shim_executable", str(shim.relative_to(root))))
        else:
            results.append(finding("FAIL", "harness_cli_shim_not_executable", str(shim.relative_to(root))))
        shim_text = shim.read_text(encoding="utf-8", errors="ignore")
        if "harness_cli.py" in shim_text and ".harness/common/cli" in shim_text:
            results.append(finding("PASS", "harness_cli_shim_points_to_cli", str(shim.relative_to(root))))
        else:
            results.append(finding("FAIL", "harness_cli_shim_drift", f"{shim.relative_to(root)} does not locate harness_cli.py"))
    else:
        results.append(finding("FAIL", "missing_harness_cli_shim", "missing harness-runtime/bin/harness or harness-runtime/bin/harness"))

    for tokens in CLI_COMMAND_EXPECTATIONS:
        ok, message = check_cli_command(cli, tokens)
        command = "harness " + " ".join(tokens)
        if ok:
            results.append(finding("PASS", "harness_cli_command", command))
        else:
            results.append(finding("FAIL", "harness_cli_command_missing", f"{command}: {message}"))

    # intake-improvement-plan M2.1 brought trace onto the CLI control plane.
    # The per-mission JSONL trace at harness-runtime/harness/traces/<id>/steps.jsonl
    # is now CLI-owned. The narrative trace-log.md continues to live in the
    # trace-log skill and is intentionally NOT exposed via CLI.
    for sub in (["trace", "log-init"], ["trace", "report"], ["trace", "step-enter"], ["trace", "step-exit"]):
        ok, message = check_cli_command(cli, sub)
        if ok:
            results.append(finding("PASS", "harness_cli_command", "harness " + " ".join(sub)))
        else:
            results.append(finding("FAIL", "harness_cli_command_missing", f"harness {' '.join(sub)}: {message}"))


def check_prd_template_fields(root: Path, results: list[dict[str, str]]) -> None:
    """PRD-stage lint: verify prd contract template has M1.4 fields and schema coverage."""
    # W-prd-confidence-coverage: schema must declare confidence_from_discovery
    schema_path = existing_path(root, ".harness/common/schemas/control_contract.v1/behaviour_contract.yaml")
    if schema_path:
        text = schema_path.read_text(encoding="utf-8")
        if "confidence_from_discovery" in text:
            results.append(finding("PASS", "W-prd-confidence-coverage", "behaviour_contract.yaml declares confidence_from_discovery"))
        else:
            results.append(finding("FAIL", "W-prd-confidence-coverage", "behaviour_contract.yaml missing confidence_from_discovery field"))
        if "agent_capability_requirements" in text:
            results.append(finding("PASS", "W-prd-agent-cap-typed", "behaviour_contract.yaml declares agent_capability_requirements"))
        else:
            results.append(finding("FAIL", "W-prd-agent-cap-typed", "behaviour_contract.yaml missing agent_capability_requirements"))
        if "domain_model" in text and "bounded_contexts" in text and "aggregates" in text:
            results.append(finding("PASS", "W-prd-domain-model-schema", "behaviour_contract.yaml declares DDD domain_model fields"))
        else:
            results.append(finding("FAIL", "W-prd-domain-model-schema", "behaviour_contract.yaml missing DDD domain_model fields"))
    else:
        results.append(finding("WARN", "W-prd-confidence-coverage", "behaviour_contract.yaml not found; skip prd template lint"))

    # W-prd-spec-id-sync: prd contract template must reference requirement_ids in capabilities
    prd_template = existing_path(root, "harness-runtime/templates/contracts/prd.contract.yaml")
    if prd_template:
        prd_text = prd_template.read_text(encoding="utf-8")
        if "capabilities" in prd_text:
            results.append(finding("PASS", "W-prd-spec-id-sync", "prd.contract.yaml declares capabilities section"))
        else:
            results.append(finding("WARN", "W-prd-spec-id-sync", "prd.contract.yaml missing capabilities section"))
        if "domain_model" in prd_text and "bounded_contexts" in prd_text and "state_machines" in prd_text:
            results.append(finding("PASS", "W-prd-domain-model-contract", "prd.contract.yaml declares structured domain_model"))
        else:
            results.append(finding("FAIL", "W-prd-domain-model-contract", "prd.contract.yaml missing structured domain_model"))

    domain_template = existing_path(root, "harness-runtime/templates/product-domain-model.md")
    if domain_template:
        domain_text = domain_template.read_text(encoding="utf-8")
        required = ("Strategic DDD", "Tactical DDD", "Bounded Contexts", "Aggregates", "Domain Commands", "Domain Events", "Invariants", "State Machines", "Permission Matrix", "Downstream Guidance")
        missing = [item for item in required if item not in domain_text]
        if missing:
            results.append(finding("FAIL", "W-prd-domain-model-template", f"product-domain-model.md missing DDD sections: {', '.join(missing)}"))
        else:
            results.append(finding("PASS", "W-prd-domain-model-template", "product-domain-model.md includes required DDD sections"))

    # PRD professional sub-artifacts are capability contracts, not decorative
    # markdown. Each one must have a method section, a template convention
    # section, stable IDs, and workflow/agent/reviewer wiring.
    aux_templates = {
        "business-object-analysis.md": {
            "path": "harness-runtime/templates/business-object-analysis.md",
            "agent": ".harness/common/agents/business-domain-modeler.md",
            "required": (
                "## 模板约定",
                "## 使用者与使用时机",
                "## 建模方法",
                "## 输入合格性判断",
                "## 候选对象清单",
                "## 业务对象详情",
                "## 状态机总览",
                "## 业务规则",
                "## 建模取舍",
                "## 下游消费提示",
                "OBJ-xx",
                "BR-xx",
            ),
        },
        "use-case-model.md": {
            "path": "harness-runtime/templates/use-case-model.md",
            "agent": ".harness/common/agents/use-case-modeler.md",
            "required": (
                "## 模板约定",
                "## 使用者与使用时机",
                "## 建模方法",
                "## 参与者与目标矩阵",
                "## 业务用例模型",
                "## 系统边界与责任切分",
                "## 系统用例模型",
                "## 系统行为描述",
                "## 界面承载要求",
                "## 验收推导提示",
                "## 领域模型反馈",
                "BUC-xx",
                "SUC-xx",
                "SUC-xx-FLOW-xx",
                "SUC-xx-OP-xx",
                "UIC-xx",
            ),
        },
        "acceptance-scenarios.md": {
            "path": "harness-runtime/templates/acceptance-scenarios.md",
            "agent": ".harness/common/agents/acceptance-scenario-designer.md",
            "required": (
                "## 模板约定",
                "## 使用者与使用时机",
                "## 设计方法",
                "## 场景地图",
                "## 用例覆盖关系",
                "## 业务规则到场景",
                "## 验收条件",
                "## 负向与边界路径",
                "## 验证证据计划",
                "SCN-xx",
                "SCN-xx-COND-xx",
            ),
        },
        "scope-strategy.md": {
            "path": "harness-runtime/templates/scope-strategy.md",
            "agent": ".harness/common/agents/product-scope-strategist.md",
            "required": (
                "## 模板约定",
                "## 使用者与使用时机",
                "## 判断方法",
                "## 授权边界",
                "## 范围决策表",
                "## 用例范围闭环",
                "## 判断理由",
                "## 依赖与风险",
                "## 方案阶段路线约束",
                "SCOPE-xx",
                "DECISION_NEEDED",
            ),
        },
    }
    prd_workflow = existing_path(root, ".harness/common/skills/prd/workflow.md")
    workflow_text = prd_workflow.read_text(encoding="utf-8") if prd_workflow else ""
    reviewer = existing_path(root, ".harness/common/agents/product-definition-reviewer.md")
    reviewer_text = reviewer.read_text(encoding="utf-8") if reviewer else ""
    for name, spec in aux_templates.items():
        template_path = existing_path(root, spec["path"])
        if not template_path:
            results.append(finding("FAIL", "W-prd-professional-template", f"{name} template is missing"))
            continue
        template_text = template_path.read_text(encoding="utf-8")
        missing = [item for item in spec["required"] if item not in template_text]
        if missing:
            results.append(finding("FAIL", "W-prd-professional-template", f"{name} missing method/template sections: {', '.join(missing)}"))
        else:
            results.append(finding("PASS", "W-prd-professional-template", f"{name} includes method and template conventions"))

        agent_path = existing_path(root, spec["agent"])
        agent_text = agent_path.read_text(encoding="utf-8") if agent_path else ""
        template_ref = f"harness-runtime/templates/{name}"
        if template_ref in agent_text and "必须使用" in agent_text:
            results.append(finding("PASS", "W-prd-professional-agent-wiring", f"{spec['agent']} requires {template_ref}"))
        else:
            results.append(finding("FAIL", "W-prd-professional-agent-wiring", f"{spec['agent']} does not require {template_ref}"))

        if template_ref in workflow_text and "<method_conventions>" in workflow_text:
            results.append(finding("PASS", "W-prd-professional-workflow-wiring", f"prd workflow passes {template_ref} through method conventions/task envelope"))
        else:
            results.append(finding("FAIL", "W-prd-professional-workflow-wiring", f"prd workflow does not wire {template_ref}"))

    if "专业模板完整性" in reviewer_text and "specialist_template_compliance" in reviewer_text:
        results.append(finding("PASS", "W-prd-professional-reviewer-check", "product-definition-reviewer checks specialist template compliance"))
    else:
        results.append(finding("FAIL", "W-prd-professional-reviewer-check", "product-definition-reviewer missing specialist template compliance check"))


def check_breakdown_template_fields(root: Path, results: list[dict[str, str]]) -> None:
    """breakdown-improvement-plan M4.2 lint: verify execution-brief template
    + schema carry the M1.4 fields the workflow / hooks depend on. Subset of
    the 17 W-execution-brief rules plan §M4.2 calls out; the rest are
    enforced at runtime by `harness execution-brief gate run` (Group A-E).
    """
    schema_path = existing_path(
        root, ".harness/common/schemas/control_contract.v1/action_contract.yaml"
    )
    if schema_path and yaml is not None:
        schema_text = schema_path.read_text(encoding="utf-8")
        # W-execution-brief-rounds-used: schema must declare effectiveness_review.rounds_used
        if "rounds_used" in schema_text:
            results.append(
                finding(
                    "PASS",
                    "W-execution-brief-rounds-used",
                    "action_contract.yaml declares effectiveness_review.rounds_used",
                )
            )
        else:
            results.append(
                finding(
                    "FAIL",
                    "W-execution-brief-rounds-used",
                    "action_contract.yaml missing effectiveness_review.rounds_used field",
                )
            )
        # W-execution-brief-execution-results-list: list form must be the
        # accepted shape (plural).
        if "execution_results" in schema_text:
            results.append(
                finding(
                    "PASS",
                    "W-execution-brief-execution-results-list",
                    "action_contract.yaml declares execution_results[] list form",
                )
            )
        else:
            results.append(
                finding(
                    "FAIL",
                    "W-execution-brief-execution-results-list",
                    "action_contract.yaml missing execution_results[] list form (M1.4 migration)",
                )
            )
        # W-execution-brief-evidence-id: required_evidence[].id must be required.
        if "required_evidence" in schema_text and "id" in schema_text:
            results.append(
                finding(
                    "PASS",
                    "W-execution-brief-evidence-id",
                    "action_contract.yaml declares required_evidence[].id (H3 primary key)",
                )
            )
        else:
            results.append(
                finding(
                    "FAIL",
                    "W-execution-brief-evidence-id",
                    "action_contract.yaml missing required_evidence[].id field",
                )
            )
    else:
        results.append(
            finding(
                "WARN",
                "W-execution-brief-schema",
                "action_contract.yaml not found; skip breakdown schema lint",
            )
        )
    # W-execution-brief-template-list-form: template must use execution_results[].
    template = existing_path(
        root, "harness-runtime/templates/contracts/execution-brief.contract.yaml"
    )
    if template:
        text = template.read_text(encoding="utf-8")
        if "execution_results:" in text:
            results.append(
                finding(
                    "PASS",
                    "W-execution-brief-template-list-form",
                    "execution-brief.contract.yaml template uses execution_results[] (M1.4)",
                )
            )
        else:
            results.append(
                finding(
                    "FAIL",
                    "W-execution-brief-template-list-form",
                    "execution-brief.contract.yaml template still on legacy singular execution_result form",
                )
            )
        if "barrier_group" in text:
            results.append(
                finding(
                    "PASS",
                    "W-execution-brief-barrier-group",
                    "execution-brief.contract.yaml template declares barrier_group",
                )
            )
        else:
            results.append(
                finding(
                    "WARN",
                    "W-execution-brief-barrier-group",
                    "execution-brief.contract.yaml template missing barrier_group (breakdown parallel-worker hook may not fire)",
                )
            )
    # W-execution-brief-hooks: install pipeline must wire the breakdown hook
    # manifest.
    hook_manifest = existing_path(
        root, ".harness/common/runtime-overlay/hooks/breakdown/hooks.json"
    )
    if hook_manifest:
        try:
            manifest = json.loads(hook_manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
        scripts = {entry.get("script") for entry in manifest.get("hooks") or []}
        critical = {
            "check_contract_via_cli.py",
            "check_first_write_completeness.py",
            "check_writing_plans_boundary.py",
            "check_barrier_complete.py",
            "check_gate_pass.py",
        }
        missing = critical - scripts
        if missing:
            results.append(
                finding(
                    "FAIL",
                    "W-execution-brief-hooks",
                    f"breakdown hooks.json missing critical scripts: {sorted(missing)}",
                )
            )
        else:
            results.append(
                finding(
                    "PASS",
                    "W-execution-brief-hooks",
                    "breakdown hooks.json registers all 5 critical breakdown hooks",
                )
            )
    else:
        results.append(
            finding(
                "FAIL",
                "W-execution-brief-hooks",
                ".harness/common/runtime-overlay/hooks/breakdown/hooks.json missing",
            )
        )


def check_verify_template_fields(root: Path, results: list[dict[str, str]]) -> None:
    """verify-improvement-plan M4 lint: check that verify workflow, schema, template,
    and hook manifest carry the M2-M3 fields the workflow and hooks depend on.

    Rules (W-verify-*):
      W-verify-workflow: workflow.md has Step 0, failure_paths, check-acceptance-trace call,
        gate run call, and no bare spawn_agent.
      W-verify-schema: verification_evidence schema has required_evidence_id field.
      W-verify-template: verification-report.contract.yaml template has acceptance_trace,
        command_evidence, result_evidence fields.
      W-verify-hooks: hooks.json registers all critical verify hooks.
    """
    # W-verify-workflow
    workflow_path = existing_path(root, ".harness/common/skills/verify/workflow.md")
    if workflow_path:
        wf_text = workflow_path.read_text(encoding="utf-8")
        workflow_checks = [
            ('n="0"', "W-verify-workflow-step0", "verify workflow has Step 0"),
            ("failure_paths", "W-verify-workflow-failure-paths", "verify workflow has <failure_paths> section"),
            ("check-acceptance-trace", "W-verify-workflow-check-acceptance-trace", "verify workflow calls contract check-acceptance-trace"),
            ("verify gate run", "W-verify-workflow-gate-run", "verify workflow calls verify gate run"),
        ]
        for marker, code, pass_msg in workflow_checks:
            if marker in wf_text:
                results.append(finding("PASS", code, pass_msg))
            else:
                results.append(finding("FAIL", code, f"verify workflow missing: {marker!r}"))
        # Flag only actual spawn_agent calls (backtick-wrapped or function-call style),
        # not documentation prose that mentions the term.
        import re as _re
        _spawn_call_pat = _re.compile(r"(`spawn_agent`|spawn_agent\s*\()")
        if _spawn_call_pat.search(wf_text):
            results.append(finding(
                "FAIL",
                "W-verify-workflow-no-spawn-agent",
                "verify workflow still contains bare spawn_agent call; use workflow-native subagent dispatch prose",
            ))
        else:
            results.append(finding(
                "PASS",
                "W-verify-workflow-no-spawn-agent",
                "verify workflow uses workflow-native subagent dispatch prose, not spawn_agent",
            ))
    else:
        results.append(finding(
            "WARN",
            "W-verify-workflow",
            ".harness/common/skills/verify/workflow.md not found; skip verify workflow lint",
        ))

    # W-verify-schema: required_evidence_id (H3 primary key, M1.4)
    schema_path = existing_path(
        root,
        ".harness/common/schemas/control_contract.v1/evidence_contract.verification_evidence.yaml",
    )
    if schema_path:
        schema_text = schema_path.read_text(encoding="utf-8")
        if "required_evidence_id" in schema_text:
            results.append(finding(
                "PASS",
                "W-verify-schema-required-evidence-id",
                "evidence_contract.verification_evidence.yaml declares required_evidence_id (H3 anchor)",
            ))
        else:
            results.append(finding(
                "FAIL",
                "W-verify-schema-required-evidence-id",
                "evidence_contract.verification_evidence.yaml missing required_evidence_id field (M1.4 H3 anchor)",
            ))
    else:
        results.append(finding(
            "WARN",
            "W-verify-schema",
            "evidence_contract.verification_evidence.yaml not found; skip verify schema lint",
        ))

    # W-verify-template: acceptance_trace, command_evidence, result_evidence
    template_path = existing_path(
        root,
        "harness-runtime/templates/contracts/verification-report.contract.yaml",
    )
    if template_path:
        tmpl_text = template_path.read_text(encoding="utf-8")
        for marker, code, pass_msg in [
            ("acceptance_trace", "W-verify-template-acceptance-trace", "verification-report.contract.yaml declares acceptance_trace"),
            ("command_evidence", "W-verify-template-command-evidence", "verification-report.contract.yaml declares command_evidence"),
            ("result_evidence", "W-verify-template-result-evidence", "verification-report.contract.yaml declares result_evidence"),
        ]:
            if marker in tmpl_text:
                results.append(finding("PASS", code, pass_msg))
            else:
                results.append(finding("FAIL", code, f"verification-report.contract.yaml missing: {marker!r}"))
    else:
        results.append(finding(
            "WARN",
            "W-verify-template",
            "harness-runtime/templates/contracts/verification-report.contract.yaml not found; skip verify template lint",
        ))

    # W-verify-hooks: critical hooks from M1.4 + M3.1
    hook_manifest = existing_path(
        root, ".harness/common/runtime-overlay/hooks/verify/hooks.json"
    )
    if hook_manifest:
        try:
            manifest = json.loads(hook_manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
        scripts = {entry.get("script") for entry in manifest.get("hooks") or []}
        critical = {
            "check_contract_via_cli.py",
            "check_evidence_id_referenced.py",
            "deny_reviewer_write.py",
            "check_worker_write_scope.py",
            "deny_direct_e2e.py",
            "check_verify_prereqs.py",
            "check_ac_evidence.py",
            "require_failure_path.py",
        }
        missing = critical - scripts
        if missing:
            results.append(finding(
                "FAIL",
                "W-verify-hooks",
                f"verify hooks.json missing critical scripts: {sorted(missing)}",
            ))
        else:
            results.append(finding(
                "PASS",
                "W-verify-hooks",
                "verify hooks.json registers all 8 critical verify hooks",
            ))
    else:
        results.append(finding(
            "FAIL",
            "W-verify-hooks",
            ".harness/common/runtime-overlay/hooks/verify/hooks.json missing",
        ))


def check_delivery_template_fields(root: Path, results: list[dict[str, str]]) -> None:
    """delivery-improvement-plan M4 lint: check delivery schema, contract
    template, hook manifest, and workflow.

    Rules (W-delivery-*):
      W-delivery-schema: delivery_contract.yaml schema exists.
      W-delivery-template: delivery.contract.yaml template exists.
      W-delivery-hooks: hooks.json registers all critical delivery hooks.
      W-delivery-workflow-no-spawn-agent: workflow.md has no bare spawn_agent.
      W-delivery-workflow-no-auto-continue: workflow.md does not say the
        autonomy loop auto-schedules retrospective.
    """
    import re as _re

    schema_path = existing_path(
        root, ".harness/common/schemas/control_contract.v1/delivery_contract.yaml"
    )
    if schema_path:
        results.append(finding(
            "PASS", "W-delivery-schema",
            "delivery_contract.yaml schema exists",
        ))
    else:
        results.append(finding(
            "FAIL", "W-delivery-schema",
            ".harness/common/schemas/control_contract.v1/delivery_contract.yaml missing",
        ))

    template_path = existing_path(
        root, "harness-runtime/templates/contracts/delivery.contract.yaml"
    )
    if template_path:
        results.append(finding(
            "PASS", "W-delivery-template",
            "delivery.contract.yaml template exists",
        ))
    else:
        results.append(finding(
            "FAIL", "W-delivery-template",
            "harness-runtime/templates/contracts/delivery.contract.yaml missing",
        ))

    hook_manifest = existing_path(
        root, ".harness/common/runtime-overlay/hooks/delivery/hooks.json"
    )
    if hook_manifest:
        try:
            manifest = json.loads(hook_manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
        scripts = {entry.get("script") for entry in manifest.get("hooks") or []}
        critical = {
            "check_contract_via_cli.py",
            "check_acceptance_write.py",
            "check_delivery_package_write.py",
            "deny_direct_approval_edit.py",
            "deny_direct_mission_status_edit.py",
            "deny_direct_workgraph_edit.py",
            "deny_git_danger.py",
            "require_handoff_pause.py",
            "mark_acceptance_written.py",
            "mark_delivery_package_written.py",
            "record_followup_graph_op.py",
            "record_acceptance_checkpoint.py",
            "record_delivery_gate.py",
        }
        missing = critical - scripts
        if missing:
            results.append(finding(
                "FAIL", "W-delivery-hooks",
                f"delivery hooks.json missing critical scripts: {sorted(missing)}",
            ))
        else:
            results.append(finding(
                "PASS", "W-delivery-hooks",
                "delivery hooks.json registers all 13 critical delivery hooks",
            ))
    else:
        results.append(finding(
            "FAIL", "W-delivery-hooks",
            ".harness/common/runtime-overlay/hooks/delivery/hooks.json missing",
        ))

    workflow_path = existing_path(root, ".harness/common/skills/delivery/workflow.md")
    if workflow_path:
        wf_text = workflow_path.read_text(encoding="utf-8")
        if "spawn_agent" in wf_text:
            results.append(finding(
                "FAIL", "W-delivery-workflow-no-spawn-agent",
                "delivery workflow still contains spawn_agent; use workflow-native subagent dispatch prose",
            ))
        else:
            results.append(finding(
                "PASS", "W-delivery-workflow-no-spawn-agent",
                "delivery workflow uses workflow-native subagent dispatch prose, not spawn_agent",
            ))
        if "自治循环将自动调度" in wf_text or "将自动调度 retrospective" in wf_text:
            results.append(finding(
                "FAIL", "W-delivery-workflow-no-auto-continue",
                "delivery workflow must not auto-schedule retrospective; use handoff --pause",
            ))
        else:
            results.append(finding(
                "PASS", "W-delivery-workflow-no-auto-continue",
                "delivery workflow declares a handoff pause boundary, no auto-continue",
            ))
    else:
        results.append(finding(
            "WARN", "W-delivery-workflow",
            ".harness/common/skills/delivery/workflow.md not found; skip delivery workflow lint",
        ))


def check_work_graph_primary_routing(root: Path, results: list[dict[str, str]])-> None:
    has_failure = False
    config_path = existing_path(root, "harness-runtime/config/harness.yaml")
    if yaml is not None and config_path:
        config_text = config_path.read_text(encoding="utf-8")
        config = yaml.safe_load(config_text) or {}
        work_graph = config.get("work_graph") if isinstance(config.get("work_graph"), dict) else {}
        if "enabled" in work_graph:
            has_failure = True
            results.append(finding("FAIL", "work_graph_enabled_flag_forbidden", f"{config_path.relative_to(root)} must not define work_graph.enabled"))
        else:
            results.append(finding("PASS", "work_graph_primary_config", f"{config_path.relative_to(root)} has no work_graph.enabled switch"))
        for pattern in FORBIDDEN_WORK_GRAPH_ROUTING_PATTERNS:
            if pattern in config_text:
                has_failure = True
                results.append(finding("FAIL", "work_graph_compat_branch_forbidden", f"{config_path.relative_to(root)} contains {pattern!r}"))

    routing_roots = [
        root / ".harness/common/rules",
        root / ".harness/common/skills",
        root / ".harness/common/agents",
        root / ".harness/docs",
        root / ".harness/common/rules",
        root / ".harness/common/skills",
        root / ".harness/common/agents",
        root / ".harness/docs",
    ]
    routing_files = [
        root / "README.md",
        root / "package/README.md",
        root / ".harness/workflow-map.html",
        root / ".harness/workflow-map.html",
    ]
    for routing_root in routing_roots:
        if not routing_root.exists():
            continue
        for pattern_glob in ("*.md", "*.html"):
            for path in sorted(routing_root.rglob(pattern_glob)):
                text = path.read_text(encoding="utf-8")
                for pattern in FORBIDDEN_WORK_GRAPH_ROUTING_PATTERNS:
                    if pattern in text:
                        has_failure = True
                        results.append(finding("FAIL", "work_graph_compat_branch_forbidden", f"{path.relative_to(root)} contains {pattern!r}"))
                if path.match("*/intake/workflow.md") and all(marker in text for marker in LEGACY_STAGE_QUEUE_MARKERS):
                    has_failure = True
                    results.append(finding("FAIL", "legacy_stage_queue_forbidden", f"{path.relative_to(root)} initializes the old full pending stage queue"))
                if path.name == "workflow.md":
                    for match in WORKFLOW_DECIMAL_STEP_RE.finditer(text):
                        decimal_step = next(value for value in match.groups() if value)
                        has_failure = True
                        results.append(finding("FAIL", "workflow_decimal_step_forbidden", f"{path.relative_to(root)} uses decimal step {decimal_step}; renumber later steps instead"))
                if path.match("*/intake/workflow.md"):
                    # intake-improvement-plan M2.2 reorganized intake into 6
                    # phases. The invariant being enforced is: Mission Slice
                    # creation must precede mission-framing-expert dispatch
                    # AND precede final mission-contract construction.
                    ordered_markers = [
                        'phase="1"',  # Intent & Work Graph binding (creates Mission Slice)
                        'phase="2"',  # Framing (dispatches mission-framing-expert)
                        'phase="4"',  # Contract Construction
                        'phase="5"',  # Review & Gate
                    ]
                    if all(marker in text for marker in ordered_markers):
                        positions = [text.index(marker) for marker in ordered_markers]
                        if positions != sorted(positions):
                            has_failure = True
                            results.append(finding("FAIL", "intake_work_graph_order_invalid", f"{path.relative_to(root)} must create Mission Slice before mission-framing-expert"))
                    else:
                        has_failure = True
                        results.append(finding("FAIL", "intake_work_graph_order_missing", f"{path.relative_to(root)} is missing Work Graph-first intake phase markers"))
                for match in LEGACY_STATUS_UPDATE_RE.finditer(text):
                    has_failure = True
                    results.append(finding("FAIL", "legacy_stage_status_update_forbidden", f"{path.relative_to(root)} updates old stage key {match.group(1)!r}"))
    for path in routing_files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_WORK_GRAPH_ROUTING_PATTERNS:
            if pattern in text:
                has_failure = True
                results.append(finding("FAIL", "work_graph_compat_branch_forbidden", f"{path.relative_to(root)} contains {pattern!r}"))
    if not has_failure:
        results.append(finding("PASS", "work_graph_primary_routing", "runtime rules use Board / Mission Slice as the primary chain"))


def check_workflow_authoring_style(root: Path, results: list[dict[str, str]]) -> None:
    """Enforce the workflow-authoring.md contract.

    Workflow files should use an XML outer shell with Markdown section bodies.
    Fine-grained row tags are intentionally blocked unless a future parser owns
    them explicitly. Workflow-authored <permissions> blocks are retired; the
    legacy parser remains only for backward compatibility tests and old inputs.
    """
    workflow_roots = [
        root / ".harness/common/skills",
        root / ".harness/common/skills",
        root / ".claude/skills",
        root / ".opencode/skills",
    ]
    checked = 0
    failures = 0
    for workflow_root in workflow_roots:
        if not workflow_root.exists():
            continue
        for path in sorted(workflow_root.glob("*/workflow.md")):
            checked += 1
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(root)
            if WORKFLOW_LEGACY_ROOT_RE.search(text):
                failures += 1
                results.append(finding("FAIL", "workflow_legacy_root_forbidden", f"{rel} uses <工作流>; use <workflow ...>"))
            root_matches = WORKFLOW_REQUIRED_ROOT_RE.findall(text)
            if len(root_matches) != 1:
                failures += 1
                results.append(finding("FAIL", "workflow_root_count_invalid", f"{rel} must contain exactly one <workflow> root, found {len(root_matches)}"))
            if "<permissions>" in text or "</permissions>" in text:
                if str(rel).startswith(".harness/common/skills/"):
                    failures += 1
                    results.append(finding("FAIL", "workflow_permissions_forbidden", f"{rel} uses retired <permissions>; move guards to runtime-overlay hooks, role policy, CLI gate, or adapter config"))
                else:
                    results.append(finding("WARN", "workflow_permissions_in_installed_copy", f"{rel} still has retired <permissions>; source template lint only fails .harness/common/skills"))
            dense_match = WORKFLOW_DENSE_TAG_RE.search(text)
            if dense_match:
                failures += 1
                results.append(finding("FAIL", "workflow_dense_tag_forbidden", f"{rel} contains dense row tag {dense_match.group(0)!r}; use Markdown tables/lists inside section tags"))
        dispatch_plan = workflow_root / "execute" / "dispatch-plan.md"
        if dispatch_plan.exists():
            checked += 1
            text = dispatch_plan.read_text(encoding="utf-8")
            rel = dispatch_plan.relative_to(root)
            if WORKFLOW_LEGACY_ROOT_RE.search(text):
                failures += 1
                results.append(finding("FAIL", "workflow_legacy_root_forbidden", f"{rel} uses <工作流>; use <workflow ...>"))
            root_matches = WORKFLOW_REQUIRED_ROOT_RE.findall(text)
            if len(root_matches) != 1:
                failures += 1
                results.append(finding("FAIL", "workflow_root_count_invalid", f"{rel} must contain exactly one <workflow> root, found {len(root_matches)}"))
            if "<permissions>" in text or "</permissions>" in text:
                if str(rel).startswith(".harness/common/skills/"):
                    failures += 1
                    results.append(finding("FAIL", "workflow_permissions_forbidden", f"{rel} uses retired <permissions>; move guards to runtime-overlay hooks, role policy, CLI gate, or adapter config"))
                else:
                    results.append(finding("WARN", "workflow_permissions_in_installed_copy", f"{rel} still has retired <permissions>; source template lint only fails .harness/common/skills"))
            dense_match = WORKFLOW_DENSE_TAG_RE.search(text)
            if dense_match:
                failures += 1
                results.append(finding("FAIL", "workflow_dense_tag_forbidden", f"{rel} contains dense row tag {dense_match.group(0)!r}; use Markdown tables/lists inside section tags"))
    if checked and not failures:
        results.append(finding("PASS", "workflow_authoring_style", f"{checked} workflow.md files follow XML outer + Markdown inner style"))


def check_code_review_template_fields(root: Path, results: list[dict[str, str]]) -> None:
    """code-review-improvement-plan M4.2 lint: verify code-review hooks, schema, and contract template.

    Emits W-code-review-hooks, W-code-review-schema, W-code-review-contract-template findings.
    """
    # W-code-review-hooks: hooks.json must register all M3.1 critical scripts
    hooks_manifest = existing_path(root, ".harness/common/runtime-overlay/hooks/code-review/hooks.json")
    if hooks_manifest:
        try:
            manifest = json.loads(hooks_manifest.read_text(encoding="utf-8"))
            scripts = {entry.get("script", "") for entry in manifest.get("hooks", [])}
            critical = {
                "check_contract_via_cli.py",
                "check_review_ready.py",
                "deny_reviewer_write.py",
                "deny_dangerous_git.py",
                "mark_pending_recheck.py",
                "reject_pass_without_recheck.py",
                "record_dispatch_envelope.py",
            }
            missing = critical - scripts
            if missing:
                results.append(
                    finding(
                        "FAIL",
                        "W-code-review-hooks",
                        f"hooks.json missing critical scripts: {sorted(missing)}",
                    )
                )
            else:
                results.append(
                    finding(
                        "PASS",
                        "W-code-review-hooks",
                        "hooks.json registers all 7 critical code-review M3.1 scripts",
                    )
                )
        except (json.JSONDecodeError, OSError) as exc:
            results.append(
                finding("FAIL", "W-code-review-hooks", f"hooks.json unreadable: {exc}")
            )
    else:
        results.append(
            finding("FAIL", "W-code-review-hooks", ".harness/common/runtime-overlay/hooks/code-review/hooks.json missing")
        )

    # W-code-review-schema: behaviour_contract.yaml must declare review_evidence fields
    schema_path = existing_path(
        root, ".harness/common/schemas/control_contract.v1/evidence_contract.review_evidence.yaml"
    )
    if schema_path:
        text = schema_path.read_text(encoding="utf-8")
        required_fields = ["pending_reviewer_recheck", "rounds_used", "role_verdicts"]
        missing_fields = [f for f in required_fields if f not in text]
        if missing_fields:
            results.append(
                finding(
                    "FAIL",
                    "W-code-review-schema",
                    f"review_evidence schema missing fields: {missing_fields}",
                )
            )
        else:
            results.append(
                finding(
                    "PASS",
                    "W-code-review-schema",
                    "review_evidence schema declares pending_reviewer_recheck, rounds_used, role_verdicts",
                )
            )
    else:
        results.append(
            finding(
                "WARN",
                "W-code-review-schema",
                "evidence_contract.review_evidence.yaml not found; skip code-review schema lint",
            )
        )

    # W-code-review-contract-template: code-review contract template must declare review_evidence fields
    cr_template = existing_path(
        root, "harness-runtime/templates/contracts/code-review.contract.yaml"
    )
    if cr_template and yaml is not None:
        cr_text = cr_template.read_text(encoding="utf-8")
        required_template_fields = ["pending_reviewer_recheck", "rounds_used", "role_verdicts"]
        missing_template = [f for f in required_template_fields if f not in cr_text]
        if missing_template:
            results.append(
                finding(
                    "FAIL",
                    "W-code-review-contract-template",
                    f"code-review.contract.yaml template missing fields: {missing_template}",
                )
            )
        else:
            results.append(
                finding(
                    "PASS",
                    "W-code-review-contract-template",
                    "code-review contract template declares pending_reviewer_recheck, rounds_used, role_verdicts",
                )
            )
    else:
        results.append(
            finding(
                "WARN",
                "W-code-review-contract-template",
                "harness-runtime/templates/contracts/code-review.contract.yaml not found; skip template lint",
            )
        )


def check_retrospective_template_fields(root: Path, results: list[dict[str, str]]) -> None:
    """retrospective-improvement-plan M4 lint: verify retrospective hooks, schemas, and workflow.

    Emits W-retrospective-hooks, W-retrospective-schemas, W-retrospective-workflow-no-spawn findings.
    """
    # W-retrospective-hooks: hooks.json must register all M3.1 critical scripts
    hooks_manifest = existing_path(root, ".harness/common/runtime-overlay/hooks/retrospective/hooks.json")
    if hooks_manifest:
        try:
            manifest = json.loads(hooks_manifest.read_text(encoding="utf-8"))
            scripts = {entry.get("script", "") for entry in manifest.get("hooks", [])}
            critical = {
                "check_data_producer_zero_write.py",
                "check_retrospective_markdown.py",
                "deny_direct_contract_edit.py",
                "deny_direct_project_context_edit.py",
                "deny_direct_template_mutation.py",
                "require_retrospective_gate_evidence.py",
                "record_planning_analyst_dispatch.py",
            }
            missing = critical - scripts
            if missing:
                results.append(
                    finding(
                        "FAIL",
                        "W-retrospective-hooks",
                        f"retrospective hooks.json missing critical scripts: {sorted(missing)}",
                    )
                )
            else:
                results.append(
                    finding(
                        "PASS",
                        "W-retrospective-hooks",
                        "retrospective hooks.json registers all 7 critical M3.1 scripts",
                    )
                )
        except (json.JSONDecodeError, OSError) as exc:
            results.append(
                finding("FAIL", "W-retrospective-hooks", f"retrospective hooks.json unreadable: {exc}")
            )
    else:
        results.append(
            finding("FAIL", "W-retrospective-hooks", ".harness/common/runtime-overlay/hooks/retrospective/hooks.json missing")
        )

    # W-retrospective-schemas: all M4 typed schema files must exist
    required_schemas = [
        ".harness/common/schemas/control_contract.v1/learning_proposal_contract.yaml",
        ".harness/common/schemas/control_contract.v1/retrospective_policy.yaml",
        ".harness/common/schemas/control_contract.v1/harness_gap_contract.yaml",
        ".harness/common/schemas/control_contract.v1/project_context_policy.yaml",
        ".harness/common/schemas/control_contract.v1/agent_eval_drift_contract.yaml",
    ]
    missing_schemas = [s for s in required_schemas if not existing_path(root, s)]
    if missing_schemas:
        results.append(
            finding(
                "FAIL",
                "W-retrospective-schemas",
                f"retrospective typed schema files missing: {missing_schemas}",
            )
        )
    else:
        results.append(
            finding(
                "PASS",
                "W-retrospective-schemas",
                "all 5 retrospective M4 typed schema files present",
            )
        )

    # W-retrospective-workflow-no-spawn: workflow.md must not contain bare spawn_agent call
    workflow_path = existing_path(root, ".harness/common/skills/retrospective/workflow.md")
    if workflow_path:
        wf_text = workflow_path.read_text(encoding="utf-8")
        if "spawn_agent" in wf_text:
            results.append(
                finding(
                    "FAIL",
                    "W-retrospective-workflow-no-spawn",
                    "retrospective workflow.md contains bare spawn_agent; must use workflow-native subagent dispatch prose",
                )
            )
        else:
            results.append(
                finding(
                    "PASS",
                    "W-retrospective-workflow-no-spawn",
                    "retrospective workflow.md uses workflow-native subagent dispatch prose (no bare spawn_agent)",
                )
            )
    else:
        results.append(
            finding(
                "WARN",
                "W-retrospective-workflow-no-spawn",
                ".harness/common/skills/retrospective/workflow.md not found; skip spawn_agent lint",
            )
        )


def check_finishing_branch_template_fields(root: Path, results: list[dict[str, str]]) -> None:
    """finishing-branch-improvement-plan M4.3 lint.

    Emits W-finishing-contract-template, W-finishing-hooks, W-finishing-mission-close-enum,
    W-finishing-cli-commands, W-finishing-workflow-failure-paths, W-finishing-workflow-no-bare-git,
    W-finishing-workflow-evidence-summary, W-finishing-workflow-no-direct-mutation.
    """
    # W-finishing-contract-template: contract template must exist
    contract_template = existing_path(
        root, "harness-runtime/templates/contracts/finishing-branch.contract.yaml"
    )
    if contract_template:
        results.append(finding(
            "PASS", "W-finishing-contract-template",
            "finishing-branch.contract.yaml template exists",
        ))
    else:
        results.append(finding(
            "FAIL", "W-finishing-contract-template",
            "harness-runtime/templates/contracts/finishing-branch.contract.yaml not found",
        ))

    # W-finishing-hooks: hooks.json must register all M3.1 critical scripts
    hooks_manifest = existing_path(
        root, ".harness/common/runtime-overlay/hooks/finishing-branch/hooks.json"
    )
    if hooks_manifest:
        try:
            manifest = json.loads(hooks_manifest.read_text(encoding="utf-8"))
            scripts = {entry.get("script", "") for entry in manifest.get("hooks", [])}
            critical = {
                "deny_force_push.py",
                "deny_hard_reset.py",
                "check_cleanup_authorization.py",
                "check_branch_cleanliness.py",
                "check_pr_body.py",
                "check_close_gate.py",
                "deny_direct_runtime_mutation.py",
                "record_git_ops.py",
            }
            missing = critical - scripts
            if missing:
                results.append(finding(
                    "FAIL", "W-finishing-hooks",
                    f"finishing-branch hooks.json missing M3.1 scripts: {sorted(missing)}",
                ))
            else:
                results.append(finding(
                    "PASS", "W-finishing-hooks",
                    "finishing-branch hooks.json registers all 8 M3.1 scripts",
                ))
        except (json.JSONDecodeError, OSError) as exc:
            results.append(finding(
                "FAIL", "W-finishing-hooks",
                f"finishing-branch hooks.json unreadable: {exc}",
            ))
    else:
        results.append(finding(
            "FAIL", "W-finishing-hooks",
            ".harness/common/runtime-overlay/hooks/finishing-branch/hooks.json not found",
        ))

    # W-finishing-mission-close-enum: the CLI surface must contain the new
    # enum values. After the harness_cli layering refactor the strategy list
    # moved into the mission command-registration module, so we check both
    # locations and PASS when *either* file declares the values.
    cli_path = existing_path(root, ".harness/common/cli/harness_cli.py")
    mission_register_path = existing_path(
        root, ".harness/common/harness_cli_core/app/commands/mission.py"
    )
    close_enum_text = ""
    if cli_path:
        close_enum_text += cli_path.read_text(encoding="utf-8")
    if mission_register_path:
        close_enum_text += "\n" + mission_register_path.read_text(encoding="utf-8")

    if close_enum_text:
        new_values = {"merged", "pr", "kept", "discarded"}
        missing_values = [
            v for v in sorted(new_values)
            if f'"{v}"' not in close_enum_text and f"'{v}'" not in close_enum_text
        ]
        if missing_values:
            results.append(finding(
                "FAIL", "W-finishing-mission-close-enum",
                f"CLI surface missing new close enum values: {missing_values}",
            ))
        else:
            results.append(finding(
                "PASS", "W-finishing-mission-close-enum",
                "CLI surface contains all new close enum values (merged/pr/kept/discarded)",
            ))
    else:
        results.append(finding(
            "FAIL", "W-finishing-mission-close-enum",
            ".harness/common/cli/harness_cli.py and harness_cli_core mission register not found",
        ))

    # W-finishing-cli-commands: the CLI surface must register the
    # finishing-branch subparser. After the layering refactor the inline
    # ``sub.add_parser("finishing-branch")`` was replaced with
    # ``register_finishing_branch_commands(...)``; both forms are accepted.
    fb_register_path = existing_path(
        root, ".harness/common/harness_cli_core/app/commands/finishing_branch.py"
    )
    fb_register_text = ""
    if cli_path:
        fb_register_text += cli_path.read_text(encoding="utf-8")
    if fb_register_path:
        fb_register_text += "\n" + fb_register_path.read_text(encoding="utf-8")
    if fb_register_text and "finishing-branch" in fb_register_text:
        results.append(finding(
            "PASS", "W-finishing-cli-commands",
            "CLI surface registers finishing-branch subparser",
        ))
    elif fb_register_text:
        results.append(finding(
            "FAIL", "W-finishing-cli-commands",
            "CLI surface does not register finishing-branch subparser",
        ))

    # W-finishing-workflow-failure-paths: workflow.md must contain failure_paths
    workflow_path = existing_path(root, ".harness/common/skills/finishing-branch/workflow.md")
    if workflow_path:
        wf_text = workflow_path.read_text(encoding="utf-8")
        if "failure_path" in wf_text or "<failure" in wf_text:
            results.append(finding(
                "PASS", "W-finishing-workflow-failure-paths",
                "finishing-branch workflow.md contains failure_paths",
            ))
        else:
            results.append(finding(
                "FAIL", "W-finishing-workflow-failure-paths",
                "finishing-branch workflow.md missing failure_paths blocks",
            ))

        # W-finishing-workflow-no-bare-git: workflow must not contain bare git command blocks
        import re as _re
        bare_git_block = _re.search(r"```(?:bash|sh)\s*\ngit ", wf_text)
        if bare_git_block:
            results.append(finding(
                "FAIL", "W-finishing-workflow-no-bare-git",
                "finishing-branch workflow.md contains bare git command blocks; route commands through harness-cli prose and CLI evidence",
            ))
        else:
            results.append(finding(
                "PASS", "W-finishing-workflow-no-bare-git",
                "finishing-branch workflow.md uses harness-cli calls (no bare git blocks)",
            ))

        # W-finishing-workflow-evidence-summary: workflow must contain evidence_summary
        if "evidence_summary" in wf_text or "<evidence" in wf_text:
            results.append(finding(
                "PASS", "W-finishing-workflow-evidence-summary",
                "finishing-branch workflow.md contains evidence_summary",
            ))
        else:
            results.append(finding(
                "FAIL", "W-finishing-workflow-evidence-summary",
                "finishing-branch workflow.md missing evidence_summary block",
            ))

        # W-finishing-workflow-no-direct-mutation: workflow must not directly mutate mission-status.yaml.
        # Only flag when the workflow instructs direct tool invocations targeting mission-status.yaml,
        # not when the file is merely mentioned as a reference or advisory comment.
        import re as _re2
        _direct_mutation = bool(
            _re2.search(r'write_yaml.*mission-status\.yaml', wf_text)
            or _re2.search(r'mission-status\.yaml.*write_yaml', wf_text)
        )
        if _direct_mutation:
            results.append(finding(
                "FAIL", "W-finishing-workflow-no-direct-mutation",
                "finishing-branch workflow.md contains direct mutation of mission-status.yaml",
            ))
        else:
            results.append(finding(
                "PASS", "W-finishing-workflow-no-direct-mutation",
                "finishing-branch workflow.md does not directly mutate mission-status.yaml",
            ))
    else:
        results.append(finding(
            "WARN", "W-finishing-workflow-failure-paths",
            ".harness/common/skills/finishing-branch/workflow.md not found; skip workflow lint",
        ))


def check(root: Path) -> dict[str, Any]:
    results: list[dict[str, str]] = []
    check_cli_assets(root, results)
    check_skill_descriptions(root, results)
    check_agent_frontmatter(root, results)
    check_work_graph_primary_routing(root, results)
    check_prd_template_fields(root, results)
    check_breakdown_template_fields(root, results)
    check_verify_template_fields(root, results)
    check_delivery_template_fields(root, results)
    check_code_review_template_fields(root, results)
    check_retrospective_template_fields(root, results)
    check_finishing_branch_template_fields(root, results)
    check_workflow_authoring_style(root, results)
    for rel in REQUIRED_PATHS:
        if existing_path(root, rel):
            results.append(finding("PASS", "path_exists", rel))
        else:
            results.append(finding("FAIL", "missing_path", rel))

    reference_roots = [
        root / ".harness/common/skills",
        root / ".harness/common/agents",
        root / ".harness/common/rules",
        root / ".harness/docs",
        root / ".harness/common/skills",
        root / ".harness/common/agents",
        root / ".harness/common/rules",
        root / ".harness/docs",
    ]
    referenced_templates: dict[str, set[str]] = {}
    for reference_root in reference_roots:
        if not reference_root.exists():
            continue
        for path in reference_root.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for ref in TEMPLATE_REFERENCE_RE.findall(text):
                if ref in IGNORED_TEMPLATE_REFS:
                    continue
                referenced_templates.setdefault(ref, set()).add(str(path.relative_to(root)))
    for ref, sources in sorted(referenced_templates.items()):
        candidates = template_reference_candidates(ref)
        rel = next((candidate for candidate in candidates if (root / candidate).exists()), candidates[0])
        if (root / rel).exists():
            results.append(finding("PASS", "template_reference_exists", f"{ref} referenced by {', '.join(sorted(sources))}"))
        else:
            results.append(finding("FAIL", "missing_template_reference", f"{ref} referenced by {', '.join(sorted(sources))} but {rel} is missing"))

    for rel in [
        "harness-runtime/templates/mission-contract.md",
        "harness-runtime/templates/product-evidence.md",
        "harness-runtime/templates/product-domain-model.md",
        "harness-runtime/templates/product-definition.md",
        "harness-runtime/templates/execution-brief.md",
        "harness-runtime/templates/verification-report.md",
        "harness-runtime/templates/delta-spec.md",
        "harness-runtime/templates/solution.md",
        "harness-runtime/templates/tech-design.md",
        "harness-runtime/templates/interaction.md",
        "harness-runtime/templates/code-review.md",
        "harness-runtime/templates/retrospective.md",
    ]:
        path = existing_path(root, rel)
        if path and has_contract_ref(path):
            results.append(finding("PASS", "contract_template", f"{rel} references external Control Contract"))
        else:
            results.append(finding("FAIL", "missing_contract_template", f"{rel} lacks external Control Contract reference"))

    runtime_files = [
        path
        for runtime_root in (root / "package", root / ".harness")
        for path in list(runtime_root.rglob("*.md")) + list(runtime_root.rglob("*.py"))
        if ".harness/docs" not in str(path.relative_to(root))
    ]
    forbidden_design_path = "docs/" + "architecture/"
    forbidden_execution_plan_terms = [
        "implementation" + "-plan",
        "implementation" + "_plan",
        "atomic_task" + "_plan",
    ]
    for path in runtime_files:
        text = path.read_text(encoding="utf-8")
        if forbidden_design_path in text:
            results.append(finding("FAIL", "forbidden_reference", str(path.relative_to(root))))
        for term in forbidden_execution_plan_terms:
            if term in text:
                results.append(finding("FAIL", "forbidden_execution_plan_reference", f"{path.relative_to(root)} contains obsolete execution-plan term"))

    for rel, expected in TEMPLATE_CONTRACT_EXPECTATIONS.items():
        path = existing_path(root, rel)
        contract = parse_control_contract(path) if path else None
        expected_type, expected_subtype = expected
        if contract is None:
            results.append(finding("FAIL", "template_type_drift", f"{rel} contract cannot be parsed"))
            continue
        if contract.get("type") != expected_type:
            results.append(finding("FAIL", "template_type_drift", f"{rel} expected {expected_type}, got {contract.get('type')}"))
        elif expected_subtype and contract.get("subtype") != expected_subtype:
            results.append(finding("FAIL", "template_type_drift", f"{rel} expected subtype {expected_subtype}, got {contract.get('subtype')}"))
        else:
            results.append(finding("PASS", "template_type", f"{rel} contract type matches"))

    for rel, expected in WORKFLOW_EXPECTATIONS.items():
        path = existing_path(root, rel) or root / rel
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for path_ref in expected["must_reference_path"]:
            variants = workflow_reference_variants(path_ref)
            matched = next((variant for variant in variants if variant in text), None)
            if matched:
                results.append(finding("PASS", "workflow_reference_path", f"{rel} references {matched}"))
            else:
                results.append(finding("FAIL", "workflow_path_drift", f"{rel} missing path reference {path_ref}"))
        for concept in expected["must_mention_concept"]:
            if concept in text:
                results.append(finding("PASS", "workflow_reference_concept", f"{rel} mentions {concept}"))
            else:
                results.append(finding("FAIL", "workflow_concept_drift", f"{rel} missing concept {concept}"))

    status = "FAIL" if any(item["level"] == "FAIL" for item in results) else "WARN" if any(item["level"] == "WARN" for item in results) else "PASS"
    return {"status": status, "findings": results}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check(Path(args.root).resolve())
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Runtime Consistency: {result['status']}")
        for item in result["findings"]:
            print(f"[{item['level']}] {item['code']}: {item['message']}")
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
