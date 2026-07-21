# 交付包: {{mission_id}}

> **来源**：交付技能 → `harness-runtime/harness/stages/{{mission_id}}/delivery-package.md`
> **参考方法论**：Diátaxis Framework（文档结构）；GitOps；SRE SLO/SLI
> **原则**：内部归档和追溯用；用户验收以 `acceptance-result.md` 为准。
> **上游**：`mission-contract.md` | `execution-brief.md` | `code-review.md` | `verification-report.md` | `acceptance-result.md`

**Author:** {{user_name}}
**Date:** {{date}}
**mission-id:** {{mission_id}}
**Final Status:** `{{final_status}}` <!-- 完成 / partial / 审查-needed -->

---

## 交付摘要

### 一句话概括

> 做了什么，达到了什么效果。

{{delivery_summary_one_line}}

### 变更范围

| 维度 | 数量 | 关键模块/文件 |
|-----|------|------------|
| 新增文件 | {{new_files_count}} | {{new_files_key}} |
| 修改文件 | {{modified_files_count}} | {{modified_files_key}} |
| 删除文件 | {{deleted_files_count}} | {{deleted_files_key}} |

### 关键技术决策

> 从 solution 和 tech-design 中提取实现过程中的关键选择，为未来维护者保留上下文。

| 决策 | 选择 | 理由摘要 |
|-----|------|---------|
| {{decision_1}} | {{choice_1}} | {{rationale_1}} |
| {{decision_2}} | {{choice_2}} | {{rationale_2}} |

---

## 验收状态

> 本节只做归档摘要。面向人的验收入口和 expected/actual 结果证明见 `acceptance-result.md`。

| AC-ID | 结论 | 用户结果证据 | 内部验证证据 |
|-------|------|--------------|--------------|
| AC-01 | ✅ 通过 / ❌ 未通过 | 验收结果 | 验证报告 |
| AC-02 | ✅ 通过 / ❌ 未通过 | 验收结果 | 验证报告 |

**整体结论：** {{overall_ac_verdict}}
<!-- 全部通过 / 部分通过（见遗留项）/ 未通过 -->

### 最终用户验收

> 交付阶段必须暂停等待用户验收；未记录用户验收前，任务不得标记为完成。

| 字段 | 值 |
|-----|---|
| 验收结论 | {{user_acceptance_status}} <!-- accepted / continue-fix / accepted-risk / pending --> |
| 验收时间 | {{accepted_at}} |
| 审批记录 | `harness-runtime/harness/state/approvals.json` |
| 用户反馈摘要 | {{user_acceptance_comment}} |

---

## 证据链接

| 文档类型 | 路径 | 关键结论 |
|---------|------|---------|
| 用户验收结果 | `harness-runtime/harness/stages/{{mission_id}}/acceptance-result.md` | {{acceptance_result_conclusion}} |
| 验证报告 | `harness-runtime/harness/stages/{{mission_id}}/verification-report.md` | {{verification_conclusion}} |
| 代码评审 | `harness-runtime/harness/stages/{{mission_id}}/code-review.md` | {{code_review_conclusion}} |
| 测试结果 | {{test_results_path}} | {{test_results_summary}} |

---

## 遗留项

> 来源：未通过的 AC、Low 优先级代码评审建议、实现中发现的新风险、新需求机会。

### 阻断性遗留项

> 必须在下一个任务中处理。

| 遗留项 | 来源 | 严重性 | 建议处理方式 |
|-------|------|--------|-----------|
| {{blocking_issue_1}} | {{source_1}} | 必须处理 | {{handling_1}} |

### 建议性遗留项

> 建议处理，不阻断当前交付。

| 遗留项 | 来源 | 严重性 | 建议处理方式 |
|-------|------|--------|-----------|
| {{advisory_issue_1}} | code-review | 建议处理 | {{handling_1}} |
| {{advisory_issue_2}} | 实现过程发现 | 可忽略 | {{handling_2}} |

---

## Agent 能力产物

> 仅当 `agent_engineering.enabled=true` 且存在 Agent 实现规格或 agent-eval-report 时填写。

<!-- 如不涉及 Agent 组件，删除此节 -->

| Agent / 能力 | 实现规格来源 | Eval 整体结论 | 制度层约束 |
|-----------|---------|------------|---------|
| {{agent_or_capability_1}} | `harness-runtime/harness/stages/{{mission_id}}/tech-design.md` | 通过/未通过 | {{policy_path_1}} |

**可观测性接入：** {{observability_setup}}
**Agent 能力已知限制：** {{agent_limitations}}

---

## 下一步建议

> 如存在后续任务的需要，给出建议。

| 优先级 | 建议 | 背景 |
|--------|------|------|
| 高 | {{next_step_1}} | {{context_1}} |
| 中 | {{next_step_2}} | {{context_2}} |

---

## 任务关闭记录

| 字段 | 值 |
|-----|---|
| 开始时间 | {{started_at}} |
| 完成时间 | {{completed_at}} |
| 最终状态 | {{final_status}} |
| Git 分支 | {{git_branch}} |
| 最终 Commit | {{final_commit}} |
