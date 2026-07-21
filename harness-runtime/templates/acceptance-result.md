# 验收结果: {{mission_id}}

> **面向对象**：用户 / 验收人
> **目的**：用可观察结果证明本次交付是否满足要求，而不是展示内部验证过程。
> **上游**：`mission-contract.md` | `verification-report.md` | 实际运行截图 / 接口（API）响应 / 命令输出 / 数据状态证据

**日期:** {{date}}
**mission-id:** {{mission_id}}
**验收状态:** `{{acceptance_status}}` <!-- ready-for-acceptance / blocked / accepted / rejected / accepted-risk -->

---

## 填写方法

> 本文件是用户验收单，不是内部过程记录。用户只读本文件和引用证据，就应该能完成验收判断。

| 步骤 | 填写要求 | 不合格表现 |
|------|----------|------------|
| 1 | 先确认交付入口真实可访问，写清环境前提、账号 / 数据、路径或命令。 | 只有“已实现”说明，没有入口。 |
| 2 | 逐条从任务契约和验收场景复制验收条件，写成原要求、预期结果、实际结果、复现步骤和结果证据。 | 只写“测试通过”或“功能正常”。 |
| 3 | 每条通过的验收场景 / 条件必须引用结果证据，证据要能证明用户可观察结果。 | 只有命令退出码，没有实际观察结果。 |
| 4 | 失败、部分满足、无法验收、接受风险的事项必须写入“未满足 / 无法验收”。 | 把失败项写成后续优化。 |
| 5 | 验收决定只能在用户确认后填写；未确认时保持待验收。 | 交付者替用户写“已接受”。 |

---

## 交付入口

> 告诉验收人从哪里开始看结果。没有可访问入口，就不能请求验收。

| 类型 | 入口 | 说明 |
|------|------|------|
| 应用 / 页面 | {{app_url_or_route}} | {{app_entry_note}} |
| 接口（API）/ 命令行（CLI） | {{api_or_cli_entry}} | {{api_or_cli_note}} |
| 测试账号 / 数据 | {{test_account_or_fixture}} | {{fixture_note}} |
| 分支 / 提交（Commit） | {{branch_and_commit}} | {{git_note}} |

---

## 你要验收什么

{{human_summary}}

### 验收前提

| 前提类型 | 具体内容 | 缺失时怎么办 |
|----------|----------|--------------|
| 环境 | {{environment_prerequisite}} | {{environment_gap_action}} |
| 配置 | {{configuration_prerequisite}} | {{configuration_gap_action}} |
| 权限 / 账号 | {{permission_prerequisite}} | {{permission_gap_action}} |
| 数据准备 | {{data_prerequisite}} | {{data_gap_action}} |

---

## 结果验收清单

> 每一条都必须写清楚：原要求是什么、实际结果是什么、验收人如何复现。只写“测试通过”不算结果证据。场景 / 条件 ID 作为下游追溯锚点，不是新的需求类型。

| 验收场景 / 条件 | 追溯锚点 | 原要求 / 预期结果 | 实际观察结果 | 复现步骤 | 结果证据 | 结论 |
|----------------|----------|------------------|--------------|----------|----------|------|
| {{acceptance_scenario_1}} | {{trace_anchor_1}} | {{expected_result_1}} | {{actual_result_1}} | {{steps_1}} | {{evidence_1}} | 通过 / 未通过 / 部分满足 / 阻塞 / 接受风险 |
| {{acceptance_scenario_2}} | {{trace_anchor_2}} | {{expected_result_2}} | {{actual_result_2}} | {{steps_2}} | {{evidence_2}} | 通过 / 未通过 / 部分满足 / 阻塞 / 接受风险 |

---

## 关键结果证据

> 证据必须能让人判断“结果是否正确”。优先使用截图、录屏、接口请求 / 响应、命令行输出、数据库可见状态或文件差异摘要。

| 证据编号 | 类型 | 路径 / 内容 | 证明什么 |
|---------|------|-------------|----------|
| EV-RESULT-001 | 截图 / 录屏 / 接口响应 / 命令行输出 / 数据状态 | {{evidence_path_or_excerpt}} | {{proves_what}} |

---

## 未满足 / 无法验收

| 项 | 状态 | 原因 | 用户影响 | 下一步 |
|----|------|------|----------|--------|
| {{blocked_item}} | 未通过 / 部分满足 / 阻塞 / 接受风险候选 | {{blocked_reason}} | {{blocked_impact}} | {{blocked_next_step}} |

### 残留风险说明

| 风险 | 来源 | 用户后果 | 是否需要用户接受 | 处理建议 |
|------|------|----------|------------------|----------|
| {{risk_1}} | {{risk_source_1}} | {{user_impact_1}} | 是 / 否 | {{risk_handling_1}} |

---

## 验收决定

| 字段 | 值 |
|------|----|
| 验收结论 | {{user_acceptance_status}} |
| 验收时间 | {{accepted_at}} |
| 用户反馈 | {{user_feedback}} |
| 审批记录 | `harness-runtime/harness/state/approvals.json` |
