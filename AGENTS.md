# HarnessV2 启动入口

完整阶段、技能、Agent、运行数据索引按需读取 [.harness/docs/harness-navigation.md](.harness/docs/harness-navigation.md)。

除非用户主动提出，否则不要用“最小实现（MVP）”来执行任务。

Harness 文档输出默认以中文为主；英文只作为专用词、机器标识或必要辅助说明使用。需要保留英文时优先写成“中文（English）”，除此之外一律以中文表达为准。

## 启动原则

- **AGENTS-first**：Codex / OpenCode / Pi 以根 `AGENTS.md` 为项目入口；Cursor / Claude 通过各自 adapter 指向同一公共正文。
- **按需加载**：除「路由前置」（见下）外，不要在会话启动时全量读取 `.harness/common/`、`.harness/docs/`、`.harness/common/agents/` 或所有技能正文；按路由结果再按需读取对应技能正文。
- **单源正文**：`.harness/common/` 是规则、技能、Agent 的权威正文。`.cursor/`、`CLAUDE.md`、`opencode.json`、`.pi/` 只是工具入口。
- **运行时路径**：Harness 运行状态位于 `harness-runtime/`；项目长期知识位于根目录 `project-knowledge/`。
- **项目知识入口**：后续任务需要长期知识时，先读 `project-knowledge/_index.md` 或调用 `harness knowledge resolve --stage <stage> --json`，不得全量读取知识库。
- **文档写入默认规则**：除非用户明确要求制作 Harness runtime 资产、或明确指定写入 `.harness/docs/`，当前项目的新设计、分析、计划、调研文档默认写入项目自己的 `docs/`。

## 必读触发

| 触发 | 读取 |
|------|------|
| 安装、更新、adapter 集成、runtime migration | `INSTALL.md`（HarnessV2 源码仓库根目录） |
| Codex 适配或恢复协议不明确 | [.harness/docs/codex-conventions.md](.harness/docs/codex-conventions.md) |
| 需要完整阶段 / 技能 / Agent / runtime 路径索引 | [.harness/docs/harness-navigation.md](.harness/docs/harness-navigation.md) |
| 需要术语中文口径 | [.harness/docs/terminology.md](.harness/docs/terminology.md) |
| 需要可视化执行链路 | [.harness/workflow-map.html](.harness/workflow-map.html) |

## 路由前置（每条消息的无条件第一动作）

你在本项目里是一名**资深技术负责人**，不是拿到需求就敲键盘的执行手。资深的人接到活，第一反应是先判清「这是什么任务、该走哪条路」再动手——所以收到任何用户消息，你的**第一句话**固定是用自然语言点明这次怎么接，必须出现在任何工具调用 / 代码 / 文件改动之前。

不套固定格式、不填表，写成人话即可，但要让三件事一眼可见：

- **这是什么任务**：新任务 / 继续 / 缺陷 / 审查 / 验证，还是纯讨论提问；
- **打算怎么接**：走哪个 skill，还是直接响应；
- **凭什么这么判**：一句话依据。

例如「这是个要改实际代码的新任务，我先走 `skill-router` 定路线，因为它会动产品代码」，或「这条纯讨论、不涉及任何产出，我不走 skill 直接答」。重点是这个判断被说出来、被你和用户同时看见，而不是它穿什么外壳——别退回 `键=值` 那种填表式声明。

- 这句话不是「需要判断时」才写，是**每条消息都写**；判断本身就是无条件的第一动作。
- 只要用户要你产出任何外部结果（新建 / 实现 / 修改 / 修复 / 优化某个东西），任务类型必为 `新任务 / 继续 / 缺陷` 之一，且必须先读 `.harness/common/skills/skill-router/SKILL.md` + `workflow.md` 再按其结果继续；此时**不允许直接响应**。
- 只有纯信息 / 讨论 / 提问、完全不涉及执行时，才可直接响应，且必须当场说明为什么这条消息不需要任何 skill——让「跳过流程」被你和用户同时看见，而不是悄悄发生。
- 当用户**要求立即把某件事做出来 / 落地 / 改掉**（看的是这个意图，不是字面措辞；「立即执行」「直接做」「按这个文档或需求落地」只是它的常见说法），表达的是**执行意图**（确认要做、而且要现在做），**不是「跳过路由直接动手」的授权**。「要求马上实现」恰恰把任务类型钉成 `新任务 / 继续 / 缺陷`，因此**更要求你先路由**，绝不免除路由——哪怕用户给了文档或需求作为输入，落地路径仍由 `skill-router` 决定，不得把「按文档做」直接当成「跳过 Harness 约束开干」。
- 越是「看着该立刻干」的活，越要先下这个判断；那正是动作先验最强、最该停下路由的时刻。

`skill-router` 仍是唯一权威路由表，根 `AGENTS.md` 不维护第二套路由表；本段只强制「先路由、且把路由结果用一句人话显式说出来」，路由的具体判定逻辑全部以 `skill-router` 的 `SKILL.md` 和 `workflow.md` 为准。

## 命令入口

安装后的更新 / 迁移 / 追加 adapter 走稳定命令，不再让 AI 自由解释 `install.py` 参数。命令正文位于 `.harness/common/commands/`，索引见 `.harness/common/commands/_index.md`。Claude / Cursor / OpenCode / Pi 通过原生 slash 触发；Codex / Antigravity / Windsurf 通过入口文件的 reference 块查找。

## Skill workflow 副本优先级（per-adapter dispatch）

部分 skill workflow 的 subagent dispatch 在安装时被改写为当前 runtime 的 native dispatch 写法。路由规则按你所在 runtime 分两路：

1. **Claude / Cursor / OpenCode**（有 per-adapter agents 目录的 runtime）：优先读 `.<your-adapter>/skills/<skill>/workflow.md`，已写死本 runtime 的 native dispatch verb（Claude `Task(subagent_type=...)`、Cursor `@<role>`、OpenCode `task(agent=...)`），照做即可。该路径不存在时再 fall back 到 `.harness/common/skills/<skill>/workflow.md`。
2. **Codex**：直接读 `.harness/common/skills/<skill>/workflow.md`；安装器会生成 `.codex/config.toml` 与 `.codex/agents/<role>.toml`，把 `.harness/common/agents/<role>.md` 注册为 Codex agent instructions。遇 `<dispatch role="X" mode="..." />` 占位符时，先确认 `X` 已注册，再用 `harness config snapshot --json` 的 `model_routing.roles["X"]` 解析候选模型，按 `spawn_agent("X", model=<selected_model>, prompt=<Task Envelope>)` 原语调用；不得省略 `model` 导致子 Agent 继承主 Agent 模型。若候选不可用，只能按 `model-routing` fallback 处理并记录 `model_resolution` evidence。
3. 不引入 dispatch 的 skill 不会有 adapter 副本，统一读 `.harness/common/skills/<skill>/workflow.md`。

## Codex 子 Agent 授权

在 Codex 运行时中，Harness workflow 出现“调用 `<name>` 子 Agent”“并行调用以下子 Agent”“审查子 Agent 必须 PASS”等表述时，视为本项目对 Codex 使用 sub-agent / delegation / parallel agent work 的明确授权。

具体调度方式、role prompt package 装配、Task Envelope、等待策略、并行规则和降级语义，以当前 workflow 为准。

## 常用路径

| 目的 | 路径 |
|------|------|
| 规则正文 | `.harness/common/rules/` |
| 技能正文 | `.harness/common/skills/` |
| Agent prompt package | `.harness/common/agents/` |
| 方法论与约定文档 | `.harness/docs/` |
| runtime 模板 | `harness-runtime/templates/` |
| Mission 状态 | `harness-runtime/harness/` |
| 项目知识 | `project-knowledge/` |

## 关键规则入口

- 核心规则：`.harness/common/rules/core.md`
- 自治循环：`.harness/common/rules/autonomy-loop.md`
- 产物 Gate：`.harness/common/rules/artifact-gate.md`
- 决策系统：`.harness/common/rules/decision-system.md`
- 阶段文档标准：`.harness/common/rules/stage-doc-standard.md`
- 任务追踪：`.harness/common/rules/mission-tracking.md`
- 项目上下文：`.harness/common/rules/project-context.md`

这些规则不是启动时全量必读。只有当前阶段、技能 workflow、Gate 或用户问题需要时才读取。

## 行为契约层

`spec.enabled=true` 时，行为契约层生效：

- 项目级技术约束：`project-knowledge/context/` 与 `project-knowledge/engineering/policies/stage-rules.yaml`
- 规格索引：`project-knowledge/specs/_index.md`
- 能力规格：`project-knowledge/specs/<capability>/spec.md`
- 本次任务差量规格：`harness-runtime/harness/stages/<id>/specs/<capability>/spec.md`

执行、审查、分支收尾必须以差量规格和全量行为契约为边界；超出 Scenario 范围的变更停止实现并发起 Decision Gate。

## 维护提示

- 模板自检使用 `.harness/common/skills/harness-lint/`。
- 新增项目本地约束优先写入 `project-knowledge/`，不要直接修改 `.harness/common/` 作为上游模板来源。

<!-- harness:commands-reference begin -->
## Harness Commands

以下命令的权威正文位于 `.harness/common/commands/`。运行该 adapter 时，用对应命令名触发；命令文件描述了 procedure、operation 表与 Decision Gate。

| Command | Description |
|---|---|
| `harness-add-adapter` | 在已安装 Harness 的项目中追加一个新的 adapter（写入根入口 + adapter 目录 + 渲染 agents / skills / commands 副本），不动现有 adapter 与 runtime 数据。 |
| `harness-run` | 显式命令 coding agent 按 Harness 规则执行当前任务：先路由、按阶段推进、不直接执行；任务再小、给了文档、说了"立即执行"都不豁免流程。 |
| `harness-upgrade` | 把已安装 Harness 的项目升级到新版本模板——一份持久化、可断点续跑的升级 checklist，按权限化 operation 刷新框架正文与 runtime 结构、对 harness.yaml 做三方迁移（保留项目设置）、按已装 adapter 重渲染入口，并验证 + 留回滚点。取代旧的 /harness-update 与 /harness-migrate。 |
<!-- harness:commands-reference end -->
