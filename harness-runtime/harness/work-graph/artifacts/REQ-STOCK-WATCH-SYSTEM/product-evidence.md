# Product Evidence: MyInvestment

> **来源**：prd 技能 → `harness-runtime/harness/stages/20260522-stock-watch-system/product/product-evidence.md`  
> **用途**：记录产品定义使用过的项目知识、规格、开源参考、代码证据和降级情况。

**mission-id:** `20260522-stock-watch-system`  
**Status:** `rewritten-for-open-source-reference`

## 控制契约

- Contract: `harness-runtime/harness/stages/20260522-stock-watch-system/contracts/prd.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本文件只记录证据和解释。

## Mission Inputs

| 输入 | 路径 / 来源 | 使用方式 | 结论 |
|---|---|---|---|
| Mission Contract | `harness-runtime/harness/missions/20260522-stock-watch-system/mission-contract.md` | 产品目标、非目标、成功定义、用户故事、AC 的权威输入 | 第一阶段边界是本地网页、多市场自选、图表/指标、MTS、提醒和本地恢复 |
| Discovery Brief | `harness-runtime/harness/stages/20260522-stock-watch-system/discovery-brief.md` | 问题空间、候选对象、风险、PRD 输入建议 | 证明产品不是单页图表，而是持续可用的跨市场观察工作台 |
| Open Source UI Reference | `docs/open-source-ui-reference.md` | 新增 PRD 参考输入 | 补强自选列表状态、图表 pane、MTS 解释卡、提醒 taxonomy、来源健康、dense/focus/mobile tab |
| Project Context | `project-context.md` | 长期项目约束 | 确认本地网页、localStorage、本地 Express 代理、Yahoo fallback 必须明示、技术信号非投资建议 |
| BO Registry | `product/business-objects.md` | BO、状态、规则、追溯 | 已重写 8 个核心 BO；`PriceBar` 重分类为 `PriceSeries`；`DataProvider` 去技术化为 `MarketDataSource` |
| BUC Package | `product/business-use-cases.md` | 用户闭环、GWT、AC、验证输入 | 已覆盖 9 个 BUC，其中 P0 路径包括自选、工作台、MTS、提醒、来源、恢复 |
| Scope Strategy | `product/scope-strategy.md` | In / Out / Later / Decision Needed | 已明确这是 solution 阶段的上游 PRD 回改，后续 solution 必须重对齐 |
| Technical Signal Research | `docs/technical-signal-research-design.md` | MTS 语义、提醒等级、研究边界 | MTS 必须是解释性技术提醒，不是收益承诺或自动交易动作 |

## Knowledge Evidence

| Evidence-ID | 来源 | 相关主题 | 产品判断影响 | 置信度 |
|---|---|---|---|---|
| KE-01 | `project-knowledge/_index.md` | 知识目录结构、条目状态 | 项目知识库存在，但大多为 `init/draft`，只作为弱证据 | medium |
| KE-02 | `project-knowledge/context/*` | 项目上下文草稿 | 与根 `project-context.md` 互相印证；正式约束以根 `project-context.md` 为准 | low |
| KE-03 | `project-knowledge/product/*` | 产品能力、surface、workflow 草稿 | 仍为 TBD/draft，不能替代本次 PRD 的 BO/BUC 定义 | low |
| KE-04 | `project-context.md` | 本地化、fallback 明示、非投资建议、质量命令 | 直接约束 PRD 范围、来源健康、文案边界和后续验证 | high |

## Spec Alignment

当前配置 `spec.enabled=true`。长期 baseline 位于 `project-knowledge/specs/_index.md`，目前只有 TBD/draft，没有已确认能力规格。因此本 mission 需要产出首次差量规格。

| Capability | Baseline Spec | Change Type | Requirement / Scenario Impact | Decision |
|---|---|---|---|---|
| local-stock-watch-workbench | none（首次建立） | ADDED | 多市场自选、默认工作台、MTS、提醒 taxonomy、来源健康、本地恢复、布局模式、fixture-first 验证 | 写入 `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md` |

## Open Source Reference Evidence

| Source | Used For | Decision Impact | Limit |
|---|---|---|---|
| OpenStock | 股票市场 Web App、提醒、现代金融 UI | 参考“市场工作台 + 个性化提醒 + 公司信息组织” | 不采用账号、MongoDB、Better Auth、AGPL 代码 |
| Invester | Widget 化投资仪表盘 | 参考可定制工作台和信息密度 | 不采用 iframe/widget 作为本地图表替代 |
| Ghostfolio | 自托管财富管理 | 参考隐私、本地/自托管、Zen Mode、风险分析 | 不采用组合管理、账号数据库、Angular/Nest 架构 |
| TradingView Lightweight Charts | 金融图表库 | 继续作为现有图表方向的参考 | 不用 TradingView iframe 替代本地可控图表 |
| KLineChart | K 线与内置指标库 | 作为后续图表能力不足时的候选 | 本轮 PRD 不承诺迁移 |
| StockAlert.pro | 提醒类型 taxonomy | 引入价格型、变化型、技术指标型、MTS 型、定时提醒分类 | 不接入云 API 或外部通知服务 |
| stonks-cli | 终端工作台、健康检查、会话状态 | 参考来源健康、会话标签、列表状态 | 不采用 TUI、AI chat、组合导入 |

## Code / Runtime Evidence

| Evidence-ID | 来源 | 产品判断 |
|---|---|---|
| CE-01 | `package.json` | 当前栈是 React/Vite/Express/lightweight-charts/lucide-react；PRD 不锁实现，但下游需与现有栈兼容或明确决策 |
| CE-02 | `src/App.tsx`、`src/types.ts` | 现有代码已有自选、图表、简单提醒和 `dataSource` 字段，但提醒 taxonomy、PriceSeries、来源健康、ChartLayout、MTS 解释卡不足 |
| CE-03 | `server/index.js` | Yahoo fallback 已存在；PRD 要求把 fallback 从 notice 提升为来源健康业务对象 |

## GitNexus Evidence

| Evidence-ID | GitNexus 查询 / 输出 | 影响面 | 产品判断 |
|---|---|---|---|
| GN-01 | 当前 Codex 会话未暴露 GitNexus MCP 查询工具 | 无法形成结构化代码图谱证据 | 本次 PRD 使用本地文件阅读作为临时证据；后续 solution / technical_analysis 如需棕地影响面，应运行 `npx gitnexus analyze` 后补证 |

## Degradations

| 缺失 / 降级 | 原因 | 风险 | 补救动作 |
|---|---|---|---|
| GitNexus 结构化证据 | 当前工具不可用 | 下游可能低估现有草稿迁移影响 | 运行 `npx gitnexus analyze` 或等效索引，在 solution / technical_analysis 补证 |
| product-knowledge 多数条目 draft/TBD | 长期知识尚未沉淀 | 不能作为定稿行为契约 | 本次以 Mission、PRD 包、根 `project-context.md` 为主证据 |
| baseline spec 缺失 | `project-knowledge/specs/_index.md` 仍为 TBD | 无长期能力基线可对照 | 本 mission 产出 delta spec，任务验收后再推广到长期 spec |
| BUC 子 Agent 超时 | 子 Agent 连续超时，主流程接管写作 | 专业子专家结果不完整 | 由 `product-definition-reviewer` 做只读审查，发现缺口后修复 |
| PRD 回改发生在 solution 阶段 | 用户要求重做 PRD，控制面已在 solution | 旧 solution 与新 PRD 不一致 | 后续必须重新跑 solution 对齐，不得沿旧 solution 继续推进 |

## Reviewer Attention

产品定义审查时重点检查：

- `PriceSeries` 口径是否已替代旧 `PriceBar` 产品语义。
- AlertRule taxonomy 与双状态机是否进入 BUC、FR、领域模型。
- 来源健康是否是一级 UI 语义，而不是单条 notice。
- `spec.enabled=true` 的 delta spec 是否存在。
- 当前 PRD 回改是否明确要求旧 solution 重对齐。
