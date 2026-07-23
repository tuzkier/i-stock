# BUC-08 切换布局模式

## 用户目标

在桌面端默认使用 focus（日常看盘）降低信息密度，需要排查或验收时切换 dense（诊断 / 验收）；在移动端使用 `mobile_tab` 访问自选、图表、提醒和来源，保证不同设备下都能读得清、切得快。

## Entry / Exit

- Entry: 用户点击布局控制器，或窗口进入移动宽度。
- Exit: 当前工作台切换到 dense、focus 或 mobile_tab。

## ASCII Wireframe

```text
布局：[日常看盘 focus] [诊断/验收 dense] [移动分栏 mobile_tab]
日常：左自选 / 中图表 + MTS + 状态摘要
诊断：左自选 / 中图表 / 右提醒、来源、恢复、布局细节
移动： [自选] [图表] [提醒] [来源]
```

## Screen Priority

1. 当前布局模式。
2. 桌面三栏或移动分栏可访问性。
3. 保留来源健康、图表、提醒和自选入口。
4. 恢复失败时的默认布局回退。

Primary / secondary content: primary 是布局切换控制与当前模式；secondary 是设备适配说明和回退策略。

## Actions

- `SwitchWorkspaceLayout`
- `SwitchMobileTab`

## Interaction Rules

- focus 是日常默认模式，只保留核心看盘路径和三项摘要入口。
- dense 是诊断 / 验收模式，展开提醒、来源、恢复和布局细节。
- dense / focus 只改变信息密度，不改变业务对象。
- mobile_tab 必须等价访问自选、图表、提醒、来源。
- 切换布局不能丢失当前选中标的和来源状态。
- 布局恢复失败时回到默认日常看盘 focus。

## States

- `dense`
- `focus`
- `mobile_tab`
- `restored`
- `default fallback`

## Recovery

- 若布局配置损坏，回退到 focus，并保持当前选中标的。
- 若进入 mobile_tab，先保留当前 tab，再允许继续切换。

## Locator / E2E Obligations

- `layout-controller`
- `layout-toggle-dense`
- `layout-toggle-focus`
- `layout-toggle-mobile-tab`
- `mobile-tab-watchlist`
- `mobile-tab-chart`
- `mobile-tab-alerts`
- `mobile-tab-source`

P1 E2E seed: 默认进入 desktop focus，断言提醒、来源、恢复细节不常驻；切换 dense 后断言 BUC-05 到 BUC-08 细节可访问；在 mobile_tab 下断言四个 tab 都可访问。

## E2E Locator Matrix

| Priority | Scenario | Locator strategy |
|---|---|---|
| P0 | E2E-BUC-08 | data-testid + accessible name strategy declared in `Locator / E2E Obligations` |

## Trace to BUC / BO / AC / Delta spec

- BUC: `BUC-08`
- BO: `BO-008`
- AC: `AC-02`, `AC-05`
- Delta spec: `工作台布局模式`, `本地工作台恢复`

## Universal State Coverage

- `STATE-LOADING`: 使用骨架屏、加载标记或保留上一次可解释状态。
- `STATE-EMPTY`: 使用空列表、无数据或无可用规则提示，不留白。
- `STATE-SUCCESS`: 用户动作完成后显示确认反馈并进入下一可操作状态。
- `STATE-ERROR`: 归一失败、数据不可用、重试失败或保存失败时显示可恢复错误。
- `STATE-PERMISSION`: 本地网页不需要账号；云同步、自动交易、外部通知等越权动作显示为不可用或范围外。
- `STATE-DISABLED`: 数据不足、标的归档、来源不可用或布局上下文不适用时禁用相关操作并说明原因。

## Review Notes

- 布局切换不能偷渡新的业务对象。
- 移动端必须保持同一信息架构，只是换成单列或 tab 访问。
