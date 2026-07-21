---
knowledge_type: pattern
status: draft
source: init
confidence: needs-review
---

# Testing Patterns

Project-specific test examples and validation rules promoted from verification,
code review, and accepted implementation work.

## Fixture-first 验收矩阵

来源：mission:20260522-stock-watch-system。状态：accepted。置信度：high。

- 多市场看盘核心路径应以冻结样本和 replay corpus 作为门禁输入，覆盖四市场标的、歧义输入、指标充足/不足、MTS 强信号/风险、提醒触发、来源降级和浏览器重开恢复。
- 用户可观察 UI 路径使用 Playwright E2E 验证；领域状态机和数据 envelope 使用 `node --test` replay/unit 验证。
- 本地持久化恢复必须验证真实写入后的 reload/reopen，而不是只验证纯函数 roundtrip。
- 投资信号文案测试应包含负向断言：不得出现收益承诺、胜率或确定性买卖建议。
