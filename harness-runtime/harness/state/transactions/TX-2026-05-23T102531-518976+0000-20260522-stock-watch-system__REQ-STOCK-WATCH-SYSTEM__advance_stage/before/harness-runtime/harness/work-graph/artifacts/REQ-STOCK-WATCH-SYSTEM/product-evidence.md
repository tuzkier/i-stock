# Product Evidence: MyInvestment

> **来源**：prd 技能 → `harness-runtime/harness/stages/20260522-stock-watch-system/product/product-evidence.md`
> **用途**：记录产品定义使用过的项目知识、规格、代码影响分析和降级情况。

**mission-id:** `20260522-stock-watch-system`  
**Status:** `draft`

---

## 控制契约

- Contract: `harness-runtime/harness/stages/20260522-stock-watch-system/contracts/prd.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本文件只记录证据和解释。

---

## Mission Inputs

| 输入 | 路径 / 来源 | 使用方式 | 结论 |
|------|-------------|----------|------|
| Mission Contract | `harness-runtime/harness/missions/20260522-stock-watch-system/mission-contract.md` | 作为产品目标、非目标、成功定义、用户故事、AC、治理边界的主权威输入 | 已确认第一阶段边界是本地网页、多市场自选、图表/指标、MTS、提醒和本地恢复；明确排除自动交易、收益承诺、云同步、完整基本面和供应商锁定 |
| Discovery Brief | `harness-runtime/harness/work-graph/artifacts/REQ-STOCK-WATCH-SYSTEM/discovery-brief.md` | 作为问题空间、现状、候选对象、依赖约束、风险与 PRD 输入建议来源 | 已确认“真实问题不是单页图表，而是持续可用的跨市场观察工作台”；并记录了 `project-context.md` 缺失、GitNexus 不可用、来源层与 MTS 语义未定稿等风险 |
| BO Registry | `harness-runtime/harness/stages/20260522-stock-watch-system/product/business-objects.md` | 作为产品领域对象、业务规则、对象边界和状态语义来源 | 已建立 8 个核心 BO，尤其把 `DataProvider` 去技术化为 `MarketDataSource`，并排除 `LegacyCompositeSignal` 进入正式产品语义 |
| BUC Package | `harness-runtime/harness/stages/20260522-stock-watch-system/product/business-use-cases.md` | 作为用户闭环、GWT、AC、原型触发与覆盖缺口来源 | 已覆盖 7 个核心业务闭环；P0 路径为自选、默认看盘、MTS、四级提醒、本地恢复、来源降级 |
| Scope Strategy | `harness-runtime/harness/stages/20260522-stock-watch-system/product/scope-strategy.md` | 作为 In / Out / Later / Decision Needed 取舍来源 | 已确认 PRD 不锁具体开源库或供应商，只把“优先评估成熟、维护活跃、许可合适的现成开源库”下放为后续方案约束 |
| Technical Signal Research | `docs/technical-signal-research-design.md` | 作为默认视图、MTS 语义、提醒等级、研究边界和回测前提来源 | 已确认 MTS 结果必须同时表达趋势状态、分数带、买卖/风控类型和提醒等级，且不直接输出自动交易或收益承诺 |
| Project Context | `harness-runtime/project-context.md` | 预期作为长期上下文权威输入 | 文件缺失；本次无法作为正式上下文使用，已在 Degradations 中记录 |

---

## Knowledge Evidence

| Evidence-ID | 来源 | 相关主题 | 产品判断影响 | 置信度 |
|-------------|------|----------|--------------|--------|
| KE-01 | `project-knowledge/_index.md` | 知识目录结构、条目状态 | 证明项目长期知识存在，但多数条目处于 `init/draft`；因此本次只能把知识库作为弱证据而非定稿事实来源 | medium |
| KE-02 | `project-knowledge/context/overview.md`、`constraints.md`、`risks.md`（由 BO Registry 引用） | 项目概览、约束、风险 | 仅辅助确认本地化、范围和风险口径；不独立驱动新的产品决策 | low |
| KE-03 | `project-knowledge/product/scope-boundaries.md`（draft） | 产品边界 | 作为与 Mission 范围边界互相印证的弱证据，帮助确认本地化与第一阶段聚焦 | low |
| KE-04 | `harness-runtime/config/harness.yaml` | `agent_engineering.enabled=true`、`spec.enabled=false`、`prototype.delivery_mode=interactive_prototype` | 直接影响 PRD 是否产出 delta spec、是否写 Agent Capability Requirements、是否触发前端 API contract 草案 | high |

---

## Spec Alignment

| Capability | Baseline Spec | Change Type | Requirement / Scenario Impact | Decision |
|------------|---------------|-------------|-------------------------------|----------|
| 多市场本地看盘系统 | N/A | not_applicable | `spec.enabled=false`，本阶段没有 baseline capability spec，也不产出 delta spec | 在产品定义和证据中显式记录“无 spec 对齐”，由主流程在 contract 中同步 |

---

## GitNexus Evidence

> 棕地项目、现有代码影响、模块边界、调用链或兼容性不确定时必须填写；不可用时写入 Degradations。

| Evidence-ID | GitNexus 查询 / 输出 | 影响面 | 产品判断 |
|-------------|----------------------|--------|----------|
| GN-01 | 不可用；Discovery Brief 已记录 “gitnexus 不可用，后续应补 `npx gitnexus analyze`” | 无法形成对现有草稿代码、模块边界和后续棕地影响面的正式结构化证据 | 本次 PRD 只以 Mission / Discovery / 子专家产物 / 研究文档完成产品定义，不把具体实现结构写成产品要求 |

---

## Degradations

| 缺失证据 | 原因 | 风险 | 补救动作 | Owner |
|----------|------|------|----------|-------|
| `harness-runtime/project-context.md` | context check 输入缺失，项目未提供正式 project context 文档 | 长期上下文、历史取舍、已有系统边界和跨阶段约束无法作为正式证据引用；尤其影响恢复粒度、来源状态口径等边界问题的一致解释 | 补写正式 `project-context.md`，并在 interaction / solution 前回查 BUC-06、BUC-07、SD-25、SD-26 的口径 | 主流程 / 项目维护者 |
| GitNexus 结构化影响分析 | 工具当前不可用 | 缺少 brownfield 影响面、调用链和模块边界的正式证据，可能导致下游方案低估现有草稿迁移成本 | 后续执行 `npx gitnexus analyze` 或等效索引流程，补充 discovery / solution / technical design 证据 | 主流程 |
| project-knowledge 多数条目为 `init/draft` | 项目长期知识尚未沉淀完成 | 若误把 draft 当成定稿约束，可能放大错误前提；若完全忽略，又会损失上下文 | 本次仅把 knowledge 作为弱证据；待后续稳定后再提升为正式长期知识 | 项目维护者 |
| baseline spec / delta spec | `spec.enabled=false` | 无法通过 spec 层提供 capability 级行为约束，PRD 的追溯主要依赖 Mission、BUC、BO 和研究证据 | 在 contract 中记录 spec 不适用；若未来启用 spec，再由后续阶段补建 capability baseline 和 delta | 主流程 |
| MarketDataSource 最终展示粒度 | 当前只确认必须有来源状态提示，未定具体信息密度 | interaction 若先行收敛错误，可能导致来源可信度表达不足或信息过载 | 作为 Decision Needed 保留到 interaction / solution 联合定稿 | 产品主流程 |
| ChartLayout 恢复粒度 | 证据不足，当前无法在产品层定死是全局、市场还是标的级恢复 | 影响本地恢复行为、状态模型和交互复杂度 | 在 interaction 原型验证中优先回答；solution 再固化为明确边界 | 产品主流程 |
| MTS reason code / invalidator taxonomy | 研究文档定义了语义，但未标准化 code 体系 | 可能造成下游实现字段、文案与验证样本不一致 | solution / technical design 阶段先按结构化字段保留，再逐步收敛命名枚举 | 产品主流程 |
