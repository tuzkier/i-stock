---
name: technical_analysis
description: '当 solution.md 已完成，需要把方案路线落到模块 / 接口 / 数据 / 验证策略的技术设计时使用。仅处理 Mission Slice control_plane.stage=technical_analysis；不处理 solution 与 interaction。用户说"做技术设计 / tech-design / 模块拆分 / interface_changes / data_changes / 实现策略"时触发。Agent 能力实现（## Agent 实现 section）由本 skill 嵌入处理，不另立独立 capability-design skill。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# Technical Analysis — stage: technical_analysis

## 概述

`control_plane.stage=technical_analysis` 专属 skill。基于 solution.md 已确定的方案，产出 `tech-design.md` + `contracts/tech-design.contract.yaml`，覆盖模块/接口/数据/验证策略 + 生产就绪四要素。

`agent-capability-designer` 与 `agent-capability-reviewer` 作为条件角色（capability-design 嵌入式实现），负责 `tech-design.md ## Agent 实现` section + `solution.md ## Agent 架构` section 协同写。

## 何时使用

- Mission Slice `control_plane.stage=technical_analysis`
- solution.md 已完成、方案路线已明确
- 用户说"做技术设计 / 模块拆分 / interface_changes / 数据迁移设计"

## 何时不使用

- solution lane 还未完成 → 先 `solution` skill
- `control_plane.stage=interaction` → 转到 `interaction` skill
- `control_plane.stage=solution` → 转到 `solution` skill

## 设计原则

- **可追溯**：每个 module / interface_change / data_change / verification_strategy 必须 traces_to upstream DEC / 系统责任 / 质量与运行约束 / 验收场景
- **生产就绪四要素**：error_handling / compatibility / observability / rollback 必须填实值或 "N/A: 理由"
- **section 级 write_scope**：tech-designer 不得写 `## Agent 实现`；agent-capability-designer 只能写 `## Agent 实现` + solution.md `## Agent 架构`
- **dep-impact 前置**：`harness tech-design check-dep-impact-trigger` 触发时必须先跑 dependency-impact skill 再进入设计

## 快速参考

| 步骤 | 产出 |
|------|------|
| Stage 初始化 + dep-impact 触发判断 + capability 触发判断 | inputs |
| 读 solution.md + 产品定义包 + interaction.md / 三份 interaction-spec 引用 | inputs |
| tech-designer 起草 tech-design.md | tech-design.md (除 ## Agent 实现) |
| capability-designer 写 ## Agent 实现 + solution ## Agent 架构 | tech-design.md ## Agent 实现 |
| 填外部 contract（CLI 路径，5 typed groups） | tech-design.contract.yaml |
| 3 reviewer 循环（effectiveness + capability + dependency-validity） | role_verdicts |
| Artifact Gate 自检 | gate run PASS |

## Stage Element Model

本阶段必须维护的关键要素见 `.harness/docs/methodologies/stage-element-model.md#technical-analysis` 和 `#agent-capability-design`。摘要：

| Element | Used By | Failure If Missing |
|---|---|---|
| Module | Breakdown / Architecture Review | 任务拆分失去边界 |
| Interface Change | Execute / Integration Review | 调用方 / 被调方不一致 |
| Data / State Flow | Execute / TDD / Verify | 实现只改局部，破坏闭环 |
| Error / Compatibility Strategy | Execute / Delivery | 生产风险无处理路径 |
| Verification Strategy | Breakdown / Code Review / Verify | 任务完成无法被证明 |
| Agent Work Rights | Agent implementation / Eval | Agent 只靠 prompt 自律 |

按 `workflow.md` 执行详细步骤。
# 技术分析阶段工作流

> **方法论参考**：`.harness/docs/methodology-reference.md` §3-5；`docs/methodologies/agent-capability-engineering.md` §1-7

下文出现的所有 `harness ...` 命令一律通过 harness-cli skill 调用。

<workflow stage="technical_analysis" version="2">

<goal>
  从 solution.md、产品定义、任务契约、交互产物和现状证据出发，判断选定方案是否能被当前系统承载；如果可以，产出可被拆解、执行、代码审查和验证直接消费的技术设计。技术设计必须覆盖 `SUC-xx-OP-xx` 系统操作到接口 / 命令 / 事件 / 模块、数据 / 状态、错误语义、原子性 / 并发 / 幂等和验证证据的映射，并覆盖模块责任、依赖影响、生产就绪策略和风险验证方式。
</goal>

<role>
  你是技术分析阶段的设计编排者。先判断输入是否足以支撑技术设计，再把已选方案转成工程可实施的设计模型。你不能重新选方案、补造产品行为、直接写实现代码，也不能把技术设计降格成任务清单。Agent 实现段落由 agent-capability-designer 负责。
</role>

<stage_capability>

技术分析对应 RUP 细化阶段的分析与设计工作。它的核心能力不是填写控制字段，而是回答“系统如何承载需求”。

| 能力 | 判断问题 | 产物要求 |
|---|---|---|
| 用例实现判断 | 每个关键用例、`SUC-xx-FLOW-xx` 流步骤、`SUC-xx-OP-xx` 系统操作、验收场景 / 条件、质量与运行约束和业务规则是否有工程落点。 | 明确每个系统操作如何映射到模块、接口 / 命令 / 事件、数据 / 状态、错误语义、原子性 / 并发 / 幂等和验证方式；没有落点时说明应回流到产品定义、交互或方案。 |
| 架构承载判断 | 选定方案落在哪些现有模块、包、服务、配置、数据结构或运行时机制上。 | 说明复用、扩展、替换、隔离和禁止承担的职责，不能只写抽象模块名。 |
| 接口契约判断 | 新增、修改或替换的接口是否足以让调用方和测试方不再猜测。 | 写清调用方、输入、输出、错误语义、兼容影响、前后差异和迁移路径。 |
| 数据与状态判断 | 业务对象、状态机、权限规则、不变量、幂等、并发、补偿、迁移和回滚是否有设计落点。 | 涉及数据 / 状态时必须写迁移、回滚、不变量校验和异常路径；不涉及时写明原因。 |
| 生产就绪判断 | 错误处理、兼容性、可观测性、回滚 / 降级、安全或权限边界是否能支持正式交付。 | 不允许只覆盖演示路径；所有生产就绪要求必须有设计和验证方式。 |
| 风险验证判断 | 高优先级架构风险如何被验证、接受、阻断或回流。 | 说明用原型、接口契约、单元测试、集成测试、端到端验证、迁移演练或人工验收证明什么结论。 |
| Agent 能力设计判断 | 任务涉及智能体（Agent）能力时，是否把“让 Agent 做事”转化为可执行、可约束、可观测、可评估、可回滚的能力设计。 | `## Agent 实现` 必须写清组件责任、六种工作权、承载物分配、制度层约束、runtime / 可观测性、eval 场景和回滚 / 降级策略；不得只写提示词期望。 |

</stage_capability>

<invariants>

| ID | 检查项 | 约束来源 |
|---|---|---|
| `tech-design-contract-via-cli` | tech-design.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness contract fill/patch | overlay=design.technical_analysis[deny=Write(tech-design.contract.yaml)] |
| `lane-action-singularity` | 同 design slice 内只能写 tech-design.md，不得写 solution.md / interaction.md / interaction-spec/** / visual-interaction/**（capability-designer 协同写 solution.md `## Agent 架构` 段落是例外） | overlay=design.technical_analysis[deny=Write(other-lane-artifacts)]<br>cli=harness solution lane-action-validate |
| `reviewer-readonly` | 3 个 reviewer (effectiveness / capability / dependency-validity / behavior / architecture) 必须在 readonly subagent 中调用 | registry=subagents/*-reviewer[readonly=true] |
| `section-level-write` | tech-designer 不得写 `## Agent 实现` 段落；capability-designer 只能写指定段落 | frontmatter=tech-designer.write_scope_exclude_section + capability-designer.write_scope_section_only |
| `dep-impact-prerequisite` | check-dep-impact-trigger required=true 时，必须先跑 dependency-impact skill 才能进入 step-1 | cli=harness tech-design check-dep-impact-trigger |
| `fix-then-recheck` | tech-design.md 修改后必须重新过 reviewer | hook=design-tech-check-pending-recheck |

</invariants>

<entry>
  - Mission Slice control_plane.stage=technical_analysis
  - solution lane 已完成（solution.md + solution.contract.yaml 存在并 PASS）
  - dep-impact-trigger required=true 时已完成 dependency-impact skill
  - 产品定义 / 交互产物足以说明 `SUC-xx-FLOW-xx` 流步骤、`SUC-xx-OP-xx` 系统操作、用户可观察行为、验收场景 / 条件和质量与运行约束
  - 代码证据、依赖证据或项目约束足以判断系统承载边界
</entry>

<exit>
  - `tech-design-written`: tech-design.md 写入 design stage worktree
  - `contract-filled`: tech-design.contract.yaml 已填充且 harness contract check PASS（含 5 类 ID cross-contract trace）
  - `effectiveness-reviewer-pass`: technical-design-effectiveness-reviewer PASS
  - `capability-reviewer-pass`: agent_engineering.enabled=true 时 agent-capability-reviewer PASS
  - `dependency-validity-reviewer-pass`: dep-impact 触发时 dependency-validity-reviewer PASS
  - `gate-pass`: harness gate transition --stage technical_analysis 返回 status=pass
</exit>

<subagents>

| 角色 | 调度方式 | 范围 / 限制 | Prompt 包 |
|---|---|---|---|
| `tech-designer` | spawn | harness-runtime/harness/artifacts/${mission-id}/technical-analysis/tech-design.md（不含 `## Agent 实现` 段落） | `.harness/common/agents/tech-designer.md` |
| `agent-capability-designer` | spawn; condition=agent_engineering.enabled=true | harness-runtime/harness/artifacts/${mission-id}/technical-analysis/tech-design.md（仅 `## Agent 实现` 段落）, harness-runtime/harness/artifacts/${mission-id}/solution/solution.md（仅 `## Agent 架构` 段落） | `.harness/common/agents/agent-capability-designer.md` |
| `technical-design-effectiveness-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/technical-design-effectiveness-reviewer.md` |
| `agent-capability-reviewer` | spawn; readonly; condition=agent_engineering.enabled=true | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/agent-capability-reviewer.md` |
| `dependency-validity-reviewer` | spawn; readonly; condition=dep-impact-trigger.required=true | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/dependency-validity-reviewer.md` |

</subagents>

<inputs>

| 引用 | 是否必需 | 平面 |
|---|---|---|
| `solution.md` | true | Memory |
| `product/product-definition.md` | true | Memory |
| `product/use-case-model.md` | true | Memory |
| `product/acceptance-scenarios.md` | true | Evidence |
| `product/product-domain-model.md` | true | Memory |
| `product/product-evidence.md` | true | Evidence |
| `mission-contract.md` | true | Intent |
| `interaction.md` | conditional: interaction lane 已完成 | Memory |
| `interaction-spec/use-case-realization.md` | conditional: interaction lane 已完成且涉及界面或用户路径 | 用例到交互实现基线 |
| `interaction-spec/surface-model.md` | conditional: interaction lane 已完成且涉及界面或用户路径 | 界面边界、信息架构和领域到界面映射 |
| `interaction-spec/interaction-contract.md` | conditional: interaction lane 已完成且涉及界面或用户路径 | 路径、状态、交互和端到端验证要求 |
| `project-context.md` | conditional: brownfield | Context |
| `harness.yaml` | true via harness config snapshot | Memory |

</inputs>

<ddd_consumption>
 <rule>technical_analysis 必须把 product-domain-model.md 中的聚合、聚合根、领域命令、领域事件、不变量、状态机和权限规则映射到模块、接口、数据 / 状态设计和验证策略。</rule>
 <rule>technical_analysis 可以选择技术实现方式，但不得反向改写产品领域模型；发现领域模型无法支撑实现时必须回流产品定义或决策门。</rule>
</ddd_consumption>

<outputs>

| 产物 | 路径 | 类型 | 平面 / 校验器 |
|---|---|---|---|
| `tech-design-md` | `harness-runtime/harness/artifacts/${mission-id}/technical-analysis/tech-design.md` | markdown | Memory |
| `tech-design-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/tech-design.contract.yaml` | contract | Artifact Contract; validator: `harness contract check --upstream solution.contract.yaml --upstream prd.contract.yaml --upstream interaction.contract.yaml --upstream mission-contract.contract.yaml` |

</outputs>

<steps>

<step id="step-0" n="0" goal="阶段初始化 + 输入合格判断">
 - 调用 `harness mission stage start --mission <mission-id> --stage technical_analysis --json`。
 - 调用 `harness trace log-init --mission <mission-id> --stage technical_analysis --json`。
 - 调用 `harness context check --json`；PASS 则读 `project-context.md`。
 - 调用 `harness config snapshot --json`，记录 `agent_engineering.enabled` / `agent_engineering.scope`。
 - 调用 `harness frame current --mission <mission-id> --json`，校验 `mission_slice.control_plane.stage=technical_analysis`。
 - 调用 `harness tech-design check-dep-impact-trigger --mission <mission-id> --json`；required=true 时校验 dependency-impact skill 已完成（`harness-runtime/harness/artifacts/<mission-id>/discovery/dependency-impact.md` 存在），否则 BLOCKED 转 dependency-impact skill。
 - 调用 `harness tech-design check-capability-trigger --mission <mission-id> --json`，确定 step-2 是否启用 capability-designer 协同。
 - 在调度 tech-designer 前做输入合格判断：
	   - 系统用例流步骤、系统操作、验收场景 / 条件或质量与运行约束不足以判断工程义务时，停止并回流产品定义 / 交互。
   - solution 只有结论、缺少决策依据或风险处理方式时，停止并回流 solution。
   - 现状代码、依赖、接口、数据结构或外部系统证据不足，且猜测会影响安全实现时，停止并回流 discovery / dependency-impact。
   - 选定方案与项目约束、领域规则、权限边界或运行环境冲突时，停止并回流 solution 或决策门。
</step>

<step id="step-1" n="1" goal="tech-designer 调度 + tech-design.md 起草（不含 ## Agent 实现）">
 通过 `Task(subagent_type="tech-designer", prompt=<Task Envelope>)` 工具调用 `tech-designer` subagent
 - 任务信封包含：任务目标 / 输入路径（solution.md、产品定义、product/use-case-model.md、product/acceptance-scenarios.md、任务契约、interaction.md、interaction-spec/use-case-realization.md、interaction-spec/surface-model.md、interaction-spec/interaction-contract.md 如存在、project-context、dependency-impact.md 如存在）/ 输出路径 `harness-runtime/harness/artifacts/<mission-id>/technical-analysis/tech-design.md` / 写入范围（除 ## Agent 实现段落）/ 完成条件。
 - tech-designer 必须先列出上游工程义务，再完成六类设计判断：系统操作映射、架构承载、接口契约、数据与状态、生产就绪、风险验证。
 - tech-designer 必须新增并填实 `## 系统操作到技术设计映射`：每个 `SUC-xx-OP-xx` 必须追溯 `SUC-xx-FLOW-xx`，并落到接口 / 命令 / 事件 / 模块、读取实现、写入 / 状态迁移实现、条件 / 错误码、原子性 / 并发 / 幂等和验证证据。
 - tech-designer 必须覆盖：模块责任（每个模块必须追溯到方案决策、系统操作、系统用例、验收场景 / 条件或业务规则）、接口设计（调用方、输入、输出、错误语义、兼容影响和前后差异）、数据 / 状态设计（迁移、回滚、不变量和异常路径）、验证策略（说明证明什么行为、约束或风险）、生产就绪四要素（错误处理、兼容性、可观测性、回滚 / 降级）。
 - tech-designer 不得写 `## Agent 实现` 段落；M3 hook 物理阻断（当前 hook 推迟，由审查员审查 + frontmatter policy notice 兜底）。
</step>

<step id="step-2" n="2" goal="条件：capability-designer 协同写 ## Agent 实现 + solution ## Agent 架构">
 - 条件：check-capability-trigger.required=true
   通过 `Task(subagent_type="agent-capability-designer", prompt=<Task Envelope>)` 工具调用 `agent-capability-designer` subagent
   - brief：任务契约中的 `## Agent Engineering`、产品定义包中的 `agent_capability_requirements`、solution.md `## Agent 架构` 当前内容、tech-design.md 当前内容（除 `## Agent 实现`）、agent-capability-engineering.md §1-7。
   - capability-designer 必须协同写：solution.md `## Agent 架构` 段落（component / work_rights_realization 六个枚举值 / implementation_loci 五层位置枚举 / traces_to_prd 命中 R-AGENT-*）+ tech-design.md `## Agent 实现` 段落（component / traces_to_solution_arch 命中 solution.agent_architecture[].component / traces_to_prd_capability 命中 R-AGENT-* / implementation_loci / eval_scenarios 四类场景）。
</step>

<step id="step-3" n="3" goal="contract.yaml 初始化 + 5 typed groups patch">
 - 若 contracts/tech-design.contract.yaml 不存在，调用 `harness contract init --mission <mission-id> --stage technical_analysis --template tech-design --json`。
 - 调用 `harness contract add-execution-result --artifact harness-runtime/harness/stages/<mission-id>/contracts/tech-design.contract.yaml --result <tech-designer-execution-result.yaml> --json`。
 - 调用 `harness contract patch` 把 modules / interface_changes（kind 枚举）/ data_changes（kind 枚举）/ verification_strategy / production_readiness 四要素从 tech-design.md 抽取写入 contract.yaml。
 - 条件：check-capability-trigger.required=true
   - 同步 patch `agent_implementation[]`（含 traces_to_solution_arch / traces_to_prd_capability / implementation_loci / eval_scenarios 四类场景）+ patch `solution.contract.yaml.agent_architecture[]`。
</step>

<step id="step-4" n="4" goal="effectiveness reviewer 循环（无轮次放行）">
 - 循环：无轮次放行（producer-fixable 缺口不设通过上限，轮次只记录修复历史）；退出条件：本轮 technical-design-effectiveness-reviewer 在等同严格度下返回 PASS
   - Round start：
     通过 `Task(subagent_type="technical-design-effectiveness-reviewer", prompt=<Task Envelope>)` 工具调用 `technical-design-effectiveness-reviewer` subagent
     - brief：tech-design.md + contracts/tech-design.contract.yaml + solution.md + 产品定义 + product/use-case-model.md + product/acceptance-scenarios.md + 任务契约 + interaction.md / 三份 interaction-spec 如存在 + project-context 技术约束 + Evidence Graph obligation slice。
	     - 审查重点：设计是否完成系统操作映射、架构承载、接口契约、数据与状态、生产就绪和风险验证六类判断；字段齐全但无法实施、无法验证或无法追溯时不得 PASS。
     - 每轮审查返回后调用 `harness contract record-review --artifact harness-runtime/harness/stages/<mission-id>/contracts/tech-design.contract.yaml --role technical-design-effectiveness-reviewer --verdict <PASS|PASS_WITH_RISK|HOLD|BLOCKED> --subagent-id <dispatch-id> --model <resolved-model> --review-basis harness-runtime/harness/stages/<mission-id>/tech-design.md --summary <review-summary> --json`，由 CLI 维护 `role_verdicts` 与审查轮次。
   - 分支：审查结论
     - 情况：HOLD / BLOCKED
       - 修复 tech-design.md，立即回 round_start（design-tech-check-pending-recheck hook 物理阻断）。
     - 情况：PASS
       - 退出循环。
 - 用户确认点：卡死——同一阻断在交回 tech-designer 修复后，reviewer 仍以相同根因连续 HOLD 且无实质进展（按缺口本质判断，不是"轮次到点"）
   - 不得降级通过。按 `core.md`「严格审查不变量」重新归因：producer 能补则留在循环升级修复策略继续修；本质是上游缺失则回流上游。仅当确需用户拍板才能解时，使用 AskUserQuestion，候选（**不含"接受降级 / 降级通过 / 重置 rounds 继续"**）：(1) 给出解决方向留在循环继续修 (2) 改范围 / 回流上游重导 (3) 升级 BLOCKED。残留风险只能由用户在充分披露后于 Decision Gate 显式拥有（走 `harness approval append --type tradeoff --status approved --json`）；审查循环本身永不把未解决阻断自动转为通过。
</step>

<step id="step-5" n="5" goal="条件：capability reviewer 循环">
 - 条件：check-capability-trigger.required=true
   - 循环：无轮次放行（producer-fixable 缺口不设通过上限）；退出条件：agent-capability-reviewer 在等同严格度下返回 PASS
     - Round start：
       通过 `Task(subagent_type="agent-capability-reviewer", prompt=<Task Envelope>)` 工具调用 `agent-capability-reviewer` subagent
       - brief：solution.md `## Agent 架构` + tech-design.md `## Agent 实现` + contract.agent_architecture / contract.agent_implementation + `R-AGENT-*` 能力要求。
       - 每轮审查返回后调用 `harness contract record-review --artifact harness-runtime/harness/stages/<mission-id>/contracts/tech-design.contract.yaml --role agent-capability-reviewer --verdict <PASS|PASS_WITH_RISK|HOLD|BLOCKED> --subagent-id <dispatch-id> --model <resolved-model> --review-basis harness-runtime/harness/stages/<mission-id>/tech-design.md --summary <review-summary> --json`。
     - 分支：审查结论
       - 情况：HOLD / BLOCKED
         - 把 finding 交回 capability-designer 修复对应段落，立即回 round_start。
       - 情况：PASS
         - 退出循环。
</step>

<step id="step-6" n="6" goal="条件：dependency-validity reviewer 循环">
 - 条件：check-dep-impact-trigger.required=true
   - 循环：无轮次放行（producer-fixable 缺口不设通过上限）；退出条件：dependency-validity-reviewer 在等同严格度下返回 PASS
     - Round start：
       通过 `Task(subagent_type="dependency-validity-reviewer", prompt=<Task Envelope>)` 工具调用 `dependency-validity-reviewer` subagent
       - brief：dependency-impact.md + tech-design.md interface_changes / data_changes 引用 + Mission Contract scope_in。
       - 每轮审查返回后调用 `harness contract record-review --artifact harness-runtime/harness/stages/<mission-id>/contracts/tech-design.contract.yaml --role dependency-validity-reviewer --verdict <PASS|PASS_WITH_RISK|HOLD|BLOCKED> --subagent-id <dispatch-id> --model <resolved-model> --review-basis harness-runtime/harness/stages/<mission-id>/dependency-impact.md --summary <review-summary> --json`。
     - 分支：审查结论
       - 情况：HOLD / BLOCKED
         - 修复 dependency-impact.md / tech-design.md，立即回 round_start。
       - 情况：PASS
         - 退出循环。
</step>

<step id="step-7" n="7" goal="Artifact Gate 自检">
 - 调用 `harness contract check --artifact contracts/tech-design.contract.yaml --upstream solution.contract.yaml --upstream prd.contract.yaml --upstream interaction.contract.yaml --upstream mission-contract.contract.yaml --json`；FAIL 必须修复后再继续。
 - 调用 `harness alignment check --mission <mission-id> --stage technical_analysis --json`；检查 modules / interfaces / data / verification_strategy 是否对齐 solution decisions、domain model、交互用例实现、界面模型和路径 / 状态合同。
 - 调用 `harness gate transition --stage technical_analysis --mission <mission-id> --mission-slice harness-runtime/harness/work-graph/mission-slices/<mission-id>.yaml --artifact tech-design.md --contract-artifact contracts/tech-design.contract.yaml --json`；status != PASS 时按返回 failed_step / failed_checks 修复后重跑。
</step>

<step id="step-8" n="8" goal="Stage 完成 + Work Graph 输出">
 - 第 7 步 `harness gate transition` PASS 后，阶段完成、Gate 报告、Work Graph operation、下一 Mission Slice 已由 CLI 串联写入；不得再单独调用 `mission stage complete` / `gate advance` / `board select`。
 - tech-design.md 必须写入 lane_action.output_artifact 对应的 artifact store 路径，并在 contract YAML 的 `work_graph_artifact.artifact_refs[]` 中引用同一 `artifact_id/path`。
</step>

</steps>

<failure_paths>

| Failure | 触发条件 | 处理方式 |
|---|---|---|
| `input-not-qualified` | 系统责任 / 验收场景 / 质量与运行约束、方案决策、现状证据不足以支撑技术设计 | 停止当前阶段；按缺口回流产品定义、交互、方案、探索或依赖影响分析。 |
| `dep-impact-not-run` | step-0 dep-impact-trigger required=true 但 dependency-impact.md 不存在 | BLOCKED；返回 skill-router 路由到 dependency-impact skill 后再回 technical_analysis。 |
| `tech-designer-blocked` | step-1 tech-designer 返回 BLOCKED | 按 BLOCKED type 路由：missing_input → 回 step-0；scope_conflict → AskUserQuestion；decision_gate → 暂停。 |
| `capability-designer-blocked` | step-2 capability-designer 返回 BLOCKED | 检查 agent_engineering.scope；scope=experimental 时降级为 WARN，scope=core 时强校验后升级 BLOCKED。 |
| `review-stuck` | step-4/step-5/step-6 loop 卡死（修复后仍以相同根因连续 HOLD 无实质进展，非轮次到点） | 由对应 step user_checkpoint 处理（重新归因；需用户拍板则 AskUserQuestion，候选仅：继续修 / 改范围回流上游 / 升级 BLOCKED，不含降级通过）。 |
| `contract-check-fail` | step-7 contract check FAIL | 按 finding code 分类：broken_module_reference → 回 step-1 修 traces_to；broken_interface_change_reference → 回 step-1 修 INT.traces_to；broken_agent_implementation_prd_trace → 回 step-2 修 capability-designer 输出；broken_data_change_reference → 回 step-1 修 DATA.traces_to。 |
| `gate-fail` | step-7 harness gate transition FAIL | 按 failed_step / failed_checks 分类修复后重跑 gate transition。 |

</failure_paths>

</workflow>
