---
name: project-lint
description: '当需要检查目标项目自身规范 / 规约时使用——代码变更范围、项目 lint profile、命令证据、原型 trace 规约和业务项目架构约束。修改业务代码后、verify 前、用户说"项目 lint"或"检查项目约束"时触发。'
---

# Project Lint — 项目约束检查

## 概述

`project-lint` 检查安装 Harness 后的目标项目自身规范 / 规约，而不是检查 Harness 模板、Adapter、Agent 运行纪律或阶段 Gate。

它读取 `project-knowledge/engineering/policies/project-lint.yaml`，结合本次变更文件、命令证据、原型 trace 规约和项目自定义外部命令，输出 Agent 可消费的确定性 findings。

**职责边界：**
- 模板只提供 linter 引擎、profile/report schema、bootstrap 脚本和 Gate 接入。
- 目标项目拥有 `project-knowledge/engineering/policies/*.yaml` 中的具体规则。
- Harness 升级可以覆盖 `.harness/common/skills/project-lint/`，不得覆盖目标项目已维护的 lint profile。

## 何时使用

- 修改了目标项目业务代码后（execute / bug-fix 落地代码后）
- `interaction` / 原型阶段产出 `visual-interaction-manifest.json` 后——此时原型设计规约（SURF↔SUC↔OBJ trace 脊柱 + FLOW / STATE / viewport 覆盖 + operable 原型规则）必须在原型阶段就被卡口，不能拖到 verify
- `verify` 阶段收集 command evidence 后
- Stage Gate 需要判断项目级约束是否满足时（代码变更或原型产物都会触发硬卡）
- 用户说"项目 lint"、"检查项目约束"、"project lint"
- `generate-context` 更新项目结构后，需要补齐项目 lint profile

`project-lint` 不只在交付末端运行，而是在**过程中**就执行：只要某个阶段产出了受约束的产物（代码、原型 manifest），就在该阶段当场跑 project-lint，`gate_effect=block` 立即停止，不把越界 / 不合规拖到后期。

## 检查维度

| 维度 | 检查内容 |
|------|---------|
| 变更范围 | 是否改到了目标项目 profile 声明的禁止路径 |
| 命令证据 | 代码变更后是否存在 fresh test / lint / typecheck 证据 |
| 原型设计规约 | 当项目 profile 启用 `prototype_trace` 且 mission 有原型产物时，检查原型是否符合项目设计规约：(1) SURF↔SUC↔OBJ trace 脊柱（委托 `trace-coverage-check`）；(2) FLOW / STATE / viewport 覆盖 + operable 原型规则（不可把 spec / review 文案混进产品 UI，委托 `visual-coverage-check`）。两者均委托内置 `harness interaction *` 命令，不重复实现 |
| 项目架构 | 通过项目配置接入 dependency-cruiser / semgrep / import-linter 等外部检查 |

不属于默认 `project-lint` 的 Harness / Agent 治理项：

- `AGENTS.md` 入口完整性：属于 adapter / agent 可操作性检查。
- Agent tool trace 重复调用：属于 execution / trace lint。
- `.harness/common/**` 模板一致性：属于 harness-lint / install-update 流程。

如果目标项目把 Agent / trace / Harness 模板治理也明确列入自己的工程规约，可以在 profile 中显式配置对应段落；缺省不启用。

## 安装后 Bootstrap

首次安装到目标项目后，可运行：

```bash
python .harness/common/skills/project-lint/scripts/bootstrap_project_lint.py --root .
```

该脚本只生成候选 `project-lint.generated.yaml`，不把推断出的架构规则直接变成 blocking 规则。

按 `workflow.md` 执行详细步骤。
