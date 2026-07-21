# 验收结果: {{mission_id}}

> **面向对象**：用户 / 验收人
> **目的**：用可观察结果证明本次交付是否满足要求，而不是展示内部验证过程。
> **上游**：`mission-contract.md` | `verification-report.md` | 实际运行截图 / API 响应 / 命令输出 / 数据状态证据

**Date:** {{date}}
**mission-id:** {{mission_id}}
**验收 Status:** `{{acceptance_status}}` <!-- ready-for-acceptance / 阻塞 / accepted / rejected / accepted-risk -->

---

## 交付入口

> 告诉验收人从哪里开始看结果。没有可访问入口，就不能请求验收。

| 类型 | 入口 | 说明 |
|------|------|------|
| 应用 / 页面 | {{app_url_or_route}} | {{app_entry_note}} |
| API / CLI | {{api_or_cli_entry}} | {{api_or_cli_note}} |
| 测试账号 / 数据 | {{test_account_or_fixture}} | {{fixture_note}} |
| 分支 / Commit | {{branch_and_commit}} | {{git_note}} |

---

## 你要验收什么

{{human_summary}}

---

## 结果验收清单

> 每一条都必须写清楚：原要求是什么、实际结果是什么、验收人如何复现。只写“测试通过”不算结果证据。

| AC-ID | 原要求 / 预期结果 | 实际观察结果 | 复现步骤 | 结果证据 | 结论 |
|-------|------------------|--------------|----------|----------|------|
| AC-01 | {{expected_result_1}} | {{actual_result_1}} | {{steps_1}} | {{evidence_1}} | pass / fail / 阻塞 |
| AC-02 | {{expected_result_2}} | {{actual_result_2}} | {{steps_2}} | {{evidence_2}} | pass / fail / 阻塞 |

---

## 关键结果证据

> 证据必须能让人判断“结果是否正确”。优先使用截图、录屏、API 请求/响应、CLI 输出、数据库可见状态或文件 diff 摘要。

| 证据 ID | 类型 | 路径 / 内容 | 证明什么 |
|---------|------|-------------|----------|
| EV-RESULT-001 | screenshot / video / api-response / cli-output / data-状态 | {{evidence_path_or_excerpt}} | {{proves_what}} |

---

## 未满足 / 无法验收

| 项 | 原因 | 影响 | 下一步 |
|----|------|------|--------|
| {{blocked_item}} | {{blocked_reason}} | {{blocked_impact}} | {{blocked_next_step}} |

---

## 验收决定

| 字段 | 值 |
|------|----|
| 验收结论 | {{user_acceptance_status}} |
| 验收时间 | {{accepted_at}} |
| 用户反馈 | {{user_feedback}} |
| 审批记录 | `harness-runtime/harness/state/approvals.json` |
