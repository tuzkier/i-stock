# Interaction Spec 入口

**mission-id:** `20260522-stock-watch-system`  
**artifact tier:** `standard`  
**权威边界:** 本目录是 AI handoff 的界面交互合同；`visual-interaction/prototype/index.html` 只作为人类确认入口。

## 阅读顺序

1. `../interaction.md`
2. `buc-index.md`
3. `buc-coverage.md`
4. `BUC-01` ~ `BUC-07`
5. `_shared/surface-registry.md`
6. `_shared/domain-ui-mapping.md`
7. `_shared/view-models.ts`
8. `_shared/consistency-report.md`

## 更新规则

- 先更新本目录，再更新 HTML 原型。
- 用户反馈若只影响布局、控件、文案、状态呈现或 locator，更新本目录并重建原型。
- 用户反馈若要求新增/修改 AC、BO、领域状态、权限或范围，停止推进并回流 PRD / Decision Gate。
- 用户可见文案默认中文；允许例外仅限股票代码、产品名、代码标识和行业通用缩写。

## UX Review Notes

- 主次层级：首屏以“来源状态、自选、当前标的图表、MTS、提醒”为扫描顺序；合同和评审信息不进入主原型界面。
- 反馈策略：新增、归档、恢复、提醒保存、来源降级都必须给用户可见反馈。
- 键盘焦点：输入框、市场选择、指标切换、提醒表单和确认按钮均应可 Tab 到达；禁用状态保留可读说明。
- 响应式：桌面三栏，移动端纵向堆叠，核心状态不被隐藏。

## Keyboard / Focus Contract

- Tab order: 来源状态条 -> 新增自选输入 -> 市场选择 -> 加入 -> 自选行操作 -> 副图切换 -> 提醒表单 -> 提醒规则操作。
- Enter: 对当前聚焦按钮执行主动作；在新增输入内提交新增自选。
- Escape: 关闭临时错误/成功提示，不改变业务状态。
- Focus: 当前聚焦控件必须有可见轮廓；副图切换按钮需要同时表达 selected 和 focus。
- Disabled: 数据不足、来源降级、归档暂停和用户手动停用都必须保留可读原因；disabled 控件不触发业务动作。

## Shared State Matrix

| State | 覆盖方式 |
|---|---|
| STATE-LOADING | 行情刷新、恢复本地配置、MTS 评估中使用骨架或状态文本 |
| STATE-EMPTY | 无自选、无提醒、无可用数据时显示下一步入口 |
| STATE-SUCCESS | 新增自选、保存提醒、恢复现场成功时显示结果 |
| STATE-ERROR | 市场不可识别、来源不可用、数据不足时显示原因 |
| STATE-PERMISSION | 本地网页无账号权限；通知权限若未开启则提示只能保留站内提醒 |
| STATE-DISABLED | disabled 提醒、archived 标的相关提醒、不可解释 MTS 操作禁用 |

## Surface 概览

| Surface | 目的 |
|---|---|
| `SURF-WATCHLIST` | 管理多市场自选、归档、恢复和来源摘要 |
| `SURF-DETAIL` | 承载主图、成交量、副图、MTS 与降级提示 |
| `SURF-ALERTS` | 创建、启停、确认和查看四级提醒 |
| `SURF-SOURCE` | 统一表达来源可信度和不可解释对象 |
