---
knowledge_type: behavior_spec
status: active
source: mission:20260522-stock-watch-system
source_artifact: harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md
confidence: accepted
---

# Local Stock Watch Workbench Specification

## Purpose
从已验收任务差量规格首次建立的长期行为契约。

## Requirements

### Requirement: 多市场自选与归一预览
系统 SHALL 在添加 US/HK/CN/KR 标的前展示市场、原始代码、归一代码或歧义错误态，并阻止未确认歧义输入进入 active 自选。

#### Scenario: 添加前预览归一结果
- **GIVEN** 用户输入支持市场的股票代码
- **WHEN** 用户选择市场或系统能明确归一
- **THEN** 页面展示市场、原始代码和归一代码预览
- **AND** 用户确认后，标的进入对应市场分组的 active 自选列表

#### Scenario: 歧义输入不得静默写入
- **GIVEN** 用户输入可能属于多个市场的数字代码
- **WHEN** 市场或归一结果尚未明确
- **THEN** 系统不得把该代码写入 active 自选
- **AND** 页面展示需要确认市场或无法识别的状态

### Requirement: 自选列表状态摘要
系统 SHALL 在自选列表行展示名称、市场、归一代码、来源状态、最近价和涨跌摘要，并支持 active/archived 恢复语义。

#### Scenario: 列表显示行情摘要
- **GIVEN** 用户已有 active 自选标的
- **WHEN** 工作台加载或行情刷新
- **THEN** 自选列表展示市场、归一代码、来源状态、最近价和涨跌摘要

#### Scenario: 归档暂停提醒
- **GIVEN** 一个 active 标的绑定了 enabled 提醒
- **WHEN** 用户归档该标的
- **THEN** 标的变为 archived
- **AND** 绑定提醒进入 suspended_by_archive 且不触发

### Requirement: 默认看盘工作台与指标切换
系统 SHALL 在用户选择 active 标的后展示默认工作台，包含主图、成交量 pane、可切换副图 pane，并提供 OHLC 与关键指标读数。

#### Scenario: 打开默认工作台
- **GIVEN** 用户选择一个 active 标的
- **WHEN** 工作台打开
- **THEN** 页面展示自选区、图表区、信号与提醒区
- **AND** 图表区包含主图、成交量 pane 和一个副图 pane

#### Scenario: 切换副图指标
- **GIVEN** 用户正在查看某 active 标的
- **WHEN** 用户切换 MACD、RSI、KDJ 或 ATR/波动副图
- **THEN** 主图与成交量保持同一标的上下文
- **AND** 副图 pane 更新为所选指标

#### Scenario: 数据不足时指标局部降级
- **GIVEN** 当前 PriceSeries 不足以计算某个指标
- **WHEN** 用户查看该指标
- **THEN** 页面展示 partial 或 unavailable 状态
- **AND** 不展示伪造读数

### Requirement: MTS 解释性信号
系统 SHALL 以 MTS 解释卡展示 trend_state、mts_score、score_band、signal_type、alert_level、reason_codes 和 invalidators，并在数据不足或来源降级时避免输出伪信号。

#### Scenario: 输出完整 MTS 卡
- **GIVEN** PriceSeries 与 IndicatorSet 足够解释
- **WHEN** 系统完成 MTS 评估
- **THEN** 页面展示 trend_state、mts_score、score_band、signal_type、alert_level、reason_codes 和 invalidators

#### Scenario: MTS 不表达投资建议
- **GIVEN** MTS 进入高强度正向或风险状态
- **WHEN** 页面展示信号
- **THEN** 文案使用技术提醒口径
- **AND** 不展示收益承诺、胜率或确定性买卖建议

#### Scenario: 数据不足时不输出伪 MTS
- **GIVEN** PriceSeries 不足或来源 unavailable
- **WHEN** 系统尝试评估 MTS
- **THEN** 页面展示 data_insufficient 或等价不可解释状态
- **AND** 不展示有效提醒等级

### Requirement: 本地提醒 taxonomy 与触发历史
系统 SHALL 支持价格型、变化型、技术指标型、MTS 型、定时提醒的本地提醒规则，并记录启停状态、触发状态、触发时间、触发理由和确认状态。

#### Scenario: 创建分类提醒
- **GIVEN** 用户正在查看 active 标的
- **WHEN** 用户创建提醒规则
- **THEN** 系统保存提醒 taxonomy、条件、启停状态和目标标的

#### Scenario: 提醒触发后可确认
- **GIVEN** 某 enabled 提醒条件命中
- **WHEN** 系统更新提醒状态
- **THEN** 规则进入 triggered
- **AND** 页面展示触发时间、触发理由和确认动作
- **WHEN** 用户确认提醒
- **THEN** 规则进入 acknowledged

### Requirement: 来源健康与降级穿透
系统 SHALL 把来源健康作为一级 UI 状态，区分 formal、demo_fallback、stale、unavailable，并将降级语义同步到图表、MTS 和提醒。

#### Scenario: demo fallback 可见
- **GIVEN** 正式来源不可用，系统使用 demo fallback
- **WHEN** 工作台刷新完成
- **THEN** 来源健康显示 demo_fallback 和降级原因
- **AND** 图表、MTS、提醒区域同步显示降级语义

#### Scenario: stale 不伪装实时成功
- **GIVEN** 当前数据已过期但仍可展示
- **WHEN** 用户查看工作台
- **THEN** 来源健康显示 stale
- **AND** 页面显示上次刷新时间或等价旧数据说明

#### Scenario: 重试失败不导致页面不可用
- **GIVEN** 用户点击重试来源
- **WHEN** 重试失败
- **THEN** 页面保留上一次可解释状态
- **AND** 显示失败原因或仍处于降级状态

### Requirement: 本地工作台恢复
系统 SHALL 在同一浏览器配置下恢复自选、提醒启停/触发/确认状态、触发历史和基础 ChartLayout；恢复失败时回到可用默认布局。

#### Scenario: 浏览器重开恢复工作台
- **GIVEN** 用户已有自选、提醒、触发历史和布局偏好
- **WHEN** 用户关闭并重新打开浏览器
- **THEN** 系统恢复自选、提醒状态、触发历史和基础 ChartLayout

#### Scenario: 布局恢复失败回退默认
- **GIVEN** 本地保存的布局状态损坏或版本不兼容
- **WHEN** 系统恢复工作台
- **THEN** 系统回到默认可用布局
- **AND** 自选和提醒仍尽可能恢复

### Requirement: 工作台布局模式
系统 SHALL 在桌面端至少支持 dense 与 focus，并在移动端使用 mobile_tab 或等价单列导航访问自选、图表、提醒和来源。

#### Scenario: 桌面 dense 与 focus 切换
- **GIVEN** 用户在桌面端查看工作台
- **WHEN** 用户切换 focus 模式
- **THEN** 页面隐藏或收起非关键侧栏
- **AND** 保留图表、副图切换和来源健康入口

#### Scenario: 移动端 tab 工作台
- **GIVEN** 用户在移动端宽度打开系统
- **WHEN** 页面进入 mobile_tab 模式
- **THEN** 自选、图表、提醒、来源以 tab 或等价导航组织
- **AND** 文本和控件不互相遮挡

### Requirement: Fixture-first 验收输入
系统 SHALL 为核心验收准备可回放输入，覆盖四市场标的、歧义输入、指标充足/不足、MTS 强信号/风险、提醒触发、来源降级和浏览器重开恢复。

#### Scenario: 使用冻结样本验收核心路径
- **GIVEN** 验证阶段准备验收 AC-01 到 AC-05
- **WHEN** 执行验证
- **THEN** 验证证据使用可回放样本覆盖核心路径
- **AND** live 行情只作为非门禁烟雾参考

---

## Promotion History

- mission:20260522-stock-watch-system from `harness-runtime/harness/stages/20260522-stock-watch-system/specs/local-stock-watch-workbench/spec.md`
