# Dependency Impact Artifact — 20260522-stock-watch-system

- **Mission:** `20260522-stock-watch-system`
- **Stage:** `technical_analysis`
- **Status:** `DONE`
- **Artifact:** `harness-runtime/harness/stages/20260522-stock-watch-system/dependency-impact.md`
- **Scope:** 仅覆盖 solution.md 约束下的本地 React/Vite/Express 多市场股票看盘系统；不扩展到账号、云同步、自动交易、runtime Agent。

## 维度覆盖摘要

| 维度 | 当前结论 | 证据摘要 |
|---|---|---|
| API / protocol | **CONFIRMED**：本地 `/api/chart/:symbol` 代理 Yahoo Finance chart endpoint；前端按 `ChartPayload` 消费。 | `server/index.js:128-177`、`src/types.ts:19-36`、`README.md:16-23` |
| Data contract | **CONFIRMED + UNCERTAIN**：`WatchSymbol`、`PriceBar`、`ChartPayload`、`AlertRule` 已存在；`SourceHealth`、`MtsExplanation`、归档/恢复快照仍待扩展。 | `src/types.ts`、`src/lib/storage.ts`、`solution.md`、`product-definition.md:112-143` |
| Config / environment | **CONFIRMED**：本地 `PORT` / `NODE_ENV`、浏览器 `localStorage` 为当前运行边界。 | `server/index.js:8-10`、`src/lib/storage.ts:4-29`、`project-context.md:19-24, 43-45` |
| Auth / permission | **EXCLUDED**：当前仓库无登录、账号、角色、token、鉴权路由或云同步。 | `package.json`、`server/index.js`、`rg` 结果、`mission-contract.md` / `product-definition.md` 范围外说明 |
| Async / scheduler | **EXCLUDED / NOT IMPLEMENTED**：当前仅有前端触发式刷新，没有 queue/job/cron/worker 代码。 | `src/App.tsx:165-183`、`server/index.js`、`package.json` 搜索结果 |
| Cache / derived state | **UNCERTAIN**：解决方案希望有短 TTL cache，但当前代码无专用缓存层；只有前端派生状态与纯函数指标计算。 | `solution.md D-03/D-06`、`server/index.js`、`src/lib/indicators.ts`、`src/lib/signals.ts` |
| Observability / operations | **EXCLUDED**：当前只有 `console.log` 启动日志，没有 metrics / alert / tracing / health endpoint。 | `server/index.js:195-197`、`rg` 结果 |
| Test / verification | **CONFIRMED GAP**：只有 `npm run build`；无独立 test script / e2e 入口。 | `package.json:3-10`、`project-context.md:61-65` |

## 1) 基础设施配置

| claim | direction | confidence | source_evidence | failure_mode | validation_action | owner_stage | blocking_threshold |
|---|---|---|---|---|---|---|---|
| 本地运行栈依赖 React 19 + Vite 7 + Express 5；后端职责仅限本地静态服务与行情代理，不存在 DB / queue / auth 运行时。 | upstream / operational | CONFIRMED | `package.json`, `server/index.js:1-197`, `project-context.md:19-24, 32-35, 43-45` | 若后续误把后端当状态中心，前后端职责会漂移，导致本地恢复与行情代理耦合失控。 | 在 `execute` 阶段只允许新增本地代理/静态服务，不允许引入持久化后端；`verify` 阶段跑 `npm run build` 与 `npm run dev`。 | technical_analysis / verify | 任何持久化状态、鉴权或队列被引入后端即停。 |
| 行情入口直接依赖 Yahoo Finance chart API，并在上游失败时返回显式 demo fallback。 | external / upstream | CONFIRMED | `server/index.js:128-177`, `README.md:16-23`, `project-context.md:24, 55-55` | Yahoo 限流、授权、响应 schema 变化会让图表/指标/提醒无法刷新；若 fallback 不透明，会把演示 K 线误读为真实行情。 | `verify` 阶段做 live smoke + fallback smoke：确认 `dataSource` 与 `notice` 字段存在、fallback 可见、错误不会抛出 500。 | verify | 若无法同时证明“可用数据”和“显式降级”，阻断上线门禁。 |
| 当前没有专用 cache layer；行情请求是直连 upstream 的一次性请求，derived state 仅存在于前端计算与 React state。 | internal / operational | UNCERTAIN | `server/index.js:128-177`（无 cache）、`src/App.tsx:165-202`、`src/lib/indicators.ts:5-162`、`solution.md D-03/D-06` | 如果 later 实现把缓存当持久化，可能掩盖 stale / demo 状态；如果完全不加缓存，则 Yahoo 波动会频繁触发重复请求。 | 在 `technical_analysis` 阶段明确“是否需要 TTL cache、cache scope、失效语义”；若需要，则把 cache 作为显式 SourceHealth 组成部分；若不需要，则用测试证明 no-cache 仍能满足刷新和降级。 | technical_analysis | 任何隐式缓存或将缓存误当本地恢复存储的方案都要停。 |
| 本地持久化依赖浏览器 `localStorage`，当前仅保存 watchlist 和 alerts，两把 key 分别为 `myinvestment.watchlist` / `myinvestment.alerts`。 | operational / downstream | CONFIRMED | `src/lib/storage.ts:4-29`, `src/App.tsx:148-163`, `project-context.md:43-45`, `README.md:27-33` | schema 演进或浏览器限制会导致重开恢复丢失；若直接覆盖写入而无版本号，旧数据会被破坏。 | 在 `execute` 阶段加入版本化 workspace snapshot、迁移器和回退测试；`verify` 阶段做重新打开浏览器恢复验证。 | execute / verify | 如果无法保留旧 watchlist / alerts 的兼容恢复，必须阻断 schema 冻结。 |
| 若 `localStorage` 容量、迁移或恢复失败率超出本地 snapshot 可承受范围，可能需要额外存储层；这不是当前默认路径。 | operational / decision-boundary | ASSUMED | `solution.md D-06`, `project-context.md:43-45`, `src/lib/storage.ts:4-29` | 若没有触发判据就提前引入 IndexedDB / 后端存储，会越过本地边界；若容量失败却没有 Storage Gate，会导致恢复路径不可用。 | `technical_analysis` 必须定义容量/迁移/恢复失败触发判据；`execute` 用旧版本 snapshot、损坏 snapshot、超大 watchlist/alerts fixture 验证；触发判据命中时发 Storage Gate，不得静默引入新存储。 | technical_analysis / execute / verify | 只有验证证明 localStorage 无法满足版本化 snapshot，才允许进入 Storage Gate；任何未授权 IndexedDB / 后端持久化都阻断。 |
| 质量检查目前只依赖 `npm run build`，没有独立 unit / integration / e2e script。 | operational / verification | CONFIRMED | `package.json:3-10`, `project-context.md:61-65` | 没有 test script 时，signal / source / restore 的回归会靠人工阅读，容易遗漏数据契约回退。 | 在 `execute` / `verify` 阶段补齐 fixture-driven unit tests 与 Playwright/e2e；最少要覆盖 market normalization、fallback、MTS、alerts、restore。 | verify | 如果没有自动化测试门禁，不允许把技术分析结论当作已验证实现。 |

## 2) 外部业务系统

| claim | direction | confidence | source_evidence | failure_mode | validation_action | owner_stage | blocking_threshold |
|---|---|---|---|---|---|---|---|
| 真实外部业务系统目前只有 Yahoo Finance；它是唯一 live 数据供应方，其余数据路径都应通过本地显式 fallback 或未来可替换边界承载。 | external / upstream | CONFIRMED | `server/index.js:128-177`, `README.md:16-23`, `project-context.md:24, 55-55`, `solution.md D-03` | 如果把 Yahoo 的响应当作固定契约，后续任何字段/频率变化都会把图表和提醒一起拖垮。 | `verify` 阶段做 provider-smoke，确认 fallback 可见且不把 demo 伪装成 formal。 | verify | 若无法区分 formal / demo / unavailable，就阻断 source contract 冻结。 |
| formal provider 的最终品牌/授权尚未锁定，核心域必须保持 provider-agnostic；Yahoo 只应作为当前实现。 | external / decision-boundary | ASSUMED | `mission-contract.md`（formal supplier 未锁定）、`solution.md D-03`, `product-definition.md:89-93` | 过早把某家供应商的 auth / rate limit / 代码格式写进领域层，会造成后续切换成本爆炸。 | `technical_analysis` 必须冻结 `MarketDataSource` adapter/interface draft，列出 provider-specific 字段禁入清单；`execute` 用 Yahoo fixture + demo fixture + fake provider fixture 证明领域层只消费 normalized `PriceSeries` / `SourceHealth`；首次 auth/quota/response schema 渗透到领域对象或 localStorage 时触发 Provider Gate。 | technical_analysis / execute / verify | 一旦 provider-specific 字段进入 `WatchSymbol`、`AlertRule`、`PriceSeries` 领域语义或持久化 schema，必须发 Decision Gate。 |

## 3) 自身代码

| claim | direction | confidence | source_evidence | failure_mode | validation_action | owner_stage | blocking_threshold |
|---|---|---|---|---|---|---|---|
| `src/App.tsx` 是当前运行时的单点聚合：同一组件里同时处理 watchlist、fetch、chart、signal、alerts 和 local storage 写回。 | internal / peer | CONFIRMED | `src/App.tsx:148-380` | 组件过大将导致 surface 之间 state 泄漏、locator 漂移、测试不可复现。 | 在 `technical_analysis` 中拆分为 watchlist / workbench / source / alerts / restore 等 surface 组件，并保留稳定 `data-testid`。 | technical_analysis | 若拆分会破坏当前 state identity 或 locator contract，先停下来做设计 Gate。 |
| 当前信号引擎仍是“四因子共振指标”实现，不是 solution 要求的完整 MTS；它依赖至少 60 根 K 线，并计算 EMA20/60、RSI14、MACD、BOLL、ATR、OBV。 | internal / peer | CONFIRMED | `src/lib/signals.ts:4-115`, `src/lib/indicators.ts:5-162`, `README.md:38-59` | 短样本会直接落到 `hold/数据不足`；若把旧分数当作 MTS 对外展示，会违反产品语义。 | 在 `execute` 中加 MTS 解释层映射：trend_state / score_band / signal_type / alert_level / reason_codes / invalidators；`verify` 阶段用冻结 bars 回放。 | execute / verify | 如果无法把旧四因子结果映射到 MTS 字段而不丢解释性，阻断对外展示。 |
| 当前 alert schema 只支持 `above/below` 价格提醒或 `signal` 提醒，只有 `enabled` / `lastTriggeredAt?`，没有 taxonomy、acked、archive suspension 或 trigger history。 | internal / peer | CONFIRMED | `src/types.ts:59-68`, `src/App.tsx:204-269`, `product-definition.md:136-143` | FR-05 需要的本地提醒模型无法闭合；归档后提醒可能丢失或无法恢复。 | 在 `execute` 中扩展提醒 schema 与触发状态机；`verify` 阶段补提醒命中/确认/归档恢复测试。 | execute / verify | 如果 alert 记录无法迁移且保持历史，阻断 schema 冻结。 |
| 当前 watchlist 语义是“删除即消失”，没有 active/archived 状态，`removeSymbol` 会直接过滤掉条目。 | internal / peer | CONFIRMED | `src/App.tsx:234-237`, `src/types.ts:3-8`, `product-definition.md:123-143` | 这会与 solution 的归档/恢复语义冲突，导致已归档标的和绑定提醒不可恢复。 | 在 `execute` 阶段把 `WatchSymbol` 改成可归档模型，并保留归档状态参与恢复；`verify` 阶段检查重开后仍可恢复。 | execute / verify | 如果归档状态无法保存在本地快照中，阻断 watchlist schema 冻结。 |
| `normalizeTicker` 仅覆盖 US/HK/CN/KR 的当前后缀规则；当前添加流程直接在 submit 时归一并写入 watchlist，没有独立归一预览或歧义确认层。 | internal / peer | CONFIRMED | `src/data/markets.ts:24-45`, `src/App.tsx:218-229`, `product-definition.md:22-28, 132-156` | 数字代码歧义可能把用户意图写错市场，污染后续行情、提醒和恢复。 | 在 `execute` 中增加归一预览与确认交互；`verify` 用歧义样本验证阻断路径。 | execute | 任何歧义输入若可静默进入 active，就阻断 FR-01。 |
| `ChartPayload` / `AlertRule` 结构只覆盖当前实现，尚不足以表达 `formal/demo_fallback/stale/unavailable`、MTS 的解释字段和 layout/restore 快照。 | internal / data contract | UNCERTAIN | `src/types.ts:19-36, 45-68`, `solution.md D-03/D-06/D-07`, `product-definition.md:24-28, 136-143` | 若继续沿用旧 schema，source health、MTS、restore 会只能靠隐式状态，导致验证和回放都失真。 | 在 `technical_analysis` 中先冻结扩展字段（SourceHealth、MtsExplanation、workspace snapshot）；如果字段膨胀超过当前结构，发 Decision Gate。 | technical_analysis | 若无法在不破坏旧数据的前提下加入这些字段，则必须暂停并做数据契约决策。 |
| 当前 UI 仍缺少独立的 source health panel、indicator switcher、restore surface 与 alert taxonomy surface；这些在 solution 和 surface registry 中都被定义为独立 surface。 | internal / UX contract | CONFIRMED | `src/App.tsx:271-380`, `surface-registry.md`, `solution.md D-01~D-07`, `docs/open-source-ui-reference.md` | 继续用单屏散装区块会让 locator / 状态词汇不稳定，后续 e2e 和验收无法对齐。 | 在 `execute` 阶段按 surface-registry 重组界面，保留每个 surface 的稳定定位器与状态词汇。 | execute | 如果 surface 复用导致语义混淆，必须停下来重做信息架构。 |

## Blockers

- **无外部系统硬 blocker。** 当前没有必须先由其他团队或基础设施团队交付的接口、数据库、队列、账号或云服务依赖。
- **存在 technical_analysis 前置设计义务。** Provider-agnostic ACL、Storage Gate 触发判据、SourceHealth 状态机、workspace snapshot、测试门禁必须在技术设计中冻结；这些不是执行阶段可以临时补的细节。

## 已确认就绪

- 本地 React/Vite/Express 栈已经可运行，开发入口清晰，生产/开发路径分离明确。
- Yahoo Finance 直连 + demo fallback 的方向已经在 server 与 README 中实现且可见。
- 指标与信号的纯函数层已存在，适合 fixture-first 回放。
- `localStorage` 已经承载 watchlist / alerts，说明本地持久化边界已确定。

## 证据缺口

1. **SourceHealth 四态与历史字段**：当前代码只有 `yahoo/demo`，没有 `formal/stale/unavailable` 状态机，也没有 last refreshed / retry state。
2. **版本化 workspace snapshot**：当前只写两把 localStorage key，没有版本号、迁移器和回退校验。
3. **Alert taxonomy 与历史状态**：当前没有价格/变化/技术指标/MTS/定时分类模型，也没有 acknowledged / suspended_by_archive / trigger history。
4. **MTS 对外解释字段**：当前 `CompositeSignal` 仍是旧 signal shape，和 solution 的 MTS 字段还没对齐。
5. **fixture-first e2e / 测试门禁**：当前只有 build gate，缺少 unit / replay / e2e test 入口。
6. **缓存策略**：方案要求短 TTL cache，但当前 repo 无 cache 实现，也没有 cache 失效语义。

## Excluded surfaces

- **数据库 / 服务器端持久化**：排除依据是 `project-context.md:43-45`、`mission-contract.md` / `product-definition.md` 的本地边界，以及 `rg` 搜索未发现 DB / ORM / migration 相关代码。
- **队列 / 定时任务 / worker**：排除依据是 `server/index.js` 仅含请求-响应流，`src/App.tsx` 仅在选择标的或切换 range 时触发 fetch，没有 job / cron / queue 调度代码。
- **账号 / 登录 / 鉴权**：排除依据是任务范围只要求本地使用；代码搜索未发现 `login` / `auth` / `token` / `session` 路由或模块，`server/index.js` 仅有行情代理与静态服务。
- **云同步 / 多设备同步**：排除依据是 mission 约束、product-definition 的 Mission fit、`project-context.md:43-45`。
- **自动交易 / broker / 外部下单**：排除依据是 mission contract 明确非目标，solution D-08 也明确拒绝 runtime Agent / trading path。
- **外部推送通知**：排除依据是 product-definition / solution 只保留本地提醒，不引入外部通知通道。
- **运行时 Agent**：排除依据是 mission contract “涉及 Agent 组件：否”，solution D-08 明确拒绝产品运行时 Agent；代码搜索未发现 agent runtime / tool / policy 执行入口。
- **KLineChart 替代路线**：排除依据是 `docs/open-source-ui-reference.md` 将其列为后续候选，不是当前主路由。
- **IndexedDB**：排除依据是 solution 仅把它列为后续备选；当前实现和当前 artifact 不依赖它。

## Decision gates

1. **Provider Gate**：若后续必须锁定某家正式行情供应商的 auth / quotas / response schema，必须先发 Decision Gate，再冻结 `MarketDataSource` contract。
2. **Cache Gate**：若 short TTL cache 需要跨请求保持或影响 restore / stale 语义，必须先做缓存边界决策，不能用隐式 state 代替。
3. **Chart Gate**：若 `lightweight-charts` 不能满足主图 / 成交量 / 副图与稳定 locator 的要求，再发图表库替换 Decision Gate。
4. **Storage Gate**：若 `localStorage` 容量或迁移不能支持版本化 snapshot，则必须先决策是否引入额外存储层，而不是静默扩张 persistence scope。

## Summary

### confirmed_dependencies
- 本地 React/Vite/Express 运行栈与 Yahoo Finance 代理、demo fallback 的本地服务链路。
- `localStorage` 作为 watchlist / alerts 的当前持久化边界。
- 现有四因子 signal / indicator 纯函数计算链路与 `lightweight-charts` 图表渲染。
- 当前 UI 仍是单组件聚合，确实需要 surface 拆分与稳定 locator。
- 当前测试门禁只有 build，没有 unit / replay / e2e。

### uncertain_dependencies
- 短 TTL cache 的最终形态与 scope。
- `ChartPayload` / `AlertRule` / workspace snapshot 的扩展字段是否能无损兼容旧数据。
- `formal/demo_fallback/stale/unavailable` 的完整 source-health 状态机。

### assumed_dependencies
- 未来正式行情供应商会通过 `MarketDataSource` ACL 接入，而不会把 provider-specific 字段写入领域层。
- 如果 `localStorage` 容量、迁移或恢复失败率超出版本化 snapshot 可承受范围，后续可能需要额外存储层；验证动作是 technical_analysis 定义触发判据、execute/verify 用旧版本/损坏/大体量 fixture 证明，命中阈值时走 Storage Gate。

### blast_radius
- **Infrastructure:** 本地服务、环境变量、浏览器存储、构建门禁、测试门禁。
- **External:** Yahoo Finance / future provider 的协议、授权、限流与 fallback 语义。
- **Self code:** watchlist、workspace、signal、alert、source-health、restore surface 的所有 state contract。

### excluded_surfaces
- DB / queue / scheduler / auth / cloud sync / auto trading / runtime Agent / external push notifications / KLineChart / IndexedDB（当前不依赖）。

### decision_gates
- Provider Gate、Cache Gate、Chart Gate、Storage Gate。

## Dependency Validity Review

**Verdict:** PASS

dependency-validity-reviewer 第二轮复审确认：当前 artifact 已把关键依赖声明、ASSUMED 假设与验证动作、blast radius 分类对齐到代码 / 文档证据，可作为 technical_analysis 输入。ASSUMED 项只能按风险和门禁前提使用，不能当作 CONFIRMED 事实。

### 可供下游直接消费

- 本地 React/Vite/Express + Express 行情代理边界。
- Yahoo Finance + 显式 demo fallback 当前链路。
- 当前 `localStorage` 持久化边界仅含 watchlist / alerts。
- `App.tsx` 单体聚合现状。
- 四因子 signal 非正式 MTS。
- 现有 alert / watchlist / schema 缺口。
- 当前测试门禁仅 build。

### 只能作为风险 / 门禁前提

- cache 是否需要 TTL 及其 scope。
- `ChartPayload` / `AlertRule` / workspace snapshot 扩展兼容性。
- 完整 `formal / demo_fallback / stale / unavailable` source-health 状态机。

### 不得当作已确认事实

- “future formal provider 可无痛 provider-agnostic 接入”必须先在 technical_analysis 冻结 adapter/interface 与 provider-specific 字段禁入清单，并在 execute / verify 用 Yahoo / demo / fake provider fixture 验证；首次 schema/auth/quota 渗透即触发 Provider Gate。
- “`localStorage` 不足时应扩到额外存储层”必须先定义容量 / 迁移 / 恢复失败触发判据，并用旧版本 / 损坏 / 大体量 fixture 验证；命中阈值后走 Storage Gate。
