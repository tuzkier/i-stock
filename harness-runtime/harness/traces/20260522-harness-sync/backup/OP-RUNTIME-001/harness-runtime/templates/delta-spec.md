# <Capability Name> — 差量规格

<!--
本文件是一次任务的行为契约增量（delta）。
写作要求见 `project-knowledge/specs/_index.md` 的「格式说明」段。
任务收尾时，Agent 必须将已确认的长期行为契约提炼并固化到 `project-knowledge/specs/<capability>/spec.md`。

基线对照：
- 若对应的 `project-knowledge/specs/<capability>/spec.md` 已存在，列出基线文件路径
- 若不存在（首次为该能力建立规格），在下方注明 "Baseline: none（首次建立）"
-->

**任务**: `<mission-id>`
**能力**: `<capability-name>`
**Baseline**: `project-knowledge/specs/<capability>/spec.md` _(或 "none（首次建立）")_

---

## 控制契约

> 差量规格是行为契约的能力级补充。这里的 ID 必须能被 PRD、拆解、执行、code-review 和验证引用。

- Contract: `contracts/delta-spec.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。


---

## ADDED Requirements

<!-- 本次新增的 Requirement。任务合并后会追加到基线规格。 -->

### Requirement: <新需求名称>
系统 SHALL <外部可观测的行为>。

#### Scenario: <场景名称>
- **GIVEN** <前置状态>（可选）
- **WHEN** <触发条件>
- **THEN** <预期结果>
- **AND** <额外结果>（可选）

<!-- 可重复多个 Requirement / 多个 Scenario。无新增时删除整个 "## ADDED Requirements" 段。 -->

---

## MODIFIED Requirements

<!--
本次修改的既有 Requirement。每条必须：
1. Requirement 名精确匹配基线规格中的名称
2. 写出完整的新版 Requirement 块（不得只写差异），合并时整块替换
3. 在块末追加 "**Change note**:" 一行说明改了什么、为什么
-->

### Requirement: <既有需求名称>
系统 SHALL <修改后的行为>。

#### Scenario: <场景名称>
- **GIVEN** <前置状态>
- **WHEN** <触发条件>
- **THEN** <预期结果>

**Change note**: <改了什么 / 为什么>

<!-- 无修改时删除整个 "## MODIFIED Requirements" 段。 -->

---

## REMOVED Requirements

<!--
本次移除的既有 Requirement。只列名称 + 移除理由；合并时按名称从基线删除整块。
无移除时删除整个 "## REMOVED Requirements" 段。
-->

- **Requirement: <既有需求名称>** — 理由：<为什么移除（功能下线 / 被新 Requirement 取代等）>
