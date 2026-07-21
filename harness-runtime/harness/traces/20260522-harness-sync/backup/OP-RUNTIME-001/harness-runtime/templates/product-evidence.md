# Product Evidence: {{project_name}}

> **来源**：prd 技能 → `harness-runtime/harness/stages/{{mission_id}}/product/product-evidence.md`
> **用途**：记录产品定义使用过的项目知识、规格、代码影响分析和降级情况。

**mission-id:** {{mission_id}}
**Status:** `draft`

---

## 控制契约

- Contract: `contracts/prd.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本文件只记录证据和解释。

---

## Mission Inputs

| 输入 | 路径 / 来源 | 使用方式 | 结论 |
|------|-------------|----------|------|
| Mission Contract | `harness-runtime/harness/missions/{{mission_id}}/mission-contract.md` | {{usage}} | {{finding}} |
| Discovery Brief | {{path}} | {{usage}} | {{finding}} |
| Project Context | {{path}} | {{usage}} | {{finding}} |

---

## Knowledge Evidence

| Evidence-ID | 来源 | 相关主题 | 产品判断影响 | 置信度 |
|-------------|------|----------|--------------|--------|
| KE-01 | {{knowledge_ref}} | {{topic}} | {{impact}} | {{confidence}} |

---

## Spec Alignment

| Capability | Baseline Spec | Change Type | Requirement / Scenario Impact | Decision |
|------------|---------------|-------------|-------------------------------|----------|
| {{capability}} | {{spec_ref}} | {{added_modified_removed}} | {{impact}} | {{decision}} |

---

## GitNexus Evidence

> 棕地项目、现有代码影响、模块边界、调用链或兼容性不确定时必须填写；不可用时写入 Degradations。

| Evidence-ID | GitNexus 查询 / 输出 | 影响面 | 产品判断 |
|-------------|----------------------|--------|----------|
| GN-01 | {{gitnexus_ref}} | {{impact_area}} | {{product_decision}} |

---

## Degradations

| 缺失证据 | 原因 | 风险 | 补救动作 | Owner |
|----------|------|------|----------|-------|
| {{missing_evidence}} | {{reason}} | {{risk}} | {{mitigation}} | {{owner}} |
