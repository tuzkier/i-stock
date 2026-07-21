---
name: bug-fix
description: '当存在 expected vs actual 偏差并需要缺陷闭环时使用：用户报告结果不对、输出丢失内容/样式、行为回归、线上异常、crash、测试失败指向产品行为缺陷、验证发现 AC 未通过，或审查员指出 correctness defect。'
---

# 缺陷修复

## 铁律

```
没有复现证据或 blocked 复现记录，不写修复代码。
```

## 何时使用

- 用户描述了 expected vs actual 偏差：结果不对、内容缺失、样式丢失、状态错误、输出与模板/规格/AC 不符
- 用户说有缺陷、线上异常、回归、crash
- 测试失败表现为产品行为缺陷，或验证中 AC fail
- correctness 审查员发现 High defect

## 典型表达

| 用户表达 | 路由原因 |
|----------|----------|
| "某个输出产物缺失了预期内容或样式" | 输出产物与预期不符，需要复现、根因、修复、回归闭环 |
| "这个接口返回结果不对" | 存在 expected vs actual 偏差 |
| "昨天还好的功能今天回归了" | 回归缺陷，需要缺陷闭环 |

## 边界

本技能不替代 `execute` 的代码修改，也不替代 `systematic-debugging` 的根因分析能力。它读取 `.harness/common/protocols/bug-fix/PROTOCOL.md`，保证复现、根因、修复、回归、验证和记忆决策闭环。

路由优先级：只要输入包含具体不符合预期的行为或产物，就先进入 `bug-fix`；只有在根因定位阶段才把 `systematic-debugging` 作为 carrier 调用。

按 `./workflow.md` 执行。
