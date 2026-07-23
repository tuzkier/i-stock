# BUC-05 管理本地提醒 taxonomy 与触发历史

## 用户目标

创建价格型、变化型、技术指标型、MTS 型和定时提醒，并能看到启停状态、触发状态、触发时间、触发原因和确认动作。

## Entry / Exit

- Entry: 用户在标的详情页打开提醒面板。
- Exit: 新提醒进入规则列表，或已有规则更新状态与历史。

## ASCII Wireframe

```text
[提醒类型] 价格型 / 变化型 / 技术指标型 / MTS 型 / 定时提醒
[提醒等级] 观察 / 确认 / 强信号 / 风控
[条件] 趋势破坏或跌破 ATR 风控线   [保存提醒]

风控  AAPL  趋势破坏  enabled  triggered   [确认]
观察  0700.HK  价格上穿  disabled         [启用]
暂停  600519.SS  强信号  suspended_by_archive
```

## Screen Priority

1. 提醒 taxonomy 和等级。
2. 绑定标的与条件。
3. 启停状态、触发历史与确认动作。
4. 风控优先级。

Primary / secondary content: primary 是规则与等级；secondary 是最近触发时间、原因和确认状态。

## Actions

- `CreateAlertRule`
- `UpdateAlertRuleState`
- `ResolveAlertOutcome`

## Interaction Rules

- 必须支持价格型、变化型、技术指标型、MTS 型和定时提醒。
- 提醒等级保持四级口径，不与交易动作混写。
- 多条件同时命中时，风控优先。
- disabled 与 `suspended_by_archive` 不触发。
- 触发历史要保留，不能因为确认而丢失。

## States

- `enabled`
- `disabled`
- `suspended_by_archive`
- `idle`
- `triggered`
- `acknowledged`

## Recovery

- 重开后保留启停状态、最近触发原因与确认状态。
- 标的恢复时，提醒按归档前用户意图恢复，而不是默认全开。

## Locator / E2E Obligations

- `alerts-panel`
- `alert-create-form`
- `alert-taxonomy-select`
- `alert-level-select`
- `alert-condition-input`
- `alert-save-button`
- `alert-rule-row-risk`
- `alert-rule-row-watch`
- `alert-rule-row-archive`
- `alert-ack-button`

P0 E2E seed: 创建一条 MTS 或价格提醒，断言新规则进入列表；触发态显示确认按钮，归档态显示暂停说明。

## E2E Locator Matrix

| Priority | Scenario | Locator strategy |
|---|---|---|
| P0 | E2E-BUC-05 | data-testid + accessible name strategy declared in `Locator / E2E Obligations` |

## Trace to BUC / BO / AC / Delta spec

- BUC: `BUC-05`
- BO: `BO-001`, `BO-003`, `BO-004`, `BO-005`, `BO-006`
- AC: `AC-04`, `AC-05`
- Delta spec: `本地提醒 taxonomy 与触发历史`

## Universal State Coverage

- `STATE-LOADING`: 使用骨架屏、加载标记或保留上一次可解释状态。
- `STATE-EMPTY`: 使用空列表、无数据或无可用规则提示，不留白。
- `STATE-SUCCESS`: 用户动作完成后显示确认反馈并进入下一可操作状态。
- `STATE-ERROR`: 归一失败、数据不可用、重试失败或保存失败时显示可恢复错误。
- `STATE-PERMISSION`: 本地网页不需要账号；云同步、自动交易、外部通知等越权动作显示为不可用或范围外。
- `STATE-DISABLED`: 数据不足、标的归档、来源不可用或布局上下文不适用时禁用相关操作并说明原因。

## Review Notes

- 提醒面板必须把“提醒等级”和“交易动作”分开。
- 归档暂停语义不能丢；恢复时要能回到原意图。
