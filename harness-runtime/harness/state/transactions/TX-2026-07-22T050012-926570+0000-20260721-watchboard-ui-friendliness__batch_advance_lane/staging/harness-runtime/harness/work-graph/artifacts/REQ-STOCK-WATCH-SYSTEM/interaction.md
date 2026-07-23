# Interaction: MyInvestment 多市场看盘工作台

Contract: `contracts/interaction.contract.yaml`

**mission-id:** `20260522-stock-watch-system`  
**stage:** `interaction`  
**artifact tier:** `standard`  
**human entry:** `visual-interaction/prototype/index.html`

## 阶段判断

本次选择 `standard`，因为 PRD 已把 8 个 prototype required BUC 明确为同一工作台上的可验证闭环：自选与归一预览、默认日常看盘工作台、主图/成交量/副图切换、MTS 解释卡、提醒 taxonomy 与触发历史、来源健康穿透、本地恢复、布局切换。仅写 light 不足以支撑后续 solution / frontend / verify 的共识；当前也不需要 deep 档的多方案对比，因此采用 standard。

## 权威边界

- `interaction-spec/` 是本阶段的 canonical handoff。
- `visual-interaction/prototype/index.html` 只作为人类确认入口与视觉证据，不承载合同解释。
- 本次没有改 PRD 产品语义；只是把既有 BUC / BO / AC 表达成界面合同。
- 若后续发现必须新增用户目标、AC、BO、权限或范围，立即回流 PRD / Decision Gate，不在 Interaction 阶段私自补造。

## 输入摘要

| 输入 | 使用方式 |
|---|---|
| `project-context.md` | 约束本地网页、localStorage、demo_fallback 明示、技术信号非投资建议 |
| `harness-runtime/harness/missions/20260522-stock-watch-system/mission-contract.md` | 约束 mission 目标、非目标、AC 与本地恢复边界 |
| `product/product-definition.md` | 作为 FR / 非目标 / 成功定义的主语义来源 |
| `product/business-objects.md` | 提供 8 个核心 BO、状态、规则与领域语义 |
| `product/business-use-cases.md` | 提供 BUC-01 ~ BUC-09，其中 BUC-01 ~ BUC-08 为 prototype required |
| `product/product-domain-model.md` | 提供命令、状态机、权限、降级与恢复约束 |
| `product/product-evidence.md` | 提供 open-source reference 与降级证据 |
| `specs/local-stock-watch-workbench/spec.md` | 提供首次建立的差量规格 |
| `contracts/prd.contract.yaml` | 提供程序化权威的 PRD 汇总与消费边界 |
| `harness-runtime/harness/missions/20260522-stock-watch-system/contracts/mission-contract.contract.yaml` | 提供任务契约的 intent 边界与治理约束 |

## BUC-first 合同概览

| BUC | 用户目标 | Prototype Required | 关键 surface |
|---|---|---:|---|
| BUC-01 | 管理多市场自选与归一预览 | yes | `WatchlistPanel`, `NormalizationPreview`, `WatchlistRow`, `RestoreStatus` |
| BUC-02 | 打开默认日常看盘工作台 | yes | `WorkbenchShell`, `ChartSurface`, `SourceHealthPanel` |
| BUC-03 | 切换主/副图指标并读取 OHLC | yes | `IndicatorPanel`, `ChartSurface` |
| BUC-04 | 解读 MTS 多周期趋势信号 | yes | `MtsSignalCard` |
| BUC-05 | 管理本地提醒 taxonomy 与触发历史 | yes | `AlertRulePanel` |
| BUC-06 | 查看来源健康并处理降级 | yes | `SourceHealthPanel`, `ChartSurface`, `MtsSignalCard`, `AlertRulePanel` |
| BUC-07 | 重开浏览器恢复本地工作台 | yes | `RestoreStatus`, `WatchlistPanel`, `AlertRulePanel` |
| BUC-08 | 切换布局模式 | yes | `LayoutController`, `WorkbenchShell`, `mobile_tab` 导航 |
| BUC-09 | 冻结样本验收关键路径 | no | 仅验证，不进入 prototype required 合同 |

## 核心流程

1. 用户先在自选区看到市场、原始代码、归一代码与歧义预览，再决定是否写入 active。
2. 用户选中标的后，默认进入日常看盘工作台：左侧自选，中间图表 / MTS / 状态摘要；诊断 / 验收模式展开来源、提醒、恢复和布局细节。
3. 用户可在主图、成交量和单一副图之间切换分析维度，OHLC 与指标读数始终可读。
4. 系统在数据充分时输出解释性 MTS 卡；在数据不足或来源降级时显式退回不可解释状态。
5. 用户可创建、启停、确认提醒，并在归档 / 恢复时保留本地触发历史与暂停语义。
6. 用户可切换 focus / dense / mobile_tab，布局切换只组织现有产品对象，不引入新业务对象。
7. 浏览器重开时，从 localStorage 恢复自选、提醒、触发历史、布局和最近浏览上下文；失败则回退可用默认布局。

## 关键状态矩阵

| 对象 | 状态 | 界面表达 |
|---|---|---|
| WatchSymbol | `active` | 行内可选中、可看盘、可创建提醒 |
| WatchSymbol | `archived` | 归档区可恢复，提醒进入 `suspended_by_archive` |
| PriceSeries | `formal / demo_fallback / stale / unavailable` | 图表可继续观察，但可信度说明必须同步显示 |
| IndicatorSet | `ready / partial / unavailable` | 副图可切换；不可计算时显示可读降级说明 |
| MtsSignal | `interpretable / data_insufficient` | 显示趋势状态、分数带、信号类型、提醒等级、原因、失效条件 |
| AlertRule | `enabled / disabled / suspended_by_archive` + `idle / triggered / acknowledged` | 提醒卡展示 taxonomy、触发历史和确认动作 |
| ChartLayout | `dense / focus / mobile_tab` | 三栏、专注、移动分栏三种呈现方式 |
| Workspace | `restored / default fallback` | 显示恢复结果或回退默认可用布局 |

## 原型与视觉资产

| 资产 | 路径 | 说明 |
|---|---|---|
| 主可操作原型 | `visual-interaction/prototype/index.html` | 唯一默认人类确认入口，支持 `#buc-001` ~ `#buc-008` |
| 设计说明 | `visual-interaction/design-brief.md` | 说明信息架构、布局、状态与中文文案策略 |
| 证据记录 | `visual-interaction/evidence/seed-state.md` | 记录原型种子状态与视口覆盖 |
| manifest | `visual-interaction/visual-interaction-manifest.json` | 仅由 Harness CLI 生成，不手写 |

## PRD 回流检查

结论：**已同步用户交互反馈，无新增 PRD 范围**。用户反馈页面信息密度过高后，本次把默认呈现改为日常看盘，诊断 / 验收细节改为按需展开；没有新增用户目标、业务用例、BO、AC、权限或范围。

若后续反馈要求以下内容，则必须回流 PRD / Decision Gate：
- 新增市场或新增交易行为。
- 把 MTS 改成收益承诺、胜率、自动买卖。
- 引入云同步、账号体系或外部通知渠道。
- 扩大到完整基本面、组合管理或回测平台。

## 沉淀候选

| 候选 | 建议沉淀位置 | 理由 |
|---|---|---|
| 多市场自选 + 归一预览 + 归档恢复模式 | `project-knowledge/product/ui-surfaces/` | 后续任务应复用同一 Watchlist 结构 |
| 日常看盘 + 诊断 / 验收 + mobile_tab 模式 | `project-knowledge/product/ui-surfaces/` | 这是本地看盘工作台的核心信息架构 |
| MTS 解释卡结构 | `project-knowledge/specs/local-stock-watch-workbench/` | 解释性信号需要稳定字段槽位 |
| 来源健康穿透表达 | `project-knowledge/specs/local-stock-watch-workbench/` | 金融数据可信度必须跨图表、MTS、提醒一致表达 |
| 本地恢复与布局回退 | `project-knowledge/product/prototype/` | 浏览器重开恢复是本地使用的关键体验 |

## 阅读顺序

1. 本文件
2. `interaction-spec/README.md`
3. `interaction-spec/buc-index.md`
4. `interaction-spec/buc-coverage.md`
5. `interaction-spec/BUC-01.md` ~ `BUC-08.md`
6. `_shared/surface-registry.md`
7. `_shared/domain-ui-mapping.md`
8. `_shared/view-models.ts`
9. `_shared/consistency-report.md`
