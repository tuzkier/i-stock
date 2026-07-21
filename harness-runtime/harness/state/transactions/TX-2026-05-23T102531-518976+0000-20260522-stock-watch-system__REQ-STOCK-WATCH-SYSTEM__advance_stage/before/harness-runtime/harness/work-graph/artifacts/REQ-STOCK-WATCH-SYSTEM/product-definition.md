# Product Definition: MyInvestment

> **来源**：prd 技能 → `harness-runtime/harness/stages/20260522-stock-watch-system/product/product-definition.md`
> **上游**：`mission-contract.md` | `product/business-objects.md` | `product/business-use-cases.md` | `product/product-evidence.md` | `product/product-domain-model.md`

**mission-id:** `20260522-stock-watch-system`  
**状态（Status）:** `draft`

---

## 控制契约

- Contract: `harness-runtime/harness/stages/20260522-stock-watch-system/contracts/prd.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本文件提供主产品定义正文。

---

## Business Definition

**业务问题：** 当前个人投资者在港股、A 股、美股、韩股之间切换时，自选股分散、代码格式不统一、图表与技术指标观察割裂、MTS 研究规则无法落成统一提醒语义，导致“持续看盘”依赖多个入口和大量手工判断。

**业务目标：** 交付一个本地网页形态的多市场股票看盘系统，把跨市场自选管理、默认可用的图表与指标上下文、MTS 多周期趋势信号和四级提醒整合到单一入口，并保持浏览器重开后的本地连续使用体验。

**成功信号：**
- 用户能在同一浏览器配置内持续维护并恢复四市场自选。
- 打开任一标的即可看到默认主图、成交量和可切换副图指标。
- MTS 结果以趋势状态、分数带、信号类型、提醒等级、理由/失效条件共同表达，而不是单一箭头。
- 提醒保持“观察 / 确认 / 强信号 / 风控”四级语义，并支持价格型与信号型规则。
- 正式来源不可用时，系统仍能继续观察，但必须显式区分正式 / 演示 / 降级状态。

**Mission fit：** 本定义严格覆盖 Mission 已授权的本地网页、多市场自选、技术指标、MTS 信号、买卖/风险提醒和本地恢复，不扩展到自动交易、收益承诺、云同步、完整基本面、正式供应商锁定或完整回测平台。

---

## Problem Diagnosis

| 业务方表述 | 底层问题 | 受影响用户 / 场景 | 价值假设 | 证据 |
|------------|----------|-------------------|----------|------|
| 做一个本地网页形态的多市场股票看盘系统 | 用户缺的不是单一图表页，而是一个可持续使用的跨市场观察工作台：统一自选、统一图表上下文、统一 MTS 解释、统一提醒与恢复语义 | 个人投资者在本地浏览器里跨市场维护自选、切换看盘、解读信号、接收提醒、重开恢复 | 若把“自选 + 默认看盘 + MTS + 提醒 + 本地恢复”闭成一个产品链路，用户可减少工具切换与手工解释成本，并能把研究规则转成日常观察节奏 | Mission Contract、Discovery Brief、技术信号研究、BO Registry、BUC Package |
| 希望支持技术指标和买卖/风险提醒 | 用户真正需要的是“可解释的趋势/风险语言”，不是把若干指标堆在界面上 | 技术分析用户与研究驱动用户在个股详情页判断趋势、突破、动量与风险 | 若 MTS 能稳定表达趋势状态、买卖点类型、风险等级和触发理由，提醒就可以服务观察与风控，而非制造模糊买卖暗示 | AC-03、AC-04、BUC-04、BUC-05、研究文档 MTS 模型 |
| 第一阶段保持本地化 | 用户要的是低维护、低依赖、不开账号也能连续使用的个人工具 | 本地使用者在同一浏览器内反复打开、关闭并继续观察 | 若自选、提醒和基础看盘上下文可在本机恢复，产品具备持续使用价值 | US-01、US-04、AC-05、BUC-06 |

---

## Users and Scenarios

| Scenario-ID | 用户 / 角色 | 场景 | 当前痛点 | 目标行为 |
|-------------|-------------|------|----------|----------|
| SCN-01 | 个人投资者 | 把港股、A 股、美股、韩股的标的统一纳入观察入口 | 自选分散、市场规则不同、代码格式难统一 | 在本地网页里按市场管理自选，保留原始代码与归一代码，并支持归档/恢复 |
| SCN-02 | 技术分析用户 | 打开个股快速进入主图、成交量和副图指标上下文 | 价格、成交量、动量与波动需要在多个视角间来回切换 | 进入个股后直接看到默认看盘布局，并在 MACD / RSI / KDJ / ATR 间切换副图 |
| SCN-03 | 研究驱动用户 | 解读 MTS 多周期趋势信号并接收分级提醒 | 只有零散指标，没有统一的趋势、买卖点和风控语义 | 看到趋势状态、分数带、买点/卖点类型、提醒等级、理由与失效条件，并据此观察或风控 |
| SCN-04 | 本地使用者 | 关闭浏览器后重新打开应用继续使用 | 不想依赖账号，也不想重复录入自选和提醒 | 直接恢复本地自选、提醒和基础看盘上下文，继续上次观察节奏 |
| SCN-05 | 任一看盘用户 | 正式来源不可用但仍需继续观察 | 容易把演示数据或降级数据误当成正式实时行情 | 在来源降级时继续观察，但清楚知道当前来源状态和哪些结论不可解释 |

---

## 业务用例地图（Business Use Case Map）

> 本节只保留 BUC 概览和追溯入口。完整 BUC 索引（BUC Index）与关键详情（Detail）以 `product/business-use-cases.md` 为准。

| BUC-ID | 名称 | 参与者（Actor） | 业务目标（Business Goal） | 相关 BO（Related BO） | 是否必须原型化（Prototype Required） | 追溯到（Traces To） | 详情来源（Detail Source） |
|---|---|---|---|---|---|---|---|
| BUC-01 | 管理多市场自选标的 | 个人投资者 | 把四市场标的纳入同一本地观察清单并保持可识别与可恢复 | BO-001, BO-002, BO-006 | yes | US-01, US-04, AC-01, AC-05 | `product/business-use-cases.md#buc-01-管理多市场自选标的` |
| BUC-02 | 打开标的进入默认看盘布局 | 个人投资者、技术分析用户 | 首次进入就获得主图、成交量和副图上下文 | BO-001, BO-003, BO-004, BO-008 | yes | US-02, AC-02 | `product/business-use-cases.md#buc-02-打开标的进入默认看盘布局` |
| BUC-03 | 切换副图指标观察不同分析维度 | 技术分析用户 | 在不离开当前标的的情况下切换副图解释视角 | BO-004, BO-008 | yes | US-02, AC-02 | `product/business-use-cases.md` |
| BUC-04 | 解读 MTS 多周期趋势信号 | 研究驱动用户 | 用统一语义理解趋势状态、买点/卖点类型和风险等级 | BO-003, BO-004, BO-005 | yes | US-03, AC-03, AC-04 | `product/business-use-cases.md#buc-04-解读-mts-多周期趋势信号` |
| BUC-05 | 配置并接收四级提醒 | 研究驱动用户、本地使用者 | 把价格或 MTS 条件转成可持续使用的本地提醒 | BO-001, BO-005, BO-006 | yes | US-03, US-04, AC-04, AC-05 | `product/business-use-cases.md#buc-05-配置并接收四级提醒` |
| BUC-06 | 重开浏览器恢复本地看盘现场 | 本地使用者 | 无需登录即可恢复自选、提醒和基础看盘上下文 | BO-001, BO-006, BO-008 | yes | US-01, US-04, AC-05 | `product/business-use-cases.md#buc-06-重开浏览器恢复本地看盘现场` |
| BUC-07 | 行情来源降级下继续看盘 | 所有看盘用户 | 在正式来源不可用时继续观察且不误读来源可信度 | BO-007, BO-003, BO-004, BO-005, BO-006 | yes | US-02, US-03, AC-02, AC-03, AC-04 | `product/business-use-cases.md#buc-07-行情来源降级下继续看盘` |

---

## Current Workflow Summary

当前用户工作流可概括为五段：

1. 先把来自不同市场的标的纳入本地自选，并依赖市场分组与代码归一维持识别性。  
2. 进入个股后，用户首先需要默认看盘布局而不是先做复杂配置。  
3. 在主图、成交量与副图指标共同构成的上下文里，用户观察价格结构、动量与波动。  
4. 系统把研究设计中的规则综合成 MTS 解释对象，再与价格型/信号型提醒结合，形成观察、确认、强信号和风控语义。  
5. 用户关闭并重新打开浏览器后，应回到连续的本地观察节奏；若来源降级，系统仍可观察，但必须显式降低可信度表达。  

---

## Scope and Tradeoffs

| 类型 | 内容 | 理由 | 追溯 |
|------|------|------|------|
| In | 本地网页看盘入口 | 是用户连续使用和低依赖的入口边界 | SD-01, Mission Objective |
| In | 四市场自选管理、代码归一、归档/恢复 | 是跨市场观察闭环的起点 | SD-02, BUC-01, BR-001, BR-002 |
| In | 默认看盘布局：主图、成交量常驻、一个可切换副图 | 是进入个股后的默认成功路径 | SD-03, SD-04, BUC-02, BUC-03 |
| In | MTS 多周期趋势信号 | 是产品差异化核心，且必须保持解释性 | SD-05, BUC-04, BR-008~BR-011 |
| In | 四级提醒：观察 / 确认 / 强信号 / 风控 | 是 MTS 和价格观察转成日常使用闭环的关键能力 | SD-06, BUC-05, BR-012, BR-013 |
| In | 本地恢复 | 是“本地持续使用”价值的直接体现 | SD-07, BUC-06, AC-05 |
| In | demo / fallback 状态提示 | 是产品风险边界，不可隐藏 | SD-08, BUC-07, BR-005 |
| In | 下游方案约束：优先评估成熟、维护活跃、许可合适的现成开源库 | 降低维护和验证风险，但 PRD 不提前锁定具体库或供应商 | SD-10, Mission Constraint |
| Out | 自动交易、券商联动、自动买卖动作 | 超出 Mission 授权，会改变产品风险边界 | SD-11 |
| Out | 收益承诺、确定性投资建议、胜率表达 | 超出产品定位并引入不当金融暗示 | SD-12, BR-009 |
| Out | 云账号、云同步、跨设备同步 | 与第一阶段本地化边界冲突 | SD-13 |
| Out | 完整基本面模块、组合调仓、仓位建议 | 会把产品从看盘系统扩成完整投研/交易终端 | SD-14, SD-18 |
| Out | 后台无人值守盯盘、浏览器外长期运行能力 | 与第一阶段本地网页形态不一致 | SD-15 |
| Out | 在 PRD 锁定正式供应商、回测数据源、成本模型 | 属于后续方案与验证决策，不在本阶段承诺 | SD-16 |
| Later | 正式行情接入、复权/停牌/交易日历、完整回测工作台、桌面封装 | 有价值，但不属于第一阶段用户可见闭环成立的先决条件 | SD-20~SD-24 |
| Decision Needed | ChartLayout 恢复粒度（全局 / 市场 / 标的） | 影响交互与持久化，但当前证据不足以定稿 | SD-25, GAP-02 |
| Decision Needed | MarketDataSource 用户可见信息密度 | 已确定必须显式显示来源状态，但展示粒度待 interaction / solution 定稿 | SD-26, GAP-03 |
| Decision Needed | MTS reason code / invalidator 标准化深度 | 必须结构化，但命名与枚举全集应在下游定稿 | SD-27, GAP-04 |

---

## 证据摘要（Evidence Summary）

| 证据类型（Evidence Type） | 来源（Source） | 对产品决策的影响（Product Decision Impact） | 降级处理（Degradation） |
|---------------|--------|-------------------------|-------------|
| Knowledge | `project-knowledge/_index.md` 及 `context/*`、`product/scope-boundaries.md` | 只作为长期约束与项目背景弱证据，辅助确认本地化、范围边界与 draft 状态 | 多数条目为 `init/draft`，不得作为定稿业务事实；主判断仍以 Mission、Discovery、BO/BUC 和研究文档为准 |
| Spec | `spec.enabled=false` | 本阶段不产出 delta spec，不以 capability spec 约束 PRD 语义 | 在 evidence 中记录“无 baseline spec 对齐”；由主流程在 contract 中同步该事实 |
| GitNexus | 不可用 | 不能提供棕地影响面、调用链和模块边界的正式证据 | 以 Discovery 已记录的手工代码阅读与输入文档替代，并把不可用性写入 degradation |
| Mission / Discovery | Mission Contract、Discovery Brief | 提供目标、非目标、成功定义、关键风险、候选对象与 PRD 输入建议 | 无 |
| Specialist Artifacts | `business-objects.md`、`business-use-cases.md`、`scope-strategy.md` | 提供 BO 边界、BUC/AC 闭环、范围取舍和后续决策点 | 无 |
| Research | `docs/technical-signal-research-design.md` | 提供 MTS 语义、默认指标分层、提醒等级、非目标和回测边界 | 仅定义产品与研究规则，不直接推导实现选型 |

---

## Product Domain Summary

> 领域模型消费 `product/business-objects.md`，本节只保留面向产品定义的摘要。

### Core Objects

| BO-ID | 对象 | 说明 | Spec 来源关系 |
|---|---|---|---|
| BO-001 | WatchSymbol / 自选标的 | 用户主动维护的观察对象，承载市场归属、代码归一、观察状态与本地恢复语义 | adjusted |
| BO-002 | Market / 市场 | 承载分组和代码归一规则的业务对象，不绑定具体供应商 | existing |
| BO-003 | PriceBar / 价格条 | 图表、指标、MTS 和提醒的共同业务输入，显式承载数据充分性与来源模式 | adjusted |
| BO-004 | IndicatorSet / 指标集 | 面向解释与展示的技术指标组合，不等于公式代码本身 | adjusted |
| BO-005 | MtsSignal / 多周期趋势信号 | 解释性结果对象，表达趋势状态、分数带、信号类型、提醒等级、理由与失效条件 | new |
| BO-006 | AlertRule / 提醒规则 | 用户显式配置的本地提醒对象，支持价格型与信号型规则 | adjusted |
| BO-007 | MarketDataSource / 行情来源 | 面向用户与产品语义的来源声明对象，表达正式 / 演示 / 降级状态 | new |
| BO-008 | ChartLayout / 看盘布局 | 用户可感知的主图/成交量/副图布局与恢复偏好对象 | new |

### State and Permission Summary

- WatchSymbol 必须覆盖 `draft_added -> active -> archived` 以及 `selected / unselected` 状态，保证归档可恢复而非语义丢失。  
- PriceBar、IndicatorSet、MtsSignal、MarketDataSource 必须共同表达“数据充分 / 数据不足 / 来源降级 / 不可解释”链路，避免伪信号。  
- AlertRule 必须支持 `enabled / disabled` 与 `idle / triggered / acknowledged`，且风控优先于观察类提醒。  
- ChartLayout 至少要定义默认布局和恢复策略，但恢复粒度仍为待决策项。  
- 本系统没有 Agent 组件，权限模型围绕“用户可创建/归档自选、配置/启停提醒、查看降级状态、恢复本地上下文”展开，不延伸到自主 Agent 行动。  

---

## Product Rules

| Rule-ID | 规则 | 验收方式 | 追溯 |
|---------|------|----------|------|
| RULE-01 | 自选标的必须归属于已支持市场，并同时保留原始代码与归一代码 | 通过 BUC-01 场景与持久化恢复验证 | BR-001, AC-01 |
| RULE-02 | 自选与提醒的本地恢复不依赖账号登录；标的归档后相关提醒进入因归档暂停状态，不再触发，标的恢复后按用户原先启停意图恢复 | 通过 BUC-01、BUC-05、BUC-06 和 AC-05 恢复验证 | BR-002, AC-05 |
| RULE-03 | 历史数据不足时可以展示价格，但不得产出伪造指标或 MTS 结论 | 通过 BUC-02、BUC-04、BUC-07 降级场景验证 | BR-004 |
| RULE-04 | 来源降级后必须显式显示正式 / 演示 / 降级语义，不得伪装为正式实时行情 | 通过 BUC-07 降级场景验证 | BR-005 |
| RULE-05 | 默认布局必须包含主图、成交量常驻和一个可切换副图 | 通过 BUC-02、BUC-03 和原型验证 | BR-006, BR-015 |
| RULE-06 | 指标与 MTS 只能服务解释与提醒，不得被包装成收益承诺 | 通过内容审查与交互文案验证 | BR-007, BR-009 |
| RULE-07 | MTS 必须同时表达趋势状态、分数带、信号类型和提醒等级 | 通过 BUC-04 场景与页面可观察结果验证 | BR-008, AC-03, AC-04 |
| RULE-08 | 买点必须区分趋势回调买点与收敛突破买点；风险必须区分趋势破坏、动量衰竭、风控止损 | 通过 BUC-04 详细 GWT 验证 | BR-010, BR-011 |
| RULE-09 | 提醒必须保持观察 / 确认 / 强信号 / 风控四级语义，且风控优先级最高 | 通过 BUC-05 规则与触发结果验证 | BR-012, BR-013 |
| RULE-10 | Legacy composite signal 不得直接作为产品信号语义对外展示 | 通过 solution / technical design 追溯和回归素材边界验证 | BR-014 |

---

## Functional Requirements

### FR-01: 多市场自选与代码归一管理

**描述：** 系统必须支持用户按市场管理港股、A 股、美股、韩股自选标的，保留原始代码与归一代码，并支持归档与恢复。

**验收标准：**
- **Given** 用户输入一个属于已支持市场的股票代码
- **When** 用户将其加入本地自选并在后续会话中继续使用
- **Then** 系统在正确市场分组中保留该标的，保持原始代码与归一代码，并支持归档后恢复

**关联：** US-01, US-04, BUC-01, BO-001, BO-002, RULE-01, RULE-02  
**优先级：** `P0`

### FR-02: 默认看盘布局与副图切换

**描述：** 用户选中任一 active 标的后，系统必须直接进入默认看盘布局，展示主图、成交量和一个可切换副图指标，并在数据不足时显式降级。

**验收标准：**
- **Given** 用户选中了一个 active 标的
- **When** 用户进入该标的的看盘页面
- **Then** 系统默认展示主图、成交量和一个可切换副图，并在数据不足时标明哪些指标不可解释

**关联：** US-02, BUC-02, BUC-03, BO-003, BO-004, BO-008, RULE-03, RULE-05  
**优先级：** `P0`

### FR-03: MTS 解释性信号输出

**描述：** 系统必须基于 PriceBar 与 IndicatorSet 形成 MtsSignal，向用户输出趋势状态、分数带、信号类型、提醒等级、理由与失效条件。

**验收标准：**
- **Given** 当前标的具备足够历史数据且价格与指标上下文可解释
- **When** 系统完成一次 MTS 评估
- **Then** 页面同时展示趋势状态、分数带、买点/卖点类型、提醒等级和触发理由，而不是单一箭头

**关联：** US-03, BUC-04, BO-005, RULE-06, RULE-07, RULE-08  
**优先级：** `P0`

### FR-04: 四级提醒配置与触发

**描述：** 系统必须支持价格型和信号型提醒规则，让用户以观察、确认、强信号、风控四级语义配置、启停、触发与确认提醒。

**验收标准：**
- **Given** 用户正在查看某个 active 标的并创建提醒规则
- **When** 价格或 MTS 条件命中
- **Then** 系统按四级语义触发提醒，保留最近触发原因，并在多条件同时命中时优先呈现风控提醒

**关联：** US-03, US-04, BUC-05, BO-006, RULE-09  
**优先级：** `P0`

### FR-05: 本地恢复与连续使用

**描述：** 系统必须在同一浏览器配置内恢复自选、提醒和基础看盘上下文，不要求用户重新登录或重新录入常用配置。

**验收标准：**
- **Given** 用户此前已保存自选与提醒配置
- **When** 用户关闭浏览器并重新打开应用
- **Then** 系统恢复已有自选、提醒和基础看盘上下文，并至少回到可用的默认看盘布局

**关联：** US-01, US-04, BUC-06, BO-001, BO-006, BO-008, RULE-02, RULE-05  
**优先级：** `P0`

### FR-06: 来源降级下的可持续观察

**描述：** 当正式来源不可用、覆盖不足或刷新失败时，系统必须继续提供可观察内容，同时显式降低来源可信度和相关解释对象的可解释性。

**验收标准：**
- **Given** 当前来源本次刷新失败或不可用
- **When** 系统更新来源状态和相关观察对象
- **Then** 页面显示来源降级原因、当前来源模式，并将受影响的指标、MTS、提醒切换为 partial、unavailable 或 data_insufficient 等降级状态

**关联：** BUC-07, BO-007, RULE-03, RULE-04  
**优先级：** `P0`

---

## Non-Functional Requirements

| ID | 类别 | 要求 | 条件 | 指标 | 测量方式 |
|--------|------|------|------|------|----------|
| NFR-01 | 可解释性 | MTS 与提醒不得退化成“买入/卖出”或单一颜色提示，必须带结构化语义 | 所有有效信号与提醒展示场景 | 页面可观察到趋势状态、分数带、信号类型、提醒等级、理由/失效条件 | 基于 BUC-04、BUC-05 的 UI 检查与验收脚本 |
| NFR-02 | 连续性 | 同一浏览器配置内，用户关闭后重开仍能继续使用核心配置 | 存在已保存自选或提醒 | 自选、提醒与基础看盘上下文可恢复 | 浏览器重开恢复验证 |
| NFR-03 | 降级透明性 | 来源降级或数据不足时，系统必须显式提示而非静默失败 | 正式来源失败、历史不足、demo fallback | 用户能区分可继续观察与当前不可解释的对象 | 降级场景截图、状态断言 |
| NFR-04 | 范围合规 | 产品不得输出收益承诺、自动交易动作或确定性投资建议 | 所有看盘、提醒、文案和帮助信息 | 无“下单”“保证收益”“胜率承诺”等越界语义 | 内容审查与验收清单 |
| NFR-05 | 可替换性约束 | 后续方案必须优先评估成熟、维护活跃、许可合适的现成开源库，但 PRD 不锁定具体库和供应商 | solution / technical design 输入 | 选型文档能证明对图表、指标、通知、数据接入进行了候选比较 | 下游方案评审 |
| NFR-06 | 确定性 | 第一阶段 MTS 与提醒计算链路必须保持 deterministic，不引入 Agent 决策 | 所有信号与提醒计算场景 | 相同输入产生相同结果 | fixture / 回放样本验证 |

---

## Agent Capability Requirements

不适用：`agent_engineering.enabled=true` 但 Mission Contract 已明确“涉及 Agent 组件：否”。本产品定义不补造 Agent 组件、Agent 工作权或 Agent 行为要求。

---

## Validation and Launch Loop

| 验证阶段 | 验证内容 | 证据 | 成功 / 失败判定 |
|----------|----------|------|-----------------|
| 产品定义完成前 | 检查 US / AC -> BO -> BUC -> FR / Rule 是否闭合；检查范围外项未被偷渡 | 本文追溯矩阵、BO Registry、BUC Package、Scope Strategy | 若任一 P0 需求无法追溯到 BO、BUC、规则和可观察验收信号，则失败 |
| 交互原型阶段 | 验证多市场新增/恢复、默认布局、MTS 信息层级、四级提醒和来源降级提示是否可理解 | 原型稿、状态矩阵、页面流程图 | 若用户需要二次解释才能分辨来源状态、MTS 等级或恢复路径，则失败 |
| 方案 / 技术设计阶段 | 验证来源层、指标层、MTS 结果对象、提醒对象与本地恢复边界保持产品语义 | solution.md、tech-design.md、测试计划 | 若方案锁死未授权供应商/库，或把技术实现混写成产品定义，则失败 |
| 验证阶段 | 使用冻结行情 fixture、可回放样本片段、浏览器重开恢复、降级场景验证 | 测试结果、截图、状态断言 | 若无法稳定复现 MTS/提醒、恢复或降级语义，则失败 |
| 上线后 / 内部持续使用 | 关注提醒误读、降级误读、恢复失败和信息密度过高导致的使用中断 | 内部使用记录、缺陷清单、后续决策项 | 若出现系统性误读或连续使用中断，需回到 interaction / solution 调整 |

---

## 追溯矩阵（Traceability Matrix）

| Mission Story / AC | BO | BUC | 场景（Scenario） | 规则（Rule） | FR / NFR | 规格 / 知识（Spec / Knowledge） | 证据（Evidence） |
|---|---|---|---|---|---|---|---|
| US-01 / AC-01 | BO-001, BO-002 | BUC-01 | SCN-01 | RULE-01 | FR-01, NFR-02 | `project-knowledge/product/scope-boundaries.md`(draft), Mission | Mission Contract, BUC Detail |
| US-02 / AC-02 | BO-003, BO-004, BO-008 | BUC-02, BUC-03 | SCN-02 | RULE-03, RULE-05 | FR-02, NFR-03 | 技术信号研究默认视图 | Discovery Brief, Research, BUC Detail |
| US-03 / AC-03 | BO-005 | BUC-04 | SCN-03 | RULE-06, RULE-07, RULE-08 | FR-03, NFR-01, NFR-06 | 技术信号研究 MTS 模型 | Research, BO Registry, BUC Detail |
| US-03 / AC-04 | BO-005, BO-006 | BUC-04, BUC-05 | SCN-03 | RULE-08, RULE-09 | FR-03, FR-04, NFR-01, NFR-04, NFR-06 | 技术信号研究提醒等级 | Research, BUC Detail |
| US-04 / AC-05 | BO-001, BO-006, BO-008 | BUC-01, BUC-05, BUC-06 | SCN-04 | RULE-02, RULE-05 | FR-01, FR-04, FR-05, NFR-02 | Mission、Knowledge draft | Mission Contract, Scope Strategy |
| AC-02 / AC-03 / AC-04 | BO-007, BO-003, BO-004, BO-005 | BUC-07 | SCN-05 | RULE-03, RULE-04 | FR-06, NFR-03 | Discovery 关于 fallback、Research 关于不可解释边界 | Discovery Brief, BUC-07 |

---

## Prototype / Interaction Trigger

| Trigger | Required | Reason | Expected Next Artifact |
|---------|----------|--------|------------------------|
| 多市场新增、归档、恢复入口设计 | required | 会直接影响自选入口负担、市场识别方式和恢复语义 | `interaction.md` |
| 默认看盘布局与副图切换 | required | 需要验证主图 / 成交量 / 副图的信息层级和单屏可读性 | `interaction.md` |
| MTS 信息分层与理由展示 | required | 是产品差异化核心，若层级处理不当易造成误读 | `interaction.md` |
| 四级提醒创建、列表、触发历史与风控优先级表达 | required | 需要验证优先级、文案和触发结果是否直观 | `interaction.md` |
| 来源降级状态条与“不可解释”提示 | required | 关系到用户信任边界和风险表达 | `interaction.md` |
| Layout 恢复粒度与首屏恢复策略 | required | 当前仍是 Decision Needed，需要在交互原型中先做认知验证 | `interaction.md` |

---

## Open Questions

- `ChartLayout` 的恢复粒度应按全局、市场、标的还是混合策略定义，才能兼顾认知成本与连续使用？
- `MarketDataSource` 面向用户的来源状态是否只保留“正式 / 演示 / 降级”，还是还需区分“延迟 / 不可用”等更细粒度状态？
- `MtsSignal.reason_codes` 与 `invalidators` 需要标准化到什么深度，既能支持验收与解释，又不在 PRD 阶段过早锁死实现细节？
- archived 的 WatchSymbol 与 AlertRule 的关系应是自动暂停、保留只读历史，还是允许恢复后继承原规则？当前需要在产品层明确最终语义。
- 当来源降级且数据部分可用时，列表页与个股页是否使用同一套可信度提示口径，还是按信息密度分层表达？
