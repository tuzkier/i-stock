# Retrospective: {{mission_id}}

> **来源**：retrospective 技能 → `harness-runtime/harness/stages/{{mission_id}}/retrospective.md`
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

## 做得好的

- {{what_went_well}}

---

## 发现的问题

| 问题 | 影响 | 证据 |
|------|------|------|
| {{issue}} | {{impact}} | {{evidence}} |

---

## 根因分析

{{root_cause}}

---

## 改进行动

| 行动 | Owner | 状态 |
|------|-------|------|
| {{action}} | {{owner}} | applied / proposed / 延后 |

---

## 更新 project-context.md

{{project_context_update}}
