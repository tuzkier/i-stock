# 验证报告: {{mission_id}}

> **来源**：验证技能 → `harness-runtime/harness/stages/{{mission_id}}/verification-report.md`
> **上游**：`harness-runtime/harness/missions/{{mission_id}}/mission-contract.md` | `harness-runtime/harness/stages/{{mission_id}}/execution-brief.md`

**Author:** {{user_name}}
**Date:** {{date}}
**mission-id:** {{mission_id}}
**Status:** `draft` <!-- draft / ready / 阻塞 -->

---

## 控制契约

> 验证证据契约是验收证据索引。AC 标记为 pass 时必须引用具体 evidence；阻塞时必须写明原因、影响和下一步。

- Contract: `contracts/verification-report.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。


---

## TL;DR

> 一句话说明本次验证的范围、结论和剩余风险。

{{verification_tldr}}

---

## 验证目标

> 明确本报告验证哪些 AC、任务项、NFR 和风险，不扩大到未授权范围。

{{verification_scope}}

---

## 验证方法

| 层级 | 命令 / 方法 | 证据 ID | 结果 |
|------|-------------|---------|------|
| 单元 / 集成 | `{{test_command}}` | CMD-001 | pass / fail / 阻塞 |
| lint / typecheck | `{{quality_command}}` | CMD-002 | pass / fail / unavailable |
| build | `{{build_command}}` | CMD-003 | pass / fail / unavailable |

---

## 验证结果

| AC-ID | 预期结果 | 实际观察结果 | 结果证据 | 结论 | 缺口 / 风险 |
|-------|----------|--------------|----------|------|-------------|
| AC-01 | {{expected_result}} | {{actual_result}} | EV-RESULT-001 | pass | 无 |
| AC-02 | {{expected_result}} | - | - | 阻塞 | {{blocked_reason}} |

---

## E2E 验证结果

> 默认必须填写。引用 `e2e-status.json` 作为 Harness 控制面事实；涉及 UI / 浏览器行为时写 E2E 统计、AC 对齐、html report、追溯/video/screenshot；无 UI 范围时写 N/A 和原因；BLOCKED 时引用 Decision Gate 原因；若 `e2e.enabled=false`，必须引用用户接受记录。

| 字段 | 值 |
|------|----|
| E2E 状态产物 | `harness-runtime/harness/traces/{{mission_id}}/e2e/e2e-status.json` |
| Status | {{e2e_status}} |
| HTML 报告 | {{e2e_html_report}} |
| 追溯 / Video / Screenshot | {{e2e_artifacts}} |
| N/A / BLOCKED / Decision Gate | {{e2e_na_blocked_or_decision_gate}} |

| AC-ID | E2E 场景 / 替代证据 | Result Evidence | 结论 | 缺口 / 风险 |
|-------|--------------------|-----------------|------|-------------|
| AC-01 | {{e2e_scenario_or_alternative}} | EV-RESULT-001 | pass / fail / 阻塞 / not_applicable | {{e2e_gap_or_risk}} |

{{e2e_result}}

---

## 未覆盖范围

| 范围 | 原因 | 影响 | 下一步 |
|------|------|------|--------|
| {{gap_scope}} | {{gap_reason}} | {{gap_impact}} | {{gap_next_step}} |

---

## 遗留问题

| 问题 | 严重级别 | 状态 | 处理方式 |
|------|----------|------|----------|
| {{issue}} | high / medium / low | open / accepted / 延后 | {{handling}} |
