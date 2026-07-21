# 代码评审: {{mission_id}}

> **来源**：code-review 技能 → `harness-runtime/harness/artifacts/{{mission_id}}/code-review/code-review.md`
> **上游**：`mission-contract.md` | `tech-design.md` | `execution-brief.md`

**Author:** {{user_name}}
**Date:** {{date}}
**mission-id:** {{mission_id}}
**Status:** `draft` <!-- draft / ready / 阻塞 -->

---

## 控制契约

- Contract: contracts/code-review.contract.yaml
- Control Contract: `contracts/code-review.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。


---

## 审查依据与范围

| 输入 | 路径 / 来源 | 状态 | 本次用途 |
|------|-------------|------|----------|
| 初始任务契约 | `mission-contract.md` | present / missing / partial | {{mission_contract_use}} |
| 产品定义包 | `product/product-definition.md` / `product/acceptance-scenarios.md` | present / missing / partial | 验收场景 / 条件、系统责任、质量与运行约束：{{product_definition_use}} |
| 方案与技术设计 | `solution.md` / `tech-design.md` | present / missing / partial | {{design_basis_use}} |
| 执行授权 | `execution-brief.md` | present / missing / partial | {{execution_brief_use}} |
| 执行结果 | `execution-result.md` | present / missing / partial | {{execution_result_use}} |
| 变更 diff | {{diff_source}} | present / missing / partial | {{diff_use}} |
| 测试与工具链证据 | {{test_evidence_source}} | present / missing / partial | {{test_evidence_use}} |

---

## 变更集承接

| Execution Unit | Changed Files | Changed Surface | Execute Deviations / Blockers | Return Condition Hits | Review Scope Decision |
|----------------|---------------|-----------------|-------------------------------|-----------------------|-----------------------|
| {{execution_unit_id}} | {{changed_files}} | {{changed_surface}} | {{deviations_or_blockers}} | {{return_condition_hits}} | covered / blocked / needs_execute_update |

---

## 审查角色选择

| Reviewer | 是否启用 | 启用依据 | 角色边界 | 结论 |
|----------|----------|----------|----------|------|
| correctness-reviewer | required | 所有实现都必须审需求忠实性 | {{correctness_boundary}} | PASS / HOLD / PASS_WITH_RISK / BLOCKED |
| tdd-reviewer | required | 所有实现都必须审测试有效性 | {{tdd_boundary}} | PASS / HOLD / PASS_WITH_RISK / BLOCKED |
| architecture-reviewer | conditional | {{architecture_trigger}} | {{architecture_boundary}} | PASS / HOLD / PASS_WITH_RISK / BLOCKED / n/a |
| security-reviewer | conditional | {{security_trigger}} | {{security_boundary}} | PASS / HOLD / PASS_WITH_RISK / BLOCKED / n/a |
| data-migration-reviewer | conditional | {{data_migration_trigger}} | {{data_migration_boundary}} | PASS / HOLD / PASS_WITH_RISK / BLOCKED / n/a |
| e2e-reviewer | conditional | {{e2e_trigger}} | {{e2e_boundary}} | PASS / HOLD / PASS_WITH_RISK / BLOCKED / n/a |
| agent-behavior-reviewer | conditional | {{agent_behavior_trigger}} | {{agent_behavior_boundary}} | PASS / HOLD / PASS_WITH_RISK / BLOCKED / n/a |

---

## 评审摘要

{{review_summary}}

---

## 发现列表

| ID | 严重级别 | 类别 | 关联项 | 摘要 | 状态 | 处理引用 |
|----|----------|------|--------|------|------|----------|
| FND-001 | High / Med / Low | correctness / tdd / architecture / security / data-migration / e2e / agent-behavior | {{traces_to}} | {{finding_summary}} | open / fixed / accepted_risk | {{resolution_ref}} |

---

## 正确性

{{correctness_review}}

---

## TDD Toolchain Status

此节是 Harness 控制面状态，不是 TDD 审查员结论。工具缺失、白名单外安装、命令未执行、报告缺失先按 toolchain status / Decision Gate 处理；只有工具报告或测试内容无法证明错误实现会失败，才进入 TDD 有效性审查。

| Artifact | Status | Missing Capabilities | Decision Gate Reasons |
|----------|--------|----------------------|-----------------------|
| `{{toolchain_status_artifact}}` | PASS / WARN / FAIL / BLOCKED | {{missing_capabilities}} | {{decision_gate_reasons}} |

---

## TDD 有效性审查

**Verdict:** {{tdd_verdict}} <!-- PASS / HOLD / PASS_WITH_RISK -->

**Probe:** `{{toolchain_probe_artifact}}`
**Toolchain Status:** `{{toolchain_status_artifact}}`

### Role Boundary

| 项 | 结论 |
|----|------|
| 本次只审测试有效性 | {{yes_no}} |
| 已排除的非 TDD 问题 | {{excluded_non_tdd_issues}} |
| 与 correctness/e2e/验证的边界 | {{review_boundary}} |

### Toolchain Signal Handling

| Signal | 处理 | 理由 |
|--------|------|------|
| {{probe_signal_code}} | accepted / rejected / risk | {{reason}} |

### Toolchain Reports Used

| 能力 | Tool / Report | Status | 审查员 Use |
|------------|---------------|--------|--------------|
| {{capability}} | {{tool_report}} | pass / warn / fail / missing | {{reviewer_use}} |

### Test Adequacy Matrix

| 验收场景/条件/任务项 | 测试追溯 | Red 有效性 | 断言强度 | 充分性 | Fault Detection | 结论 |
|------------------|----------|------------|----------|--------|-----------------|------|
| {{trace_target}} | {{test_refs}} | valid / missing / invalid | strong / weak | adequate / 缺口 | proven / missing | pass / hold |

### TDD Blocking Gaps

| ID | 严重性 | TDD 问题类型 | 关联验收场景/条件/任务项 | 缺口 | 为什么阻断 | 为什么这是 TDD 问题 | 必须补什么 |
|----|--------|---------------|----------------------|------|------------|--------------------|------------|
| {{tdd_gap_id}} | High | {{tdd_issue_type}} | {{traces_to}} | {{gap}} | {{blocking_reason}} | {{tdd_reason}} | {{required_fix}} |

### TDD Non-blocking Risks

| ID | 严重性 | 关联项 | 风险 | 建议 |
|----|--------|--------|------|------|
| {{tdd_risk_id}} | Med/Low | {{traces_to}} | {{risk}} | {{recommendation}} |

---

## E2E 控制面 Status

此节是 Harness 控制面状态，不是 E2E 审查员结论。Playwright/Cypress 等工具缺失、命令未执行、`e2e-status.json` 缺失、report 路径错误、追溯/video/screenshot/UI diff 缺失、验证 report 缺 result evidence 先按 E2E status / Decision Gate / Stage Gate 处理；只有 E2E 测试本身无法证明用户可观察路径正确，才进入 E2E 审查 finding。

| Artifact | Status | Missing Capabilities | Decision Gate Reasons | Artifacts |
|----------|--------|----------------------|-----------------------|-----------|
| `{{e2e_status_artifact}}` | PASS / WARN / FAIL / BLOCKED | {{e2e_missing_capabilities}} | {{e2e_decision_gate_reasons}} | report: {{e2e_html_report}}; 追溯/video/screenshots/UI diff: {{e2e_artifact_summary}} |

---

## E2E 审查

**Verdict:** {{e2e_verdict}} <!-- PASS / HOLD / PASS_WITH_RISK -->

**Methodology:** `.harness/docs/e2e-effectiveness-reviewer-methodology.md`

**E2E Status:** `{{e2e_status_artifact}}`

### Role Boundary

| 项 | 结论 |
|----|------|
| 本次只审 E2E 用户路径证明力 | {{yes_no}} |
| 已排除的 Harness Gate / 验证问题 | {{excluded_non_e2e_issues}} |
| 与 correctness/tdd/验证的边界 | {{e2e_review_boundary}} |

### E2E Artifacts Used

| Artifact Type | Path / Ref | Status | 审查员 Use |
|---------------|------------|--------|--------------|
| {{artifact_type}} | {{artifact_ref}} | pass / warn / fail / missing | {{reviewer_use}} |

### E2E Coverage Matrix

| 验收场景/条件/任务项 | e2e_obligation | E2E 测试追溯 | 用户可观察结果断言 | 数据真实性 | 负向路径 | Realtime/Refresh | 可靠性 | 诊断 Artifact | 结论 |
|------------------|----------------|---------------|--------------------|------------|----------|------------------|--------|---------------|------|
| {{trace_target}} | {{e2e_obligation_ref}} | {{e2e_test_refs}} | strong / weak / missing | real / fixture / mock_缺口 | covered / 缺口 / n/a | covered / 缺口 / n/a | stable / risk | 追溯 / video / screenshot / missing | pass / hold |

### E2E Blocking Gaps

| ID | 严重性 | E2E 问题类型 | 关联验收场景/条件/任务项 | 缺口 | 为什么阻断 | 为什么这是 E2E 问题 | 必须补什么 |
|----|--------|---------------|----------------------|------|------------|--------------------|------------|
| {{e2e_gap_id}} | High | {{e2e_issue_type}} | {{traces_to}} | {{gap}} | {{blocking_reason}} | {{e2e_reason}} | {{required_fix}} |

### E2E Non-blocking Risks

| ID | 严重性 | 关联项 | 风险 | 建议 |
|----|--------|--------|------|------|
| {{e2e_risk_id}} | Med/Low | {{traces_to}} | {{risk}} | {{recommendation}} |

---

## 设计一致性

{{architecture_review}}

---

## 安全与可靠性

{{security_review}}

---

## 修复闭环

| Round | High Findings | 修复动作 | 重审范围 | 重审结论 |
|-------|---------------|----------|----------|----------|
| {{round_id}} | {{high_findings}} | {{fix_summary}} | all_reviewers / selected_reason | {{round_verdict}} |

---

## 验证交接

| 验证关注点 | 来源 Finding / Risk | 建议验证层次 | 证据要求 |
|------------|---------------------|--------------|----------|
| {{verify_focus}} | {{finding_or_risk_ref}} | unit / integration / e2e / manual / operational | {{required_evidence}} |

---

## 评审结论

{{review_conclusion}}
