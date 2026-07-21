---
name: quality-control
description: '当用户要求质量评估、Stage Gate 出现 evidence 缺口、验证证据不足、审查员 HOLD、或需要跨阶段质量治理时使用。'
---

# 质量控制

## 铁律

```
质量结论必须同时引用程序化证据和语义判断；两者不能互相替代。
```

## 何时使用

- 用户要求检查质量、架构、正确性、安全、测试充分性或验收证据
- Stage Gate 出现 evidence 缺口或 contract WARN / FAIL
- 验证中 AC 证据不足
- 审查员 HOLD 需要分类、修复闭环或风险接受
- 复盘发现重复质量问题

## 边界

本技能不替代 `code-review` 的具体审查员，不替代 `verify` 的验收，也不替代 `stage-gate` 的程序化 Gate。它读取 `.harness/common/protocols/quality-control/PROTOCOL.md`，组织证据、分类 findings、推动修复闭环和记忆决策。

按 `./workflow.md` 执行。
