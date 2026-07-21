---
name: design
description: '设计阶段路由入口（routing-only）。design 阶段不再有合一 workflow，按 Mission Slice control_plane.stage 路由到 interaction / solution / technical_analysis 三个独立 skill 之一。用户说"设计一下""怎么实现""技术方案"但尚未确定具体设计 stage 时由本 skill 指引选择。'
---

# Design — 设计阶段路由入口（M5 REFACTOR-DESIGN-SKILL-SPLIT 后）

design 聚合阶段已被拆分为三个独立 stage skill。本 SKILL.md 仅作为路由入口，**没有 workflow.md**——具体执行流程在对应 stage skill。

## 路由表

| Mission Slice 信号 | 路由到 | 对应 skill |
|---|---|---|
| `control_plane.stage=interaction` | 用户旅程 / 状态矩阵 / 视觉资产 | [`interaction`](../interaction/SKILL.md) |
| `control_plane.stage=solution` | 方案路线选择 / 关键决策 | [`solution`](../solution/SKILL.md) |
| `control_plane.stage=technical_analysis` | 模块/接口/数据/验证策略 + Agent 实现 | [`technical_analysis`](../technical_analysis/SKILL.md) |

## 何时路由到 design 入口

仅当：
- 用户说"设计一下 / 怎么实现 / 技术方案"但尚未确定具体设计 stage
- Mission Slice 缺少明确的 `control_plane.stage`，但用户意图属于设计域

此时先用 `harness frame current --json` 查 mission_slice 是否声明了 `control_plane.stage`；若已声明，直接路由到对应 stage skill；若未声明，向用户 AskUserQuestion 确认要做哪条 stage：

| 选项 | 含义 |
|------|------|
| interaction | 用户旅程 / state matrix / 视觉资产 |
| solution | 方案路线选择、关键决策、tradeoff |
| technical_analysis | 模块/接口/数据/验证策略 + Agent 实现 |

确认后由 Board Router / Mission Slice 创建流程写入对应 `control_plane.stage`，再触发对应 skill。

## Stage 单一性硬约束

设计三 stage **必须分次启动，不能在同一个 mission slice 中顺跑全链**。每次只处理 Mission Slice 指向的一个 stage：

- `interaction` skill 只允许 Write `interaction.md` + `visual-interaction/variants/**` + `visual-interaction/design-brief.md`
- `solution` skill 只允许 Write `solution.md`
- `technical_analysis` skill 只允许 Write `tech-design.md`（除 `## Agent 实现` section）+ `solution.md ## Agent 架构` section（仅 capability-designer）

物理 enforcement 由 `design.<lane>.json` overlay + `harness solution lane-action-validate` CLI + lane-specific PreToolUse hook 三层覆盖。

## capability-design 嵌入实现

Agent 能力设计由 `agent-capability-designer` / `agent-capability-reviewer` 作为 `solution` 与 `technical_analysis` skill 的条件角色实现（`agent_engineering.enabled=true` 时启用），写 `solution.md ## Agent 架构` section + `tech-design.md ## Agent 实现` section。**不再有独立 capability-design skill**（M5 REFACTOR 推荐方案 a）。

### 为什么不留独立 capability-design skill

按 [work-item-board-operating-model.md](../../docs/work-item-board-operating-model.md) 权威 lane 模型，capability-design **不是独立 stage**，而是 solution / technical_analysis 两 lane 各自内部的 sub-action：

- solution lane 内：写 `## Agent 架构`（高层架构 + 六种工作权设计）
- technical_analysis lane 内：写 `## Agent 实现`（implementation_loci + eval_scenarios + hook 配置）

立独立 skill 会带来三个问题：

1. **违反 stage 单一性**：同 mission slice 里就出现两个设计 stage 触发，需要额外 overlay / hook / lint 处理
2. **数据流断裂**：当前 capability-designer 直接读写两 lane 的 `*.md` 与 `*.contract.yaml`；独立 skill 必须经 `<call skill>` 间接传 path，多一层胶水
3. **触发条件已被 CLI 覆盖**：`harness tech-design check-capability-trigger` 已自动判定 `mission-contract.## Agent Engineering` 或 `prd.contract.yaml.agent_capability_requirements` 是否非空；触发后 dispatch 的代码 ~15 行，重复在两 workflow 里也是 acceptable

### 真问题（已知技术债）

solution skill step-5 + technical_analysis skill step-2 的 capability dispatch + reviewer loop 大约 15 行 XML 重复 2 处。如果未来要 DRY，**优先方案是 sub-routine 文档**而不是独立 skill：

- 创建项目级文档 `agent-capability-design-procedure.md`（**文档**，非 skill；放置位置由项目文档目录决定）
- 两 workflow `<include ref="agent-capability-design-procedure.md" />` 引用同一段 dispatch 描述
- 仍保持 dispatch 由本 lane skill 主流程执行，不引入独立 skill 路由

此项尚未做。已记入项目文档 `cli-backlog.md` 的「共性观察」段（capability dispatch DRY 跟进项），不在本 skill 范围内。

## 历史

REFACTOR-DESIGN-SKILL-SPLIT 之前，design 阶段是合一 skill（`design/workflow.md` 单文件 303 行），通过 `<check if="stage=...">` 三分支路由。M5 拆出独立 skill 后：

- `design/workflow.md` 删除（合一形态废弃）
- `capability-design/` 空目录删除（推荐方案 a，capability-design 改为嵌入式实现）
- `interaction/`, `solution/`, `technical_analysis/` 三独立 skill 接管
