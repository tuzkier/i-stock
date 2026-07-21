# Codex 模板约定

## 先说结论

HarnessV2 在 Codex 里不能照搬 Cursor 的加载模型。

`Cursor` 的主入口是 `.cursor/rules/*.mdc` + hook。
`Codex` 在已安装目标项目中的主入口是**目标项目根 `AGENTS.md`**。该文件的模板源是 `package/adapters/codex/AGENTS.md`；HarnessV2 源码仓库根 `AGENTS.md` 只服务维护本仓库本身。HarnessV2 默认不安装 `.codex/`；`.codex/rules/*.rules` 只在项目需要命令执行策略时另行添加。

所以，Codex 适配的原则只有一条：

> **AGENTS-first。**
> 根 `AGENTS.md` 负责把 Codex 引到正确的规则、工作流和状态文件，但不承担完整百科索引。

根 `AGENTS.md` 是启动胶囊：默认只读它。完整阶段、技能、Agent、runtime 路径索引移到 `.harness/docs/harness-navigation.md`，只有在需要全貌、排查引用或人工查表时再读取。

## Codex 的规则层级

当前 Codex 会话里，真实有效的约束层从上到下是：

1. **Codex App/System 固定层**
 运行时、工具、输出格式、权限、协作模式。这层项目改不了。
2. **全局 Home 层**
 例如 `~/.codex/AGENTS.md`、`~/.codex/config.toml`、全局技能。
3. **项目层**
 根 `AGENTS.md` 会按目录作用域注入到当前项目。
4. **技能发现层**
 会话里已经被 Codex 列出的技能，属于原生可发现能力。
5. **手动引用层**
 例如 `.harness/common/rules/*`、`.harness/common/skills/*`、`.harness/common/agents/*`。这些文件只有在 `AGENTS.md` 或当前任务显式引导时才会被读取。

## 哪些会自动生效，哪些不会

| 资产 | 是否自动生效 | 用法 |
|------|-------------|------|
| 根 `AGENTS.md` | 是 | 项目级轻量主入口 |
| 作用域内其他 `AGENTS.md` | 是 | 子目录覆盖/补充 |
| `.codex/rules/*.rules` | 不默认安装 | Codex 命令执行策略，不进入 Harness 行为规则链 |
| `.harness/common/skills/*` | 否 | 作为共享工作流正文手动读取 |
| `.harness/common/agents/*` | 否 | 作为 Harness 子 Agent 角色定义，在 workflow 调用对应子 Agent 时读取 |
| `~/.codex/prompts/*` | 仅在显式调用命令时 | 全局 slash prompt，不是 Harness 主入口 |

**不要假设**项目内 `.codex/rules/` 或 `.codex/skills/` 会像 Cursor 规则一样自动注入行为规则。当前模板不靠这个假设。

## HarnessV2 在 Codex 中的映射

| Harness 概念 | Cursor / Claude | Codex |
|-------------|------------------|-------|
| 规则入口 | `.cursor/rules/harness.mdc` / `CLAUDE.md` | 根 `AGENTS.md` |
| 规则适配层 | 原生自动加载 | `AGENTS.md` 引导读取公共规则 |
| 工作流正文 | `.harness/common/skills/*` | 直接读取 `.harness/common/skills/*` |
| 角色化子 Agent | 预定义 Agent 文件 + 任务项 | workflow 明确声明“调用 `<name>` 子 Agent” |
| 自动继续机制 | stop hook | 主 Agent 自驱 loop |

## Codex 子 Agent 调用授权

在 Codex 运行时中，Harness workflow 出现“调用 `<name>` 子 Agent”“并行调用以下子 Agent”“审查子 Agent 必须 PASS”等表述时，视为本项目对 Codex 使用 sub-agent / delegation / parallel agent work 的明确授权。

Codex 主 Agent 应按 workflow 声明调用对应子 Agent，并读取 `.harness/common/agents/<name>.md` 作为角色定义和输出契约。除非用户在当前对话中明确禁用子 Agent，否则不得以“缺少授权”为由跳过 Harness workflow 要求的子 Agent 调用；若当前运行环境无法调用指定子 Agent，阶段必须停在 Gate 并报告 BLOCKED，不得由主 Agent 自审自批。

## Agent 调用映射

Codex 当前不是“预注册很多 Harness 角色文件”的模型。HarnessV2 在 Codex 中只声明要调用的子 Agent 名称，不声明底层工具名。

所以 HarnessV2 里的 `.harness/common/agents/*.md` 在 Codex 中的角色是：

- **角色定义**
- **职责边界说明**
- **阶段工作流和 `professional_roles.stage_policies` 的调度依据**

推荐映射：

| Harness 角色类型 | Codex 调用要求 |
|-------------|------------|
| 执行类 Agent（如 `general-engineer`、`senior-product-expert`、`solution-architect`） | 能读取角色定义、执行阶段任务、返回 `DONE` / `BLOCKED` |
| 审查类 Agent（如 `correctness-reviewer`、`spec-reviewer`、`tdd-reviewer`） | 能只读审查材料包、返回 `PASS` / `HOLD` / `BLOCKED` |
| 多个互不冲突的问题并行修复 | 能按 workflow 并行调用多个子 Agent，并按 Harness 角色返回结果 |

### 角色调度语义

Harness workflow 中的“多个子 Agent”不是装饰性角色清单。Codex 主 Agent 必须按依赖关系把它们调度成可执行 DAG：

- `required_execution_roles` / `required_review_roles` / dispatch plan 中的 `primary_executors`、`supporting_executors`、`reviewers` 都是角色集合，不是串行 for-loop。
- 同一阶段内没有产物依赖、没有共享写入范围、材料包可独立准备的执行角色，必须并行调用。
- 产物生成者与审查者存在依赖，必须先产出再审查；同一审查 barrier 内的只读 reviewer 必须并行调用。
- execute 阶段必须先做执行单位批次规划：多个 Atomic Task 若 `depends_on` 为空或已满足、`write_scope` 不相交、不会编辑同一测试 / fixture / 生成物，就应放入同一 parallel batch，由对应专家 Agent 并行执行。
- 若无法证明独立性，才保守串行，并记录 `parallelization_decision: conservative_serial`。
- 不能把多个 required role 压缩成一个通用 Agent，也不能只调用列表中的第一个角色后宣称本阶段完成。

落地规则：

- 阶段工作流只写“调用 `<name>` 子 Agent”，不写底层工具名。
- 阶段工作流不写具体模型名；Codex 通过 `harness-cli` 的 `harness config snapshot --json` 获取模型路由摘要，reviewer 默认优先高级模型，执行 Agent 默认使用执行候选，候选不可用时回退主 Agent 模型。
- Codex 主 Agent 必须读取 `.harness/common/agents/<name>.md` 作为该角色的职责和输出契约。
- execute 阶段派发子 Agent 时，材料包第一段必须声明 `execution_context.skill=execute`，并写明 role package 路径；不能只用“你是 `<name>`”的临时 prompt 替代 Harness skill 和角色定义。
- 要求改代码的角色必须有独立执行范围和可回传变更摘要。
- 只读审查角色不得修改产物，只返回裁决、证据和阻断项。
- 不存在角色定义文件时，调度结果必须是 `BLOCKED`，不得临时改由主 Agent 自审自批。

### 运行时承载边界

本节只说明 Codex 对 Harness 子 Agent 调用的承载要求，不是 `autonomy-loop` 的控制规则。Harness workflow 只声明子 Agent 名称，并只消费 `DONE` / `PASS` / `HOLD` / `BLOCKED` 等结果。

Codex 运行时需要满足：

- 能按子 Agent 名称解析 `.harness/common/agents/<name>.md` 的角色定义。
- 能为执行类角色返回 `DONE` / `BLOCKED`。
- 能为审查类角色返回 `PASS` / `HOLD` / `BLOCKED`。
- 无法调用指定子 Agent 时返回 `BLOCKED`，不得伪造 PASS。
- 用户明确禁用子 Agent 调用时，由 workflow 记录降级决策和风险。

## Codex 下的恢复协议

Codex 运行 HarnessV2 时，主 Agent 不依赖 hook。恢复按需执行：只有用户说继续、存在 active mission、当前任务需要 Harness 状态，或 workflow 进入阶段推进时，才读取状态并恢复。

1. 调用 `harness-cli` 获取运行配置快照
2. 调用 `harness-cli` 获取当前 Mission 状态
3. 调用 `harness-cli` 获取 Board / Work Graph / 当前 active mission 的 Mission Slice 快照（若存在）
4. 执行执行日志 recover
5. 执行 git-workflow recover
6. 读 `project-context.md`（如果存在）
7. 有活跃任务时再装配当前 mission contract
8. 再进入 `autonomy-loop`

这套协议仍然成立；区别只在于：

- **触发者不是 hook，而是主 Agent 自己**
- **规则入口不是 `.cursor/rules/core.mdc` 自动注入，也不是启动时全量加载；`AGENTS.md` 只保留轻量入口，路由交给 `skill-router`，规则按 workflow / Gate 需要读取**
- **恢复不是启动全文加载**：无 active mission 或用户只是提问时，不应主动读取全部规则、技能、Agent 或状态文件。

## 当前实现边界

当前 Codex 接入的边界明确：

- 已支持：Codex 用户进入项目后，有明确入口、规则映射、子 Agent 调用授权、状态恢复方式
- 已支持：Codex 能按 HarnessV2 的文档链和治理边界工作，不需要猜 Cursor 机制
- 已支持：规则 / 技能 / Agent 的权威正文集中在 `.harness/common/`
- 未做：完整 `.codex/skills/` 镜像
- 未做：提供 Codex 原生自定义 Agent 注册器；当前由 Codex 主 Agent 按 workflow 读取角色文件并调用子 Agent
- 未做：任何“本地 `.codex/rules/*.md` 会自动生效”的伪装

## 推荐读取顺序

在 Codex 中进入 HarnessV2 项目后：

1. 根 `AGENTS.md`
2. 如果只是普通问答，直接回答；如果需要完整索引，再读 `.harness/docs/harness-navigation.md`
3. 如果命中具体阶段或技能，再读当前阶段对应的 `.harness/common/skills/<skill>/SKILL.md` 和 `workflow.md`
4. 如果 workflow 明确要求规则，再读对应 `.harness/common/rules/<rule>.md`
5. 如需 sub-agent，再读对应 `.harness/common/agents/<role>.md`
6. 如需恢复 active mission，再通过 `harness-cli` 读取 Mission / Board / Work Graph / trace 状态

这就是 Codex 版 HarnessV2 的主路径。
