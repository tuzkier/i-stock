# Watchboard Presentation — 差量规格

<!--
本文件是一次任务的行为契约增量（delta），能力：看盘界面呈现 / 状态色语义 / 信号可读性。
所有 Requirement 为本任务新增（ADDED），相对既有 spec 基线为「新增-draft」。
任务收尾时提炼固化到 project-knowledge/specs/watchboard-presentation/spec.md。

基线对照：
- project-knowledge/specs/watchboard-presentation/spec.md 不存在 → Baseline: none（首次建立）
- 相关既有能力 project-knowledge/specs/local-stock-watch-workbench/spec.md（active）提供功能基线上下文；本能力与其正交（呈现忠实性，非功能）
-->

**任务**: `20260721-watchboard-ui-friendliness`
**能力**: `watchboard-presentation`（看盘界面呈现 / 状态色语义 / 信号可读性）
**Baseline**: `none（首次建立）` _(相关既有能力：`local-stock-watch-workbench`，仅提供功能上下文，不修改)_
**状态**: `draft`（新增）

---

## 控制契约

> 差量规格是行为契约的能力级补充。这里的 ID 必须能被 PRD、拆解、执行、code-review 和验证引用。

- Contract: `contracts/delta-spec.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。
- 约束基线：本能力只改「既有领域状态如何被呈现」，不改 domain 算法 / 状态机 / 数据（SCOPE-11~14）；所有 Scenario 均为呈现忠实性义务，用户为只读观察者。

---

## ADDED Requirements

### Requirement: 状态色语义分档忠实呈现
系统 SHALL 按既有领域状态分类，将来源健康、技术评分极性、工作台恢复态映射为四档呈现色语义（正常 / 信息 / 谨慎-风险 / 警告-异常），使正常态不出现警告色、仅真异常出现警告色，且「市场看空」与「数据/恢复故障」两类色物理可辨。

#### Scenario: 来源正常态不出现警告色
- **GIVEN** 某标的来源健康为 `formal`，或应用初始/未选中（`not_loaded`），布局未回退
- **WHEN** 用户打开/切换到该标的界面
- **THEN** 来源承载处呈中性/正常语义，0 处黄色警告横幅（`.data-notice`）
- **AND** 界面无「需关注」视觉信号

#### Scenario: 来源真异常态出现警告色并标注受影响范围
- **GIVEN** 某标的来源健康为 `stale` 或 `unavailable`，带 affectedObjects/degradationReason
- **WHEN** 用户打开该标的界面
- **THEN** 出现警告/错误色提示，并呈现降级原因与受影响范围（chart/mts/alerts）
- **AND** 警告色不外溢到 formal/not_loaded/restored 等正常态

#### Scenario: 工作台正常恢复态不出现警告色黄条
- **GIVEN** 应用启动，restoreMetadata.status 为 `restored`/`partial`/`default_fallback`（含首次 snapshot_missing）
- **WHEN** 用户打开工作台
- **THEN** restored 呈中性/成功、partial/default_fallback 呈信息级，均不渲染警告色黄条
- **AND** 恢复原因/migratedFromLegacy/snapshotBytes 等技术态收进详情，不拼进主提示文案

#### Scenario: 工作台恢复失败态出现需关注提示
- **GIVEN** restoreMetadata.status 为 `failed`，或 discardedLayoutKeys 非空
- **WHEN** 用户打开工作台
- **THEN** 出现警告/需关注提示与「已丢弃坏布局」明细
- **AND** 与正常恢复态形成物理可辨对比

#### Scenario: 负向评分与来源故障色物理区分
- **GIVEN** 某标的 MtsExplanation.scoreBand 为 `negative`/`strong_negative`，或 alertLevel 为 `风控`
- **WHEN** 用户查看主视图技术提醒区
- **THEN** 评分/提醒呈谨慎/风险语义色，表达「技术面看空」而非「系统/数据故障」
- **AND** 该色与来源 stale/unavailable 的警告横幅物理区分（承载不复用同一警告类名）
- **AND** 正向/中性评分（positive/neutral/not_applicable）呈积极/中性无色

#### Scenario: demo_fallback 呈信息级不用高危警告色（DEC-01 默认档，待用户确认）
- **GIVEN** 某标的来源健康为 `demo_fallback`（兜底/演示数据）
- **WHEN** 用户打开该标的界面
- **THEN** demo_fallback 呈信息级/次级提示，不使用与 stale/unavailable 相同的高危警告色，也不完全等同 formal 无提示
- **AND** 用户能识别「这是兜底/演示数据」但不被当作严重故障
- **AND** 最终色档以 DEC-01 用户确认为准；若改判「需关注」则并入警告色档（不派生硬阻断）

### Requirement: 内部枚举人话化与评分可读呈现
系统 SHALL 将主视图技术信号与交易信号以人话文案 + 进度条式评分呈现，不直接暴露原始枚举/理由代码；原始字段与技术态仅在展开详情/调试区可见。

#### Scenario: 主视图不暴露原始枚举/理由代码
- **GIVEN** 某标的有 trendState/mtsScore/scoreBand/signalType/alertLevel 及理由代码（如 TREND_ABOVE_EMA）
- **WHEN** 用户查看主视图技术提醒区（未展开详情）
- **THEN** 主视图 0 处裸枚举、0 处裸理由代码，呈现人话文案（复用 displayLabel/technicalReminder/中文 alertLevel/MtsReason.label）
- **AND** 不出现 `trend_state:` 等前缀裸值

#### Scenario: 评分以进度条式可读呈现
- **GIVEN** 某标的 mtsScore 为有效数值
- **WHEN** 用户查看主视图评分区
- **THEN** 评分以进度条/可视化条 + 可读文案呈现，不以裸数字替代进度条
- **AND** scoreBand 为 not_applicable/null 时按中性处理，不呈现误导性进度条填充

#### Scenario: 原始枚举/理由代码仅在展开详情可见
- **GIVEN** 某标的详情区含原始枚举、理由代码、失效项、cache/retry 技术态
- **WHEN** 用户默认查看（未展开），随后点击展开详情/调试区
- **THEN** 默认态不呈现原始字段；展开后详情区显示 code/枚举/失效项/关注位
- **AND** 技术态（retryState/cacheState）仅在折叠区，不外溢主视图

#### Scenario: 未注册理由码兜底不直呈
- **GIVEN** 某理由 code 未在版本化注册表注册（回落 UNKNOWN_CODE）
- **WHEN** 用户查看理由项
- **THEN** 未注册码不作为有效解释直呈主视图，按 UNKNOWN_CODE 兜底处理，不裸露原始 code

#### Scenario: 非 ready 技术/交易状态人话化
- **GIVEN** 某标的处于非 ready 态：MTS trendState=`data_insufficient`/`source_degraded`，或 TradeSignalState.status=`not_target_symbol`/`data_insufficient`/`source_degraded`
- **WHEN** 用户查看技术提醒区/交易信号卡
- **THEN** 各非 ready 态呈对应人话说明（如「数据不足以给出信号」「该标的无定制策略信号」「数据来源降级，暂不给出买卖价位」），0 处裸枚举串
- **AND** 来源降级态不呈现回测块

### Requirement: 重复信息收敛唯一主源
系统 SHALL 将来源状态、价格/涨跌各收敛到 1 处权威主源呈现，侧栏来源仅作弱化次级信号，且涨跌红绿色与来源/布局警告色语义分离。

#### Scenario: 来源状态收敛到唯一权威主源
- **GIVEN** 改造前来源状态在标题黄条/图表角标/指标条等 3~5 处重复
- **WHEN** 用户扫读改造后界面
- **THEN** 来源状态仅 1 处权威呈现点（计数=1）
- **AND** 侧栏来源为弱化小圆点（次级、非主源），去重后来源可读性不丢失

#### Scenario: 价格/涨跌收敛唯一主源且涨跌色与警告色分离
- **GIVEN** 改造前价格/涨跌在多处重复，涨跌红绿色与来源警告色视觉相近
- **WHEN** 用户扫读界面
- **THEN** 价格/涨跌只出现 1 处权威主源（计数=1）
- **AND** 涨跌红绿色与来源/布局警告色语义分离、视觉可辨

### Requirement: 顶部信息层级重排
系统 SHALL 将标的标题呈现为顶部视觉主位，周期/视图切换控件降级右对齐，且不改变既有布局切换语义。

#### Scenario: 标题为顶部视觉主位、控件降级
- **GIVEN** 用户打开某标的界面（默认 focus 布局）
- **WHEN** 用户观察顶部区域
- **THEN** 标的标题以最高字号/权重呈现为视觉主位，周期/视图控件视觉权重低于标题且右对齐

#### Scenario: 切换周期/布局后标题仍主位、切换语义不变
- **GIVEN** 顶部含周期切换与视图（dense/focus/mobile_tab）控件
- **WHEN** 用户操作切换周期/布局模式
- **THEN** 布局结构随切换调整但标题主位不变，切换功能与白名单语义不减
- **AND** 非法布局值由既有归一化回退默认 focus，呈现不新增失败分支

### Requirement: 主看信息层级建立
系统 SHALL 使交易信号主卡视觉突出、回测/理由/原始字段降为次级灰字形成明确层级差，且 nonAdvice 免责声明始终可见。

#### Scenario: 主卡突出、次级降灰形成层级差
- **GIVEN** 某标的同时有当前可操作信号（stanceLabel/关键数字）与回测/理由/原始字段
- **WHEN** 用户查看交易信号区
- **THEN** 主卡突出呈现建议与关键数字，回测/理由/原始字段降为次级灰字，主/次视觉层级差明确可辨

#### Scenario: 免责声明保持可见
- **GIVEN** 交易信号卡含 nonAdvice 免责声明
- **WHEN** 用户查看信号卡（默认态与折叠态）
- **THEN** nonAdvice 免责始终可见，层级降级/明细折叠均不隐藏免责

### Requirement: 侧栏扫读优化
系统 SHALL 使侧栏每条以名称+代码一行、价格+涨跌右对齐为主看信息，来源状态弱化为小圆点次级信号，且 archived 标的弱化区分 active。

#### Scenario: 侧栏条目主看信息突出
- **GIVEN** 侧栏含多条 active 自选标的
- **WHEN** 用户扫读侧栏列表
- **THEN** 每条呈现名称+代码一行、价格+涨跌右对齐主看数字，不与来源状态混排为同级

#### Scenario: 侧栏来源弱化为小圆点非主源
- **GIVEN** 侧栏条目来源档为 formal 或非 formal
- **WHEN** 用户扫读侧栏
- **THEN** 来源弱化为小圆点：formal 呈中性圆点、非 formal 呈需关注弱提示圆点，均不喧宾夺主
- **AND** 侧栏来源不重复承载为来源主源

#### Scenario: 归档标的弱化区分
- **GIVEN** 侧栏同时含 active 与 archived 标的
- **WHEN** 用户扫读侧栏
- **THEN** archived 条目弱化呈现、与 active 明确区分，不作主看强调（不改归档/恢复业务逻辑）

### Requirement: 交易信号卡密度优化
系统 SHALL 使交易信号卡默认仅呈现关键数字、三段回测明细默认折叠可展开，且仅 ready 态呈现回测块。

#### Scenario: 默认呈现关键数字
- **GIVEN** 某标的 TradeSignalState.status=ready，有 stanceLabel/holding/回测关键数字
- **WHEN** 用户查看交易信号卡（未展开）
- **THEN** 默认呈现关键数字（stanceLabel、持仓中/空仓、胜率、累计收益），三段回测/回合流水/事件默认不铺开

#### Scenario: 三段回测明细默认折叠、展开后呈现
- **GIVEN** ready 态信号卡含三段回测明细与反T回合
- **WHEN** 用户默认查看后点击展开明细
- **THEN** 默认态明细折叠、仅关键数字可见；展开后呈现三段回测/反T回合明细
- **AND** 明细不与关键数字同权重平铺

#### Scenario: 仅 ready 呈现回测块、价位分层级
- **GIVEN** 某标的 status=ready（含回测与关键价位），或非 ready（无回测）
- **WHEN** 用户展开信号卡明细
- **THEN** ready 态呈现回测块且正式信号位与 ATR 观察位分层级区分
- **AND** 非 ready 态不呈现回测块（不呈现空回测容器）

### Requirement: 跨呈现状态一致性
系统 SHALL 在来源态、交易信号态、恢复态之间保持呈现一致，来源降级时信号卡同步降级，恢复态与来源态各自独立承载；呈现层只读取既有门控结果，不重实现门控。

#### Scenario: 来源降级时信号卡同步降级
- **GIVEN** 某标的来源健康变为 stale/unavailable（非 formal）
- **WHEN** 用户查看该标的交易信号卡
- **THEN** 信号卡同步降级为 source_degraded 人话说明，不再显 ready 且不给买卖价位
- **AND** 不出现「来源已 stale 而信号卡仍 ready」的矛盾呈现

#### Scenario: 恢复态与来源态各自独立承载
- **GIVEN** 恢复态与来源态同时存在（两套独立状态机）
- **WHEN** 应用启动后用户观察顶部
- **THEN** 恢复态与来源态各自归位、不共用同一条黄条，两类语义不混用同一警告承载
