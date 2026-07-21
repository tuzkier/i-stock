# Retrospective: {{mission_id}}

> **来源**：retrospective 技能 → `harness-runtime/harness/artifacts/{{mission_id}}/retrospective/retrospective.md`
> **上游**：`mission-contract.md` | `verification-report.md` | `acceptance-result.md` | `code-review.md`

**Author:** {{user_name}}
**Date:** {{date}}
**mission-id:** {{mission_id}}
**Status:** `draft` <!-- draft / ready / 阻塞 -->

---

## 控制契约

- Contract: `contracts/retrospective.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。


---

## 执行摘要

{{summary}}

---

## 复盘输入与链路边界

| 输入 | 是否存在 | 用途 | 证据 |
|------|----------|------|------|
| 交付包 | {{delivery_package_exists}} | 交付范围、验收路径、残留风险 | {{delivery_package_evidence}} |
| 验收结果 | {{acceptance_result_exists}} | 用户可验收结果和未满足条件 | {{acceptance_result_evidence}} |
| 验证报告 | {{verification_report_exists}} | 命令证据、结果证据、未覆盖范围 | {{verification_report_evidence}} |
| 代码审查 | {{code_review_exists}} | 发现列表、修复闭环、验证交接 | {{code_review_evidence}} |
| 阶段门报告 / 工作图历史 | {{gate_history_exists}} | 返工、HOLD、RETURN、阻塞事件 | {{gate_history_evidence}} |

---

## 计划偏差（planning_delta）

| 计划点 | 实际发生 | 偏差类型 | 原因 | 影响 | 证据 |
|--------|----------|----------|------|------|------|
| {{planned_point}} | {{actual_result}} | {{delta_type}} | {{delta_reason}} | {{delta_impact}} | {{delta_evidence}} |

---

## 跨阶段失败模式（failure_patterns）

| 失败模式 | 出现阶段 | 重复性 | 根因 | 影响面 | 证据 |
|----------|----------|--------|------|--------|------|
| {{failure_pattern}} | {{stage_refs}} | one-off / repeated / systemic | {{root_cause}} | {{impact_surface}} | {{evidence_refs}} |

---

## 交付真实性回查

| 回查点 | 结论 | 依据 | 处理 |
|--------|------|------|------|
| 交付范围是否与验证证据一致 | {{delivery_scope_truth}} | {{delivery_scope_evidence}} | keep / re-verify / course-correction |
| 用户验收路径是否可独立执行 | {{acceptance_path_truth}} | {{acceptance_path_evidence}} | keep / fix-delivery / re-verify |
| 残留风险是否已披露 | {{risk_disclosure_truth}} | {{risk_disclosure_evidence}} | keep / fix-delivery / course-correction |

---

## 流程 / 模板 / 检查器改进（improvement_proposals）

| 改进 | target_kind | 目标位置 | 优先级 | 证据 | 预期效果 | 归宿 |
|------|-------------|----------|--------|------|----------|------|
| {{improvement}} | workflow / template / lint_check / agent_prompt / methodology / test / project-knowledge | {{target_ref}} | P0 / P1 / P2 | {{evidence}} | {{expected_effect}} | applied / proposed / 延后 |

---

## 知识沉淀（knowledge_updates）

| 知识类型 | 内容摘要 | 目标位置 | 来源 | 置信度 | 归宿 |
|----------|----------|----------|------|--------|------|
| product / behavior / design / engineering / operation / lesson | {{knowledge_summary}} | {{target_ref}} | {{source_ref}} | high / medium / low | applied / proposed / 延后 |

---

## 跟进行动（follow_up_actions）

| 行动 | Owner | 触发条件 | 必要证据 | 阻断等级 | 状态 |
|------|-------|----------|----------|----------|------|
| {{action}} | {{owner}} | {{trigger_condition}} | {{required_evidence}} | blocking / advisory | applied / proposed / 延后 |

---

## DORA 轻量信号

> 只用于趋势观察，不作为单次绩效评价。

| 信号 | 数值 | 说明 | 证据 |
|------|------|------|------|
| lead time | {{lead_time}} | {{lead_time_note}} | {{lead_time_evidence}} |
| rework count | {{rework_count}} | {{rework_note}} | {{rework_evidence}} |
| review hold count | {{review_hold_count}} | {{review_hold_note}} | {{review_hold_evidence}} |
| verification failure count | {{verification_failure_count}} | {{verification_failure_note}} | {{verification_failure_evidence}} |
| rollback / follow-up count | {{rollback_followup_count}} | {{rollback_followup_note}} | {{rollback_followup_evidence}} |

---

## 更新 project-context.md

{{project_context_update}}
