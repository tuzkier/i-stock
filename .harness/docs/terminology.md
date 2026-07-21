# HarnessV2 术语表

本文定义 HarnessV2 文档中的术语口径。正文以中文为主；文件名、配置字段、命令、状态码、工具名、行业通用缩写、真实专名，以及 Harness 控制面专用词可保留英文标识，但必须有清楚的中文说明。

## 写作原则

1. 普通 Harness 概念首次引入时可使用“中文（English）”，后续正文使用中文。
2. 文件名、目录名、字段名、命令和代码标识不翻译，例如 `mission-contract.md`、`project-context.md`、`execute_mode`。
3. `Agent`、`sub-agent`、`Checkpoint`、`Decision Gate`、`Stage Gate`、`Artifact Gate`、`Hard Gate`、`Soft Gate` 是 Harness 专用词，正文可保留英文标识；首次出现或面向用户说明时必须写清中文含义。
4. 工具和产品名不翻译，例如 HarnessV2、Codex、Cursor、Claude Code、Graphify、OpenCode。
5. 行业缩写按原文保留，必要时在首次出现时解释，例如 PRD、TDD、SDD、E2E、API。
6. 不使用半中文半英文的随意拼接；如果英文是专用词，前后用空格分开，例如“主 Agent 调度 sub-agent”“Stage Gate 检查”。

## 核心术语

| 中文术语 | 英文原词 | 使用说明 |
|----------|----------|----------|
| 任务 | Mission | 一次由 Harness 管理的完整工作单元。涉及文件名时保留 `mission`。 |
| 任务契约 | Mission Contract | 定义目标、范围、验收标准、执行治理级别和升级规则的入口文档。文件名保留 `mission-contract.md`。 |
| 自治循环 | Autonomy Loop | 主 Agent 的恢复、选择、调度、验证和继续推进机制。 |
| 技能 | Skill | 可执行工作流单元。具体技能名保留英文标识，例如 `execute`、`verify`。 |
| Agent | Agent | 角色化执行者或审查者。具体 Agent 文件名保留英文标识。 |
| sub-agent | Sub-agent | 由主 Agent 派发的独立执行上下文。 |
| 审查 Agent | Reviewer Agent | 执行审查职责的 sub-agent 统称。 |
| 工作流 | Workflow | 技能的具体执行步骤。文件名保留 `workflow.md`。 |
| 阶段文档 | Stage Docs | 当前 Mission Slice action 产出的正式文档与证据材料。 |
| Checkpoint | Checkpoint | 需要人工确认后才能继续的暂停点。 |
| Decision Gate | Decision Gate | 主 Agent 不应自行决定时触发的人工决策机制。 |
| Stage Gate | Stage Gate | 阶段切换前的程序化和语义检查。 |
| 控制契约 | Control Contract | 阶段文档对应的结构化 YAML 契约，是脚本检查的权威来源。 |
| 证据图 | Evidence Graph | 把验收标准、任务项、验证义务、证据和角色裁决连起来的事实图。 |
| 验证义务 | Obligation | 某个验收场景 / 任务项必须被什么证据证明的要求。字段名保留 `obligations`。 |
| 执行结果 | Execution Result | 执行类角色对本阶段产物和完成状态的结构化结果。字段名保留 `execution_result`。 |
| 角色裁决 | Role Verdict | 审查类角色给出的 PASS / HOLD / BLOCKED 等结构化裁决。字段名保留 `role_verdicts`。 |
| 行为规格 | Spec | 项目或能力的可验证行为契约。字段名和目录名保留 `spec`。 |
| 差量规格 | Delta Spec | 本次任务对行为规格的增量变更。 |
| 能力 | Capability | 可独立描述和验证的系统能力。目录名中保留 `capability`。 |
| Work Graph | Work Graph | 长期工作对象的事实源，保存 node、关系、Board 派生视图和 canonical artifacts。路径保留 `harness-runtime/harness/work-graph/`。 |
| 工作对象 | Node | Work Graph 中的单个工作事实，例如 requirement、solution、task、bug。字段名保留 `node` / `node_id`。 |
| Board | Board | 从 Work Graph node 派生出的看板视图，用 lane 表示粗粒度工作环节；不是事实源，事实源仍是 `nodes/**/*.yaml`。 |
| Lane | Lane | Board 上的粗粒度泳道，只使用 8 个 `*-lane` id：`requirement-lane`、`product-definition-lane`、`solution-lane`、`technical-analysis-lane`、`breakdown-lane`、`development-lane`、`verification-lane`、`delivery-lane`。Lane 是容器，不等于具体阶段。 |
| Stage | Stage | Lane 内部的细粒度任务生命周期步骤，例如 `intake`、`prd`、`solution`、`execute`、`code-review`、`verify`。Stage id 不带 `-lane` 后缀，且不得与 lane id 重名。 |
| Mission Slice | Mission Slice | 从 Work Graph 选出的本次可执行事务，绑定 mission、`control_plane.lane`、`control_plane.stage`、primary nodes 和 graph operation。 |
| Board Router | Board Router | 从 Board 选择可推进 node 并创建或恢复 Mission Slice 的技能。技能名保留 `board-router`。 |
| 图操作 | Graph Operation | 对 Work Graph node 事实源执行的结构化操作，例如 `advance_stage`、`advance_lane`、`split_node`、`merge_nodes`、`supersede_node`。 |
| 项目约束检查 | Project Lint | 目标项目改动范围、命令证据、执行轨迹和 Harness 资产保护的检查。技能名和报告名保留 `project-lint`。 |
| 可视化交互设计 | Visual Interaction | 为交互流程生成或归档 HTML / SVG 设计变体、manifest 和审查证据的控制面。技能名保留 `visual-interaction-design`。 |
| 原型合同 | Interaction Spec | interaction 阶段给下游 AI 消费的结构化原型实现合同，目录名保留 `interaction-spec/`，标准合同文件为 `interaction-spec/interaction-contract.md`；人类确认入口是独立原型工程目录中的主可操作原型，目录由 `prototype.interactive_prototype.prototype_project_root` 解析（默认建议 `prototype/`，git 跟踪、随 Mission 分支隔离，不在 `project-knowledge/` 下），`visual-interaction/` 只保存 manifest、变体和内部证据。 |
| Trace 脊柱 | Trace Spine | 贯穿 PRD → interaction-spec → 原型 → 验证的稳定 ID 绑定：界面边界 `SURF-xxx`、系统用例 `SUC-xx`、业务对象 `OBJ-xx`（对象轴，来自 `business-object-analysis.md`）、验收场景 `SCN-xx`。权威 binding 在 `surface-model.md#Surface 绑定脊柱` 与 `interaction.contract.yaml#surface_bindings`。 |
| Trace 锚点 | Trace Anchor | 原型里引用脊柱 ID 的两级标记：页面级声明块（harness 注释含 `surf/suc/obj/scn`）+ 元素级 `data-surf`/`data-suc`/`data-obj`（同时复用为 E2E 定位器）。ID 引用上游真源、永不回收、不在原型新造。 |
| Trace 对账 | Trace Coverage Check | `harness interaction trace-coverage-check`：PRD 清单 ↔ binding ↔ 原型锚点三方 diff，检测被改丢、dangling 和未知引用；接入 interaction Stage Gate 与 finishing-branch 合并前硬门。 |
| Trace 索引 | Trace Index | `trace-coverage-check` 从原型抽出的低噪音回溯产物 `trace-index.json`，落在独立原型工程目录；其 git diff 即"哪个 SURF 掉了哪个 OBJ"的审计记录。 |
| 执行日志 | Trace Log | 记录执行位置、决策、阻塞和恢复信息的日志。文件名保留 `trace-log.md`。 |
| 交付包 | Delivery Package | 面向内部归档的交付追溯材料。文件名保留 `delivery-package.md`。 |
| 验收结果 | Acceptance Result | 面向用户的验收入口。文件名保留 `acceptance-result.md`。 |

## 执行治理级别

`autonomy_level` 是机器字段名；正文面向人时使用“执行治理级别”。不要再使用编号式等级名。

| 推荐名称 | 适用场景 | 行为 |
|----------|----------|------|
| 快速执行 | 治理风险低、边界清晰、局部可逆、自动验证充分 | 可跳过 `execution_governance.levels.快速执行.skippable_stages` 中允许跳过的阶段；实际执行的阶段仍必须通过 Stage Gate。 |
| 专家确认 | 中等技术 / 验证风险，需要专业角色把关，但不需要人做业务、安全或风险接受决策 | 阶段专业 reviewer PASS + Stage Gate PASS 通常即可继续；只有 `human_checkpoints` 中配置的阶段会暂停给人确认。 |
| 受控推进 | 高治理风险、不可逆影响、关键数据 / 权限 / 外部依赖 / Agent 行动权变化，或方案 / 验证不确定 | 默认不跳过阶段；哪些阶段必须人工确认由 `execution_governance.levels.受控推进.human_checkpoints` 显式配置。 |

配置和脚本中可能仍出现 `autonomous_execution`、`governed_execution`、`autonomy_level` 等字段名；这些是机器接口，不作为面向人的分类名称。具体配置位于 `harness-runtime/config/harness.yaml` 的 `execution_governance` 段。旧 `A1` / `A2` / `A3` 只能通过 `legacy_level_aliases` 迁移到新治理级别；运行时不再读取旧的扁平 `checkpoints`。

治理级别由 `governance_assessment` 支撑：先看 hard triggers，再看决策权、可逆性、影响面、验证可靠性、数据 / 权限、外部依赖、Agent 行动权和不确定性。文件数、角色数和模块跨度只是规模信号，不得用于稀释高风险。

## 状态码

状态码是机器裁决值，保留英文大写；正文解释必须写清它对流程的影响。

| 状态码 | 中文含义 | 流程影响 |
|--------|----------|----------|
| `PASS` | 通过 | 可进入下一步。 |
| `WARN` | 警告 | 可继续，但必须记录风险或后续处理。 |
| `FAIL` | 失败 | 不能继续，必须修复或进入 Decision Gate。 |
| `HOLD` | 审查阻断 | 审查员认为必须修复；修复后需要同一角色重审。 |
| `BLOCKED` | 外部阻塞 / 输入不足 | 当前无法完成，需要补输入、补环境或人工决策。 |
| `PASS_WITH_RISK` | 带风险通过 | 仅适用于非阻断风险；必须记录风险，必要时引用用户接受记录。 |
