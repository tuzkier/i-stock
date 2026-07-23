# 执行简报: 20260522-stock-watch-system

> **来源**：拆解技能 → `harness-runtime/harness/stages/20260522-stock-watch-system/execution-brief.md`
> **参考方法论**：OpenSpec Vertical Slicing（纵切交付）+ TDD Red-Green-Refactor
> **TDD 计划契约**：`.harness/docs/tdd-planning-contract.md`
> **设计原则**：这份文件读完即可理解任务边界、Atomic Task 队列、证据要求和停止条件；它是唯一的执行计划产物，不再另起第二份计划文档。
> **上游**：`mission-contract.md` | `product/product-definition.md` | `product/product-domain-model.md` | `business-objects.md` | `business-use-cases.md` | `product-evidence.md` | `solution.md` | `tech-design.md` | `interaction.md` | `interaction-spec/`

**Author:** Codex
**Date:** 2026-05-23
**mission-id:** `20260522-stock-watch-system`

---

## 控制契约

- Contract: `contracts/execution-brief.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本文只承载执行切片、Atomic Task 队列和 TDD 计划，不承载执行结果、审查 verdict 或 Gate 结论。

---

## TL;DR

把本 mission 拆成 6 个可独立消费的纵切交付：先冻结自选 identity 与归一预览，再落地来源/图表/布局的可见降级，再替换旧四因子为可解释的 MTS，再把提醒做成带 taxonomy、触发、确认和 scheduled 的本地状态机，再把版本化 `WorkspaceSnapshotV2` 与 per-symbol layout 恢复补齐，最后用冻结样本和稳定 locator 把四市场、歧义、降级、触发与恢复串成可回放门禁。全程显式覆盖 Provider / Cache / Storage / Chart Gate；不引入产品运行时 Agent。

---

## 任务覆盖总览

| Parent task | 交付结果 | 主要 surface | 主要 scenario / spec | 依赖 |
|---|---|---|---|---|
| T001 | 多市场自选归一、列表摘要、归档暂停与恢复 | `SURF-WATCHLIST`, `SURF-RESTORE` | 添加前预览归一结果、歧义输入不得静默写入、列表显示行情摘要、归档暂停提醒 | 无 |
| T002 | 默认工作台、来源健康、指标切换、可见降级 | `SURF-WORKBENCH`, `SURF-SOURCE`, `SURF-LAYOUT` | 打开默认工作台、切换副图指标、指标局部降级、demo fallback 可见、stale 不伪装实时成功、重试失败不导致页面不可用、dense/focus、mobile_tab | T001 |
| T003 | MTS 解释卡、ReasonRegistry、非投资建议边界 | `SURF-MTS`, `SURF-WORKBENCH` | 输出完整 MTS 卡、MTS 不表达投资建议、数据不足时不输出伪 MTS | T002 |
| T004 | 分类提醒、触发/确认、scheduled、归档暂停 | `SURF-ALERTS`, `SURF-MTS` | 创建分类提醒、提醒触发后可确认；并补齐 scheduled 与归档暂停状态机 | T003 |
| T005 | `WorkspaceSnapshotV2`、per-symbol layout、浏览器重开恢复、默认回退 | `SURF-RESTORE`, `SURF-LAYOUT`, `SURF-WATCHLIST` | 浏览器重开恢复工作台、布局恢复失败回退默认、dense/focus 切换、mobile_tab 工作台 | T001, T002, T004 |
| T006 | 冻结样本、回放、unit/e2e 门禁、AC 映射 | 全部 surfaces | 使用冻结样本验收核心路径 | T001~T005 |

### scenario 覆盖映射

- **T001** 覆盖：1 添加前预览归一结果、2 歧义输入不得静默写入、3 列表显示行情摘要、4 归档暂停提醒。
- **T002** 覆盖：5 打开默认工作台、6 切换副图指标、7 数据不足时指标局部降级、13 demo fallback 可见、14 stale 不伪装实时成功、15 重试失败不导致页面不可用、18 桌面 dense 与 focus 切换、19 移动端 tab 工作台。
- **T003** 覆盖：8 输出完整 MTS 卡、9 MTS 不表达投资建议、10 数据不足时不输出伪 MTS。
- **T004** 覆盖：11 创建分类提醒、12 提醒触发后可确认；并把 scheduled alert 与归档暂停落成可验证状态机。
- **T005** 覆盖：16 浏览器重开恢复工作台、17 布局恢复失败回退默认、18 桌面 dense 与 focus 切换、19 移动端 tab 工作台。
- **T006** 覆盖：20 使用冻结样本验收核心路径，以及 AC-01~AC-05 的跨切片回放。

---

## 硬性约束

| 约束 | 来源 | 说明 |
|---|---|---|
| 不做自动交易、不做收益承诺、不做胜率/确定性买卖建议 | mission-contract / product / solution | 所有信号与提醒都必须保留技术分析边界。 |
| 不引入产品运行时 Agent | mission-contract / solution / tech-design | `agent_engineering.enabled=true` 只影响阶段治理，不进入产品 runtime。 |
| 不把 demo / stale / unavailable 伪装成正式实时行情 | project-context / solution D-03 | 来源健康必须显式可见，且下游图表/MTS/提醒同步降级。 |
| 本地持久化边界只允许 `localStorage + WorkspaceSnapshotV2` | project-context / solution D-06 / tech-design INT-07 | 不把 localStorage 当数据库，不静默升级到 IndexedDB 或后端持久化。 |
| 图表主路径继续以 `lightweight-charts` 为前提，若不满足合同先走 Chart Gate | solution D-01 / tech-design Gate | 不在组件层硬缝补丁绕过图表库边界。 |
| 代码归一必须显式预览，歧义输入不得静默写入 active | mission-contract / product / tech-design | 多市场数字代码风险必须在写入前暴露。 |

**编码规范要点：** 用户可见文案默认中文；金融缩写、股票代码、指标名可保留英文；本地持久化边界仍是浏览器 `localStorage`。

**技术选择限制：** React/Vite/Express 运行栈不变；后端只做本地服务与行情代理；fixture-first E2E 作为门禁，live 只做 smoke。

**已知的坑：** Yahoo 限流或 schema 变化、数字代码跨市场歧义、`localStorage` schema 演进、`lightweight-charts` pane / locator 稳定性、旧四因子信号残留为正式 MTS 文案。

---

## 接口与数据合同速查

| 接口 / 数据对象 | 变更类型 | 签名摘要 |
|---|---|---|
| `MarketDataSource.fetchSeries(symbol, range, options)` | 新增 | 返回 `MarketDataEnvelope`，含 `priceSeries`、`sourceHealth`、`meta`、`servedAt`、`cacheState`；TTL 60 秒，`forceRefresh` 必须绕过 cache。 |
| `ChartPayload` → `MarketDataEnvelope` | 修改 | 新增 `sourceHealth`、`degradationReason`、`sourceName`、`lastRefreshedAt`、`retryState`、`cacheState`，保留旧 `bars` 过渡。 |
| `SourceHealth` | 新增 | `formal | demo_fallback | stale | unavailable`，带 `affectedObjects`、`retryState`、`lastRefreshedAt`。 |
| `PriceSeries` | 替换 | 以整段行情序列替代裸 `PriceBar[]`，产出 `latestOhlc`、`latestPrice`、`changeSummary`。 |
| `MtsExplanation` + `MtsReasonRegistry` | 替换 | 结构化 MTS 输出，不允许自由文本 reason；未知码必须降级为 `UNKNOWN_CODE`. |
| `AlertRule` | 修改 | 新增 `taxonomy`、`activationState`、`triggerState`、`history[]`、`acknowledgedAt`、`suspendedReason`、`restoreIntent`、scheduled 语义。 |
| `WorkspaceSnapshotV2` | 新增 | `version`、`watchlist`、`alerts`、`selectedSymbol`、`layoutBySymbol`、`globalLayoutFallback`、`selectedMobileTab`、`restoreMetadata`。 |

---

## Atomic Task 代码模式参考详表

> 本节是 execute 阶段的代码模式权威参考。若本节与 Atomic Task 下方的简短 `code pattern references` 列表冲突，以本节的 `do_not_copy_boundary` 为准；若实际代码已被前序任务改动，执行者必须先对齐最新实现，再继续本 Atomic Task。

### T001-A1

| path | pattern_type | symbol / section | observed_convention | reuse_in_this_task | do_not_copy_boundary |
|---|---|---|---|---|---|
| `src/data/markets.ts` | domain helper | `normalizeTicker` | 纯函数输入 `symbol + market`，先 `trim/toUpperCase/remove spaces`，再按市场后缀归一；不触发 UI 或网络副作用。 | 抽出 `src/domain/market-normalization.ts` 时沿用纯函数与显式 market 参数，新增 preview / ambiguous result。 | 不复制当前“纯数字 + 已选 market 就直接推断”的静默写入行为；歧义必须停在确认态。 |
| `src/data/markets.ts` | seed / labels | `marketLabels`, `marketHints`, `defaultWatchlist` | 市场展示文案集中在 data 层，默认样本保留四市场代表标的。 | 继续集中维护市场标签、输入 hint 与四市场 fixture seed。 | 不把行情状态、alert 状态或 layout 偏好塞进 market seed。 |
| `src/App.tsx` | form state pattern | `addSymbol` / `symbol-form` | 表单提交在组件内做输入清理、构造 `WatchSymbol`、更新 watchlist 和 selected。 | 先保留同一提交路径，把写入前插入 normalization preview/confirm。 | 不继续在 `addSymbol` 内直接调用 `normalizeTicker` 后写 active；不在 UI 里重复实现市场规则。 |

### T001-A2

| path | pattern_type | symbol / section | observed_convention | reuse_in_this_task | do_not_copy_boundary |
|---|---|---|---|---|---|
| `src/lib/storage.ts` | storage adapter | `readWatchlist` / `writeWatchlist` | `readJson<T>(key, fallback)` 捕获 JSON parse / localStorage 异常并回退；写入使用 `JSON.stringify`。 | 继续用小型 storage adapter 封装读写，扩展 active/archived 与 restoreIntent。 | 不把 server cache、行情 fallback 或 provider payload 写进 localStorage。 |
| `src/App.tsx` | list rendering | `.watch-list`, `.watch-item`, `removeSymbol` | watchlist 行是 button，selected 由 symbol 匹配，删除动作阻止事件冒泡。 | 沿用行级可点击结构和明确的删除动作，改为 archive / restore 状态展示。 | 不把归档实现成 `filter` 物理删除；不让删除 icon 触发选中副作用。 |
| `src/types.ts` | shared model | `WatchSymbol`, `AlertRule` | 共享类型集中定义，UI 与 storage 共用同一结构。 | 在 shared type 上增加 active/archive 与 alert suspension 字段。 | 不用组件局部临时 state 代替持久化业务状态。 |

### T002-A1

| path | pattern_type | symbol / section | observed_convention | reuse_in_this_task | do_not_copy_boundary |
|---|---|---|---|---|---|
| `server/index.js` | API route | `/api/chart/:symbol` | route 内先归一 symbol/range，再 fetch Yahoo，失败时返回 JSON fallback 而不是 500。 | 保留单一路由和“不拖垮页面”的失败语义，包装为 `MarketDataEnvelope`。 | 不新增未经设计的 public route；不把 provider auth/quota/schema 细节暴露给前端领域对象。 |
| `server/index.js` | parser | `compactBars` | 从 Yahoo `result.indicators.quote[0]` 提取 OHLCV，并过滤非 finite OHLC。 | 沿用“只传递可用 bar”的清洗规则，补充 sourceHealth/cacheState 元数据。 | 不把 malformed bar 静默伪装成 0；不把 volume 缺失升级成整条 bar 不可用。 |
| `server/index.js` | fallback generator | `fallbackPayload`, `generateFallbackBars` | demo fallback 使用 deterministic-ish seed，返回 `dataSource: demo` 与中文 notice。 | 将 demo/stale/unavailable 显式映射进 `SourceHealth`，继续可见告知用户。 | 不把 demo fallback 标成 formal；不把 demo bar 写入 workspace snapshot。 |

### T002-A2

| path | pattern_type | symbol / section | observed_convention | reuse_in_this_task | do_not_copy_boundary |
|---|---|---|---|---|---|
| `src/App.tsx` | chart lifecycle | `ChartPanel` | React `useEffect` 内创建 `lightweight-charts`，cleanup 调用 `chart.remove()`，series 数据来自 `bars`。 | 沿用生命周期和 cleanup，扩展主图/成交量/副图 surface 与稳定 locator。 | 不在 render 阶段创建 chart；不绕过 Chart Gate 手写 canvas 状态。 |
| `src/App.tsx` | user-visible source notice | `payload?.notice`, `.data-notice` | 当前降级只通过 notice 文案显示，未结构化区分 formal/demo/stale/unavailable。 | 保留可见告知位置，替换为 `SourceHealthPanel` 和可断言状态。 | 不让 source 降级只停留在 console/error；不把 unavailable 显示成实时成功。 |
| `src/lib/indicators.ts` | indicator functions | `ema`, `macd`, `rsi`, `atr`, `lastFinite` | 指标函数返回数组或 `Number.NaN`，展示层用 `lastFinite` 和格式化处理不可用。 | 继续让不可用以 `NaN`/局部降级表达，UI 展示指标状态说明。 | 不用 0 填充数据不足的指标；不让局部指标失败导致整页不可用。 |

### T003-A1

| path | pattern_type | symbol / section | observed_convention | reuse_in_this_task | do_not_copy_boundary |
|---|---|---|---|---|---|
| `src/lib/signals.ts` | scoring domain | `buildSignal` | 当前以 bars 为唯一输入，返回 `CompositeSignal`，数据不足时 `kind=hold`、`confidence=0`、中文 reasons。 | 迁移为 `MtsExplanation` 时保留纯函数输入输出与数据不足短路。 | 不复制“强买点/强卖点”作为正式建议文案；不继续输出自由文本 reason 作为唯一解释合同。 |
| `src/lib/indicators.ts` | numeric helper | `lastFinite`, `slope`, `bollinger` | 指标计算通过 `Number.NaN` 表示不可用，调用方再聚合。 | MTS 计算继续消费 `IndicatorSet` / `PriceSeries`，把不可解释写入 invalidators。 | 不在 MTS 里重新发起行情请求；不把 provider 细节写进 reason code。 |
| `src/types.ts` | legacy type | `CompositeSignal`, `SignalKind` | 旧类型包含 `kind/label/score/confidence/buyLine/sellLine/stopLine/reasons/warnings`。 | 作为迁移对照，拆成 `MtsExplanation` 与 `MtsReasonRegistry`。 | 不保留自由文本 `reasons[]` 作为 registry 的替代品。 |

### T003-A2

| path | pattern_type | symbol / section | observed_convention | reuse_in_this_task | do_not_copy_boundary |
|---|---|---|---|---|---|
| `src/App.tsx` | side panel composition | `.signal-panel`, `.signal-card`, `.reason-list` | 右侧面板分 `section`，卡片 tone 由 signal kind 映射，原因/警告以列表展示。 | 沿用侧栏结构，替换为 MTS card、reason code 展示和非投资建议边界。 | 不继续展示“交易线/强买/强卖”作为推荐动作；不让文案覆盖 source degraded。 |
| `src/App.tsx` | formatting helpers | `formatNumber`, `formatCompact` | 数值格式化集中在组件顶部，非 finite 显示 `--`。 | MTS 卡所有数值读数继续用统一格式化和不可用占位。 | 不把 `NaN`、`undefined` 或原始 JS 错误显示给用户。 |
| `src/styles.css` | panel styling | `.signal-card`, `.side-section`, `.metric-strip` | 页面已有密集信息面板和条带式指标布局。 | 保持工作台信息密度与扫描性，新增 MTS 状态不做营销式 hero。 | 不新增浮夸卡片或遮挡图表的解释层。 |

### T004-A1

| path | pattern_type | symbol / section | observed_convention | reuse_in_this_task | do_not_copy_boundary |
|---|---|---|---|---|---|
| `src/types.ts` | alert model | `AlertRule` | 当前 AlertRule 是扁平对象：`direction/price/signal/enabled/lastTriggeredAt`。 | 扩展为 taxonomy、activationState、triggerState、history 与 scheduled condition。 | 不把 `enabled: boolean` 同时当作暂停、触发和确认状态；不丢弃 last trigger history。 |
| `src/App.tsx` | alert creation | `addPriceAlert`, `addSignalAlert` | 价格和 signal alert 由 UI 构造对象并 prepend 到 alerts。 | 保留创建入口，把表单结果交给 alert domain validator。 | 不让 UI 直接拼非法 taxonomy；不把 scheduled 做成后台推送。 |
| `src/lib/storage.ts` | alert persistence | `readAlerts` / `writeAlerts` | alert 本地存储与 watchlist 使用同一 readJson/write 模式。 | 继续本地持久化 alert rule 和 history。 | 不把 alert evaluator 或 clock tick 写进 storage helper。 |

### T004-A2

| path | pattern_type | symbol / section | observed_convention | reuse_in_this_task | do_not_copy_boundary |
|---|---|---|---|---|---|
| `src/App.tsx` | derived state | `triggeredAlerts = useMemo(...)` | 当前触发逻辑是从 latest price、selected symbol、signal kind 派生的同步过滤。 | 抽出 app-open evaluator，继续用 observation + alert set 得到可回放结果。 | 不把 evaluator 留在组件内成长条件树；不把触发结果只存在 render 派生态。 |
| `src/App.tsx` | alert panel UI | `.triggered`, `.alert-builder`, `.alert-list` | UI 已有创建、开关和删除操作，但缺少确认、历史和暂停说明。 | 沿用面板入口，新增确认动作、history 与 `missed_while_closed` 可见状态。 | 不新增系统通知、后台 worker 或外部推送。 |
| `src/lib/signals.ts` | signal input | `buildSignal` | signal 目前是 alert 匹配输入之一。 | MTS alert 只消费结构化 `MtsExplanation` / reason code。 | 不重新计算 MTS；不把旧 `SignalKind` 当长期 taxonomy。 |

### T005-A1

| path | pattern_type | symbol / section | observed_convention | reuse_in_this_task | do_not_copy_boundary |
|---|---|---|---|---|---|
| `src/lib/storage.ts` | JSON fallback | `readJson<T>` | localStorage parse 失败时返回 fallback，不抛出到 UI。 | 扩展为 versioned snapshot reader，输出 `restoreStatus` 和 migration metadata。 | 不静默吞掉迁移失败原因；不在失败时清空用户旧 key。 |
| `src/lib/storage.ts` | key boundary | `watchlistKey`, `alertKey` | 当前只有两个 key，分别承载 watchlist 与 alerts。 | 迁移到 `WorkspaceSnapshotV2` 时保留旧 key 读取兼容和幂等迁移。 | 不要求 IndexedDB、后端 DB 或账号同步才能通过。 |
| `src/types.ts` | shared model | `WatchSymbol`, `AlertRule` | 本地状态和 storage 共用 shared types。 | 新增 `WorkspaceSnapshotV2`、`layoutBySymbol`、`restoreMetadata` 类型。 | 不把 provider cache、chart runtime object 或 function 写入 snapshot。 |

### T005-A2

| path | pattern_type | symbol / section | observed_convention | reuse_in_this_task | do_not_copy_boundary |
|---|---|---|---|---|---|
| `src/App.tsx` | selected state | `selected`, `range`, `payload`, `loading`, `error` | App 顶层集中持有工作台状态，通过 props/局部函数驱动 UI。 | 引入 layout/restore state 时仍保持单向状态流，并以 snapshot 恢复初始化。 | 不让 layout 切换改变业务对象；不把恢复失败变成页面空白。 |
| `src/styles.css` | responsive shell | `.terminal-shell`, `.watch-panel`, `.market-workspace`, `.signal-panel` | 页面已有三栏工作台与响应式样式基础。 | 在现有 shell 上实现 dense/focus/mobile_tab 视图，不重做整站信息架构。 | 不做卡片套卡片或让移动端强行复刻桌面三栏。 |
| `src/App.tsx` | chart component boundary | `ChartPanel({ bars })` | ChartPanel 只接收 bars，不知道 selected symbol 或 layout 业务状态。 | layout 控制器负责容器和可见性，ChartPanel 继续保持数据展示边界。 | 不把 `IChartApi` 或 DOM ref 存入 `WorkspaceSnapshotV2`。 |

### T006-A1

| path | pattern_type | symbol / section | observed_convention | reuse_in_this_task | do_not_copy_boundary |
|---|---|---|---|---|---|
| `package.json` | command boundary | `scripts.build` | 当前唯一门禁命令是 `tsc --noEmit && vite build`；尚无 test/e2e scripts。 | 新增测试命令时保持 `build` 语义不变，并让 fixture-first 命令可单独运行。 | 不把 live Yahoo 请求作为阻塞验收门禁。 |
| `server/index.js` | deterministic fixture seed | `generateFallbackBars` | fallback bars 由 symbol seed 生成，适合冻结样本对照。 | 用其输出形态设计 provider success/failure/stale fixtures。 | 不把 demo generator 当正式行情真值；fixture 需要 checksum/replay log。 |
| `src/lib/indicators.ts` | pure computation | indicator helpers | 指标函数无 IO，适合作为 unit/replay fixture 的断言对象。 | 以 frozen bars 驱动指标、MTS 和 alert replay。 | 不通过 mock UI 文案替代 domain 输出断言。 |

### T006-A2

| path | pattern_type | symbol / section | observed_convention | reuse_in_this_task | do_not_copy_boundary |
|---|---|---|---|---|---|
| `src/App.tsx` | accessible interaction baseline | buttons, form labels, `aria-label="刷新行情"` | 多数操作已有 button/form 元素，刷新按钮已有 aria-label，适合作为 Playwright locator 基础。 | E2E 优先使用角色、可访问名称和稳定 data-testid 的组合。 | 不写依赖 CSS 层级或图表内部 canvas DOM 的脆弱 locator。 |
| `src/App.tsx` | user-visible assertions | `.data-notice`, `.quote-line`, `.metric-strip`, `.triggered` | 关键状态已有用户可见文本/数值区域。 | E2E 断言用户可见结果，而不是只断言内部 state。 | 不用 mock 后的实现细节证明 AC；必须能被用户界面观察到。 |
| `package.json` | tooling gap | scripts | 当前无 test runner、Playwright 或 fixture 命令。 | 新增 Vitest/Playwright 时同步 scripts 和 lockfile，并保留 build。 | 不引入产品运行时 Agent 来补测试；新增依赖若超出白名单先停下走 Decision Gate。 |

---

## 全局风险与门禁摘要

| 风险 / Gate | 说明 | 本计划的缓解路径 |
|---|---|---|
| Provider Gate | provider-specific auth / quota / schema 渗透到领域对象或快照 | 通过 `MarketDataSource` 显式边界与 source health 传播隔离。 |
| Cache Gate | cache 被误当本地恢复存储，或 stale 语义无法解释 | 只允许 server-side 60 秒 TTL 内存 cache，不写 `localStorage`。 |
| Storage Gate | `WorkspaceSnapshotV2` 迁移、大小、恢复失败 | 版本化快照 + default fallback + 大体量/损坏样本。 |
| Chart Gate | `lightweight-charts` 无法稳定承载主图/成交量/副图/locator | 若无法满足，先停下并发起图表库决策。 |
| Fixture-first 门禁 | live 数据不稳定导致验收不可复现 | 冻结样本 + replay + Playwright + smoke live only。 |

---

## Execution Units

### T001：多市场自选归一、列表摘要与归档暂停

```yaml
parent_task:
  id: "T001"
  title: "多市场自选归一、列表摘要与归档暂停"
  depends_on: []
  surfaces:
    - "SURF-WATCHLIST"
    - "SURF-RESTORE"
    - "SURF-ALERTS"
  authorized_paths:
    - "src/data/markets.ts"
    - "src/domain/market-normalization.ts"
    - "src/features/watchlist/**"
    - "src/lib/storage.ts"
    - "src/types.ts"
    - "tests/unit/watchlist/**"
    - "tests/e2e/watchlist/**"
    - "fixtures/watchlist/**"
  prohibited_paths:
    - "harness-runtime/harness/stages/**/contracts/**"
    - "harness-runtime/harness/stages/**/product/**"
    - "harness-runtime/harness/stages/**/solution.md"
    - "harness-runtime/harness/stages/**/tech-design.md"
    - "server/index.js"
    - "src/lib/signals.ts"
  required_evidence:
    - red_report
    - green_report
    - regression_report
    - screenshot_or_locator_evidence
    - mutation_or_fault_injection_report
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "T001-A1"
        execution_order: 1
        depends_on: []
        write_scope:
          - "src/domain/market-normalization.ts"
          - "src/data/markets.ts"
          - "src/features/watchlist/NormalizationPreview.tsx"
          - "src/types.ts"
          - "tests/unit/watchlist/normalization.spec.ts"
        read_scope:
          - "src/data/markets.ts"
          - "src/App.tsx"
          - "harness-runtime/harness/stages/20260522-stock-watch-system/interaction-spec/_shared/surface-registry.md"
        detail_ref: "T001-A1"
        reviewer_verdict: "pending"
      - id: "T001-A2"
        execution_order: 2
        depends_on:
          - "T001-A1"
        write_scope:
          - "src/features/watchlist/WatchlistPanel.tsx"
          - "src/features/watchlist/WatchlistRow.tsx"
          - "src/lib/storage.ts"
          - "src/types.ts"
          - "tests/unit/watchlist/archive.spec.ts"
          - "tests/e2e/watchlist/archive.spec.ts"
        read_scope:
          - "src/App.tsx"
          - "src/lib/storage.ts"
          - "src/features/watchlist/NormalizationPreview.tsx"
        detail_ref: "T001-A2"
        reviewer_verdict: "pending"
```

**目标：** 用户在添加四市场标的时，能先看到市场、原始代码、归一代码或歧义错误态；列表行能展示市场、归一代码、来源状态、最近价和涨跌摘要；归档动作不会删除标的，会把绑定提醒暂停并保留恢复语义。

**完成边界：** 完成后，watchlist 的 identity、row summary、archive / restore 语义与 localStorage 持久化一致；但不扩展到完整 alert 创建、MTS 计算、chart 渲染或布局恢复。

**surface：** `SURF-WATCHLIST` 为主，`SURF-RESTORE` 和 `SURF-ALERTS` 为联动面。

**dependencies：** 无上游任务；但实现必须先冻结 `MarketCode`、`SymbolCode`、`WatchSymbol` 与 `suspended_by_archive` 语义。

**authorized_paths：** `src/data/markets.ts`、`src/domain/market-normalization.ts`、`src/features/watchlist/**`、`src/lib/storage.ts`、`src/types.ts`、`tests/unit/watchlist/**`、`tests/e2e/watchlist/**`、`fixtures/watchlist/**`。

**prohibited_paths：** `server/index.js`、`src/lib/signals.ts`、`src/features/alerts/**` 的业务重写、以及任何契约/产品/方案文档。

**stop_if：**
- 代码归一必须靠“猜市场”才能通过。
- 归档开始删除标的而不是保留 archived 状态。
- 为了支持列表摘要而把行情 fallback 伪装成 formal。
- 需要新增市场或新的身份规则但未回流上游决策。

**required_evidence：**
- 单元测试的 Red / Green / Regression 报告。
- 至少一个针对歧义输入和归档暂停的失败注入或 mutation 证据。
- watchlist 列表和归一预览的截图或 locator 证据。

**test_obligation：**
```yaml
risk_level: high
surfaces:
  - SURF-WATCHLIST
  - SURF-RESTORE
  - SURF-ALERTS
required_capabilities:
  - unit
  - replay
  - screenshot_or_locator
  - mutation_or_fault_injection
evidence_required:
  - red_report
  - green_report
  - regression_report
  - mutation_report
accepted_alternatives:
  mutation_or_fault_injection:
    - targeted_fault_injection_report
```

**e2e_obligation：**
```yaml
risk_level: high
user_surfaces:
  - watchlist_add_flow
  - archive_restore_flow
required_capabilities:
  - browser_flow
  - user_visible_assertion
  - accessibility_smoke
  - local_persistence_replay
evidence_required:
  - e2e_run_report
  - screenshot_or_trace
  - assertion_summary
accepted_alternatives:
  browser_flow:
    - manual_acceptance_walkthrough_with_recorded_steps
```

**spec_refs：**
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#添加前预览归一结果`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#歧义输入不得静默写入`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#列表显示行情摘要`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#归档暂停提醒`
- `solution D-02`
- `INT-07`, `INT-08`, `DATA-05`, `DATA-06`, `SF-05`, `SF-06`

**traces_to：**
- AC: `AC-01`, `AC-05`
- FR: `FR-01`, `FR-02`, `FR-07`
- MOD: `MOD-01`, `MOD-06`
- INT: `INT-07`, `INT-08`
- DATA: `DATA-05`, `DATA-06`
- VS: `VS-05`, `VS-06`
- SF: `SF-05`, `SF-06`
- Gate: `Storage Gate`

**TASK node candidate：** `parent_task_id=T001`; `atomic_task_ids=[T001-A1, T001-A2]`; `dependencies=[]`; `authorized_paths=[src/data/markets.ts, src/domain/market-normalization.ts, src/features/watchlist/**, src/lib/storage.ts, src/types.ts, tests/unit/watchlist/**, tests/e2e/watchlist/**, fixtures/watchlist/**]`。

**Atomic Task details：**

#### T001-A1

**目标**：见本 Atomic Task 的 `single_action`。
**执行边界**：见本块的 `parent_task_coverage`、`stop conditions` 与 `migration / route boundaries`。
**文件行动**：以本 Parent 的 `atomic_task_queue.execution_units[]` 中 `write_scope` 为准。
**输入**：见 `explicit inputs / outputs` 的输入项。
**输出**：见 `explicit inputs / outputs` 的输出项。
**代码模式参考**：见下方 `code pattern references`。
**TDD 范围**：见测试样本、验证命令和证据要求。
**执行期验证命令**：见下方 `validation commands`。
**证据**：见下方 `evidence requirements`。
**停止条件**：见下方 `stop conditions`。

**single_action：** 把多市场代码归一与添加前预览切成显式 domain contract 和 UI preview，任何歧义都停在确认态，不得静默写入 active。

**explicit inputs / outputs：**
- 输入：`rawSymbol`、`market candidate`、`supported market set`、默认 watchlist 种子。
- 输出：归一预览对象、`normalizedSymbol`、歧义/错误态、加入按钮可用性。

**parent_task_coverage：** 只覆盖 `T001` 的 identity / preview 子边界，不触碰 chart、MTS 或 alert 业务。

**ac_scenario_coverage：** `AC-01`；Scenario：添加前预览归一结果、歧义输入不得静默写入。

**code pattern references：**
- `src/data/markets.ts::normalizeTicker`
- `src/data/markets.ts::marketLabels`、`marketHints`
- `src/App.tsx::addSymbol`
- `interaction-spec/_shared/domain-ui-mapping.md` 中 `NormalizationPreview`

**interface / data / state contracts：**
- `MarketCode`、`SymbolCode`、`WatchSymbol`
- `NormalizationPreviewView`
- 状态：`preview` / `confirmed` / `rejected` / `ambiguous`

**test fixtures / seed data：**
- US：`AAPL`
- HK：`700`、`0700.HK`
- CN：`600519`、`000001`
- KR：`005930`
- 歧义样本：可能跨市场的纯数字代码
- 空输入、重复输入、同 identity 重复添加

**validation commands：**
- `npx vitest run tests/unit/watchlist/normalization.spec.ts`
- `npm run build`

**evidence requirements：**
- Red 测试能抓到“歧义输入被静默写入”的错误。
- Green 只实现预览与确认，不扩展到其它业务。
- Regression 证明四市场样本重复执行结果一致。
- 至少一个针对“删掉歧义门禁”或“删掉市场确认”的故障注入证据。

**stop conditions：**
- 任何“自动猜市场”式实现。
- 需要新增市场或新增不在 mission 内的识别规则。
- 预览态开始承担行情请求或缓存职责。

**migration / route boundaries：**
- 仅允许改动 watchlist identity 相关文件。
- 不允许引入新 API 路由。
- 不允许把归一逻辑写进 MTS、提醒或恢复模块。

#### T001-A2

**目标**：见本 Atomic Task 的 `single_action`。
**执行边界**：见本块的 `parent_task_coverage`、`stop conditions` 与 `migration / route boundaries`。
**文件行动**：以本 Parent 的 `atomic_task_queue.execution_units[]` 中 `write_scope` 为准。
**输入**：见 `explicit inputs / outputs` 的输入项。
**输出**：见 `explicit inputs / outputs` 的输出项。
**代码模式参考**：见下方 `code pattern references`。
**TDD 范围**：见测试样本、验证命令和证据要求。
**执行期验证命令**：见下方 `validation commands`。
**证据**：见下方 `evidence requirements`。
**停止条件**：见下方 `stop conditions`。

**single_action：** 让 watchlist 行展示市场、归一代码、来源状态、最近价和涨跌摘要，并把 archive / restore 语义与 `suspended_by_archive` 链接起来。

**explicit inputs / outputs：**
- 输入：watchlist items、来源状态摘要、绑定提醒、归档/恢复指令。
- 输出：row summary view、archived count、restore summary、本地持久化状态。

**parent_task_coverage：** 只覆盖 `T001` 的列表摘要与归档联动，不扩展到完整 alert 创建流程。

**ac_scenario_coverage：** `AC-01`, `AC-05`；Scenario：列表显示行情摘要、归档暂停提醒。

**code pattern references：**
- `src/lib/storage.ts::readWatchlist/writeWatchlist`
- `src/lib/storage.ts::readAlerts/writeAlerts`
- `src/App.tsx` 中当前 watchlist 列表渲染与 `removeSymbol`
- `src/data/markets.ts::defaultWatchlist`

**interface / data / state contracts：**
- `WatchSymbol` 的 `active / archived` 状态
- `SourceHealth` 摘要
- `AlertRule.activationState = suspended_by_archive`
- `restoreIntent` 需要保留，不可在归档时丢失

**test fixtures / seed data：**
- active watchlist + 一个 archived symbol
- 绑定提醒处于 enabled 状态的标的
- 来源状态：formal / demo_fallback / stale / unavailable
- 重复添加同一 identity 的样本

**validation commands：**
- `npx vitest run tests/unit/watchlist/archive.spec.ts`
- `npx playwright test tests/e2e/watchlist/archive.spec.ts`
- `npm run build`

**evidence requirements：**
- Row summary 截图或 locator 证据。
- `suspended_by_archive` 的状态断言。
- 归档后提醒不触发、恢复后按原意图恢复的回放证据。
- Mutation 证据：删掉 `suspended_by_archive` 更新后测试应失败。

**stop conditions：**
- 归档实现成物理删除或重建。
- 为了列表摘要而把行情 fallback 当成正式实时数据。
- 跨到完整提醒规则编辑或 MTS 解释。

**migration / route boundaries：**
- 仅允许改 watchlist / storage / shared types。
- 不新增任何后端 route。
- 不把 alert 评估逻辑写入本任务。

---

### T002：默认工作台、来源健康、指标切换与可见降级

```yaml
parent_task:
  id: "T002"
  title: "默认工作台、来源健康、指标切换与可见降级"
  depends_on:
    - "T001"
  surfaces:
    - "SURF-WORKBENCH"
    - "SURF-SOURCE"
    - "SURF-LAYOUT"
  authorized_paths:
    - "server/index.js"
    - "src/domain/market-data-source.ts"
    - "src/domain/observation.ts"
    - "src/features/source/**"
    - "src/features/chart/**"
    - "src/features/workbench/**"
    - "src/lib/indicators.ts"
    - "src/App.tsx"
    - "src/types.ts"
    - "tests/unit/source/**"
    - "tests/e2e/workbench/**"
    - "fixtures/source/**"
  prohibited_paths:
    - "harness-runtime/harness/stages/**/contracts/**"
    - "harness-runtime/harness/stages/**/product/**"
    - "harness-runtime/harness/stages/**/solution.md"
    - "harness-runtime/harness/stages/**/tech-design.md"
    - "src/lib/signals.ts"
    - "src/lib/storage.ts"
  required_evidence:
    - red_report
    - green_report
    - regression_report
    - screenshot_or_trace
    - cache_or_fault_injection_report
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "T002-A1"
        execution_order: 1
        depends_on:
          - "T001-A1"
        write_scope:
          - "server/index.js"
          - "src/domain/market-data-source.ts"
          - "src/types.ts"
          - "tests/unit/source/market-data-source.spec.ts"
        read_scope:
          - "server/index.js"
          - "harness-runtime/harness/stages/20260522-stock-watch-system/tech-design.md"
        detail_ref: "T002-A1"
        reviewer_verdict: "pending"
      - id: "T002-A2"
        execution_order: 2
        depends_on:
          - "T002-A1"
        write_scope:
          - "src/features/chart/ChartSurface.tsx"
          - "src/features/source/SourceHealthPanel.tsx"
          - "src/features/workbench/WorkbenchShell.tsx"
          - "src/App.tsx"
          - "tests/e2e/workbench/default.spec.ts"
        read_scope:
          - "src/lib/indicators.ts"
          - "src/styles.css"
          - "interaction-spec/_shared/surface-registry.md"
        detail_ref: "T002-A2"
        reviewer_verdict: "pending"
```

**目标：** 用户选中 active 标的后，默认工作台直接可用，主图 / 成交量 / 副图 / OHLC / 来源健康同时可见；`formal / demo_fallback / stale / unavailable` 都要显式穿透到图表与说明区，且副图切换与布局切换不会丢标的上下文。

**完成边界：** 完成后，workbench 具备可见 source health、可切换 secondary indicator、可读 OHLC、可解释降级；但不负责 alert 触发、workspace 持久化或 MTS 解释文案。

**surface：** `SURF-WORKBENCH`、`SURF-SOURCE`、`SURF-LAYOUT`。

**dependencies：** 依赖 T001 的 normalized identity 和 symbol selection；实现中要先冻结 `MarketDataEnvelope`、`SourceHealth`、`PriceSeries`、`IndicatorState`。

**authorized_paths：** `server/index.js`、`src/domain/market-data-source.ts`、`src/domain/observation.ts`、`src/features/source/**`、`src/features/chart/**`、`src/features/workbench/**`、`src/lib/indicators.ts`、`src/App.tsx`、`src/types.ts`、`tests/unit/source/**`、`tests/e2e/workbench/**`、`fixtures/source/**`。

**prohibited_paths：** `src/lib/signals.ts`、`src/lib/storage.ts`、`src/features/alerts/**` 的业务扩写，以及任何 contract / solution / product 文档。

**stop_if：**
- provider-specific 字段必须进入领域对象或快照。
- cache 需要跨重启、跨进程或写入 `localStorage` 才能工作。
- 图表库无法稳定满足主图 / 成交量 / 副图 / locator contract。
- 降级状态开始只显示顶部 notice，不再穿透到图表与说明区。

**required_evidence：**
- provider success / failure / fallback / stale 的回放证据。
- cache hit / bypass / stale 语义的断言证据。
- 默认工作台与指标切换的截图或 Playwright trace。
- Mutation / fault injection 证据：移除 source banner 或去掉 `stale` 分支时测试失败。

**test_obligation：**
```yaml
risk_level: high
surfaces:
  - SURF-WORKBENCH
  - SURF-SOURCE
  - SURF-LAYOUT
required_capabilities:
  - unit
  - replay
  - browser_flow
  - user_visible_assertion
  - cache_semantics
evidence_required:
  - red_report
  - green_report
  - regression_report
  - cache_trace
accepted_alternatives:
  browser_flow:
    - component_integration_with_real_api_contract
```

**e2e_obligation：**
```yaml
risk_level: high
user_surfaces:
  - workbench_default_open
  - indicator_switch
  - source_degradation
required_capabilities:
  - browser_flow
  - user_visible_assertion
  - realtime_or_refresh
  - accessibility_smoke
evidence_required:
  - e2e_run_report
  - trace_or_video
  - screenshot_on_failure
  - assertion_summary
accepted_alternatives:
  browser_flow:
    - manual_acceptance_walkthrough_with_recorded_steps
```

**spec_refs：**
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#打开默认工作台`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#切换副图指标`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#数据不足时指标局部降级`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#demo fallback 可见`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#stale 不伪装实时成功`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#重试失败不导致页面不可用`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#桌面 dense 与 focus 切换`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#移动端 tab 工作台`
- `solution D-01`, `solution D-03`, `solution D-04`

**traces_to：**
- AC: `AC-02`, `AC-03`, `AC-04`
- FR: `FR-03`, `FR-06`, `FR-08`
- MOD: `MOD-02`, `MOD-03`, `MOD-07`
- INT: `INT-01`, `INT-02`, `INT-03`, `INT-04`
- DATA: `DATA-01`, `DATA-02`
- VS: `VS-01`, `VS-02`, `VS-08`
- SF: `SF-01`, `SF-02`
- Gate: `Provider Gate`, `Cache Gate`, `Chart Gate`

**TASK node candidate：** `parent_task_id=T002`; `atomic_task_ids=[T002-A1, T002-A2]`; `dependencies=[T001]`; `authorized_paths=[server/index.js, src/domain/market-data-source.ts, src/domain/observation.ts, src/features/source/**, src/features/chart/**, src/features/workbench/**, src/lib/indicators.ts, src/App.tsx, src/types.ts, tests/unit/source/**, tests/e2e/workbench/**, fixtures/source/**]`。

#### T002-A1

**目标**：见本 Atomic Task 的 `single_action`。
**执行边界**：见本块的 `parent_task_coverage`、`stop conditions` 与 `migration / route boundaries`。
**文件行动**：以本 Parent 的 `atomic_task_queue.execution_units[]` 中 `write_scope` 为准。
**输入**：见 `explicit inputs / outputs` 的输入项。
**输出**：见 `explicit inputs / outputs` 的输出项。
**代码模式参考**：见下方 `code pattern references`。
**TDD 范围**：见测试样本、验证命令和证据要求。
**执行期验证命令**：见下方 `validation commands`。
**证据**：见下方 `evidence requirements`。
**停止条件**：见下方 `stop conditions`。

**single_action：** 把 `server/index.js` 的行情代理提升为显式 `MarketDataSource` 边界，输出 `MarketDataEnvelope`、`SourceHealth`、`cacheState` 与 `retryState`，并把 TTL / bypass / stale 语义固定下来。

**explicit inputs / outputs：**
- 输入：`symbol`、`range`、`forceRefresh`、provider 名称、上游响应或失败。
- 输出：`MarketDataEnvelope`（含 `priceSeries`、`sourceHealth`、`meta`、`servedAt`、`cacheState`、`degradationReason`、`lastRefreshedAt`、`retryState`）。

**parent_task_coverage：** 只覆盖 `T002` 的来源与数据 envelope 子边界，不触碰 MTS、提醒或本地快照。

**ac_scenario_coverage：** `AC-02`, `AC-03`, `AC-04`；Scenario：demo fallback 可见、stale 不伪装实时成功、重试失败不导致页面不可用。

**code pattern references：**
- `server/index.js::fallbackPayload`
- `server/index.js::compactBars`
- `server/index.js::yahooIntervalByRange`
- `src/types.ts::ChartPayload`
- `harness-runtime/harness/stages/20260522-stock-watch-system/tech-design.md::INT-01/02/03`

**interface / data / state contracts：**
- `MarketDataEnvelope`
- `SourceHealth = formal | demo_fallback | stale | unavailable`
- `cacheState = miss | hit | bypass | stale_fallback | disabled`
- `SourceHealth` 传播到 `PriceSeries`、`IndicatorSet`、`MtsSignal`、`AlertRule`

**test fixtures / seed data：**
- Yahoo success payload
- parse failure payload
- upstream 500 / non-JSON payload
- cache hit within 60 秒 TTL
- `forceRefresh` bypass
- range / provider change
- 上游失败后可回退的 `stale` 样本

**validation commands：**
- `npx vitest run tests/unit/source/market-data-source.spec.ts`
- `npm run build`

**evidence requirements：**
- Red 测试能抓到“没有显式 source health”或“cache 误穿透”的问题。
- Green 只把 envelope 做到位，不扩展别的业务。
- Regression 证明 cache / stale / bypass / retry 规则在重复执行下稳定。
- 要有至少一次故障注入或 mutation，验证删掉 `stale` / `bypass` 分支会失败。

**stop conditions：**
- provider-specific auth / quota / schema 字段想进入领域对象或快照。
- cache 需要跨重启或写入 `localStorage` 才能工作。
- 需要新增 public route 或改变 `/api/chart/:symbol` 的基本路由边界。

**migration / route boundaries：**
- 只允许保留并强化 `/api/chart/:symbol` 这个 route；不新增公开 API 面。
- 不允许把 provider 字段写入 `WatchSymbol`、`PriceSeries`、`AlertRule` 或 `WorkspaceSnapshot`。

#### T002-A2

**目标**：见本 Atomic Task 的 `single_action`。
**执行边界**：见本块的 `parent_task_coverage`、`stop conditions` 与 `migration / route boundaries`。
**文件行动**：以本 Parent 的 `atomic_task_queue.execution_units[]` 中 `write_scope` 为准。
**输入**：见 `explicit inputs / outputs` 的输入项。
**输出**：见 `explicit inputs / outputs` 的输出项。
**代码模式参考**：见下方 `code pattern references`。
**TDD 范围**：见测试样本、验证命令和证据要求。
**执行期验证命令**：见下方 `validation commands`。
**证据**：见下方 `evidence requirements`。
**停止条件**：见下方 `stop conditions`。

**single_action：** 把默认工作台、来源健康面板和图表 shell 组合成一个可扫描的 runtime surface，包含主图、成交量、可切换副图、OHLC、指标读数和降级说明。

**explicit inputs / outputs：**
- 输入：`selected WatchSymbol`、`PriceSeries`、`IndicatorSet` 状态、`SourceHealth`、布局模式。
- 输出：`WorkbenchShell` / `ChartSurface` / `SourceHealthPanel` 的可见状态、`indicatorStatusNote`、图表 locator、截图可断言的 DOM。

**parent_task_coverage：** 只覆盖 `T002` 的 workbench / source / layout runtime 子边界，不触碰 alert 触发或 workspace snapshot。

**ac_scenario_coverage：** `AC-02`, `AC-03`, `AC-04`；Scenario：打开默认工作台、切换副图指标、指标局部降级、demo fallback 可见、stale 不伪装实时成功、重试失败不导致页面不可用、dense/focus 切换、mobile_tab 工作台。

**code pattern references：**
- `src/App.tsx::ChartPanel`
- `src/App.tsx::indicatorSnapshot`
- `src/lib/indicators.ts`
- `src/styles.css` 的三栏 grid / panel style
- `interaction-spec/_shared/surface-registry.md`

**interface / data / state contracts：**
- `ChartSurfaceView`
- `SourceHealthView`
- `IndicatorState = ready | partial | unavailable`
- 视图态只表达 `dense / focus / mobile_tab`，不把布局当持久化对象

**test fixtures / seed data：**
- ready / partial / unavailable 指标样本
- formal / demo_fallback / stale / unavailable 来源样本
- 选中 `symbol-row-aapl` 的默认工作台样本
- indicator tab 切换样本

**validation commands：**
- `npx playwright test tests/e2e/workbench/default.spec.ts`
- `npm run build`

**evidence requirements：**
- 默认工作台和降级工作台的截图证据。
- 副图切换后主图上下文仍然相同的断言。
- Mutation 证据：删掉 source banner 或 secondary panel 后 E2E 失败。

**stop conditions：**
- chart library 不能稳定承载主图 / 成交量 / 副图 / locator contract。
- 降级文案只显示在顶部，不再穿透到图表说明与 MTS/提醒入口。
- 需要把布局恢复能力混进本任务的持久化逻辑。

**migration / route boundaries：**
- 只改 workbench / source surface 的组合层，不改本地快照 schema。
- 不新增后端 route。
- 不把 alert 状态或 MTS 解释塞进本任务。

---

### T003：MTS 解释卡、ReasonRegistry 与非投资建议边界

```yaml
parent_task:
  id: "T003"
  title: "MTS 解释卡、ReasonRegistry 与非投资建议边界"
  depends_on:
    - "T002"
  surfaces:
    - "SURF-MTS"
    - "SURF-WORKBENCH"
  authorized_paths:
    - "src/domain/mts.ts"
    - "src/domain/mts-registry.ts"
    - "src/lib/signals.ts"
    - "src/features/mts/**"
    - "src/App.tsx"
    - "src/types.ts"
    - "tests/unit/mts/**"
    - "tests/replay/mts/**"
    - "fixtures/mts/**"
  prohibited_paths:
    - "harness-runtime/harness/stages/**/contracts/**"
    - "harness-runtime/harness/stages/**/product/**"
    - "harness-runtime/harness/stages/**/solution.md"
    - "harness-runtime/harness/stages/**/tech-design.md"
    - "server/index.js"
    - "src/lib/storage.ts"
  required_evidence:
    - red_report
    - green_report
    - regression_report
    - mutation_or_registry_report
    - screenshot_or_copy_review
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "T003-A1"
        execution_order: 1
        depends_on:
          - "T002-A1"
        write_scope:
          - "src/domain/mts-registry.ts"
          - "src/domain/mts.ts"
          - "src/lib/signals.ts"
          - "src/types.ts"
          - "tests/unit/mts/registry.spec.ts"
        read_scope:
          - "src/lib/signals.ts"
          - "harness-runtime/harness/stages/20260522-stock-watch-system/tech-design.md"
        detail_ref: "T003-A1"
        reviewer_verdict: "pending"
      - id: "T003-A2"
        execution_order: 2
        depends_on:
          - "T003-A1"
        write_scope:
          - "src/features/mts/MtsSignalCard.tsx"
          - "src/App.tsx"
          - "tests/e2e/mts/card.spec.ts"
        read_scope:
          - "src/lib/signals.ts"
          - "interaction-spec/_shared/domain-ui-mapping.md"
          - "interaction-spec/_shared/view-models.ts"
        detail_ref: "T003-A2"
        reviewer_verdict: "pending"
```

**目标：** 把旧四因子共振指标替换为结构化、可回放、可解释的 MTS 卡；用户能看到趋势状态、分数带、信号类型、提醒等级、原因和失效条件，但不会看到收益承诺、胜率或确定性买卖建议。

**完成边界：** 完成后，MTS 解释是一个独立、可审计的领域对象；但不负责 alert 触发、source adapter、storage 或 layout。

**surface：** `SURF-MTS` 为主，`SURF-WORKBENCH` 为承载容器。

**dependencies：** 依赖 T002 的 `PriceSeries`、`IndicatorSet` 和 `SourceHealth` 输入。

**authorized_paths：** `src/domain/mts.ts`、`src/domain/mts-registry.ts`、`src/lib/signals.ts`、`src/features/mts/**`、`src/App.tsx`、`src/types.ts`、`tests/unit/mts/**`、`tests/replay/mts/**`、`fixtures/mts/**`。

**prohibited_paths：** `server/index.js`、`src/lib/storage.ts`、`src/features/alerts/**` 的业务逻辑、以及任何将 MTS 改写成建议/交易语义的文档或代码。

**stop_if：**
- `reasonCodes` / `invalidators` 变成自由文本。
- MTS 文案开始出现“强买/强卖/收益概率/胜率”语义。
- 数据不足时还在输出有效信号。
- registry 不能保持 additive / deprecated-only 演进。

**required_evidence：**
- MTS registry 回放测试。
- 解释卡截图或 copy review。
- Mutation / registry evidence：删掉某个 registry entry 或未知码未降级时测试必须失败。

**test_obligation：**
```yaml
risk_level: high
surfaces:
  - SURF-MTS
  - SURF-WORKBENCH
required_capabilities:
  - unit
  - replay
  - mutation_or_registry_validation
  - screenshot_or_copy_review
evidence_required:
  - red_report
  - green_report
  - regression_report
  - registry_report
accepted_alternatives:
  mutation_or_registry_validation:
    - targeted_fault_injection_report
```

**e2e_obligation：**
```yaml
risk_level: medium
user_surfaces:
  - mts_card_reading
  - source_degraded_mts
required_capabilities:
  - browser_flow
  - user_visible_assertion
  - accessibility_smoke
evidence_required:
  - e2e_run_report
  - screenshot_or_trace
  - assertion_summary
accepted_alternatives:
  browser_flow:
    - manual_acceptance_walkthrough_with_recorded_steps
```

**spec_refs：**
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#输出完整 MTS 卡`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#MTS 不表达投资建议`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#数据不足时不输出伪 MTS`
- `solution D-04`, `solution D-05`
- `INT-05`, `DATA-03`, `VS-03`, `SF-03`

**traces_to：**
- AC: `AC-03`, `AC-04`
- FR: `FR-04`
- MOD: `MOD-04`
- INT: `INT-05`
- DATA: `DATA-03`
- VS: `VS-03`
- SF: `SF-03`
- Gate: `Provider Gate`

**TASK node candidate：** `parent_task_id=T003`; `atomic_task_ids=[T003-A1, T003-A2]`; `dependencies=[T002]`; `authorized_paths=[src/domain/mts.ts, src/domain/mts-registry.ts, src/lib/signals.ts, src/features/mts/**, src/App.tsx, src/types.ts, tests/unit/mts/**, tests/replay/mts/**, fixtures/mts/**]`。

#### T003-A1

**目标**：见本 Atomic Task 的 `single_action`。
**执行边界**：见本块的 `parent_task_coverage`、`stop conditions` 与 `migration / route boundaries`。
**文件行动**：以本 Parent 的 `atomic_task_queue.execution_units[]` 中 `write_scope` 为准。
**输入**：见 `explicit inputs / outputs` 的输入项。
**输出**：见 `explicit inputs / outputs` 的输出项。
**代码模式参考**：见下方 `code pattern references`。
**TDD 范围**：见测试样本、验证命令和证据要求。
**执行期验证命令**：见下方 `validation commands`。
**证据**：见下方 `evidence requirements`。
**停止条件**：见下方 `stop conditions`。

**single_action：** 建立 `MtsReasonRegistry` 和 `MtsExplanation` 的结构化域合同，把自由文本原因迁移成稳定 code，并保证未知码只能降级为 `UNKNOWN_CODE`。

**explicit inputs / outputs：**
- 输入：`PriceSeries`、`IndicatorSet`、`SourceHealth`、registry entry 集合。
- 输出：`MtsExplanation`（`trendState`、`scoreBand`、`signalType`、`alertLevel`、`reasonCodes`、`invalidators`、`interpretability`、`registryVersion`）。

**parent_task_coverage：** 只覆盖 `T003` 的解释数据模型子边界，不触碰提醒状态机或 workspace restore。

**ac_scenario_coverage：** `AC-03`, `AC-04`；Scenario：输出完整 MTS 卡、MTS 不表达投资建议、数据不足时不输出伪 MTS。

**code pattern references：**
- `src/lib/signals.ts::buildSignal`
- 旧 `CompositeSignal` 输出结构
- 当前 `reasons` / `warnings` 数组模式
- `harness-runtime/harness/stages/20260522-stock-watch-system/tech-design.md::INT-05`、`DATA-03`

**interface / data / state contracts：**
- `MtsReasonRegistry`：`id`、`kind`、`category`、`severityHint`、`displayKey`、`introducedIn`、`deprecated`
- `MtsExplanation`：所有有效 MTS 必须含 `reasonCodes` 与 `invalidators`
- `alertLevel` 只能落在观察、确认、强信号、风控

**test fixtures / seed data：**
- 趋势向上、趋势确认、风险破坏、动量背离样本
- bars 不足 / source degraded 样本
- unknown registry code 样本

**validation commands：**
- `npx vitest run tests/unit/mts/registry.spec.ts`
- `npx vitest run tests/replay/mts/replay.spec.ts`
- `npm run build`

**evidence requirements：**
- Red 能抓到“原因码自由文本化”或“未知码未降级”的问题。
- Green 只完成解释合同，不扩张到 alert 触发。
- Regression 证明 registry add / deprecate 规则稳定。
- 至少一个 mutation 或 targeted fault injection 证据。

**stop conditions：**
- 解释对象开始承载收益概率或交易建议。
- registry 无法保持 additive 演进。
- 需要把 source provider 细节写进 MTS 合同。

**migration / route boundaries：**
- 只改 domain / signal 相关文件。
- 不新增 API route。
- 不把 alert 触发逻辑混入这个任务。

#### T003-A2

**目标**：见本 Atomic Task 的 `single_action`。
**执行边界**：见本块的 `parent_task_coverage`、`stop conditions` 与 `migration / route boundaries`。
**文件行动**：以本 Parent 的 `atomic_task_queue.execution_units[]` 中 `write_scope` 为准。
**输入**：见 `explicit inputs / outputs` 的输入项。
**输出**：见 `explicit inputs / outputs` 的输出项。
**代码模式参考**：见下方 `code pattern references`。
**TDD 范围**：见测试样本、验证命令和证据要求。
**执行期验证命令**：见下方 `validation commands`。
**证据**：见下方 `evidence requirements`。
**停止条件**：见下方 `stop conditions`。

**single_action：** 把 MTS 解释卡渲染成用户可见 surface，并移除旧四因子 / 强买强卖式文案，让 data_insufficient 成为明确可见的降级结果。

**explicit inputs / outputs：**
- 输入：`MtsExplanation`、`SourceHealth`、`IndicatorState`。
- 输出：`MtsSignalCard` 的 DOM、copy、data-testid、不可解释状态文案。

**parent_task_coverage：** 只覆盖 `T003` 的展示边界，不负责提醒规则生成。

**ac_scenario_coverage：** `AC-03`, `AC-04`；Scenario：完整 MTS 卡、MTS 不表达投资建议、数据不足不输出伪 MTS。

**code pattern references：**
- `src/App.tsx` 中当前 `buildSignal(bars)` 调用和 signal 渲染
- `interaction-spec/_shared/view-models.ts::MtsSignalCardView`
- `interaction-spec/_shared/domain-ui-mapping.md` 中 `mts-signal-card`

**interface / data / state contracts：**
- `MtsSignalCardView`
- `interpretability = interpretable | data_insufficient`
- `sourceHealth != formal` 时必须同步暴露降级

**test fixtures / seed data：**
- 完整 MTS 卡样本
- 风控优先样本
- data_insufficient 样本

**validation commands：**
- `npx playwright test tests/e2e/mts/card.spec.ts`
- `npm run build`

**evidence requirements：**
- 截图或 trace 显示六要素完整可见。
- 文案审查证明没有胜率/收益承诺/确定性买卖建议。
- Regression 证明 data_insufficient 时不再展示有效信号。

**stop conditions：**
- 文案开始出现投资建议语义。
- 数据不足时仍输出假信号。
- 需要把 alert 编排逻辑塞进 MTS 组件。

**migration / route boundaries：**
- 只改 MTS card 和承载它的 workbench 片段。
- 不改 alert state machine。
- 不改 storage 或 source adapter。

---

### T004：分类提醒、触发/确认、scheduled 与归档暂停

```yaml
parent_task:
  id: "T004"
  title: "分类提醒、触发/确认、scheduled 与归档暂停"
  depends_on:
    - "T003"
  surfaces:
    - "SURF-ALERTS"
    - "SURF-MTS"
  authorized_paths:
    - "src/domain/alert.ts"
    - "src/lib/alerts.ts"
    - "src/features/alerts/**"
    - "src/App.tsx"
    - "src/types.ts"
    - "tests/unit/alerts/**"
    - "tests/replay/alerts/**"
    - "fixtures/alerts/**"
  prohibited_paths:
    - "harness-runtime/harness/stages/**/contracts/**"
    - "harness-runtime/harness/stages/**/product/**"
    - "harness-runtime/harness/stages/**/solution.md"
    - "harness-runtime/harness/stages/**/tech-design.md"
    - "server/index.js"
    - "src/lib/signals.ts"
  required_evidence:
    - red_report
    - green_report
    - regression_report
    - state_transition_report
    - screenshot_or_history_trace
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "T004-A1"
        execution_order: 1
        depends_on:
          - "T003-A1"
        write_scope:
          - "src/domain/alert.ts"
          - "src/lib/alerts.ts"
          - "src/types.ts"
          - "tests/unit/alerts/rule-model.spec.ts"
        read_scope:
          - "src/App.tsx"
          - "harness-runtime/harness/stages/20260522-stock-watch-system/tech-design.md"
        detail_ref: "T004-A1"
        reviewer_verdict: "pending"
      - id: "T004-A2"
        execution_order: 2
        depends_on:
          - "T004-A1"
        write_scope:
          - "src/features/alerts/AlertRulePanel.tsx"
          - "src/App.tsx"
          - "tests/replay/alerts/trigger-flow.spec.ts"
          - "tests/e2e/alerts/panel.spec.ts"
        read_scope:
          - "interaction-spec/_shared/view-models.ts"
          - "interaction-spec/_shared/domain-ui-mapping.md"
        detail_ref: "T004-A2"
        reviewer_verdict: "pending"
```

**目标：** 提醒从简单到价提醒扩成本地分类规则系统，覆盖价格型、变化型、技术指标型、MTS 型、定时提醒；能记录启停、触发、确认、历史、归档暂停和 scheduled miss，不外发通知、不自动交易。

**完成边界：** 完成后，提醒规则具备可见 taxonomy、状态机、触发历史和恢复意图；但不做外部推送，也不承担 workspace restore。

**surface：** `SURF-ALERTS` 为主，`SURF-MTS` 为触发来源面。

**dependencies：** 依赖 T003 的 `MtsExplanation` 和 `alertLevel` 语义。

**authorized_paths：** `src/domain/alert.ts`、`src/lib/alerts.ts`、`src/features/alerts/**`、`src/App.tsx`、`src/types.ts`、`tests/unit/alerts/**`、`tests/replay/alerts/**`、`fixtures/alerts/**`。

**prohibited_paths：** `server/index.js`、`src/lib/signals.ts` 的业务扩写、外部通知/自动交易相关代码、以及任何契约/产品/方案文档。

**stop_if：**
- 要把提醒发到外部通知服务、系统通知或后台 worker。
- 触发与启停开始混成一个状态。
- archive 变成删除而不是 `suspended_by_archive`。
- scheduled 需要浏览器关闭期间补发。

**required_evidence：**
- 状态机的 Red / Green / Regression 报告。
- `triggered` / `acknowledged` / `suspended_by_archive` / `missed_while_closed` 的历史证据。
- 触发后可确认、归档后暂停的截图或历史 trace。

**test_obligation：**
```yaml
risk_level: high
surfaces:
  - SURF-ALERTS
  - SURF-MTS
required_capabilities:
  - unit
  - replay
  - state_transition_assertion
  - screenshot_or_history_trace
evidence_required:
  - red_report
  - green_report
  - regression_report
  - state_transition_report
accepted_alternatives:
  state_transition_assertion:
    - targeted_fault_injection_report
```

**e2e_obligation：**
```yaml
risk_level: medium
user_surfaces:
  - alert_create_flow
  - alert_ack_flow
  - archive_suspend_flow
required_capabilities:
  - browser_flow
  - user_visible_assertion
  - local_history_replay
evidence_required:
  - e2e_run_report
  - screenshot_or_trace
  - assertion_summary
accepted_alternatives:
  browser_flow:
    - manual_acceptance_walkthrough_with_recorded_steps
```

**spec_refs：**
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#创建分类提醒`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#提醒触发后可确认`
- `solution D-05`
- `INT-06`, `DATA-06`, `VS-04`, `SF-04`, `SF-05`

**traces_to：**
- AC: `AC-04`, `AC-05`
- FR: `FR-05`
- MOD: `MOD-05`
- INT: `INT-06`
- DATA: `DATA-06`
- VS: `VS-04`
- SF: `SF-04`, `SF-05`
- Gate: `Storage Gate`

**TASK node candidate：** `parent_task_id=T004`; `atomic_task_ids=[T004-A1, T004-A2]`; `dependencies=[T003]`; `authorized_paths=[src/domain/alert.ts, src/lib/alerts.ts, src/features/alerts/**, src/App.tsx, src/types.ts, tests/unit/alerts/**, tests/replay/alerts/**, fixtures/alerts/**]`。

#### T004-A1

**目标**：见本 Atomic Task 的 `single_action`。
**执行边界**：见本块的 `parent_task_coverage`、`stop conditions` 与 `migration / route boundaries`。
**文件行动**：以本 Parent 的 `atomic_task_queue.execution_units[]` 中 `write_scope` 为准。
**输入**：见 `explicit inputs / outputs` 的输入项。
**输出**：见 `explicit inputs / outputs` 的输出项。
**代码模式参考**：见下方 `code pattern references`。
**TDD 范围**：见测试样本、验证命令和证据要求。
**执行期验证命令**：见下方 `validation commands`。
**证据**：见下方 `evidence requirements`。
**停止条件**：见下方 `stop conditions`。

**single_action：** 建立提醒规则的 taxonomy、启停 / 触发双状态机、scheduled 条件语义和恢复意图字段。

**explicit inputs / outputs：**
- 输入：rule form 字段、目标 symbol、当前观察上下文、local clock 语义。
- 输出：合法的 `AlertRule` 域对象、校验错误、状态机转移结果。

**parent_task_coverage：** 只覆盖 `T004` 的 rule model 子边界，不做面板布局或 workspace 恢复。

**ac_scenario_coverage：** `AC-04`, `AC-05`；Scenario：创建分类提醒、提醒触发后可确认，并补齐 scheduled / archive 语义。

**code pattern references：**
- `src/types.ts::AlertRule`
- `src/App.tsx::addPriceAlert`
- `src/App.tsx::addSignalAlert`
- `src/App.tsx::triggeredAlerts`
- `harness-runtime/harness/stages/20260522-stock-watch-system/tech-design.md::INT-06`、`DATA-06`

**interface / data / state contracts：**
- `taxonomy = price | change | technical_indicator | mts | scheduled`
- `activationState = enabled | disabled | suspended_by_archive`
- `triggerState = idle | triggered | acknowledged`
- scheduled condition：`daily_time`、`localTime`、`timezone=local`、可选 `daysOfWeek`、`skipIfMarketClosed`

**test fixtures / seed data：**
- 价格提醒样本
- 变化提醒样本
- 技术指标提醒样本
- MTS 提醒样本
- scheduled 提醒样本
- invalid taxonomy 样本
- archived symbol 样本

**validation commands：**
- `npx vitest run tests/unit/alerts/rule-model.spec.ts`
- `npm run build`

**evidence requirements：**
- Red 能抓到 taxonomy 非法、状态混用或 scheduled 语义缺失。
- Green 只补齐规则模型，不扩展到 UI 交互。
- Regression 证明 archive / restore / ack / scheduled 规则不回退。
- 至少一次针对非法 taxonomy 或 state conflation 的 fault injection 证据。

**stop conditions：**
- 开始引入外部通知、系统通知或后台 worker。
- 提醒状态被 UI 临时 state 替代。
- 归档语义被实现成删除或重建。

**migration / route boundaries：**
- 只改 alert domain / shared types。
- 不新增后端 route。
- 不把 scheduled 语义做成后台推送。

#### T004-A2

**目标**：见本 Atomic Task 的 `single_action`。
**执行边界**：见本块的 `parent_task_coverage`、`stop conditions` 与 `migration / route boundaries`。
**文件行动**：以本 Parent 的 `atomic_task_queue.execution_units[]` 中 `write_scope` 为准。
**输入**：见 `explicit inputs / outputs` 的输入项。
**输出**：见 `explicit inputs / outputs` 的输出项。
**代码模式参考**：见下方 `code pattern references`。
**TDD 范围**：见测试样本、验证命令和证据要求。
**执行期验证命令**：见下方 `validation commands`。
**证据**：见下方 `evidence requirements`。
**停止条件**：见下方 `stop conditions`。

**single_action：** 把提醒触发、确认、归档暂停和 scheduled miss 编排成可回放的事件流，并在 UI 中暴露历史与确认动作。

**explicit inputs / outputs：**
- 输入：latest observation、`MtsExplanation`、clock tick、当前 alert set。
- 输出：`triggered` / `acknowledged` / `missed_while_closed` / `suspended_by_archive` 的历史记录与面板状态。

**parent_task_coverage：** 只覆盖 `T004` 的 orchestration 子边界，不改 source adapter、chart 或 layout。

**ac_scenario_coverage：** `AC-04`, `AC-05`；Scenario：提醒触发后可确认、归档暂停提醒，并补齐 scheduled 行为。

**code pattern references：**
- `src/App.tsx::triggeredAlerts`
- `src/App.tsx` 当前 alert list / builder 渲染
- `harness-runtime/harness/stages/20260522-stock-watch-system/tech-design.md::SF-04`, `SF-05`
- `interaction-spec/_shared/view-models.ts::AlertRuleCardView`

**interface / data / state contracts：**
- `AlertRuleCardView`
- `AlertPriorityPolicy`
- `AlertRule.history[]`
- `restoreIntent` 在归档后必须保留

**test fixtures / seed data：**
- enabled hit 样本
- acknowledged 样本
- archived symbol 样本
- scheduled due while app open 样本
- `missed_while_closed` 样本

**validation commands：**
- `npx vitest run tests/replay/alerts/trigger-flow.spec.ts`
- `npx playwright test tests/e2e/alerts/panel.spec.ts`
- `npm run build`

**evidence requirements：**
- 触发、确认、暂停、missed 的历史 trace。
- 面板截图证明确认动作可见。
- Regression 证明 app 关闭期间的 scheduled tick 不补发。

**stop conditions：**
- scheduled 需要后台常驻或外部通知。
- 归档后还能触发。
- UI 只显示结果不保留历史。

**migration / route boundaries：**
- 只改 alert 面板和其对应事件编排。
- 不把 workspace restore 逻辑混入 alert 任务。
- 不修改 server 路由。

---

### T005：`WorkspaceSnapshotV2`、per-symbol layout 与浏览器重开恢复

```yaml
parent_task:
  id: "T005"
  title: "WorkspaceSnapshotV2、per-symbol layout 与浏览器重开恢复"
  depends_on:
    - "T001"
    - "T002"
    - "T004"
  surfaces:
    - "SURF-RESTORE"
    - "SURF-LAYOUT"
    - "SURF-WATCHLIST"
  authorized_paths:
    - "src/domain/workspace.ts"
    - "src/lib/storage.ts"
    - "src/features/layout/**"
    - "src/features/restore/**"
    - "src/App.tsx"
    - "src/types.ts"
    - "tests/unit/workspace/**"
    - "tests/replay/workspace/**"
    - "tests/e2e/restore-layout/**"
    - "fixtures/workspace/**"
  prohibited_paths:
    - "harness-runtime/harness/stages/**/contracts/**"
    - "harness-runtime/harness/stages/**/product/**"
    - "harness-runtime/harness/stages/**/solution.md"
    - "harness-runtime/harness/stages/**/tech-design.md"
    - "server/index.js"
    - "src/lib/signals.ts"
  required_evidence:
    - red_report
    - green_report
    - regression_report
    - migration_report
    - screenshot_or_restore_trace
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "T005-A1"
        execution_order: 1
        depends_on:
          - "T001-A2"
          - "T004-A1"
        write_scope:
          - "src/domain/workspace.ts"
          - "src/lib/storage.ts"
          - "src/types.ts"
          - "tests/unit/workspace/snapshot-migration.spec.ts"
        read_scope:
          - "src/lib/storage.ts"
          - "harness-runtime/harness/stages/20260522-stock-watch-system/tech-design.md"
        detail_ref: "T005-A1"
        reviewer_verdict: "pending"
      - id: "T005-A2"
        execution_order: 2
        depends_on:
          - "T005-A1"
          - "T002-A2"
        write_scope:
          - "src/features/layout/LayoutController.tsx"
          - "src/features/restore/RestoreStatus.tsx"
          - "src/App.tsx"
          - "tests/e2e/restore-layout/resume.spec.ts"
        read_scope:
          - "interaction-spec/_shared/surface-registry.md"
          - "interaction-spec/_shared/view-models.ts"
        detail_ref: "T005-A2"
        reviewer_verdict: "pending"
```

**目标：** 用版本化 `WorkspaceSnapshotV2` 承载本地工作台恢复，保留 `watchlist`、`alerts`、`selectedSymbol`、`layoutBySymbol` 和 `globalLayoutFallback`；浏览器重开后恢复工作台，坏掉的布局只回退到默认 focus，不阻断看盘。

**完成边界：** 完成后，恢复功能能恢复 watchlist / alerts / 触发历史 / layout / 最近上下文；但不引入账号、云同步、跨设备同步或数据库。

**surface：** `SURF-RESTORE`、`SURF-LAYOUT`、`SURF-WATCHLIST`。

**dependencies：** 依赖 T001 的 watchlist identity、T002 的 layout runtime，以及 T004 的 alert history 结构。

**authorized_paths：** `src/domain/workspace.ts`、`src/lib/storage.ts`、`src/features/layout/**`、`src/features/restore/**`、`src/App.tsx`、`src/types.ts`、`tests/unit/workspace/**`、`tests/replay/workspace/**`、`tests/e2e/restore-layout/**`、`fixtures/workspace/**`。

**prohibited_paths：** `server/index.js`、`src/lib/signals.ts`、任何 cloud / account / sync / DB 代码、以及所有契约 / 产品 / 方案文档。

**stop_if：**
- 迁移超过 Storage Gate 阈值或会静默丢失 watchlist / alerts。
- layoutBySymbol 退化成全局单一偏好而不是按 symbol 记录。
- 恢复失败后页面无法回到默认 focus 工作台。
- 要靠 IndexedDB / 后端持久化才能通过。

**required_evidence：**
- 旧 key → V2 迁移证据。
- 损坏 snapshot / 大体量 snapshot 的恢复证据。
- per-symbol layout 独立恢复的截图或 trace。

**test_obligation：**
```yaml
risk_level: high
surfaces:
  - SURF-RESTORE
  - SURF-LAYOUT
  - SURF-WATCHLIST
required_capabilities:
  - unit
  - replay
  - browser_flow
  - screenshot_or_restore_trace
  - storage_migration_assertion
evidence_required:
  - red_report
  - green_report
  - regression_report
  - migration_report
accepted_alternatives:
  storage_migration_assertion:
    - targeted_fault_injection_report
```

**e2e_obligation：**
```yaml
risk_level: high
user_surfaces:
  - browser_reopen_restore
  - layout_switch
  - mobile_tab_restore
required_capabilities:
  - browser_flow
  - user_visible_assertion
  - local_persistence_replay
  - screenshot_or_trace
evidence_required:
  - e2e_run_report
  - screenshot_or_trace
  - assertion_summary
accepted_alternatives:
  browser_flow:
    - manual_acceptance_walkthrough_with_recorded_steps
```

**spec_refs：**
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#浏览器重开恢复工作台`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#布局恢复失败回退默认`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#桌面 dense 与 focus 切换`
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#移动端 tab 工作台`
- `solution D-06`, `solution D-07`
- `INT-07`, `INT-08`, `DATA-04`, `DATA-05`, `DATA-06`, `VS-05`, `VS-06`

**traces_to：**
- AC: `AC-05`
- FR: `FR-07`, `FR-08`
- MOD: `MOD-06`, `MOD-07`
- INT: `INT-07`, `INT-08`
- DATA: `DATA-04`, `DATA-05`, `DATA-06`
- VS: `VS-05`, `VS-06`
- SF: `SF-06`
- Gate: `Storage Gate`, `Chart Gate`

**TASK node candidate：** `parent_task_id=T005`; `atomic_task_ids=[T005-A1, T005-A2]`; `dependencies=[T001, T002, T004]`; `authorized_paths=[src/domain/workspace.ts, src/lib/storage.ts, src/features/layout/**, src/features/restore/**, src/App.tsx, src/types.ts, tests/unit/workspace/**, tests/replay/workspace/**, tests/e2e/restore-layout/**, fixtures/workspace/**]`。

#### T005-A1

**目标**：见本 Atomic Task 的 `single_action`。
**执行边界**：见本块的 `parent_task_coverage`、`stop conditions` 与 `migration / route boundaries`。
**文件行动**：以本 Parent 的 `atomic_task_queue.execution_units[]` 中 `write_scope` 为准。
**输入**：见 `explicit inputs / outputs` 的输入项。
**输出**：见 `explicit inputs / outputs` 的输出项。
**代码模式参考**：见下方 `code pattern references`。
**TDD 范围**：见测试样本、验证命令和证据要求。
**执行期验证命令**：见下方 `validation commands`。
**证据**：见下方 `evidence requirements`。
**停止条件**：见下方 `stop conditions`。

**single_action：** 把 localStorage 的双 key 读取迁移到版本化 `WorkspaceSnapshotV2`，并让迁移、回退、大小阈值和恢复结果都变成可断言合同。

**explicit inputs / outputs：**
- 输入：旧 watchlist / alerts key、corrupt snapshot、`selectedSymbol`、`layoutBySymbol`、`globalLayoutFallback`。
- 输出：迁移后的 `WorkspaceSnapshotV2`、`restoreMetadata`、读取/写入/迁移函数。

**parent_task_coverage：** 只覆盖 `T005` 的存储和迁移子边界，不碰 chart adapter 或 alert 触发逻辑。

**ac_scenario_coverage：** `AC-05`；Scenario：浏览器重开恢复工作台、布局恢复失败回退默认。

**code pattern references：**
- `src/lib/storage.ts::readWatchlist/writeWatchlist`
- `src/lib/storage.ts::readAlerts/writeAlerts`
- 当前 `window.localStorage` JSON parse / stringify 模式
- `src/App.tsx` 初始状态从 storage 读取的模式

**interface / data / state contracts：**
- `WorkspaceSnapshotV2`
- `layoutBySymbol[normalizedSymbol]`
- `globalLayoutFallback`
- `restoreStatus = restored | partial | default_fallback | failed`

**test fixtures / seed data：**
- legacy watchlist / alerts keys
- corrupt snapshot
- 500 symbols + 2000 alert history 的大体量样本
- 两个 symbol 各自不同布局的样本

**validation commands：**
- `npx vitest run tests/unit/workspace/snapshot-migration.spec.ts`
- `npm run build`

**evidence requirements：**
- Red 能抓到“旧 key 丢失”或“恢复失败不回退默认布局”的问题。
- Green 只补迁移器，不扩到 UI 大改。
- Regression 证明重复迁移是幂等的。
- 要有损坏 snapshot 或大体量样本的迁移证据。

**stop conditions：**
- 迁移超出 localStorage 阈值或需要 IndexedDB / backend 才能通过。
- 迁移会清空旧 key 或丢 alert history。
- `layout_scope=symbol` 的 key 不是 normalized symbol。

**migration / route boundaries：**
- 只允许 localStorage 读取 / 写入与迁移。
- 不新增后端 route。
- 不把 workspace snapshot 变成数据库模型。

#### T005-A2

**目标**：见本 Atomic Task 的 `single_action`。
**执行边界**：见本块的 `parent_task_coverage`、`stop conditions` 与 `migration / route boundaries`。
**文件行动**：以本 Parent 的 `atomic_task_queue.execution_units[]` 中 `write_scope` 为准。
**输入**：见 `explicit inputs / outputs` 的输入项。
**输出**：见 `explicit inputs / outputs` 的输出项。
**代码模式参考**：见下方 `code pattern references`。
**TDD 范围**：见测试样本、验证命令和证据要求。
**执行期验证命令**：见下方 `validation commands`。
**证据**：见下方 `evidence requirements`。
**停止条件**：见下方 `stop conditions`。

**single_action：** 把布局控制与恢复横幅接起来，让 dense / focus / mobile_tab、per-symbol 恢复和默认 focus fallback 都成为可见 UI 行为。

**explicit inputs / outputs：**
- 输入：snapshot 恢复结果、viewport mode、selected symbol、mobile tab。
- 输出：布局模式、活动 tab、恢复横幅、按 symbol 恢复后的界面状态。

**parent_task_coverage：** 只覆盖 `T005` 的 layout / restore 展示子边界，不负责 storage 迁移规则本身。

**ac_scenario_coverage：** `AC-05`；Scenario：布局恢复失败回退默认、桌面 dense 与 focus 切换、移动端 tab 工作台。

**code pattern references：**
- `src/styles.css` 的三栏 grid / responsive panel pattern
- `src/App.tsx` 当前全局 shell 结构
- `interaction-spec/_shared/surface-registry.md`
- `interaction-spec/_shared/view-models.ts::LayoutControllerView`、`RestoreStatusView`

**interface / data / state contracts：**
- `ChartLayout = dense | focus | mobile_tab`
- `selectedMobileTab`
- `layoutBySymbol` 优先于 global fallback
- `restoreStatus` 失败时必须回落默认可用布局

**test fixtures / seed data：**
- desktop focus 样本
- desktop dense 样本
- mobile_tab 样本
- 两个 symbol 的不同布局恢复样本
- 单个 symbol 的坏 layout 样本

**validation commands：**
- `npx playwright test tests/e2e/restore-layout/resume.spec.ts`
- `npm run build`

**evidence requirements：**
- 浏览器重开前后截图。
- per-symbol 布局独立恢复的 trace。
- Regression 证明坏 layout 只会回退到默认 focus，不会让页面不可用。

**stop conditions：**
- 恢复逻辑需要账号、云同步或跨设备数据库。
- layout 切换改变了业务对象而不是纯呈现。
- 需要把 source / alert 的业务状态塞进布局控制器。

**migration / route boundaries：**
- 只改布局与恢复 surface。
- 不新增 route。
- 不把图表库 API 当作业务布局合同。

---

### T006：冻结样本、回放、unit/e2e 门禁与 AC 验收矩阵

```yaml
parent_task:
  id: "T006"
  title: "冻结样本、回放、unit/e2e 门禁与 AC 验收矩阵"
  depends_on:
    - "T001"
    - "T002"
    - "T003"
    - "T004"
    - "T005"
  surfaces:
    - "SURF-WATCHLIST"
    - "SURF-WORKBENCH"
    - "SURF-MTS"
    - "SURF-ALERTS"
    - "SURF-SOURCE"
    - "SURF-LAYOUT"
    - "SURF-RESTORE"
  authorized_paths:
    - "tests/unit/**"
    - "tests/replay/**"
    - "tests/e2e/**"
    - "fixtures/**"
    - "package.json"
    - "package-lock.json"
  prohibited_paths:
    - "harness-runtime/harness/stages/**/contracts/**"
    - "harness-runtime/harness/stages/**/product/**"
    - "harness-runtime/harness/stages/**/solution.md"
    - "harness-runtime/harness/stages/**/tech-design.md"
    - "server/index.js"
    - "src/lib/signals.ts"
  required_evidence:
    - red_report
    - green_report
    - regression_report
    - e2e_run_report
    - trace_or_video
    - fixture_checksum_or_replay_log
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "T006-A1"
        execution_order: 1
        depends_on:
          - "T002-A1"
          - "T003-A1"
          - "T004-A1"
          - "T005-A1"
        write_scope:
          - "fixtures/**"
          - "tests/replay/**"
          - "tests/unit/**"
        read_scope:
          - "harness-runtime/harness/stages/20260522-stock-watch-system/interaction-spec/buc-index.md"
          - "harness-runtime/harness/stages/20260522-stock-watch-system/interaction-spec/buc-coverage.md"
          - "harness-runtime/harness/stages/20260522-stock-watch-system/interaction-spec/_shared/surface-registry.md"
        detail_ref: "T006-A1"
        reviewer_verdict: "pending"
      - id: "T006-A2"
        execution_order: 2
        depends_on:
          - "T006-A1"
        write_scope:
          - "tests/e2e/**"
          - "tests/unit/**"
          - "package.json"
        read_scope:
          - "harness-runtime/config/harness.yaml"
          - "harness-runtime/templates/contracts/execution-brief.contract.yaml"
        detail_ref: "T006-A2"
        reviewer_verdict: "pending"
```

**目标：** 把四市场、歧义输入、来源降级、MTS 强/弱/不可解释、提醒触发、归档恢复、布局恢复和 snapshot 损坏都变成冻结样本，并用 unit / replay / E2E 把 AC-01~AC-05 做成稳定门禁。

**完成边界：** 完成后，验收不再依赖 live 行情作为门禁；live Yahoo 只做 smoke。此任务不改产品运行时语义，只提供证据与门禁。

**surface：** 覆盖所有 surfaces，但只作为验证入口，不改变业务对象。

**dependencies：** 依赖 T001~T005 的 domain / surface / storage / alert / layout 合同已经冻结。

**authorized_paths：** `tests/unit/**`、`tests/replay/**`、`tests/e2e/**`、`fixtures/**`、`package.json`、`package-lock.json`。

**prohibited_paths：** 生产代码核心逻辑、任何 contract / product / solution / tech-design 文档、以及所有产品运行时 Agent 相关内容。

**stop_if：**
- 验证只能靠 live 行情才能跑通。
- locator contract 漂移到脆弱 DOM 结构。
- gate 证据无法在 fixture-first 路径中复现。
- 需要引入产品运行时 Agent 来“补测试”。

**required_evidence：**
- unit / replay / e2e 的完整 Red / Green / Regression 报告。
- Playwright trace / video / screenshot。
- fixture checksum、replay log、AC mapping matrix。

**test_obligation：**
```yaml
risk_level: high
surfaces:
  - SURF-WATCHLIST
  - SURF-WORKBENCH
  - SURF-MTS
  - SURF-ALERTS
  - SURF-SOURCE
  - SURF-LAYOUT
  - SURF-RESTORE
required_capabilities:
  - unit
  - replay
  - browser_flow
  - user_visible_assertion
  - accessibility_smoke
  - fixture_first
  - mutation_or_fault_injection
evidence_required:
  - red_report
  - green_report
  - regression_report
  - e2e_run_report
  - trace_or_video
accepted_alternatives:
  browser_flow:
    - manual_acceptance_walkthrough_with_recorded_steps
```

**e2e_obligation：**
```yaml
risk_level: high
user_surfaces:
  - watchlist_flow
  - workbench_flow
  - mts_flow
  - alert_flow
  - restore_flow
required_capabilities:
  - browser_flow
  - user_visible_assertion
  - realtime_or_refresh
  - accessibility_smoke
  - local_persistence_replay
evidence_required:
  - e2e_run_report
  - trace_or_video
  - screenshot_on_failure
  - assertion_summary
accepted_alternatives:
  browser_flow:
    - manual_acceptance_walkthrough_with_recorded_steps
```

**spec_refs：**
- `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md#使用冻结样本验收核心路径`
- `solution D-07`
- `VS-01` ~ `VS-08`
- `interaction-spec/buc-index.md`
- `interaction-spec/buc-coverage.md`
- `interaction-spec/_shared/surface-registry.md`

**traces_to：**
- AC: `AC-01`, `AC-02`, `AC-03`, `AC-04`, `AC-05`
- FR: `FR-09`
- MOD: `MOD-08`
- INT: `INT-01`, `INT-02`, `INT-03`, `INT-04`, `INT-05`, `INT-06`, `INT-07`, `INT-08`
- DATA: `DATA-01`, `DATA-02`, `DATA-03`, `DATA-04`, `DATA-05`, `DATA-06`
- VS: `VS-01`, `VS-02`, `VS-03`, `VS-04`, `VS-05`, `VS-06`, `VS-07`, `VS-08`
- SF: `SF-01`, `SF-02`, `SF-03`, `SF-04`, `SF-05`, `SF-06`
- Gate: `Provider Gate`, `Cache Gate`, `Storage Gate`, `Chart Gate`

**TASK node candidate：** `parent_task_id=T006`; `atomic_task_ids=[T006-A1, T006-A2]`; `dependencies=[T001, T002, T003, T004, T005]`; `authorized_paths=[tests/unit/**, tests/replay/**, tests/e2e/**, fixtures/**, package.json, package-lock.json]`。

#### T006-A1

**目标**：见本 Atomic Task 的 `single_action`。
**执行边界**：见本块的 `parent_task_coverage`、`stop conditions` 与 `migration / route boundaries`。
**文件行动**：以本 Parent 的 `atomic_task_queue.execution_units[]` 中 `write_scope` 为准。
**输入**：见 `explicit inputs / outputs` 的输入项。
**输出**：见 `explicit inputs / outputs` 的输出项。
**代码模式参考**：见下方 `code pattern references`。
**TDD 范围**：见测试样本、验证命令和证据要求。
**执行期验证命令**：见下方 `validation commands`。
**证据**：见下方 `evidence requirements`。
**停止条件**：见下方 `stop conditions`。

**single_action：** 先把所有核心路径需要的冻结样本、回放 loader 和 seed 规范建起来，让每个场景都能脱离 live 数据重复执行。

**explicit inputs / outputs：**
- 输入：四市场标的、歧义数字代码、source degraded payload、MTS 强/弱/不可解释样本、alert trigger 样本、archive/restore 样本、corrupt layout 样本。
- 输出：fixture 文件、回放 loader、固定 seed 约定、fixture checksum 或快照。

**parent_task_coverage：** 只覆盖 `T006` 的数据准备子边界，不直接改产品运行时代码。

**ac_scenario_coverage：** `AC-01`~`AC-05`；Scenario：使用冻结样本验收核心路径。

**code pattern references：**
- `server/index.js::generateFallbackBars`
- `src/data/markets.ts::defaultWatchlist`
- `src/lib/indicators.ts` 的纯函数风格
- `interaction-spec/BUC-0*.md` 的 E2E seed 说明

**interface / data / state contracts：**
- fixture 命名与目录必须与 scenario / surface 一一对应
- seed 数据不可变，不能依赖 live 网络
- replay loader 必须可重复执行且输出一致

**test fixtures / seed data：**
- `fixtures/watchlist/*`
- `fixtures/source/*`
- `fixtures/mts/*`
- `fixtures/alerts/*`
- `fixtures/workspace/*`

**validation commands：**
- `npx vitest run tests/replay/**/*.spec.ts`
- `npm run build`

**evidence requirements：**
- fixture checksum / diff summary。
- replay log 证明重复执行结果一致。
- Red / Green / Regression 报告能定位到具体 fixture 名。

**stop conditions：**
- fixture 必须依赖 live Yahoo 才能生成。
- fixture 形状无法表达 negative path。
- seed 规范需要新增未授权的产品语义。

**migration / route boundaries：**
- 只允许 test / fixture 文件。
- 不改生产 route。
- 不把 fixture 写成临时 demo 代码。

#### T006-A2

**目标**：见本 Atomic Task 的 `single_action`。
**执行边界**：见本块的 `parent_task_coverage`、`stop conditions` 与 `migration / route boundaries`。
**文件行动**：以本 Parent 的 `atomic_task_queue.execution_units[]` 中 `write_scope` 为准。
**输入**：见 `explicit inputs / outputs` 的输入项。
**输出**：见 `explicit inputs / outputs` 的输出项。
**代码模式参考**：见下方 `code pattern references`。
**TDD 范围**：见测试样本、验证命令和证据要求。
**执行期验证命令**：见下方 `validation commands`。
**证据**：见下方 `evidence requirements`。
**停止条件**：见下方 `stop conditions`。

**single_action：** 把 unit / replay / e2e 的门禁串成一套可执行的验收矩阵，稳定覆盖所有 surfaces 与 gate。

**explicit inputs / outputs：**
- 输入：fixture corpus、稳定 locator、AC / scenario 对照表。
- 输出：unit specs、Playwright specs、gate assertions、AC 映射矩阵、failure artifacts。

**parent_task_coverage：** 只覆盖 `T006` 的测试门禁子边界，不触碰产品 runtime 逻辑。

**ac_scenario_coverage：** `AC-01`~`AC-05`；Scenario：使用冻结样本验收核心路径，并确保 20 个 delta scenario 都能回放。

**code pattern references：**
- harness config 的 Playwright / vitest 约定
- `interaction-spec/_shared/surface-registry.md` 的 locator root
- `interaction-spec/_shared/view-models.ts`
- `buc-index.md`、`buc-coverage.md`

**interface / data / state contracts：**
- `data-testid` + accessible name 双保险
- `source-status-banner`、`chart-main-panel`、`chart-volume-panel`、`chart-secondary-panel`、`indicator-tab-*`、`mts-signal-card`、`alert-rule-row-*`、`restore-banner`、`layout-toggle-*`
- gate fixtures 必须可复用，不依赖脆弱 DOM 结构

**test fixtures / seed data：**
- 全量 gate fixture
- live smoke fixture（非门禁）
- 屏幕截图 / trace seed

**validation commands：**
- `npx vitest run`
- `npx playwright test`
- `npm run build`

**evidence requirements：**
- unit / replay / e2e 的完整报告。
- screenshot / trace / video。
- AC 映射矩阵与 gate pass / fail 汇总。

**stop conditions：**
- E2E 只能靠 live 才能通过。
- locator 漂移到脆弱结构。
- 需要通过产品运行时 Agent 补齐测试。

**migration / route boundaries：**
- 只改 tests / fixtures / scripts。
- 不改产品逻辑。
- 不把测试门禁与运行时功能混写。

---

## 结论

这份 breakdown 将 mission 切成 6 个 parent task、12 个 atomic task，所有必须覆盖的 delta scenario 都有落点，并且把 Provider / Cache / Storage / Chart Gate、`MtsReasonRegistry`、`WorkspaceSnapshotV2` per-symbol layout、scheduled alert、state flows 和 fixture-first testing 都显式纳入任务边界。`## Agent 实现` 不适用，本计划不包含任何产品运行时 Agent 任务。

## contract_update 摘要（供主流程写入 external contract）

- `execution_result`: `DONE`
- parent_tasks: `6`
- atomic_tasks: `12`
- 关键门禁：Provider / Cache / Storage / Chart / Fixture-first E2E
- 关键合同：`MarketDataEnvelope`、`SourceHealth`、`MtsExplanation + MtsReasonRegistry`、`AlertRule` 双状态机、`WorkspaceSnapshotV2`
- 关键验收：AC-01 ~ AC-05 与 delta spec scenario 1 ~ 20 全覆盖
