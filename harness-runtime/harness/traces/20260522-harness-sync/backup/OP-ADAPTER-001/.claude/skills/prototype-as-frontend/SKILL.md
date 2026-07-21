---
name: prototype-as-frontend
description: '当 prototype.delivery_mode=frontend_engineering 且 Mission Slice control_plane.stage=interaction 时使用——原型阶段的产出不是 HTML 变体 + spec 文档，而是由 frontend-prototype-engineer 对长期前端工程做 surface patch（真页面 + 真组件 + MSW + shared types draft），让用户在浏览器走查 PRD 列出的所有用户 path。仅处理 frontend_engineering 路线；interactive_prototype 路线请用 interaction skill。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# Prototype-as-Frontend — stage: interaction（原型即前端交付）

## 概述

`control_plane.stage=interaction` 在 `prototype.delivery_mode=frontend_engineering` 路线下的专属 skill。先从 PRD 的用户任务、信息架构和领域可见性决策推导前端 surface，再把产品定义、领域模型和 API 草案落成对长期前端工程的 patch，产出可运行前端代码 + `frontend-changeset.md` + `contracts/prototype-as-frontend.contract.yaml`，由 `frontend-prototype-engineer` 执行、`frontend-reviewer` 审查。

## 何时使用

- Mission Slice `control_plane.stage=interaction`
- `harness config snapshot` 返回 `prototype.delivery_mode=frontend_engineering`
- PRD 已完成（产品定义包 + API 草案 + prd.contract.yaml 存在并 PASS）
- 用户说"做前端 / 做原型即前端 / 把前端工程搭起来"

## 何时不使用

- `prototype.delivery_mode=interactive_prototype` → 转到 `interaction` skill
- `control_plane.stage=solution` → 转到 `solution` skill
- `control_plane.stage=technical_analysis` → 转到 `technical_analysis` skill
- `control_plane.stage=execute` → 转到 `execute` skill
- PRD 还未完成 → 先 `prd` skill

## 设计原则

interaction stage 共性原则（与 `interaction` skill 一致，两 skill 各自完整声明）：

- **领域驱动，但不机械界面化**：surface / 状态 / 用户动作必须从 PRD 领域模型推导；领域模型是底层事实来源，不是页面目录、组件树或字段清单
- **信息架构优先**：先明确 primary user tasks、navigation model、页面层级和决策顺序，再实现组件
- **领域可见性决策**：关键领域概念必须分类为 primary object / supporting context / state indicator / action affordance / hidden internal，并说明展示、折叠、合并或隐藏原因
- **Surface 优先 + baseline**：把前端工程视为 living codebase，本次 mission 是它的 patch；非 create 改动引 baseline
- **可追溯**：每条改动 traces_to AC + 关联领域实体或动作
- **状态完整**：覆盖加载 / 空态 / 错误 / 权限 / 取消 / 重复 / 边界
- **中文文案默认**：用户可见文字默认中文；外语例外有理由
- **PRD 回流**：发现需要改 PRD / 领域 / AC / 范围时，停下来发 Decision Gate
- **E2E locator 准备**：关键可交互元素准备 testid / aria，可断言点列在 changeset；本阶段**不写 / 不跑** e2e
- **长期沉淀**：可复用 pattern / type / locator 约定标为 project-knowledge 候选

本路线（frontend_engineering）专属：

- **效果优先，质量后补**：本阶段证明效果到位（用户走查所有 path 通过）；质量门（lint / coverage / a11y 评分 / e2e 充分性）由 code-review / verify 承接
- **shared types draft**：`lib/types/**` 是 draft；freeze 由 tech-design 完成
- **MSW 仅 interaction 阶段用**：execute 切真 API 后不作契约证据

## 快速参考

| 步骤 | 产出 |
|------|------|
| Stage 初始化 + delivery_mode / frontend_project_root 解析 | inputs |
| 用户任务 / 信息架构 / 领域可见性 + Surface baseline 判断 + `frontend-changeset.md` 起草 | changeset |
| 实现 / 修改 / 扩展 surface + `lib/types/` draft + MSW handlers + scenarios | 前端工程 |
| 填外部 contract（CLI 路径） | `prototype-as-frontend.contract.yaml` |
| frontend-reviewer 循环（四维 verdict） | role_verdicts |
| 用户浏览器走查所有 path checkpoint | user_acceptance |
| Artifact Gate 自检 | gate run PASS |

按 `workflow.md` 执行详细步骤。
