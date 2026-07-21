# 交付包: {{mission_id}}

> **来源**：交付技能 → `harness-runtime/harness/artifacts/{{mission_id}}/delivery/delivery-package.md`
> **参考方法论**：文档结构框架（Diátaxis Framework）；配置即代码（GitOps）；站点可靠性工程（SRE）服务水平目标 / 指标（SLO / SLI）
> **原则**：内部归档和追溯用；用户验收以 `acceptance-result.md` 为准。
> **上游**：`mission-contract.md` | `execution-brief.md` | `code-review.md` | `verification-report.md` | `acceptance-result.md`

**作者:** {{user_name}}
**日期:** {{date}}
**mission-id:** {{mission_id}}
**最终状态:** `{{final_status}}` <!-- 完成 / 部分交付 / 需要审查 -->

---

## 填写方法

> 本文件是交付归档和移交说明。它不替代用户验收结果，也不重新定义交付范围。

| 步骤 | 填写要求 | 不合格表现 |
|------|----------|------------|
| 1 | 从任务契约、执行简报、代码审查、验证报告和实际差异汇总事实。 | 根据聊天记录或主观判断补写事实。 |
| 2 | 先写交付边界，再写变更范围。已交付、未交付、范围外、延后事项必须分开。 | 把范围外或延后事项写成已交付。 |
| 3 | 检查部署 / 使用就绪：入口、环境、配置、权限、数据、迁移、回滚、可观测性。 | 用户拿到产物后无法运行或无法验收。 |
| 4 | 证据链接必须能追溯到验收结果、验证报告、代码审查和关键结果证据。 | 只有“测试通过”摘要，没有证据路径。 |
| 5 | 残留风险和遗留项必须说明来源、影响、用户后果和处理建议。 | 用“后续优化”掩盖阻断风险。 |

---

## 交付摘要

### 一句话概括

> 做了什么，达到了什么效果。

{{delivery_summary_one_line}}

### 交付边界

| 分类 | 内容 | 来源 | 对用户的含义 |
|------|------|------|--------------|
| 已交付 | {{delivered_scope_1}} | {{delivered_source_1}} | {{delivered_user_meaning_1}} |
| 未交付 | {{not_delivered_1}} | {{not_delivered_source_1}} | {{not_delivered_user_meaning_1}} |
| 范围外 | {{out_of_scope_1}} | {{out_of_scope_source_1}} | {{out_of_scope_user_meaning_1}} |
| 延后 | {{deferred_1}} | {{deferred_source_1}} | {{deferred_user_meaning_1}} |

### 变更范围

| 维度 | 数量 | 关键模块/文件 |
|-----|------|------------|
| 新增文件 | {{new_files_count}} | {{new_files_key}} |
| 修改文件 | {{modified_files_count}} | {{modified_files_key}} |
| 删除文件 | {{deleted_files_count}} | {{deleted_files_key}} |

### 关键技术决策

> 从方案和技术设计中提取实现过程中的关键选择，为未来维护者保留上下文。

| 决策 | 选择 | 理由摘要 |
|-----|------|---------|
| {{decision_1}} | {{choice_1}} | {{rationale_1}} |
| {{decision_2}} | {{choice_2}} | {{rationale_2}} |

---

## 部署 / 使用就绪检查

> 移交阶段必须确认用户或维护者能接收本次增量。没有实际入口或关键使用前提时，不应请求验收。

| 检查项 | 当前结论 | 证据 / 路径 | 不满足时处理 |
|--------|----------|-------------|--------------|
| 交付入口 | {{entry_readiness}} | {{entry_evidence}} | {{entry_gap_action}} |
| 环境前提 | {{environment_readiness}} | {{environment_evidence}} | {{environment_gap_action}} |
| 配置要求 | {{config_readiness}} | {{config_evidence}} | {{config_gap_action}} |
| 账号 / 权限 | {{permission_readiness}} | {{permission_evidence}} | {{permission_gap_action}} |
| 数据准备 / 迁移 | {{data_readiness}} | {{data_evidence}} | {{data_gap_action}} |
| 回滚 / 恢复 | {{rollback_readiness}} | {{rollback_evidence}} | {{rollback_gap_action}} |
| 可观测性 | {{observability_readiness}} | {{observability_evidence}} | {{observability_gap_action}} |

---

## 验收状态

> 本节只做归档摘要。面向人的验收入口和预期 / 实际结果证明见 `acceptance-result.md`。

| 验收场景 / 条件 | 追溯锚点 | 结论 | 用户结果证据 | 内部验证证据 | 交付归宿 |
|----------------|----------|------|--------------|--------------|----------|
| {{acceptance_scenario_1}} | {{trace_anchor_1}} | 通过 / 未通过 / 部分满足 / 阻塞 / 接受风险 | 验收结果 | 验证报告 | delivered / deferred / returned |
| {{acceptance_scenario_2}} | {{trace_anchor_2}} | 通过 / 未通过 / 部分满足 / 阻塞 / 接受风险 | 验收结果 | 验证报告 | delivered / deferred / returned |

**整体结论：** {{overall_acceptance_verdict}}
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
| 用户验收结果 | `harness-runtime/harness/artifacts/{{mission_id}}/delivery/acceptance-result.md` | {{acceptance_result_conclusion}} |
| 验证报告 | `harness-runtime/harness/artifacts/{{mission_id}}/verify/verification-report.md` | {{verification_conclusion}} |
| 代码评审 | `harness-runtime/harness/artifacts/{{mission_id}}/code-review/code-review.md` | {{code_review_conclusion}} |
| 测试结果 | {{test_results_path}} | {{test_results_summary}} |

---

## 遗留项

> 来源：未通过的验收场景 / 条件、低严重级别代码审查建议、实现中发现的新风险、新需求机会。

### 阻断性遗留项

> 必须在下一个任务中处理。

| 遗留项 | 来源 | 用户影响 | 严重性 | 建议处理方式 |
|-------|------|----------|--------|-----------|
| {{blocking_issue_1}} | {{source_1}} | {{user_impact_1}} | 必须处理 | {{handling_1}} |

### 建议性遗留项

> 建议处理，不阻断当前交付。

| 遗留项 | 来源 | 用户影响 | 严重性 | 建议处理方式 |
|-------|------|----------|--------|-----------|
| {{advisory_issue_1}} | 代码审查 | {{advisory_user_impact_1}} | 建议处理 | {{handling_1}} |
| {{advisory_issue_2}} | 实现过程发现 | {{advisory_user_impact_2}} | 可忽略 | {{handling_2}} |

### 残留风险

| 风险 | 来源 | 用户后果 | 接受状态 | 处理建议 |
|------|------|----------|----------|----------|
| {{accepted_risk_1}} | {{risk_source_1}} | {{risk_user_effect_1}} | 已接受 / 待决策 / 不接受 | {{risk_next_step_1}} |

---

## Agent 能力产物

> 仅当 `agent_engineering.enabled=true` 且存在 Agent 实现规格或 Agent 评估报告（agent-eval-report）时填写。

<!-- 如不涉及 Agent 组件，删除此节 -->

| Agent / 能力 | 实现规格来源 | 评估整体结论 | 制度层约束 |
|-----------|---------|------------|---------|
| {{agent_or_capability_1}} | `harness-runtime/harness/artifacts/{{mission_id}}/technical-analysis/tech-design.md` | 通过/未通过 | {{policy_path_1}} |

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

## 移交说明

| 事项 | 说明 |
|------|------|
| 维护者需要知道的上下文 | {{maintainer_context}} |
| 用户需要知道的限制 | {{user_limitations}} |
| 重新验证方式 | {{reverification_method}} |
| 出现问题时的回退方式 | {{rollback_method}} |
| 后续恢复入口 | {{resume_entry}} |

---

## 任务关闭记录

| 字段 | 值 |
|-----|---|
| 开始时间 | {{started_at}} |
| 完成时间 | {{completed_at}} |
| 最终状态 | {{final_status}} |
| Git 分支 | {{git_branch}} |
| 最终提交（Commit） | {{final_commit}} |
