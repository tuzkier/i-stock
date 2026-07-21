---
name: project-lint
description: '当需要检查目标项目本身是否被 Agent 稳定约束时使用——代码变更范围、项目 lint profile、命令证据、轨迹规则和业务项目架构约束。修改业务代码后、verify 前、用户说"项目 lint"或"检查项目约束"时触发。'
---

# Project Lint — 项目约束检查

## 概述

`project-lint` 检查安装 Harness 后的目标项目，而不是检查 Harness 模板自身。

它读取 `project-knowledge/engineering/policies/project-lint.yaml`，结合本次变更文件、命令证据和可选执行轨迹，输出 Agent 可消费的确定性 findings。

**职责边界：**
- 模板只提供 linter 引擎、profile/report schema、bootstrap 脚本和 Gate 接入。
- 目标项目拥有 `project-knowledge/engineering/policies/*.yaml` 中的具体规则。
- Harness 升级可以覆盖 `.harness/common/skills/project-lint/`，不得覆盖目标项目已维护的 lint profile。

## 何时使用

- 修改了目标项目业务代码后
- `verify` 阶段收集 command evidence 后
- Stage Gate 需要判断项目级约束是否满足时
- 用户说"项目 lint"、"检查项目约束"、"project lint"
- `generate-context` 更新项目结构后，需要补齐项目 lint profile

## 检查维度

| 维度 | 检查内容 |
|------|---------|
| 变更范围 | 是否改到了受保护的 Harness 框架资产或任务禁止路径 |
| 命令证据 | 代码变更后是否存在 fresh test / lint / typecheck 证据 |
| Agent 指令 | `AGENTS.md` 是否至少包含 setup / test / style / delivery 指令 |
| 轨迹规则 | 是否出现重复工具循环、缺少必要命令证据等可确定违规 |
| 项目架构 | 通过项目配置接入 dependency-cruiser / semgrep / import-linter 等外部检查 |

## 安装后 Bootstrap

首次安装到目标项目后，可运行：

```bash
python .harness/common/skills/project-lint/scripts/bootstrap_project_lint.py --root .
```

该脚本只生成候选 `project-lint.generated.yaml`，不把推断出的架构规则直接变成 blocking 规则。

按 `workflow.md` 执行详细步骤。
