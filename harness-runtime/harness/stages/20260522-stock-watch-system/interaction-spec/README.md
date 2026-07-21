# Interaction Spec 入口

**mission-id:** `20260522-stock-watch-system`  
**artifact tier:** `standard`  
**权威边界:** 本目录是 AI handoff 的界面交互合同；`visual-interaction/prototype/index.html` 只作为人类确认入口。

## 阅读顺序

1. `../interaction.md`
2. `buc-index.md`
3. `buc-coverage.md`
4. `BUC-01` ~ `BUC-08`
5. `_shared/surface-registry.md`
6. `_shared/domain-ui-mapping.md`
7. `_shared/view-models.ts`
8. `_shared/consistency-report.md`

## 更新规则

- 先更新本目录，再更新 HTML 原型。
- 若用户反馈只影响布局、控件、文案、状态反馈、焦点或 locator，更新本目录并重建原型。
- 若用户反馈要求新增 / 删除用户路径、AC、BO、领域状态、权限或范围，停止推进并回流 PRD / Decision Gate。
- 原型中用户可见文案默认中文；保留英文仅限股票代码、市场代码、指标名、产品专名、行业缩写与上游指定术语。
- deep link 统一使用 `#buc-001` ~ `#buc-008`，对应本目录的 BUC 合同。

## 交互合同总则

- 信息架构优先于视觉装饰：先让用户看见自己在哪、能做什么、下一步是什么。
- 风险与降级优先于装饰性状态：来源健康、数据不足、提醒暂停、归档恢复必须显式可见。
- 技术信号不得被解释为收益承诺、胜率或自动买卖指令。
- 桌面端必须同时覆盖 dense 与 focus；移动端必须有等价的 `mobile_tab` 导航。
- 本地恢复必须在首次加载和重开后都能给出可理解结果，不阻塞继续看盘。
