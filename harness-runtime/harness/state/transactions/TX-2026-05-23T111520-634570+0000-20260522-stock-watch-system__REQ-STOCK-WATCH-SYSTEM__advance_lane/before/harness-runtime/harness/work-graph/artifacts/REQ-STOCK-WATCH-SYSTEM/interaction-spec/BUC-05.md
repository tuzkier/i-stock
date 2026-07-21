# BUC-05 配置并接收四级提醒

## 用户目标
创建价格型或信号型提醒，并以观察 / 确认 / 强信号 / 风控四级语义查看启停、触发和确认状态。

## Entry / Exit
- Entry: 用户在标的详情页打开提醒面板。
- Exit: 新提醒进入规则列表，或现有规则更新启停 / 确认状态。

## ASCII Wireframe
```text
[提醒类型: 价格型/信号型] [等级: 观察/确认/强信号/风控]
[条件输入] [保存提醒]
风控  AAPL  趋势破坏  enabled triggered  [确认]
观察  0700.HK  价格上穿  disabled         [启用]
```

## Screen Priority
1. 提醒类型和等级。
2. 绑定标的和触发条件。
3. 启停状态、最近触发时间、触发原因。
4. 风控优先级高亮。

Primary-secondary content: primary 是提醒等级、条件和启停状态；secondary 是最近触发时间、原因和确认动作。

## Actions
- `CreateAlertRule`
- `UpdateAlertRuleState`
- `ResolveAlertOutcome`

## Interaction Rules
- 必须支持价格型和信号型。
- 提醒等级必须保持四级口径。
- 多条件同时命中时，风控优先。
- disabled 不触发；归档标的提醒 suspended_by_archive 不触发。

## States / Recovery
- `enabled / disabled / suspended_by_archive`
- `idle / triggered / acknowledged`
- 恢复：重开后保留启停状态和最近触发原因。

## E2E Locators
- `alerts-shell`
- `alert-create-form`
- `alert-type-select`
- `alert-level-select`
- `alert-save-button`
- `alert-rule-row-risk`

## E2E Obligation / Locator Strategy
P0 path submits `alert-create-form` and asserts `alert-rule-row-*`; risk precedence path asserts `alert-rule-row-risk` appears before observation rules.

| Scenario | Priority | Locator Strategy |
|---|---|---|
| E2E-BUC-05-S01 创建信号型提醒 | P0 | data-testid: `alert-create-form`, `alert-type-select`, `alert-level-select`, `alert-save-button`, `alert-rule-row-risk` |
| E2E-BUC-05-S02 风控优先 | P0 | data-testid: `alert-rule-row-risk`, `alert-rule-row-watch`; accessibility order assertion |

## Common State Coverage
- STATE-LOADING: 保存提醒时显示处理中。
- STATE-EMPTY: 无提醒时显示创建入口。
- STATE-SUCCESS: 保存成功后规则出现在列表。
- STATE-ERROR: 条件非法或目标标的不可用时显示错误。
- STATE-PERMISSION: 浏览器通知权限未开启时保留站内提醒。
- STATE-DISABLED: disabled 和 suspended_by_archive 不触发。

## UX Review Notes
提醒面板必须把“提醒等级”与“交易动作”分开；风控优先级要可见，但不能制造自动卖出暗示。

## Traces To
US-03, US-04, AC-04, AC-05, BO-001, BO-005, BO-006, BR-012, BR-013
