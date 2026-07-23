# 验收场景：多市场看盘终端（MyInvestment）界面友好化改造

> **来源**：prd 技能 → `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/product/acceptance-scenarios.md`
> **用途**：把已确认系统用例（SUC-01~06）、用例流 / 结局节拍（SUC-xx-FLOW / fan-out token）、业务对象状态（OBJ / STM）和业务规则（BR-02/04/10 等）转成可观察、可验证、可追溯的验收场景与验收条件。本文不设计测试代码、测试工具或自动化实现。
> **任务性质约束**：呈现层友好化改造（状态色归位 / 枚举人话化 / 去重复 / 顶部重排 / 信息层级 / 侧栏扫读 / 信号卡密度）。所有验收条件均为「界面忠实、无误导地承载既有领域状态」的呈现义务，不新增业务功能、不改算法、不改数据。证据以 preview 截图 / DOM 断言 / Playwright E2E / axe 为主，`npm run build`（EVD-01）仅作前提证据。

**任务编号（mission-id）：** 20260721-watchboard-ui-friendliness
**状态：** `draft`

---

## 模板约定

- 场景编号固定使用 `SCN-xx`（对齐契约 SCN-01~07）；验收条件编号使用 `SCN-xx-COND-xx` 作为下游追溯锚点；规则覆盖用 `RC-xx`；负向 / 边界 / 状态限制路径用 `NEG-xx`。
- 每条验收条件均来自已确认系统用例、用例流 / 结局节拍、业务规则或对象状态变化；不从 use-case-model 的「待澄清系统责任」（DEC-01）派生硬性阻断验收条件。
- 每条验收条件均含 Given / When / Then、可观察结果、验证证据类型和追溯引用。
- 证据类型口径：**界面状态（preview 截图）** = EVD-02 逐条比对；**界面状态（DOM 断言）** = 对元素类名 / 结构 / 计数的静态断言；**E2E（Playwright）/ axe** = EVD-03 交互与可访问性；**命令结果（build）** = EVD-01，仅作「改造已编译进产物」的前提证据，不单独构成验收通过。
- 不适用项写 `不适用：原因...`；证据不足 / 待决项写 `待澄清：原因...`。

---

## 场景地图

| 场景 ID | 用户 / 角色 | 用户目标 | 来源系统用例 / 流 | 优先级 | 覆盖理由 |
|---------|-------------|----------|-------------------|--------|----------|
| SCN-01 | ACT-01 看盘用户 | 一眼判断「哪里真的需要关注」——正常态不被警告色误导，仅真异常见警告色，且「技术看空」与「数据故障」两类色物理可辨 | SUC-01 / FLOW-02（来源三档）、SUC-06 / FLOW-02（恢复四态）、SUC-02 / FLOW-02（评分极性） | 高 | 契约核心杂乱问题（状态色滥用），是 7 类改造中误导性最强、fan-out 结局最多的一类，须逐结局落条件 |
| SCN-02 | ACT-01 看盘用户 | 不懂内部枚举也能读懂技术信号，评分可读 | SUC-02 / FLOW-01/03、SUC-03 / FLOW-03 | 高 | 主视图裸露 `trend_state`/`score_band` 等内部枚举与理由代码，直接抬高理解门槛 |
| SCN-03 | ACT-01 看盘用户 | 同一信息只看一次 | SUC-01 / FLOW-03、SUC-04 / FLOW-02、SUC-05 / FLOW-01 | 高 | 来源状态与价格 / 涨跌 3~5 处重复，制造扫读噪音 |
| SCN-04 | ACT-01 看盘用户 | 先定位标的再操作 | SUC-05 / FLOW-01/02 | 中 | 周期 / 视图控件与大标题抢焦点，顶部动线不清 |
| SCN-05 | ACT-01 看盘用户 | 第一眼抓到可操作信号 | SUC-03 / FLOW-01 | 中 | 回测 / 理由 / 原始字段与主信号权重接近，注意力被稀释 |
| SCN-06 | ACT-01 看盘用户 | 侧栏快速定位标的 | SUC-04 / FLOW-01/02 | 中 | 侧栏主看信息与来源状态混排，定位成本高 |
| SCN-07 | ACT-01 看盘用户 | 先看结论再看明细 | SUC-03 / FLOW-02 | 中 | 三段回测流水账默认铺开，结论被明细淹没 |

---

## 用例覆盖关系

| 系统用例 / 流 | 是否进入验收 | 覆盖场景 | 不覆盖原因 | 风险 |
|---------------|--------------|----------|------------|------|
| SUC-01 / 主成功流 + FLOW-02 fan-out（not_loaded/formal/demo_fallback/stale/unavailable） | 是 | SCN-01（COND-01/02/03）、SCN-03 | — | demo_fallback 档为 DEC-01 待确认，落成默认信息级条件而非硬阻断 |
| SUC-01 / FLOW-03（价格涨跌唯一主源） | 是 | SCN-03（COND-02） | — | 「主源在哪一处」是承载选点（交互层），本文只固化「必须唯一」义务 |
| SUC-02 / FLOW-01（人话 + 进度条） | 是 | SCN-02（COND-01/02） | — | 中 |
| SUC-02 / FLOW-02 fan-out（positive/negative 极性上色） | 是 | SCN-01（COND-06） | — | negative 色须与来源故障色物理区分，是 SCN-01 与 SCN-02 交界关键点 |
| SUC-02 / FLOW-03（详情展开 / 数据不足 / 来源降级） | 是 | SCN-02（COND-03/04） | — | 中 |
| SUC-03 / FLOW-01（主卡关键数字突出） | 是 | SCN-05（COND-01）、SCN-07（COND-01） | — | 中 |
| SUC-03 / FLOW-02 fan-out（明细折叠 / 展开 / 免责可见） | 是 | SCN-07（COND-02/03）、SCN-05（COND-02） | — | 中 |
| SUC-03 / FLOW-03 fan-out（not_target/data_insufficient/source_degraded 人话化） | 是 | SCN-02（COND-04）、NEG-01/NEG-02 | — | 状态一致性（来源降级须门控信号卡）是关键约束 |
| SUC-04 / FLOW-01（侧栏主看突出） | 是 | SCN-06（COND-01） | — | 中 |
| SUC-04 / FLOW-02 fan-out（来源小圆点 normal/attention） | 是 | SCN-06（COND-02） | — | 中 |
| SUC-05 / FLOW-01/02（标题主位 / 控件降级） | 是 | SCN-04（COND-01/02） | — | 中 |
| SUC-06 / FLOW-02 fan-out（restored/partial/default_fallback/failed） | 是 | SCN-01（COND-04/05） | — | restored 被染黄是 SCN-01 直接根因，须逐态落条件 |
| SUC-01 ST-01f「刷新中」纯 UI 态 | 否 | — | 纯 UI 表现态，use-case-model 明确交 interaction 层补，非领域色语义 | 低 |
| SUC-05 异常流 | 否 | — | use-case-model 标「不适用：呈现重排无失败结局，非法值由既有归一化处理」 | 低（在 NEG-06 以边界形式登记） |
| OBJ-05 AlertRule / OBJ-09 NormalizationPreview 相关流 | 否 | — | 不在 7 类改造锚定的主看盘扫读路径（提醒管理 / 添加流程），契约范围外 | 低 |

---

## 业务规则到场景

| 规则覆盖 ID | 业务规则 | 承载对象 / 状态 | 覆盖场景 | 验收条件 | 覆盖方式 |
|-------------|----------|----------------|----------|--------|----------|
| RC-01 | BR-02（来源三档：formal/not_loaded 正常、demo_fallback 信息级、stale/unavailable 真异常） | OBJ-02 / STM-02 | SCN-01 | SCN-01-COND-01/02/03 | 正向（正常态无警告）+ 负向（真异常见警告）+ 边界（demo_fallback 信息级） |
| RC-02 | BR-10（恢复态 restored/partial/default_fallback 正常 / 信息、failed / 坏布局丢弃需关注） | OBJ-06 / STM-07 | SCN-01 | SCN-01-COND-04/05 | 正向（正常恢复无黄条）+ 负向（failed 见警告） |
| RC-03 | BR-04（负向 / 风控评分是市场业务结论，非系统异常，不得与来源故障共用告警色） | OBJ-03 / scoreBand / alertLevel | SCN-01 | SCN-01-COND-06 | 状态限制（两类色物理区分）+ 负向（negative 谨慎色而非黄条） |
| RC-04 | BR-05（理由代码经注册表呈现 label/detail，未注册回落 UNKNOWN_CODE 不直呈） | OBJ-07 / MtsReasonCode | SCN-02 | SCN-02-COND-01/03/04 | 正向（显示 label）+ 边界（详情折叠）+ 负向（UNKNOWN_CODE 不直呈，见 NEG-04） |
| RC-05 | STM-05（交易信号 status 门控：not_target/source_degraded/data_insufficient/ready） | OBJ-04 / STM-05 | SCN-02、SCN-07 | SCN-02-COND-04、SCN-07-COND-01 | 正向（ready 关键数字）+ 负向（非 ready 人话化） |
| RC-06 | BR-03（来源非 formal 时门控信号输出为 source_degraded） | OBJ-04 ← OBJ-02 | SCN-01 关联 SCN-07 | NEG-01 | 状态限制（来源 stale 时信号卡须同步降级，跨呈现一致性） |
| RC-07 | BR-07（回测 / 反T仅 status=ready 时计算） | OBJ-08 ← OBJ-04 | SCN-07 | SCN-07-COND-03、NEG-02 | 状态限制（非 ready 无回测块）+ 负向（不呈空回测容器） |
| RC-08 | 去重复承载（UIC-03，来源 / 价格涨跌各唯一主源；涨跌红绿与警告色语义分离） | OBJ-02、EXC-01 价格 / 涨跌 | SCN-03 | SCN-03-COND-01/02 | 正向（各 1 处主源）+ 状态限制（涨跌色 ≠ 警告色） |
| RC-09 | STM-01（active/archived 呈现区分） | OBJ-01 / STM-01 | SCN-06 | SCN-06-COND-03 | 状态限制（archived 弱化区分） |
| RC-10 | nonAdvice 免责始终可见（ATTR-29） | OBJ-04 | SCN-05、SCN-07 | SCN-05-COND-02、NEG-05 | 正向（免责可见）+ 负向（折叠不得隐藏免责） |
| RC-11 | STM-06（布局模式切换不改语义，非法值归一化） | OBJ-06 / STM-06 | SCN-04 | SCN-04-COND-02、NEG-06 | 边界（切换后标题仍主位，非法值归一化） |

---

## 验收条件

### 验收条件 SCN-01-COND-01：来源 formal / not_loaded 正常态不出现警告色

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-01 |
| 来源系统用例 / 流 | SUC-01 / FLOW-02（节拍 `SUC-01-FLOW-02.formal`、`SUC-01-FLOW-02.not_loaded`） |
| 来源规则 / 对象 | BR-02；OBJ-02 / STM-02（formal、not_loaded） |
| 可观察结果 | 选中 formal 数据标的或初始未加载态时，主区来源承载处不出现黄色 `.data-notice` 警告横幅，呈现为中性 / 正常语义 |
| 验证证据类型 | 界面状态（preview 截图）+ 界面状态（DOM 断言：来源承载容器无 `.data-notice` 警告类名） |
| 追溯 | US-01；SCN-01；BR-02；App.tsx:639；OBJ-02 |

**Given：** 某标的 SourceHealth.status = `formal`（真实健康数据），或应用初始 / 未选中任何标的（status = `not_loaded`），布局未回退。

**When：** 用户打开 / 切换到该标的界面（或应用初次加载）。

**Then：** 来源状态主源处呈现中性 / 正常语义；不渲染黄色警告横幅（当前 `App.tsx:639` 对 `status!=="formal"` 一律 `.data-notice` 的行为不得波及 formal / not_loaded）；界面无「需关注」视觉信号。

---

### 验收条件 SCN-01-COND-02：来源 demo_fallback 呈信息级、不用高危警告色（DEC-01 待确认默认档）

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-01 |
| 来源系统用例 / 流 | SUC-01 / FLOW-02（节拍 `SUC-01-FLOW-02.demo_fallback`） |
| 来源规则 / 对象 | BR-02（demo_fallback = 降级可用 / 信息级）；OBJ-02 / STM-02.demo_fallback；DEC-01 |
| 可观察结果 | demo_fallback 态呈现为信息级 / 次级提示（区别于 stale/unavailable 的高危警告色），且区别于 formal 的完全中性——用户可识别「这是兜底 / 演示数据」但不被当作严重故障 |
| 验证证据类型 | 界面状态（preview 截图，与 formal、stale 两档并置对比）；**待澄清：最终色档需 DEC-01 用户确认后定档** |
| 追溯 | SCN-01；BR-02；DEC-01；OBJ-02 / STM-02.demo_fallback；App.tsx:639 |

**Given：** 某标的 SourceHealth.status = `demo_fallback`（数据不可得时回落兜底 / 演示数据）。

**When：** 用户打开该标的界面。

**Then（默认档，DEC-01 未改判前）：** demo_fallback 呈现为信息级 / 次级提示，**不使用与 stale/unavailable 相同的高危警告色**，也不完全等同 formal 的无提示；用户能区分三档（正常 / 兜底可用 / 真异常）。

> **DEC-01 处理方式（不派生硬阻断）：** 本条按 use-case-model DEC-01 的默认口径落成「信息级、不用高危警告色」，作为**待用户确认的产品决策**，不据其派生「必须无任何提示」或「必须高危警告」的硬性阻断验收。**若用户改判 demo_fallback 为「需关注」**：本条 Then 调整为「demo_fallback 与 stale/unavailable 同归警告色档」，此时 SCN-01-COND-03 的「仅真异常见警告色」口径需同步扩容纳入 demo_fallback，追溯锚点与证据计划不变。改判前后均须与 formal / stale 并置截图对账，不得三档共用同一视觉。

---

### 验收条件 SCN-01-COND-03：来源 stale / unavailable 真异常态出现警告色并标注受影响范围

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-01 |
| 来源系统用例 / 流 | SUC-01 / FLOW-02（节拍 `SUC-01-FLOW-02.stale`、`SUC-01-FLOW-02.unavailable`）；异常流 X |
| 来源规则 / 对象 | BR-02（stale/unavailable = 真异常）；OBJ-02 / STM-02（stale、unavailable）、affectedObjects、degradationReason |
| 可观察结果 | stale / unavailable 态出现警告 / 错误色提示，并呈现降级说明与受影响对象（chart/mts/alerts）范围 |
| 验证证据类型 | 界面状态（preview 截图）+ 界面状态（DOM 断言：警告承载存在且含受影响范围文案） |
| 追溯 | US-01；SCN-01；BR-02；OBJ-02 / STM-02；ATTR-08/09 |

**Given：** 某标的 SourceHealth.status = `stale`（数据陈旧）或 `unavailable`（来源失败 / 无 payload+错误），并带 affectedObjects / degradationReason。

**When：** 用户打开该标的界面。

**Then：** 界面出现警告 / 错误色提示（此为警告色的合法归属），呈现降级原因与受影响范围；warning 承载与「正常态无警告」形成对比，且警告色不外溢到 formal / not_loaded / restored 等正常态。

---

### 验收条件 SCN-01-COND-04：工作台恢复 restored / partial / default_fallback 正常 / 信息态不出现警告色黄条

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-01 |
| 来源系统用例 / 流 | SUC-06 / FLOW-02（节拍 `SUC-06-FLOW-02.restored`、`.partial`、`.default_fallback`）；主成功流 + 备选流 A |
| 来源规则 / 对象 | BR-10；OBJ-06 / STM-07（restored、partial、default_fallback）；BR-11（超限回退 → default_fallback） |
| 可观察结果 | 应用启动读取快照后，restored / partial / default_fallback（含首次 snapshot_missing）态不渲染黄色 `.data-notice` 警告横幅；restored 呈中性 / 成功，partial / default_fallback 呈信息级 |
| 验证证据类型 | 界面状态（preview 截图，逐态）+ 界面状态（DOM 断言：`RestoreStatus` 承载在这三态下无警告类名） |
| 追溯 | US-01；SCN-01；BR-10；OBJ-06 / STM-07；RestoreStatus.tsx:7-21 |

**Given：** 应用启动，restoreMetadata.status = `restored`（快照完好）/ `partial`（旧存储迁移）/ `default_fallback`（缺失 / 损坏 / 超限回退，含首次 snapshot_missing）。

**When：** 用户打开工作台（应用初次渲染顶部恢复状态区）。

**Then：** restored 呈中性 / 成功语义、不显黄条；partial / default_fallback 呈信息级提示、非警告色；恢复原因 / migratedFromLegacy / snapshotBytes 等技术态收进详情，不拼进主提示文案（修正 `RestoreStatus.tsx:8` 对 restored 复用 `.data-notice` 的现状根因）。

---

### 验收条件 SCN-01-COND-05：工作台恢复 failed / 坏布局丢弃需关注态出现警告色

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-01 |
| 来源系统用例 / 流 | SUC-06 / FLOW-02（节拍 `SUC-06-FLOW-02.failed`）；异常流 X |
| 来源规则 / 对象 | BR-10（failed / 坏布局丢弃 = 需关注）；OBJ-06 / STM-07.failed、discardedLayoutKeys |
| 可观察结果 | restoreMetadata.status = failed 或 discardedLayoutKeys 非空时，出现警告 / 需关注提示，且与正常恢复态形成可辨对比 |
| 验证证据类型 | 界面状态（preview 截图）+ 界面状态（DOM 断言：failed 态存在需关注承载） |
| 追溯 | US-01；SCN-01；BR-10；OBJ-06 / STM-07.failed |

**Given：** 应用启动，restoreMetadata.status = `failed`（版本无效等致恢复失败）或 discardedLayoutKeys 非空（坏布局被丢弃）。

**When：** 用户打开工作台。

**Then：** 出现警告 / 需关注提示（警告色的合法归属），呈现「已丢弃坏布局」等需关注明细；与 restored / partial / default_fallback 的中性 / 信息呈现形成物理可辨对比。

---

### 验收条件 SCN-01-COND-06：负向 / 风控评分呈谨慎 / 风险色，且与来源故障警告色物理区分

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-01（与 SCN-02 交界） |
| 来源系统用例 / 流 | SUC-02 / FLOW-02（节拍 `SUC-02-FLOW-02.negative`、`SUC-02-FLOW-02.positive`）；SUC-02 备选流 A |
| 来源规则 / 对象 | BR-04；OBJ-03 / scoreBand（negative/strong_negative）、alertLevel（风控） |
| 可观察结果 | scoreBand negative/strong_negative 或 alertLevel=风控 时，评分 / 提醒呈谨慎 / 风险语义色；该色**不是** stale/unavailable 所用的同一黄色 `.data-notice` 警告横幅，两类色在界面上物理可辨；正向 / 中性评分呈积极 / 中性无色 |
| 验证证据类型 | 界面状态（preview 截图，negative 评分与 stale 来源两态并置对比证明色物理区分）+ 界面状态（DOM 断言：评分承载不复用来源警告横幅类名） |
| 追溯 | US-02；SCN-01；SCN-02 关联；BR-04；OBJ-03；App.tsx:95-97 |

**Given：** 某标的 MtsExplanation.scoreBand = `negative` / `strong_negative`，或 alertLevel = `风控`（技术面看空 / 风险级，属市场业务结论）。

**When：** 用户查看该标的主视图技术提醒区。

**Then：** 评分 / 提醒呈谨慎 / 风险语义色（表达「技术面看空」而非「系统 / 数据故障」）；此色与来源 stale/unavailable 的警告横幅**物理区分**（非同一 `.data-notice` 黄条）；正向 / 中性评分（positive/neutral/not_applicable）呈积极 / 中性无色。用户能区分「市场看空」与「数据故障」两类语义。

---

### 验收条件 SCN-02-COND-01：主视图不直接暴露原始枚举 / 理由代码

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-02 |
| 来源系统用例 / 流 | SUC-02 / FLOW-01；系统操作 SUC-02-OP-01 |
| 来源规则 / 对象 | BR-05；OBJ-03（displayLabel/technicalReminder/中文 alertLevel）、OBJ-07（label/detail） |
| 可观察结果 | 主视图技术提醒区不出现 `trend_state`/`mts_score`/`score_band`/`signal_type`/`alert_level` 裸字段前缀，也不出现 `TREND_ABOVE_EMA` 等理由代码；改为人话文案（复用 displayLabel/technicalReminder/中文 alertLevel/MtsReason.label） |
| 验证证据类型 | 界面状态（DOM 断言：主视图文本不含上述枚举 / 代码 token）+ 界面状态（preview 截图）+ E2E（Playwright 断言主视图渲染文本） |
| 追溯 | US-02；SCN-02；BR-05；OBJ-03/07；App.tsx:651-655 |

**Given：** 某标的有 trendState / mtsScore / scoreBand / signalType / alertLevel 及 reasonCodes（如 TREND_ABOVE_EMA）。

**When：** 用户查看主视图技术提醒区（未展开详情）。

**Then：** 主视图 0 处裸枚举、0 处裸理由代码；呈现人话文案（displayLabel / technicalReminder / 中文 alertLevel / reasons 的 label）；不出现 `trend_state:` 等前缀裸值（修正 `App.tsx:651-655` 现状）。

---

### 验收条件 SCN-02-COND-02：评分以进度条式可读呈现

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-02 |
| 来源系统用例 / 流 | SUC-02 / FLOW-01；系统操作 SUC-02-OP-01 |
| 来源规则 / 对象 | OBJ-03 / mtsScore（ATTR-13）；UIC-02 |
| 可观察结果 | mtsScore 以进度条 / 可视化条呈现（而非仅裸数字），用户可视觉估读评分高低 |
| 验证证据类型 | 界面状态（DOM 断言：存在进度条承载元素）+ 界面状态（preview 截图） |
| 追溯 | US-02；SCN-02；OBJ-03 / ATTR-13；UIC-02 |

**Given：** 某标的 MtsExplanation.mtsScore 为有效数值。

**When：** 用户查看主视图评分区。

**Then：** 评分以进度条式呈现（可视化条 + 可读文案），不以裸数字替代进度条；scoreBand 为 not_applicable / null 时按中性处理，不呈现误导性进度条填充。

---

### 验收条件 SCN-02-COND-03：原始枚举 / 理由代码仅在展开详情 / 调试区可见

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-02 |
| 来源系统用例 / 流 | SUC-02 / FLOW-03（节拍 `SUC-02-FLOW-03.detail`）；备选流 B；系统操作 SUC-02-OP-02 |
| 来源规则 / 对象 | OBJ-03 / reasonCodes、OBJ-07 / code；EXC-03（cache/retry 技术态折叠） |
| 可观察结果 | 原始 trend_state/score_band/signal_type/alert_level 与理由 code / 失效项 / 关注位默认隐藏，仅用户展开详情 / 调试区后可见 |
| 验证证据类型 | E2E（Playwright：默认态断言无原始字段 → 点击展开 → 断言原始字段出现）+ 界面状态（preview 截图，收起 / 展开两态） |
| 追溯 | US-02；SCN-02；OBJ-03/07；EXC-03；App.tsx:641 |

**Given：** 某标的详情区含原始枚举、理由代码、失效项、cache/retry 技术态。

**When：** 用户默认查看（未展开），随后点击展开详情 / 调试区。

**Then：** 默认态不呈现原始字段；展开后详情区显示 code / 枚举 / 失效项 / 关注位；技术态（retryState/cacheState）仅在此折叠区，不外溢主视图（修正 `App.tsx:641` retry 泄漏进 notice）。

---

### 验收条件 SCN-02-COND-04：非 ready 技术 / 交易状态人话化，不裸呈枚举串

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-02 |
| 来源系统用例 / 流 | SUC-02 / FLOW-03（`.data_insufficient`、`.source_degraded`）、SUC-03 / FLOW-03（`.not_target`、`.data_insufficient`、`.source_degraded`） |
| 来源规则 / 对象 | STM-05；BR-03；OBJ-04 / status、OBJ-03 / trendState |
| 可观察结果 | trendState=data_insufficient / source_degraded、TradeSignalState.status=not_target_symbol / data_insufficient / source_degraded 时，呈现人话说明而非裸枚举串 |
| 验证证据类型 | 界面状态（DOM 断言：非 ready 承载文本不含 `not_target_symbol` 等枚举串）+ 界面状态（preview 截图，逐态）+ E2E（Playwright） |
| 追溯 | US-02；SCN-02；STM-05；BR-03；App.tsx:532 |

**Given：** 某标的处于非 ready 态：MTS trendState=`data_insufficient`/`source_degraded`，或 TradeSignalState.status=`not_target_symbol`/`data_insufficient`/`source_degraded`。

**When：** 用户查看技术提醒区 / 交易信号卡。

**Then：** 各非 ready 态呈现对应人话说明（如「数据不足以给出信号」「该标的无定制策略信号」「数据来源降级，暂不给出买卖价位」），0 处裸枚举串（修正 `App.tsx:532` 直呈 status 枚举）；来源降级态不呈现回测块（衔接 NEG-02）。

---

### 验收条件 SCN-03-COND-01：来源状态收敛到唯一权威主源

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-03 |
| 来源系统用例 / 流 | SUC-01 / FLOW-02、SUC-04 / FLOW-02；系统操作 SUC-01-OP-02、SUC-04-OP-01 |
| 来源规则 / 对象 | UIC-03；OBJ-02 / STM-02 |
| 可观察结果 | 来源状态在主区仅保留 1 处权威呈现点；侧栏来源仅作弱化次级信号（小圆点），不构成第二个来源主源 |
| 验证证据类型 | 界面状态（DOM 断言：来源权威承载计数 = 1）+ 界面状态（preview 截图） |
| 追溯 | US-03；SCN-03；UIC-03；OBJ-02 |

**Given：** 改造前来源状态在标题黄条 / 图表角标 / 指标条等 3~5 处重复。

**When：** 用户扫读改造后界面。

**Then：** 来源状态仅 1 处权威呈现点；侧栏来源为弱化小圆点（次级、非主源，见 SCN-06-COND-02）；去重后来源可读性不丢失。

---

### 验收条件 SCN-03-COND-02：价格 / 涨跌收敛唯一主源，涨跌红绿色与来源 / 布局警告色语义分离

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-03 |
| 来源系统用例 / 流 | SUC-01 / FLOW-03；系统操作 SUC-01-OP-02 |
| 来源规则 / 对象 | UIC-03；EXC-01（价格 / 涨跌呈现属性）；DMF-02（主源选点属承载） |
| 可观察结果 | 价格 / 涨跌仅 1 处权威主源；涨跌红绿色不等同于来源 / 布局警告色（红绿 = 涨跌方向，警告色 = 数据 / 布局异常） |
| 验证证据类型 | 界面状态（DOM 断言：价格 / 涨跌权威承载计数 = 1）+ 界面状态（preview 截图，涨跌红绿与警告色并置对比） |
| 追溯 | US-03；SCN-03；UIC-03；EXC-01；DMF-02 |

**Given：** 改造前价格 / 涨跌在多处重复；涨跌红绿色与来源警告色视觉相近。

**When：** 用户扫读界面。

**Then：** 价格 / 涨跌只出现 1 处权威主源（「哪一处」为交互层承载选点，本条只固化「必须唯一」义务）；涨跌红绿色与来源 / 布局警告色语义分离、视觉可辨。

---

### 验收条件 SCN-04-COND-01：标的标题为顶部视觉主位

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-04 |
| 来源系统用例 / 流 | SUC-05 / FLOW-01；系统操作 SUC-05-OP-01 |
| 来源规则 / 对象 | UIC-04；OBJ-01 / name |
| 可观察结果 | 顶部标的标题字号 / 权重最高，为视觉主位，先于操作控件被注意到 |
| 验证证据类型 | 界面状态（preview 截图）+ 界面状态（DOM 断言：标题字号 / 权重高于周期 / 视图控件） |
| 追溯 | US-04；SCN-04；UIC-04；OBJ-01 |

**Given：** 用户打开某标的界面（默认 focus 布局）。

**When：** 用户观察顶部区域。

**Then：** 标的标题以最高字号 / 权重呈现为视觉主位；周期 / 视图控件视觉权重低于标题。

---

### 验收条件 SCN-04-COND-02：周期 / 视图切换控件降级右对齐、切换语义不变

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-04 |
| 来源系统用例 / 流 | SUC-05 / FLOW-01/02；备选流 A |
| 来源规则 / 对象 | UIC-04；OBJ-06 / STM-06（不改切换语义） |
| 可观察结果 | 周期 / 视图（布局模式）控件降一级、右对齐，不与标题抢焦点；切换后标题仍主位、切换功能与语义不减 |
| 验证证据类型 | 界面状态（preview 截图，各布局模式）+ E2E（Playwright：切换周期 / 布局后断言标题仍主位且切换生效） |
| 追溯 | US-04；SCN-04；UIC-04；STM-06 |

**Given：** 顶部含周期切换与视图（dense/focus/mobile_tab）控件。

**When：** 用户观察顶部并操作切换周期 / 布局模式。

**Then：** 控件降级右对齐、不抢标题焦点；切换后布局结构随 STM-06 调整但标题主位不变；切换语义（STM-06 白名单集合）不被改动。

---

### 验收条件 SCN-05-COND-01：主卡突出、次级信息降灰形成明确层级差

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-05 |
| 来源系统用例 / 流 | SUC-03 / FLOW-01；系统操作 SUC-03-OP-01 |
| 来源规则 / 对象 | UIC-05；OBJ-04（stanceLabel / 关键数字）、OBJ-08（回测次级） |
| 可观察结果 | 主卡（建议 stanceLabel + 关键数字）视觉突出；回测 / 理由 / 原始字段为次级灰字，与主卡存在明确视觉层级差 |
| 验证证据类型 | 界面状态（preview 截图，主 / 次层级差可辨）+ 界面状态（DOM 断言：次级容器为降级 / 灰字样式） |
| 追溯 | US-05；SCN-05；UIC-05；OBJ-04/08 |

**Given：** 某标的同时有当前可操作信号（stanceLabel / 关键数字）与回测 / 理由 / 原始字段。

**When：** 用户查看交易信号区。

**Then：** 主卡突出呈现建议与关键数字；回测 / 理由 / 原始字段降为次级灰字；主 / 次视觉层级差明确可辨，不出现回测与主卡权重接近。

---

### 验收条件 SCN-05-COND-02：nonAdvice 免责声明保持可见

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-05 |
| 来源系统用例 / 流 | SUC-03 / FLOW-01/02；系统操作 SUC-03-OP-01 |
| 来源规则 / 对象 | OBJ-04 / nonAdvice（ATTR-29）；UIC-05/UIC-07 |
| 可观察结果 | 信息层级重排与折叠后，nonAdvice 免责声明仍可见，不被降级隐藏 |
| 验证证据类型 | 界面状态（DOM 断言：nonAdvice 文案存在且可见）+ 界面状态（preview 截图） |
| 追溯 | US-05；SCN-05；OBJ-04 / ATTR-29；UIC-05 |

**Given：** 交易信号卡含 nonAdvice 免责声明。

**When：** 用户查看信号卡（默认态与折叠态）。

**Then：** nonAdvice 免责始终可见；层级降级 / 明细折叠均不得隐藏免责（衔接 NEG-05）。

---

### 验收条件 SCN-06-COND-01：侧栏条目名称+代码一行、价格+涨跌右对齐为主看信息

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-06 |
| 来源系统用例 / 流 | SUC-04 / FLOW-01；系统操作 SUC-04-OP-01 |
| 来源规则 / 对象 | UIC-06；OBJ-01（name/symbol）、EXC-01（价格 / 涨跌） |
| 可观察结果 | 侧栏每条以名称+代码为一行、价格+涨跌右对齐为主看数字，结构清晰可快速扫读 |
| 验证证据类型 | 界面状态（preview 截图，含多条自选标的）+ 界面状态（DOM 断言：条目结构含名称+代码行与右对齐价格） |
| 追溯 | US-06；SCN-06；UIC-06；OBJ-01 |

**Given：** 侧栏含多条自选标的（active）。

**When：** 用户扫读侧栏列表。

**Then：** 每条呈现名称+代码一行、价格+涨跌右对齐主看数字；主看信息突出，不与来源状态混排为同级。

---

### 验收条件 SCN-06-COND-02：侧栏来源状态弱化为小圆点、区分正常 / 需关注且不作重复主源

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-06 |
| 来源系统用例 / 流 | SUC-04 / FLOW-02（节拍 `SUC-04-FLOW-02.normal`、`SUC-04-FLOW-02.attention`）；异常流 X |
| 来源规则 / 对象 | UIC-06/UIC-03；OBJ-02 / STM-02；BR-02（弱化上色） |
| 可观察结果 | 条目来源为小圆点弱化次级信号：formal 呈中性圆点、非 formal 呈需关注弱提示圆点；侧栏来源不作为来源状态权威主源（呼应 SCN-03-COND-01） |
| 验证证据类型 | 界面状态（preview 截图，正常 / 需关注两态）+ 界面状态（DOM 断言：来源承载为小圆点、非主源横幅） |
| 追溯 | US-06；SCN-06；SCN-03 关联；UIC-06；BR-02；OBJ-02 |

**Given：** 侧栏条目来源档为 formal 或非 formal（demo_fallback/stale/unavailable）。

**When：** 用户扫读侧栏。

**Then：** 来源弱化为小圆点：formal → 中性圆点，非 formal → 需关注弱提示圆点，均不喧宾夺主；侧栏来源不重复承载为来源主源。

---

### 验收条件 SCN-06-COND-03：归档标的弱化呈现、与 active 区分

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-06 |
| 来源系统用例 / 流 | SUC-04 / 备选流 A（状态 ST-04b） |
| 来源规则 / 对象 | STM-01（active/archived）；OBJ-01 / status |
| 可观察结果 | archived 条目弱化呈现，与 active 条目视觉区分，不作主看强调 |
| 验证证据类型 | 界面状态（preview 截图，含 active 与 archived 条目）+ 界面状态（DOM 断言：archived 条目为弱化样式） |
| 追溯 | US-06；SCN-06；STM-01；OBJ-01 |

**Given：** 侧栏列表同时含 active 与 archived 标的。

**When：** 用户扫读侧栏。

**Then：** archived 条目弱化呈现、与 active 明确区分；不作主看强调（不改归档 / 恢复业务逻辑，仅呈现区分）。

---

### 验收条件 SCN-07-COND-01：交易信号卡默认呈现关键数字

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-07 |
| 来源系统用例 / 流 | SUC-03 / FLOW-01、FLOW-02（节拍 `SUC-03-FLOW-02.collapsed`）；系统操作 SUC-03-OP-01 |
| 来源规则 / 对象 | UIC-07；OBJ-04（stanceLabel/holding）、OBJ-08（winRate/strategyReturnPct） |
| 可观察结果 | ready 态信号卡默认呈现关键数字（stanceLabel / 持仓 / 胜率 / 累计收益），无三段回测流水账铺开 |
| 验证证据类型 | 界面状态（preview 截图，默认态）+ 界面状态（DOM 断言：默认态含关键数字、无回测明细流水） |
| 追溯 | US-07；SCN-07；UIC-07；OBJ-04/08 |

**Given：** 某标的 TradeSignalState.status=ready，有 stanceLabel / holding / 回测关键数字。

**When：** 用户查看交易信号卡（未展开）。

**Then：** 默认呈现关键数字（stanceLabel、持仓中 / 空仓、胜率、累计收益）；三段回测 / 回合流水 / 事件默认不铺开。

---

### 验收条件 SCN-07-COND-02：三段回测明细默认折叠、展开后呈现

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-07 |
| 来源系统用例 / 流 | SUC-03 / FLOW-02（节拍 `SUC-03-FLOW-02.collapsed` → `.expanded`）；备选流 B |
| 来源规则 / 对象 | UIC-07；OBJ-08（trades/rounds）、STM-08（反T回合） |
| 可观察结果 | 三段回测明细 / 反T回合默认折叠；用户展开后才呈现，明细与关键数字不同权重平铺 |
| 验证证据类型 | E2E（Playwright：默认断言明细不可见 → 展开 → 断言明细可见）+ 界面状态（preview 截图，收起 / 展开两态） |
| 追溯 | US-07；SCN-07；UIC-07；OBJ-08；STM-08 |

**Given：** ready 态信号卡含三段回测明细与反T回合。

**When：** 用户默认查看后点击展开明细。

**Then：** 默认态明细折叠、仅关键数字可见；展开后呈现三段回测 / 反T回合明细；明细不与关键数字同权重平铺。

---

### 验收条件 SCN-07-COND-03：仅 ready 呈现回测块，正式信号位与 ATR 观察位分层级

| 项 | 内容 |
|----|------|
| 来源场景 | SCN-07 |
| 来源系统用例 / 流 | SUC-03 / FLOW-02、备选流 B；系统操作 SUC-03-OP-01 |
| 来源规则 / 对象 | BR-07（ready 才有回测）；OBJ-04 / levels（正式信号位 vs ATR 观察位） |
| 可观察结果 | 仅 TradeSignalState.status=ready 时呈现回测块；展开的关键价位区分正式信号位与 ATR 投影观察位两个层级 |
| 验证证据类型 | 界面状态（preview 截图，展开价位层级）+ 界面状态（DOM 断言：非 ready 态无回测块承载） |
| 追溯 | US-07；SCN-05 关联；SCN-07；BR-07；OBJ-04 / levels |

**Given：** 某标的 status=ready（含回测与关键价位），或非 ready（无回测）。

**When：** 用户展开信号卡明细。

**Then：** ready 态呈现回测块与关键价位，且正式信号位与 ATR 观察位分层级区分；非 ready 态不呈现回测块（衔接 NEG-02）。

---

## 负向与边界路径

| 路径 ID | 类型 | 来源系统用例 / 规则 | Given | When | Then | 验证证据 |
|---------|------|--------------------|-------|------|------|----------|
| NEG-01 | 状态限制（跨呈现一致性） | BR-03；操作间依赖 SUC-01-OP-01→SUC-03-OP-02 | 某标的来源 SourceHealth.status 变为 stale/unavailable（非 formal） | 用户查看该标的交易信号卡 | 信号卡须同步降级为 source_degraded 人话说明、不再显 ready 且不给买卖价位；不得出现「来源已 stale 而信号卡仍 ready」的矛盾呈现 | E2E（Playwright：降级来源态下断言信号卡为 source_degraded）+ 界面状态（preview 截图） |
| NEG-02 | 负向 | BR-07 | 某标的 status 非 ready（not_target/data_insufficient/source_degraded） | 用户查看交易信号卡 | 不呈现空回测容器 / 空图表占位误导；呈现对应非 ready 人话说明 | 界面状态（DOM 断言：非 ready 态无回测块 DOM）+ preview 截图 |
| NEG-03 | 状态限制（语义分离） | 操作间依赖 SUC-06-OP-01 vs SUC-01-OP-01（STM-07 vs STM-02） | 恢复态与来源态同时存在（两套独立状态机） | 应用启动后用户观察顶部 | 恢复态与来源态各自归位、不共用同一条黄条；两类语义不混用同一警告承载 | 界面状态（DOM 断言：恢复承载与来源承载为独立元素）+ preview 截图 |
| NEG-04 | 负向（边界） | BR-05 | 某理由 code 未在版本化注册表注册（回落 UNKNOWN_CODE） | 用户查看理由项 | 未注册码不作为有效解释直呈主视图；按 UNKNOWN_CODE 兜底处理，不裸露原始 code | 界面状态（DOM 断言：主视图不含未解析原始 code）+ preview 截图 |
| NEG-05 | 负向 | RC-10；UIC-07 | 交易信号卡明细处于折叠态 | 用户默认查看（明细未展开） | 折叠明细不得隐藏 nonAdvice 免责；免责始终可见 | E2E（Playwright：折叠态断言 nonAdvice 可见）+ preview 截图 |
| NEG-06 | 边界（状态归一化） | STM-06；SUC-05 异常流「不适用」 | 布局模式为非法值（由既有 workspace 归一化处理） | 用户切换 / 加载布局 | 呈现重排不新增失败分支；非法值由既有归一化回退默认 focus，标题主位不变；改造不改 STM-06 归一化逻辑 | 界面状态（preview 截图，各布局模式）+ E2E（Playwright：布局切换后标题仍主位） |
| NEG-07 | 边界（可访问性无回归） | 成功定义 EVD-03；契约 | 改造后主看盘界面（各主要态） | 运行 axe 可访问性扫描 + Playwright E2E 回归 | 改造不引入 axe 可访问性回归、E2E 既有用户路径不回归；build（EVD-01）exit 0 作前提 | axe 扫描结果 + E2E（Playwright）回归 + 命令结果（build EVD-01 前提） |

---

## 验证证据计划

| 验收条件 | 必需证据 | 后续验证阶段 | 不足时处理 |
|--------|----------|--------------|------------|
| SCN-01-COND-01 | formal / not_loaded 态 preview 截图 + DOM 断言（无 `.data-notice` 警告类名） | verify | 截图无法覆盖 not_loaded 初始态时，补 DOM 断言 |
| SCN-01-COND-02 | demo_fallback 与 formal/stale 三档并置 preview 截图 | verify（**先经 DEC-01 用户确认定档**） | **待澄清**：DEC-01 未确认前按默认「信息级」验收；用户改判则按本条 DEC-01 备注调整口径后重验 |
| SCN-01-COND-03 | stale / unavailable 态 preview 截图 + DOM 断言（警告承载 + 受影响范围文案） | verify | 无法构造真 stale 数据时，用 mock/demo 数据触发降级态并截图 |
| SCN-01-COND-04 | restored/partial/default_fallback 逐态 preview 截图 + DOM 断言（无警告类名） | verify | 三态难以自然触发时，构造快照 fixture 分别驱动 |
| SCN-01-COND-05 | failed / 坏布局丢弃态 preview 截图 + DOM 断言（需关注承载） | verify | 构造无效版本 / 坏布局快照 fixture 触发 |
| SCN-01-COND-06 | negative 评分与 stale 来源并置 preview 截图（证色物理区分）+ DOM 断言（评分承载 ≠ 来源警告类名） | verify | 需同屏 / 同批并置对比截图，单态截图不足以证明「区分」 |
| SCN-02-COND-01 | 主视图 DOM 断言（无枚举 / 代码 token）+ preview 截图 + Playwright 文本断言 | verify | — |
| SCN-02-COND-02 | 进度条承载 DOM 断言 + preview 截图 | verify | — |
| SCN-02-COND-03 | Playwright 展开交互（默认无 → 展开有）+ 收起 / 展开截图 | verify | — |
| SCN-02-COND-04 | 非 ready 逐态 DOM 断言（无枚举串）+ preview 截图 + Playwright | verify | 逐态构造数据 fixture |
| SCN-03-COND-01 | 来源权威承载计数 = 1 DOM 断言 + preview 截图 | verify | — |
| SCN-03-COND-02 | 价格 / 涨跌权威承载计数 = 1 DOM 断言 + 涨跌色 vs 警告色并置截图 | verify | — |
| SCN-04-COND-01 | 标题 vs 控件字号 / 权重 DOM 断言 + preview 截图 | verify | — |
| SCN-04-COND-02 | 各布局模式 preview 截图 + Playwright（切换后标题仍主位 + 切换生效） | verify | — |
| SCN-05-COND-01 | 主 / 次层级差 preview 截图 + 次级样式 DOM 断言 | verify | 层级差含主观性，以截图 + 样式断言双证据锚定 |
| SCN-05-COND-02 | nonAdvice 可见 DOM 断言 + preview 截图 | verify | — |
| SCN-06-COND-01 | 侧栏条目结构 preview 截图 + DOM 断言 | verify | — |
| SCN-06-COND-02 | 正常 / 需关注小圆点 preview 截图 + 来源承载 DOM 断言 | verify | — |
| SCN-06-COND-03 | active / archived 并置 preview 截图 + archived 弱化样式 DOM 断言 | verify | — |
| SCN-07-COND-01 | 默认态 preview 截图 + 关键数字 / 无流水 DOM 断言 | verify | — |
| SCN-07-COND-02 | Playwright 折叠 / 展开交互 + 两态截图 | verify | — |
| SCN-07-COND-03 | 展开价位层级 preview 截图 + 非 ready 无回测块 DOM 断言 | verify | — |
| NEG-01~NEG-07 | 见「负向与边界路径」表各行证据列 | verify | axe / E2E 回归以既有 tests/e2e 与 axe 集成为准；build 仅作前提 |

---

## 追溯关系

| 任务契约 / 用户故事 | 业务用例 | 系统用例 | 业务对象 / 规则 | 场景 | 验收条件 | 证据类型 |
|----------------------|----------|----------|----------------|------|--------|----------|
| US-01 / 契约 SCN-01 | BUC-01、BUC-03 | SUC-01、SUC-06、SUC-02 | OBJ-02/06/03；STM-02/07；BR-02/04/10 | SCN-01 | SCN-01-COND-01/02/03/04/05/06 | 界面状态（截图 + DOM）；DEC-01 条待用户确认 |
| US-02 / 契约 SCN-02 | BUC-01 | SUC-02、SUC-03 | OBJ-03/07/04；STM-05；BR-04/05 | SCN-02 | SCN-02-COND-01/02/03/04 | 界面状态 + E2E（Playthrough） |
| US-03 / 契约 SCN-03 | BUC-01、BUC-02 | SUC-01、SUC-04、SUC-05 | OBJ-02、EXC-01；UIC-03 | SCN-03 | SCN-03-COND-01/02 | 界面状态（DOM 计数 + 截图） |
| US-04 / 契约 SCN-04 | BUC-01、BUC-02 | SUC-05 | OBJ-01/06；STM-06 | SCN-04 | SCN-04-COND-01/02 | 界面状态 + E2E |
| US-05 / 契约 SCN-05 | BUC-01 | SUC-03 | OBJ-04/08；nonAdvice | SCN-05 | SCN-05-COND-01/02 | 界面状态（截图 + DOM） |
| US-06 / 契约 SCN-06 | BUC-02 | SUC-04 | OBJ-01/02；STM-01；BR-02 | SCN-06 | SCN-06-COND-01/02/03 | 界面状态（截图 + DOM） |
| US-07 / 契约 SCN-07 | BUC-01 | SUC-03 | OBJ-04/08；STM-05/08；BR-07 | SCN-07 | SCN-07-COND-01/02/03 | 界面状态 + E2E |
| 成功定义 EVD-03 / 约束 | BUC-01/02/03 | SUC-01~06 | BR-03/07；STM-02/05/06/07 | 全场景 | NEG-01~NEG-07 | E2E（Playwright）+ axe + build（EVD-01 前提） |

---

## 不得派生验收条件的内容

| 内容 | 来源 | 为什么不能派生验收条件 | 处理方式 |
|------|------|----------------------|----------|
| demo_fallback 的最终色档「必须无提示」或「必须高危警告」 | DEC-01（use-case-model 待澄清系统责任） | 属待用户确认的产品决策，源码现状（App.tsx:639 与真异常同级）与 intent-framing（未点名 demo_fallback）证据不一致，硬定档会误导 | 用户决策：SCN-01-COND-02 只落「默认信息级、不用高危警告色」软口径 + 改判备选说明，不阻断；最终档 DEC-01 确认后定 |
| 具体色值 / 字号 / 间距 / 灰度 / 折叠动效数值 | use-case-model 验收推导提示「不能从本用例推导的内容」 | 属交互 / 视觉方案层的样式设计，非领域承载义务；PRD 只定「必须承载什么语义」 | 交互 / 技术分析阶段决定；本文只固化「主位 / 弱化 / 区分 / 层级差」的可观察义务 |
| 价格 / 涨跌 / 来源「主源在哪一处」的最终选点 | DMF-02；UIC-03 | 属承载选点决策（交互层），不影响「必须唯一」义务 | 交互阶段消费 UIC-03 时决定；SCN-03 只固化「计数 = 1」 |
| MTS / 交易信号 / 回测算法结果本身的正确性 | 契约范围外；EXC-05 | 本任务只改呈现、不改算法 / 数据 / 状态机，算法正确性不在本次验收范围 | 明确排除；呈现忠实承载既有计算结论即可 |
| 新增 MTS 状态机 / 新业务规则 | DMF-01；EXC-05 | MTS 极性 / 档位是「计算分类」（BR-04/05 治理），非生命周期状态；任务不授权新增业务语义 | 回流用例建模已定论；本文只引用 BR-04/05 分色 / 人话化，不虚构 STM |
| 提醒管理（OBJ-05）/ 添加流程校验（OBJ-09）相关验收 | 契约范围内清单 + EXC-06 | 不在 7 类改造锚定的主看盘扫读路径 | 明确排除，除非用户扩范围（触发 scope_change 升级） |

---

> **总结说明**：本文共 7 个验收场景（SCN-01~07，对齐契约）、22 条验收条件、7 条负向 / 边界路径。SCN-01「状态色语义」按 use-case-model fan-out token 拆为 6 条结局条件（来源 formal/not_loaded、demo_fallback、stale/unavailable，恢复 restored/partial/default_fallback、failed/坏布局丢弃，评分 negative/风控与来源故障色物理区分）。每条验收条件均含 Given/When/Then、可观察结果、验证证据类型与上游追溯，且均引用已确认 SUC 流 / 结局节拍或业务规则。demo_fallback（DEC-01）按默认「信息级、不用高危警告色」软口径处理并标注待用户确认，未派生硬性阻断验收；给出改判为「需关注」时的口径调整备选。整体不发起 NEEDS_DECISION。
