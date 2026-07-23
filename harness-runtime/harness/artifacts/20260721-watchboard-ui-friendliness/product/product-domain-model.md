# 产品领域模型（Product Domain Model）：多市场看盘终端（MyInvestment）界面友好化改造

> **来源**：prd 技能 → `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/product/product-domain-model.md`
> **用途**：按 DDD 方法沉淀产品领域模型。本文定义业务语义、边界、规则、状态和行为契约，不定义存储结构、接口协议、框架、缓存中间件、消息中间件或部署方案。

**任务编号（mission-id）：** 20260721-watchboard-ui-friendliness
**状态：** `draft`

> **本任务的 DDD 适用性说明**：本任务是**呈现层友好化改造**，唯一主参与者 ACT-01 看盘用户为**只读观察者**，本任务范围内**无任何写入命令、无用户触发的状态迁移**。因此写侧战术要素（领域命令 / 领域事件 / 写一致性聚合边界 / 权限分层）大多标注为不适用并附原因。需下游保留的领域语义是：限界上下文与只读语义边界、统一语言（内部枚举 → 人话映射）、既有状态机（只读呈现）、业务规则作为呈现不变量、以及领域状态到呈现语义的四档映射。全部要素从既有实现抽取，非本任务新增。
>
> 若某个 DDD 要素不适用，必须写明 `不适用：原因...`，不得留空。本文对写侧要素逐项标注原因。

---

## 控制契约

- 控制契约（程序识别标记：Control Contract: `contracts/prd.contract.yaml`）
- 权威来源：外部 YAML 是程序化权威来源；本文件提供产品领域模型解释。

---

## Domain Intent

> 领域意图：本任务要稳定的业务问题、产品能力、非目标与建模深度。

| 项 | 内容 | 追溯 |
|----|------|------|
| 业务问题 | 看盘界面把既有领域状态误导性 / 泄漏式呈现（正常态染警告色、内部枚举裸呈、信息重复、层级缺失），抬高扫读认知成本 | REQ-WATCHBOARD-UI-FRIENDLINESS；US-01~US-07 |
| 产品能力 | 呈现层忠实、无误导地承载既有领域对象与状态（watchboard-presentation 差量能力） | SCN-01~SCN-07；watchboard-presentation spec |
| 非目标 | 不改既有领域计算 / 状态机语义、不改数据与后端、不新增业务功能 / 规则 / 状态机、不触 alibaba 在途策略代码 | SCOPE-11~SCOPE-16；EXC-05 |
| 建模深度 | standard（标准）——核心对象 / 状态机 / 规则须建到「被验收逐条引用即可对上」的颗粒；写侧聚合 / 命令 / 事件退化。不适用：原因是本任务无写入命令，故写侧要素只读化 | 呈现型只读任务；风险按 mission 治理 medium |

---

## Product Semantics Core Model（产品语义核心模型）

> 业务对象说明「业务上有什么」，状态机说明「它如何变化」，用例说明「谁在什么目标下观察这些状态」。本任务用户只观察不触发迁移。

| 核心模型 | 来源 | 本阶段结论 | 下游必须保留 |
|----------|------|------------|--------------|
| 业务对象 | `business-object-analysis.md` | OBJ-01 WatchSymbol、OBJ-02 SourceHealth、OBJ-03 MtsExplanation、OBJ-04 TradeSignalState、OBJ-06 WorkspaceLayout/RestoreMetadata、OBJ-07 MtsReason、OBJ-08 回测/反T（OBJ-05 提醒、OBJ-09 添加预览为范围外候选，仅登记） | 对象身份与语义不变；界面忠实承载，不泄漏内部编码 |
| 状态机 | `business-object-analysis.md` + `use-case-model.md 领域模型反馈` | STM-01（active/archived）、STM-02（来源五态）、STM-05（信号 status+stance）、STM-06（布局模式）、STM-07（恢复四态）、STM-08（反T阶段）——均只读呈现；STM-03/04（提醒）范围外 | 状态集合与迁移语义不变；呈现层只读结果，不驱动迁移 |
| 用例覆盖 | `use-case-model.md` + `acceptance-scenarios.md` | SUC-01~SUC-06 全覆盖 BUC-01~BUC-03，映射 SCN-01~SCN-07；全为只读观察用例 | 用例为呈现型只读；不得改写为新增系统行为 |
| 业务规则 | `business-object-analysis.md` + `acceptance-scenarios.md` | BR-02/03/04/05/07/10/11 作为呈现不变量 INV-01~INV-07；BR-01/06/08/09/12 关联范围外对象 | 规则语义不变；界面呈现须与规则分类一致 |

### Domain Model Feedback Handling（领域模型反馈处理）

| 反馈 ID | 来源 | 处理结论 | 写入的领域元素 | 未采纳原因 / 风险 |
|---------|------|----------|----------------|-------------------|
| DMF-01 | `use-case-model.md` | 已采纳 | 统一语言「MTS 计算分类」条目 + INV-03；明确 scoreBand/trendState/signalType/alertLevel 是每次观测重算的计算分类结论，非生命周期状态，不新建状态机 | 无新增状态机风险：原因是若下游误建 MTS 状态机会范围溢出，已在统一语言与非目标显式禁止 |
| DMF-02 | `use-case-model.md` | 已采纳 | 统一语言「唯一主源」条目 + INV-05；价格/涨跌是呈现属性（EXC-01），主源选点属承载（交互层），产品阶段只固化「计数=1」 | 无新增对象风险：原因是不把价格/涨跌建为独立对象；主源选点不派生验收 |

---

## Strategic DDD

*战略领域建模。*

### 领域 / 子域（Domains / Subdomains）

| 类型 | 名称 | 存在原因 | 核心 / 支撑 / 通用 | 追溯 |
|------|------|----------|--------------------|------|
| 领域 | 多市场看盘（Market Watchboard） | 让用户盯多市场自选股、判断技术面与可操作信号 | 核心 | REQ-WATCHBOARD-UI-FRIENDLINESS |
| 子域 | 看盘界面呈现（Watchboard Presentation） | 把既有领域状态忠实、无误导地呈现给只读用户——本任务作用子域 | 支撑 | watchboard-presentation spec |
| 子域 | 技术信号计算（MTS / 交易信号 / 回测） | 计算领域状态（既有，本任务不改） | 核心（本任务范围外） | SCOPE-11；EXC-05 |
| 子域 | 工作台布局与快照恢复 | 布局偏好与快照恢复（既有，本任务只呈现恢复态） | 支撑 | OBJ-06；SCOPE-12 |

### Bounded Contexts

*限界上下文：本任务作用于呈现上下文，只读消费领域计算上下文。*

| 上下文 ID | 上下文名称 | 责任 | 上下文内语言 | 边界之外 |
|-----------|------------|------|--------------|----------|
| BC-01 | 看盘界面呈现上下文（本任务作用域） | 读取既有领域状态并映射为界面呈现语义（色档 / 人话 / 进度条 / 层级 / 折叠 / 去重复 / 一致性） | 呈现色语义档（正常 / 信息 / 谨慎-风险 / 警告-异常）、人话文案、进度条评分、唯一主源、小圆点弱化、主卡层级差 | 不拥有领域状态计算、状态迁移、数据读写；不拥有页面结构与呈现样式取值（交互层） |
| BC-02 | 领域计算上下文（既有，只被读取） | 计算来源健康 / MTS / 交易信号 / 回测 / 恢复态 | trendState/scoreBand/signalType/alertLevel/status/stance/restoreMetadata 等内部枚举 | 本任务不改；BC-01 仅只读消费其输出 |

### Context Map

*上下文映射：呈现上下文以只读防腐关系消费领域计算上下文。*

| 上游上下文 | 关系 | 下游上下文 | 契约 / 翻译规则 | 风险 |
|-----------|------|-----------|-----------------|------|
| BC-02 领域计算 | Conformist / 防腐层（只读 + 翻译） | BC-01 界面呈现 | BC-01 忠实读取 BC-02 输出的枚举 / 状态，经统一语言映射为人话与呈现色语义；内部枚举 / 理由代码 / 技术态不外溢主视图（收进折叠详情）；不反向影响 BC-02 | 若 BC-01 把内部枚举当展示文案直呈（现状缺陷），泄漏内部编码、抬高理解门槛（SCN-02） |

### Ubiquitous Language

*统一语言：本上下文核心术语与禁止混淆含义。*

| 术语 | 本上下文定义 | 禁止混淆的含义 | 来源 |
|------|--------------|----------------|------|
| 呈现色语义档 | 界面据领域状态映射的四档语义：正常（中性/成功）/ 信息（次级提示）/ 谨慎-风险（市场看空业务结论）/ 警告-异常（数据或恢复故障） | 不得把「市场看空（负向评分）」与「数据/恢复故障」共用同一告警色；不得把「涨跌红绿」等同「警告色」 | BR-02/04/10；领域状态→呈现语义映射 |
| 来源健康档 | not_loaded/formal（正常）、demo_fallback（降级可用 / 信息级，DEC-01）、stale/unavailable（真异常） | 不得把 formal/not_loaded 或 demo_fallback 当真异常上色 | BR-02；STM-02 |
| MTS 计算分类 | scoreBand/trendState/signalType/alertLevel 是每次观测重算的计算分类结论（受 BR-04/05 治理），非生命周期状态 | 不得为 MTS 新建状态机；不得把 negative 计算结论当系统异常（DMF-01） | DMF-01；BR-04 |
| 人话文案源 | 既有可读串：displayLabel/technicalReminder/中文 alertLevel/stanceLabel/sourceStatusLabel/MtsReason.label/detail | 不得把原始枚举 / 理由代码当展示文案直呈；不得新建重复映射 | ATTR-16/19/24；OBJ-07 |
| 唯一主源 | 某信息（来源状态、价格/涨跌）在界面仅 1 处权威呈现点（计数=1）；侧栏来源为弱化次级信号非主源 | 不得在多处重复同一信息为同级主源 | DMF-02；UIC-03 |
| 恢复态 | restored/partial/default_fallback（正常/信息）、failed/坏布局丢弃（需关注）；与来源态是两套独立状态机 | 不得把 restored 正常态染警告黄条；不得与来源黄条共用同一承载 | BR-10；STM-07；NEG-03 |

### 能力边界（Capability Boundaries）

| 能力 ID | 能力 | 新增 / 变更 / 移除 / 复用 | 边界规则 | 追溯 |
|---------|------|---------------------------|----------|------|
| CAP-01 | 看盘界面呈现忠实性（状态色 / 人话 / 去重复 / 层级 / 密度 / 一致性） | 新增（watchboard-presentation 差量能力，draft） | 只读映射既有状态；改动限于界面呈现层 | SCN-01~SCN-07；spec |
| CAP-02 | 自选 / 工作台 / 信号功能行为 | 复用（不变） | 既有 local-stock-watch-workbench 能力不改；呈现改造不破坏其功能场景 | KE-06；NEG-07 |
| CAP-03 | 领域状态计算（来源健康 / MTS / 交易信号 / 回测 / 恢复判定） | 复用（不变） | 不改既有领域计算逻辑与状态机 | SCOPE-11；EXC-05 |

---

## Tactical DDD

*战术领域建模。*

### 参与者（Actors）

| 参与者 ID | 参与者 / 角色 | 目标 | 允许访问的上下文 |
|-----------|--------------|------|------------------|
| ACT-01 | 看盘用户 | 只读扫读某标的当前状态与可操作信号、在自选列表定位标的 | BC-01（只读观察，可展开 / 收起详情、切换标的 / 周期 / 布局） |
| ACT-02 | 系统数据管道 / 领域计算引擎 | 每次观测重算领域状态（既有） | BC-02（本任务不改） |
| ACT-03 | 快照存储（浏览器本地存储） | 提供布局快照读取、产出恢复态元数据（既有） | BC-02（本任务只呈现结果） |
| ACT-04 | 外部行情数据源 | 提供行情、决定来源健康档（既有） | BC-02（本任务范围外） |

### Aggregates

*聚合：本呈现型任务无写一致性边界。*

不适用：原因是本任务为呈现层只读改造，用户不产生任何领域写操作，聚合作为「写一致性边界」在本任务不成立。既有领域对象（OBJ-01~OBJ-08）的一致性由 BC-02 领域计算上下文维护，BC-01 仅只读消费；跨呈现一致性（来源态 ↔ 信号态 ↔ 恢复态）以呈现不变量 INV-05/INV-07 表达，而非写聚合边界。

| 聚合 ID | 聚合 | 聚合根 | 一致性边界 | 负责的不变量 |
|---------|------|--------|------------|--------------|
| 不适用 | 不适用：原因是呈现层只读、无写一致性边界 | 不适用：原因同上，无写聚合根 | 不适用：原因同上；跨呈现一致性以 INV-05/INV-07 表达 | INV-05；INV-07 |

### 实体（Entities）

| 实体 ID | 实体 | 身份标识 | 生命周期 | 所属聚合 |
|---------|------|----------|----------|----------|
| ENT-01 | WatchSymbol（OBJ-01） | symbol（归一化代码，业务身份）；id（技术标识） | active↔archived（STM-01，既有；本任务只呈现区分） | 不适用：原因是本任务无写聚合，一致性由 BC-02 维护 |

> 说明：OBJ-02/03/04/06/07/08 依附选中标的、无独立跨会话身份或为计算派生，作为被观察的领域状态建模，本任务不新增 / 不修改任何实体身份或生命周期。

### 值对象（Value Objects）

| 值对象 ID | 值对象 | 属性 | 相等性 / 校验规则 | 使用方 |
|-----------|--------|------|-------------------|--------|
| VO-01 | 呈现色语义档（Presentation Tone） | tone ∈ {正常, 信息, 谨慎-风险, 警告-异常} | 由领域状态经 BR-02/04/10 映射得出；同状态同档（呈现幂等） | BC-01 呈现层（UIC-01） |
| VO-02 | 人话文案（Humanized Label） | 复用既有 label/displayLabel/stanceLabel/中文 alertLevel/detail | 优先复用既有源；未注册理由码回落 UNKNOWN_CODE（BR-05） | BC-01 呈现层（UIC-02） |
| VO-03 | 可读评分（Readable Score） | mtsScore 数值 + 进度条可视化；not_applicable/null 按中性 | not_applicable/null 不呈现误导性满条 | BC-01 呈现层（UIC-02，SCN-02 评分可读） |

### Domain Commands

*领域命令：本呈现型任务无用户领域写命令。*

不适用：原因是本任务范围内 ACT-01 为只读观察者，不产生任何领域写命令。用户的「展开 / 收起详情、切换标的 / 周期 / 布局」是纯呈现交互，不写领域状态（布局切换语义 STM-06 由既有逻辑处理，本任务不改）。既有写命令（添加 / 归档 / 恢复标的、提醒管理）属范围外对象，本任务不触碰。

| 命令 ID | 命令 | 参与者 / 系统 | 目标聚合 | 前置条件 | 结果 |
|---------|------|---------------|----------|----------|------|
| 不适用 | 不适用：原因是呈现层只读、无领域写命令 | ACT-01（只读） | 不适用：原因同上，无写聚合 | 不适用：原因同上 | 不适用：原因同上 |

### Domain Events

*领域事件：本任务不产生领域事件。*

不适用：原因是本任务无领域写入，故无本任务产生的领域事件。既有领域状态变化（观测重算、快照恢复）由 BC-02 / ACT-02 / ACT-03 产生，BC-01 只读呈现其结果，不消费 / 不发布领域事件。

| 事件 ID | 事件 | 产生方 | 业务含义 | 消费方 / 后续动作 |
|---------|------|--------|----------|-------------------|
| 不适用 | 不适用：原因是呈现层只读、不产生领域事件 | 不适用：原因同上 | 不适用：原因同上 | BC-01 只读呈现既有状态结果 |

### Invariants

> 本任务的不变量是呈现不变量——界面呈现必须始终满足的忠实性约束（由既有 BR 派生），下游不得违反，均可被验收逐条对上。

| 不变量 ID | 不变量 | 上下文 | 保护的呈现映射 | 失败行为 | 追溯 |
|-----------|--------|--------|----------------|----------|------|
| INV-01 | 正常态（来源 formal/not_loaded、恢复 restored/partial/default_fallback、评分 positive/neutral）呈现 0 处警告色 | BC-01 | SUC-01/06/02 只读映射 | 呈现层若染警告色 → SCN-01 失败，回退现状缺陷 | BR-02/10/04；SCN-01-COND-01；SCN-01-COND-04；RULE-01；RULE-02 |
| INV-02 | 真异常态（来源 stale/unavailable、恢复 failed/坏布局丢弃）呈警告色 + 受影响范围 | BC-01 | SUC-01/06 只读映射 | 漏报异常 → 用户误信坏数据 | BR-02/10；SCN-01；RULE-01；RULE-02 |
| INV-03 | 负向 / 风控评分呈谨慎-风险色，且与来源故障警告色物理区分（承载不复用同一类名） | BC-01 | SUC-02 只读映射 | 共用告警色 → 误判「技术看空=数据故障」 | BR-04；DMF-01；SCN-01-COND-06；RULE-03 |
| INV-04 | 主视图 0 处裸枚举 / 裸理由代码；原始字段 / 技术态收进折叠详情；未注册码不直呈 | BC-01 | SUC-02/03 只读映射 | 泄漏内部编码 → 抬高理解门槛（SCN-02） | BR-05；EXC-03；SCN-02-COND-01；SCN-02-COND-04；RULE-04 |
| INV-05 | 来源状态、价格 / 涨跌各 1 处权威主源（计数=1）；涨跌红绿 ≠ 警告色 | BC-01 | SUC-01/04 只读映射 | 重复呈现 → 扫读噪音（SCN-03） | UIC-03；DMF-02；SCN-03；SCN-03-COND-01 |
| INV-06 | nonAdvice 免责始终可见，层级降级 / 折叠不隐藏 | BC-01 | SUC-03 只读映射 | 隐藏免责 → 触碰投资边界（PIT-003） | ATTR-29；SCN-05-COND-02；NEG-05；RULE-09 |
| INV-07 | 跨呈现一致性：来源 stale/unavailable 时信号卡同步 source_degraded、不显 ready；恢复态与来源态各自独立黄条不混用 | BC-01 | SUC-01→SUC-03、SUC-06↔SUC-01 只读映射 | 矛盾呈现（来源 stale 而信号 ready）误导操作 | BR-03；NEG-01；NEG-03；RULE-05 |

### Policies（策略）

| 策略 ID | 策略 | 触发条件 | 决策输入 | 结果 | 追溯 |
|---------|------|----------|----------|------|------|
| POL-01 | 领域状态 → 呈现色语义档映射（四档） | 每次呈现某标的状态 | OBJ-02 来源档 / OBJ-03 评分极性 / OBJ-06 恢复态 | 映射为 VO-01 呈现色语义档 | BR-02/04/10；INV-01~INV-03 |
| POL-02 | 内部枚举 / 理由代码 → 人话文案翻译 | 呈现 MTS / 交易信号 / 非 ready 态 | OBJ-03/07/04 枚举 + 既有可读源 | 映射为 VO-02 人话文案；原始字段收折叠；未注册码回落 UNKNOWN_CODE | BR-05；INV-04 |
| POL-03 | 跨呈现一致性只读同步 | 来源态变化时呈现 MTS / 信号 / 恢复 | STM-02/05/07 只读结果（BR-03 已在既有领域层门控） | 三处呈现保持一致，不在呈现层重实现门控 | BR-03；INV-07 |

> 以上策略是呈现映射策略（领域状态如何被翻译成界面语义），不是写侧领域策略，不产生领域事件 / 命令。

### 领域服务（Domain Services）

不适用：原因是本任务无跨实体的领域写入协调，无需领域服务。呈现映射（POL-01~POL-03）由 BC-01 呈现层执行，属只读翻译，不是领域计算服务（领域计算属 BC-02，本任务不改）。

### State Machines

> 全部为既有状态机，本任务只读呈现其状态，不驱动迁移、不改迁移语义。仅列入被本轮验收引用的状态机。

| 状态机 ID | 实体 / 聚合 | 起始状态（From State） | 目标状态（To State） | 触发（Trigger）命令 / 事件 | 参与者（Actor） | 前置条件（Preconditions） / 守卫 | 迁移动作 / 业务结果 | 终态 | 非法迁移（Invalid Transitions） | 追溯 |
|-----------|------------|----------------------|--------------------|-----------------------------|----------------|----------------------------------|---------------------|------|--------------------------------|------|
| STM-01 | WatchSymbol | active | archived | 归档（既有，本任务不触发） | ACT-01（既有写侧，范围外） | 恢复目标须在自选 | 归档非物理删除 | archived 非终态可恢复 | 重复添加 active 被拒 | SCN-06-COND-03；RULE-07 |
| STM-02 | SourceHealth | not_loaded | formal/demo_fallback/stale/unavailable | 加载 / 刷新 / 重试 / 错误（ACT-02/04 既有） | ACT-02 | 有 payload 才判健康档 | 每次数据加载重算 | 随刷新循环 | not_loaded/formal 不当异常上色 | SCN-01-COND-01；SCN-01-COND-02；INV-01；INV-02 |
| STM-05 | TradeSignalState | 观测 | not_target_symbol/source_degraded/data_insufficient/ready(+stance) | 观测重算（ACT-02 既有） | ACT-02 | 门控顺序：非策略→来源→数据 | 每次观测重判 | 每次观测重判 | 门控优先级固定 | SCN-02-COND-04；SCN-07-COND-01；INV-04；INV-07 |
| STM-06 | WorkspaceLayout | focus | dense/mobile_tab（互切） | 用户切换布局（既有逻辑处理） | ACT-01 | 仅白名单值合法 | 呈现结构调整，标题主位不变 | 无 | 非法值归一化回退 focus | SCN-04-COND-02；NEG-06；RULE-08 |
| STM-07 | WorkspaceRestoreMetadata | 读取快照 | restored/partial/default_fallback/failed | 启动读取快照（ACT-03 既有） | ACT-03 | 读取时一次性判定 | 本次会话恢复结果固定 | 是（会话内固定） | 超上限回退 default_fallback（BR-11） | SCN-01-COND-04；INV-01；INV-02 |
| STM-08 | FanTState | full | reduced（互切） | 高卖 / 买回触发（既有计算） | ACT-02 | 仅震荡回归型标的且 ready | 反T仓位阶段 | 无 | 未配置 / 数据不足则停用 | SCN-07-COND-03；INV-04 |

> STM-03（提醒激活）、STM-04（提醒触发）不列入。不适用：原因是二者关联 OBJ-05 提醒管理，属范围外（SCOPE-16），不被本轮验收引用。MtsExplanation 极性 / 档位不建状态机。不适用：原因是它是计算分类而非生命周期状态（DMF-01）。

---

## Rules & Constraints

*规则与约束。*

### Permission Matrix

*权限矩阵：本任务退化为唯一只读参与者。*

| 参与者（Actor） | 命令（Command） | 目标聚合 / 实体 | 状态（State） | 是否允许（Allowed） | 原因（Reason） / 规则 | 是否需要审计 |
|-----------------|-----------------|-----------------|---------------|---------------------|------------------------|--------------|
| ACT-01 看盘用户 | 只读观察（无写命令） | 全部被呈现的领域状态 | 任意 | 是（只读） | 原因是本任务范围内 ACT-01 无写权限，唯一只读参与者、无角色分级 | 否 |

> 权限矩阵在本任务退化为唯一只读参与者。不适用：原因是无写入命令、无用户触发的状态迁移，故无权限分层、无写权限校验；既有写侧操作（添加 / 归档 / 恢复、提醒管理）属范围外对象，其权限不在本任务重定义。

### 异常 / 补偿 / 幂等（Exceptions / Compensation / Idempotency）

| 场景 ID | 场景 | 触发条件 | 期望处理 | 幂等 / 冲突规则 | 追溯 |
|---------|------|----------|----------|-----------------|------|
| EXC-01 | 来源真异常呈现 | STM-02=stale/unavailable | 呈警告色 + 降级说明 + 受影响范围 | 呈现幂等（同档同呈现）；来源恢复 formal 后重新输出 | INV-02；SCN-01 |
| EXC-02 | 非 ready 交易信号呈现 | STM-05=not_target/data_insufficient/source_degraded | 各态人话化说明，无裸枚举；source_degraded 无回测块 | 来源恢复 formal 后重回 ready 呈现 | INV-04；INV-07；SCN-02-COND-04；NEG-02 |
| EXC-03 | 未注册理由码 | 理由码未在版本化注册表 | 回落 UNKNOWN_CODE，不作有效解释直呈主视图 | 幂等回落 | INV-04；BR-05；NEG-04 |
| EXC-04 | 恢复失败 / 坏布局 | STM-07=failed 或 discardedLayoutKeys 非空 | 呈警告 / 需关注 + 「已丢弃坏布局」明细 | 会话内恢复结果固定 | INV-02；SCN-01-COND-04 关联异常态 |
| EXC-05 | 布局非法值 | 布局 mode 非白名单 | 由既有归一化回退 focus，标题主位不变；呈现不新增失败分支 | 既有归一化幂等 | RULE-08；NEG-06 |

### 合规 / 安全 / 审计（Compliance / Safety / Audit）

| 规则 ID | 规则 | 适用对象 | 证据 / 审计要求 | 追溯 |
|---------|------|----------|-----------------|------|
| AUD-01 | 投资信号提醒边界：强买卖 / 评分 / 信号呈现须保留「提醒 / 技术分析」边界，nonAdvice 免责始终可见 | OBJ-04 交易信号呈现 | nonAdvice 在默认态与折叠态可见（结构断言） | INV-06；PIT-003；CODE-003；SCN-05-COND-01；SCN-05-COND-02；NEG-05 |
| AUD-02 | 数据真实性：demo_fallback（演示 / 兜底数据）呈现须让用户识别、不伪装真实行情 | OBJ-02 demo_fallback 态 | 三档并置截图可辨识兜底数据（最终色档 DEC-01 待确认） | PIT-001；CODE-003；SCN-01-COND-02 |

---

## Traceability

> 把 product-definition.md 出现的每个需求 / 场景 ID 追溯到具体领域元素（OBJ / STM / BR / INV / POL / VO / AUD / UIC）。

| 产品需求 / 场景 ID | 领域元素 | 元素类型 | 覆盖原因 |
|--------------------|----------|----------|----------|
| REQ-WATCHBOARD-UI-FRIENDLINESS | CAP-01；BC-01；INV-01~INV-07 | Capability / BoundedContext / Invariant | 呈现忠实性能力由呈现上下文承载，7 类改造点落成 7 条呈现不变量 |
| US-01 | INV-01；INV-02；POL-01；STM-02；STM-07 | Invariant / Policy / StateMachine | 正常态无警告色、真异常见警告色（来源与恢复状态映射四档色） |
| US-02 | INV-03；INV-04；POL-02；VO-02；VO-03 | Invariant / Policy / ValueObject | 人话化 + 进度条 + 负向评分分色 |
| US-03 | INV-05；POL-01 | Invariant / Policy | 来源 / 价格唯一主源、涨跌色与警告色分离 |
| US-04 | STM-06；EXC-05 | StateMachine / Exception | 标题主位 + 控件降级，切换语义不变、非法值归一化 |
| US-05 | INV-06；OBJ-04；OBJ-08 | Invariant / BusinessObject | 主卡层级差 + 免责可见 |
| US-06 | STM-01；INV-05；OBJ-01；OBJ-02 | StateMachine / Invariant | 侧栏主看突出 + 来源弱化非主源 + archived 区分 |
| US-07 | INV-04；STM-05；STM-08；BR-07 | Invariant / StateMachine / BusinessRule | 关键数字 + 明细折叠 + 仅 ready 有回测 |
| SCN-01 | INV-01；INV-02；INV-03；POL-01；STM-02；STM-07 | Invariant / Policy / StateMachine | 状态色语义：正常无警告、真异常见警告、看空与故障分色 |
| SCN-01-COND-01 | INV-01；STM-02（formal/not_loaded） | Invariant / StateMachine | 来源正常态 0 处警告色 |
| SCN-01-COND-02 | AUD-02；STM-02（demo_fallback）；VO-01 | Audit / StateMachine / ValueObject | demo_fallback 信息级、可辨识兜底数据（DEC-01 默认档） |
| SCN-01-COND-04 | INV-01；STM-07（restored/partial/default_fallback） | Invariant / StateMachine | 恢复正常 / 信息态无警告黄条 |
| SCN-01-COND-06 | INV-03；BR-04；POL-01 | Invariant / BusinessRule / Policy | 负向 / 风控评分与来源故障色物理区分 |
| SCN-02 | INV-04；POL-02；VO-02；VO-03 | Invariant / Policy / ValueObject | 主视图无裸枚举、评分可读、原始字段折叠 |
| SCN-02-COND-01 | INV-04；POL-02；BR-05 | Invariant / Policy / BusinessRule | 主视图不暴露原始枚举 / 理由代码 |
| SCN-02-COND-04 | INV-04；INV-07；STM-05；EXC-02 | Invariant / StateMachine / Exception | 非 ready 态人话化，无裸枚举串 |
| SCN-03 | INV-05；POL-01 | Invariant / Policy | 来源 / 价格 / 涨跌收敛唯一主源 |
| SCN-03-COND-01 | INV-05；UIC-03 | Invariant / UICarrier | 来源状态收敛到唯一权威主源（计数=1） |
| SCN-04 | STM-06；EXC-05 | StateMachine / Exception | 顶部标题主位、控件降级不改切换语义 |
| SCN-04-COND-01 | STM-06；OBJ-01 | StateMachine / BusinessObject | 标题为顶部视觉主位 |
| SCN-04-COND-02 | STM-06；EXC-05；RULE-08 | StateMachine / Exception | 控件降级右对齐、切换语义不变、非法值归一化 |
| SCN-05 | INV-06；OBJ-04；OBJ-08 | Invariant / BusinessObject | 主卡突出、次级降灰形成层级差 |
| SCN-05-COND-01 | OBJ-04；OBJ-08；VO-01 | BusinessObject / ValueObject | 主卡突出、次级灰字层级差 |
| SCN-05-COND-02 | INV-06；AUD-01；ATTR-29 | Invariant / Audit | nonAdvice 免责保持可见 |
| SCN-06 | STM-01；INV-05；OBJ-01；OBJ-02 | StateMachine / Invariant | 侧栏扫读：主看突出、来源弱化、archived 区分 |
| SCN-06-COND-01 | OBJ-01；UIC-06 | BusinessObject / UICarrier | 侧栏名称+代码一行、价格+涨跌右对齐主看 |
| SCN-06-COND-03 | STM-01；OBJ-01；RULE-07 | StateMachine / BusinessRule | 归档标的弱化区分 active |
| SCN-07 | INV-04；STM-05；STM-08；BR-07 | Invariant / StateMachine / BusinessRule | 信号卡默认关键数字、明细折叠、仅 ready 有回测 |
| SCN-07-COND-01 | STM-05；OBJ-04；OBJ-08 | StateMachine / BusinessObject | 默认呈现关键数字 |
| SCN-07-COND-03 | BR-07；STM-08；OBJ-04 | BusinessRule / StateMachine | 仅 ready 呈现回测块、价位分层级 |
| RULE-01 | INV-01；INV-02；BR-02；POL-01；STM-02 | Invariant / Policy / StateMachine | 来源三档：正常无警告、真异常见警告 |
| RULE-02 | INV-01；INV-02；BR-10；STM-07 | Invariant / StateMachine | 恢复态正常 / 信息 vs 需关注分色 |
| RULE-03 | INV-03；BR-04；POL-01 | Invariant / Policy | 负向 / 风控评分与来源故障色物理区分 |
| RULE-04 | INV-04；BR-05；POL-02；EXC-03 | Invariant / Policy / Exception | 理由代码人话化，未注册回落 UNKNOWN_CODE |
| RULE-05 | INV-07；BR-03；POL-03 | Invariant / Policy | 来源降级门控信号，呈现层只读不重实现 |
| RULE-06 | BR-07；STM-08；INV-04 | BusinessRule / StateMachine | 回测 / 反T仅 ready 时呈现 |
| RULE-07 | STM-01；OBJ-01 | StateMachine / BusinessObject | active/archived 呈现区分，不改归档逻辑 |
| RULE-08 | STM-06；EXC-05 | StateMachine / Exception | 布局切换语义不变、非法值归一化 |
| RULE-09 | INV-06；AUD-01；ATTR-29 | Invariant / Audit | nonAdvice 免责始终可见 |

---

## 给方案阶段的领域边界（Domain Boundaries for Solution）

> 本节把会影响实现路线的领域语义集中说明。不决定技术实现方式，只说明必须保留哪些业务边界、规则和状态语义，哪些做法会破坏领域模型。

| 领域元素 | 方案必须保留的语义 | 后续不能采用的做法 | 影响的用例 / 规则 | 破坏后的风险 |
|----------|--------------------|--------------------|-------------------|--------------|
| 限界上下文 BC-01↔BC-02（只读防腐） | BC-01 只读消费 BC-02 输出并翻译为呈现语义；内部枚举 / 理由代码 / 技术态不外溢主视图 | 不得在呈现层重实现既有领域门控 / 计算；不得把内部枚举当展示文案直呈；不得改 BC-02 状态机 / 计算逻辑 | SUC-01~SUC-06；INV-04；INV-07 | 泄漏内部编码、双份门控逻辑漂移、触碰非目标领域语义 |
| 策略 POL-01 四档色映射 | 语义色分层（正常 / 信息 / 谨慎-风险 / 警告-异常）；negative 评分与来源故障物理区分；涨跌红绿与警告色分离 | 不得沿用「非 formal 一律同级提示」「所有恢复态复用同一黄条」「negative 与来源故障共用告警色」 | SUC-01/02/06；INV-01~INV-03 | 误判「看空=故障」「正常恢复=异常」，回退现状缺陷 |
| 策略 POL-02 人话化翻译 | 优先复用既有可读源；未注册码回落 UNKNOWN_CODE | 不得新建重复枚举→文案映射；不得把内部码当人话直呈 | SUC-02/03；INV-04 | 语义漂移、理解门槛未降 |
| 不变量 INV-07 跨呈现一致性 | 来源 stale 时信号卡同步 source_degraded；恢复态与来源态独立黄条 | 不得在呈现层重实现来源→信号降级门控；不得混用同一警告承载 | SUC-01→SUC-03、SUC-06；NEG-01；NEG-03 | 矛盾呈现误导操作 |
| 不变量 INV-06 免责可见 | nonAdvice 免责在默认 / 折叠态均可见 | 折叠 / 层级降级不得隐藏免责 | SUC-03；AUD-01 | 触碰投资边界合规红线 |
| 状态机 STM-01~STM-08（只读） | 忠实呈现既有状态集合，不驱动迁移、不改迁移语义 | 不得为 MTS 新建状态机（DMF-01）；不得改 STM-06 切换白名单 | 全用例 | 范围溢出、改变领域语义 |

### 领域问题对方案阶段的影响（Domain Questions Affecting Solution）

| 问题 / 风险 | 影响的领域元素 | 是否阻断方案路线选择 | 处理方式 |
|-------------|----------------|----------------------|----------|
| DEC-01：demo_fallback 来源色档最终归类（信息级 / 需关注） | STM-02.demo_fallback；VO-01；AUD-02 | 否，原因：仅影响单一来源结局的呈现色档（信息级↔警告档），不改上下文边界、状态机、其他不变量或一致性；默认信息级软口径足以推进 | 作为方案阶段风险输入 + 待用户确认产品决策；verify 前定档，改判仅调整 SCN-01-COND-02 相关口径 |
| 折叠交互状态承载归属（interaction 可跳过） | INV-04；UIC-02/07 折叠义务 | 否，原因：不改领域语义，是承载层归属决策；但折叠义务不得因跳过而丢失 | 作为方案关键决策点：方案明确折叠交互状态承载层 |

---

## Downstream Guidance

| 消费方 | 必须保留 / 消费的内容 | 来源领域元素 | 备注 |
|--------|------------------------|--------------|------|
| 用例模型 | 参与者只读边界、状态机（只读呈现）、业务规则作为呈现不变量 | ACT-01；STM-01/02/05/06/07/08；INV-01~INV-07 | 已在 use-case-model 消费；本文回填 DMF-01/DMF-02 |
| 交互设计 | 对象 / 状态机、四档呈现色语义、人话文案源、折叠展开入口、唯一主源选点 | STM-*；POL-01/02；VO-01/02/03；INV-04；INV-05 | 每个扇出状态须提供可操作入口；主源选点在此层决定 |
| 方案设计 | 限界上下文只读防腐边界、四档色策略、跨呈现一致性只读约束、改动面限呈现层 | BC-01/02；POL-01/03；INV-07 | 不得在呈现层重实现门控；复用既有可读源 |
| 技术分析 | 呈现不变量、状态机只读对齐、技术态（重试 / 缓存快照等）收进折叠详情 | INV-01~INV-07；STM-*；EXC-03 | 不设计存储结构 / 服务拆分 / 算法；不改既有领域计算逻辑 |
| 拆解 / 测试 | 呈现不变量、状态呈现对账、只读权限、异常呈现场景 | INV-01~INV-07；STM-*；EXC-01~EXC-05；AUD-01/02 | 每条不变量可被验收逐条对上；主观项双证据 |

---

## 待澄清问题与建模风险（Open Questions & Modeling Risks）

| 风险 ID | 问题 / 风险 | 影响 | 决策期限 | 负责人 |
|---------|-------------|------|----------|--------|
| RISK-01 | DEC-01：demo_fallback 来源色档最终归类（信息级 / 需关注） | VO-01 / STM-02.demo_fallback / AUD-02；单一来源结局色档 | verify 前（用户确认定档） | 用户 / senior-product-expert |
| RISK-02 | MTS 计算分类被下游误建为新状态机 | 若误建状态机则范围溢出（违反 SCOPE-13 / DMF-01） | 贯穿下游 | 统一语言已显式禁止；下游遵守 |
| RISK-03 | 呈现层被误用于重实现既有领域门控（跨呈现一致性 INV-07） | 双份门控逻辑漂移、触碰非目标 | 方案 / 执行阶段 | 方案须只读承载（POL-03）；不重实现 |
