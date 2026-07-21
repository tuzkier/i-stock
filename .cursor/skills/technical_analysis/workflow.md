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
  - `hinge-review-pass`: agent_engineering 触发时，step-1b tech-design 枢纽审查闸经 technical-design-effectiveness-reviewer 在等同严格度下 PASS（或已澄清回填 / Decision Gate approval）后才允许 step-2 capability-designer 消费；未触发 agent_engineering 时本条 N/A
  - `contract-filled`: tech-design.contract.yaml 已填充且 harness contract check PASS（含 5 类 ID cross-contract trace）
  - `effectiveness-reviewer-pass`: technical-design-effectiveness-reviewer PASS
  - `capability-reviewer-pass`: agent_engineering.enabled=true 时 agent-capability-reviewer PASS
  - `dependency-validity-reviewer-pass`: dep-impact 触发时 dependency-validity-reviewer PASS
  - `gate-pass`: harness gate run --stage technical_analysis 返回 status=pass
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
 - **输入合格性判定方法**（在调度 tech-designer 前，对每类输入逐行判定，结论写入 tech-design.md 输入合格判断段；不能只写"已确认"）：

   | 来源 | 执行义务（这类输入要支撑什么技术判断） | 是否足够 | 处理动作 |
   |---|---|---|---|
   | 产品定义 / 用例模型 | `SUC-xx-FLOW-xx` 流步骤、`SUC-xx-OP-xx` 系统操作、验收场景 / 条件、质量与运行约束可推出每个系统操作的工程义务 | `fit` / `return_to_prd` / `return_to_interaction` / `needs_decision` | `fit` 时至少推出一个系统操作的接口 / 模块落点；return / decision 时写明缺的上游结论与为何 technical_analysis 无权补 |
   | solution.md | 选定路线、禁止路线、关键决策依据、风险处理方式足以约束技术承载边界 | `fit` / `return_to_solution` / `needs_decision` | return 时写明缺的决策依据或风险处理、为何不能在 tech-design 内自行拍板 |
   | 交互 / 原型产物（如适用） | 作用面（`SURF-xxx`）、页面状态（`PS-`）、用户路径、状态、端到端义务足以推界面承载与验证落点 | `fit` / `return_to_interaction` / `needs_decision` | return 时写明缺的界面 / 路径 / 状态定义 |
   | 现状代码 / 依赖 / 接口 / 数据结构证据 | 现有模块、包、服务、配置、数据结构能判断复用 / 扩展 / 替换 / 隔离边界 | `fit` / `return_to_discovery` / `return_to_dependency_impact` / `needs_decision` | 证据不足且猜测会影响安全实现时回流，不脑补现状 |

   - `是否足够` 只允许上表枚举值；判 `fit` 时必须能从该来源直接推出至少一个技术承载落点；判 return / decision 时必须写明缺少的上游结论、为何 technical_analysis 无权补齐、继续设计会引入什么实现风险。
   - 缺口属于产品行为、方案路线、界面 / 路径、现状事实时，不得在 technical_analysis 内补造；只有技术映射表达不清、模块落点粒度不当这类本阶段自身缺口才在本阶段修复。
 - **现状代码证据最小检索规程**（判 `fit` 前必须真实检索，不得凭印象断言现状）：
   - 从 `project-context.md` 模块地图或 `harness knowledge resolve --stage technical_analysis --json` 返回的 `engineering` 索引定位实现代码库源码根（brownfield 时必做）。
   - 在源码根用 Glob / Grep 检索本次涉及的模块 / 接口 / 数据结构是否已存在、由谁承载，记录检索范围（路径 glob + 关键词）与命中文件，作为架构承载判断与「是否足够」判定的依据。
   - 命中即把真实文件 / 符号作为复用 / 扩展 / 替换边界的事实来源；确无命中时记 `no_match` + 搜索范围，并按 `return_to_discovery` / `return_to_dependency_impact` 阻断或回流，**不得脑补现状代码或假设模块存在**。（建议后续加门：校验输入合格判定表枚举出口与现状检索范围非空。）
</step>

<step id="step-1" n="1" goal="tech-designer 调度 + tech-design.md 起草（不含 ## Agent 实现）">
 通过 `@tech-designer` native delegation调用 `tech-designer` subagent（Cursor auto-routes 到对应 agent registry 项）
 - 任务信封包含：任务目标 / 输入路径（solution.md、产品定义、product/use-case-model.md、product/acceptance-scenarios.md、任务契约、interaction.md、interaction-spec/use-case-realization.md、interaction-spec/surface-model.md、interaction-spec/behavior-graph.yaml、interaction-spec/interaction-contract.md 如存在、project-context、dependency-impact.md 如存在）/ 输出路径 `harness-runtime/harness/artifacts/<mission-id>/technical-analysis/tech-design.md` / 写入范围（除 ## Agent 实现段落）/ 完成条件。
 - tech-designer 必须先列出上游工程义务，再完成六类设计判断：系统操作映射、架构承载、接口契约、数据与状态、生产就绪、风险验证。
 - tech-designer 必须新增并填实 `## 系统操作到技术设计映射`：每个 `SUC-xx-OP-xx` 必须追溯 `SUC-xx-FLOW-xx`，并落到接口 / 命令 / 事件 / 模块、读取实现、写入 / 状态迁移实现、条件 / 错误码、原子性 / 并发 / 幂等和验证证据。
 - tech-designer 必须覆盖：模块责任（每个模块必须追溯到方案决策、系统操作、系统用例、验收场景 / 条件或业务规则）、接口设计（调用方、输入、输出、错误语义、兼容影响和前后差异）、数据 / 状态设计（迁移、回滚、不变量和异常路径）、验证策略（说明证明什么行为、约束或风险）、生产就绪四要素（错误处理、兼容性、可观测性、回滚 / 降级）。
 - 如该 mission 有原型产物（interaction lane 已完成且产出 interaction-spec/behavior-graph.yaml）：behavior-graph.yaml 是原型契约 SSOT，每个 mission 内的界面边界（`SURF-xxx`）必须被某个模块 / 决策 `traces_to` 承载，页面状态（`PS-<surf>-<state>`）是可追溯 ref 可直接被引用；下游对原型决策【要么承载、要么显式改写并经决策门 + 在契约 `prototype_coverage_exemptions` 登记 N/A 豁免】，禁止静默漂移或自由重设计界面。未承载的 mission SURF 会被覆盖率门报 `SURFACE_NOT_CARRIED`。
 - tech-designer 不得写 `## Agent 实现` 段落；M3 hook 物理阻断（当前 hook 推迟，由审查员审查 + frontmatter policy notice 兜底）。
</step>

<step id="step-1b" n="1b" goal="条件：tech-design 枢纽审查闸（先于 capability-designer 消费）">
 - 条件：check-capability-trigger.required=true。未触发 agent_engineering 时 tech-design.md 不被同阶段后续步骤消费，跳过本步，由 step-4 末尾全量审查覆盖。
 - 按 `core.md`「step 级枢纽审查」执行：tech-design.md（除 `## Agent 实现`）是枢纽工件——agent-capability-designer 将在 step-2 消费它写 `## Agent 实现`。若设计正文未审即被消费，Agent 实现会建在未验证的设计上，等 step-4 才发现则 tech-design 正文与 `## Agent 实现` 两段都要返工。
   通过 `@technical-design-effectiveness-reviewer` native delegation调用 `technical-design-effectiveness-reviewer` subagent（Cursor auto-routes 到对应 agent registry 项）
   - 任务信封（收窄实例化）：审查对象 = tech-design.md（除 `## Agent 实现` 段落）；直接上游 = solution.md、产品定义、product/use-case-model.md、product/acceptance-scenarios.md、任务契约、interaction-spec（如存在）、`materials/` 原始材料与已确认澄清、project-context 技术约束；只读约束；审查清单收窄到六类设计判断（系统操作映射、架构承载、接口契约、数据与状态、生产就绪、风险验证）在 tech-design.md 文档子集上的完备（每个 `SUC-xx-OP-xx` 落到接口 / 命令 / 事件 / 模块且可实施、可验证、可追溯）与自洽（无互否、不与 solution 决策 / 领域边界冲突）。本步只审 markdown 设计正文，不要求 contract（contract 在 step-3 patch）。结论经 `harness contract record-review --artifact contracts/tech-design.contract.yaml --role technical-design-effectiveness-reviewer --verdict <PASS|HOLD|BLOCKED> --reviewed-obligation HINGE-tech-design --review-basis <.../tech-design.md> --subagent-id <id> --model <model> --summary <...> --json` 写入 `role_verdicts`（hinge-scoped `--reviewed-obligation` 必传；只用 record-review，**不调** `--add-round`，故不消耗 step-4 effectiveness 轮次计数、不冒充末尾 reviewer-pass，见 `core.md`「step 级枢纽审查」记录约束）。
   - 循环：无轮次放行；退出条件：technical-design-effectiveness-reviewer 在等同严格度下对 tech-design.md 正文返回 PASS。
     - HOLD / BLOCKED：设计自身缺陷 → 交回 tech-designer 重做对应段落后原地重审；信息缺失需上游澄清（`gap_root=clarification` / `missing_upstream_trace`）→ 按 step-4 同款上游分流（决策依据回 solution、产品定义不足回 prd、依赖事实未知回 discovery / dep-impact），不消耗轮次，澄清回填后重审。
     - 卡死：处理同 step-4（不降级通过，重新归因，AskUserQuestion 候选不含降级通过，残留风险走 Decision Gate `harness approval`）。
   - 本步 PASS 后才能进入 step-2 让 agent-capability-designer 消费 tech-design.md；未 PASS 不得进入 step-2。
</step>

<step id="step-2" n="2" goal="条件：capability-designer 协同写 ## Agent 实现 + solution ## Agent 架构">
 - 条件：check-capability-trigger.required=true
   通过 `@agent-capability-designer` native delegation调用 `agent-capability-designer` subagent（Cursor auto-routes 到对应 agent registry 项）
   - brief：任务契约中的 `## Agent Engineering`、产品定义包中的 `agent_capability_requirements`、solution.md `## Agent 架构` 当前内容、tech-design.md 当前内容（除 `## Agent 实现`）、agent-capability-engineering.md §1-7。
   - capability-designer 必须协同写：solution.md `## Agent 架构` 段落（component / work_rights_realization 六个枚举值 / implementation_loci 五层位置枚举 / traces_to_prd 命中 R-AGENT-*）+ tech-design.md `## Agent 实现` 段落（component / traces_to_solution_arch 命中 solution.agent_architecture[].component / traces_to_prd_capability 命中 R-AGENT-* / implementation_loci / eval_scenarios 四类场景）。
</step>

<step id="step-3" n="3" goal="contract.yaml 初始化 + 5 typed groups patch">
 - 若 contracts/tech-design.contract.yaml 不存在，调用 `harness contract init --mission <mission-id> --stage technical_analysis --template tech-design --json`。
 - 调用 `harness contract add-execution-result --mission <mission-id> --stage technical_analysis --role tech-designer --json`。
 - 调用 `harness contract patch` 把 modules / interface_changes（kind 枚举）/ data_changes（kind 枚举）/ verification_strategy / production_readiness 四要素从 tech-design.md 抽取写入 contract.yaml。
 - 条件：check-capability-trigger.required=true
   - 同步 patch `agent_implementation[]`（含 traces_to_solution_arch / traces_to_prd_capability / implementation_loci / eval_scenarios 四类场景）+ patch `solution.contract.yaml.agent_architecture[]`。
</step>

<step id="step-4" n="4" goal="effectiveness reviewer 循环（无轮次放行）">
 - 循环：无轮次放行（producer-fixable 缺口不设通过上限，轮次只记录修复历史）；退出条件：本轮 technical-design-effectiveness-reviewer 在等同严格度下返回 PASS
   - Round start：
     通过 `@technical-design-effectiveness-reviewer` native delegation调用 `technical-design-effectiveness-reviewer` subagent（Cursor auto-routes 到对应 agent registry 项）
     - brief：tech-design.md + contracts/tech-design.contract.yaml + solution.md + 产品定义 + product/use-case-model.md + product/acceptance-scenarios.md + 任务契约 + interaction.md / interaction-spec（含 behavior-graph.yaml、surface-model.md）如存在 + project-context 技术约束 + Evidence Graph obligation slice。
	     - 审查重点：设计是否完成系统操作映射、架构承载、接口契约、数据与状态、生产就绪和风险验证六类判断；字段齐全但无法实施、无法验证或无法追溯时不得 PASS。
     - 每轮进入前调用 `harness contract patch --add-round --mission <mission-id> --stage technical_analysis --review effectiveness --json`。
   - 分支：审查结论
     - 情况：HOLD / BLOCKED — carrier 分流
       - 缺口本质=设计自身缺陷（系统操作映射、架构承载、接口契约、数据与状态、生产就绪、风险验证任一不实施 / 不可验证 / 不可追溯）：把 finding 交回 tech-designer 重做对应段落；finding 落在 `## Agent 实现` 段落时交回 agent-capability-designer 重做该段落；改完立即回 round_start（design-tech-check-pending-recheck hook 物理阻断）。
       - 缺口本质=信息缺失需上游澄清（reviewer 标 missing_upstream_trace，或缺口本质为 solution 决策依据不足 / 领域模型无法支撑当前设计 / 外部依赖事实未知）：立即按缺失来源分流——决策依据 / 路线取舍缺失走 AskUserQuestion 或 `harness approval`（决策门）并回流 solution；产品定义 / 领域模型不足回流交互 / 产品定义；现状代码 / 依赖 / 外部系统事实未知回流 discovery / dependency-impact；澄清回填后回 round_start。
     - 情况：PASS
       - 退出循环。
 - 用户确认点：卡死——同一阻断在交回 tech-designer 修复后，reviewer 仍以相同根因连续 HOLD 且无实质进展（按缺口本质判断，不是"轮次到点"）
   - **可操作判据**：连续 2 轮 reviewer 的 `blocking_gap` 指向同一 obligation ID 且 `finding_type` 相同、且 producer（tech-designer / capability-designer）本轮 diff 未触及该 obligation 对应章节 → 判定卡死（由 record-review 已存的 verdict 历史程序化比对前后两轮即可识别）。据此区分"修了措辞没修实质"（diff 未触及对应章节 = 仍卡死）与"真有实质进展"（diff 已改对应章节 = 未卡死，继续循环）。
   - 不得降级通过。按 `core.md`「严格审查不变量」重新归因：producer 能补则留在循环升级修复策略继续修；本质是上游缺失走上面的上游澄清分流。仅当确需用户拍板才能解时，使用 AskUserQuestion，候选（**不含"接受降级 / 降级通过"**）：(1) 给出解决方向留在循环继续修 (2) 改范围 / 回流上游重导 (3) 升级 BLOCKED。残留风险只能由用户在充分披露后于 Decision Gate 显式拥有（走 `harness approval append --type tradeoff --status approved --json`）；审查循环本身永不把未解决阻断自动转为通过。
</step>

<step id="step-5" n="5" goal="条件：capability reviewer 循环">
 - 条件：check-capability-trigger.required=true
   - 循环：无轮次放行（producer-fixable 缺口不设通过上限）；退出条件：agent-capability-reviewer 在等同严格度下返回 PASS
     - Round start：
       通过 `@agent-capability-reviewer` native delegation调用 `agent-capability-reviewer` subagent（Cursor auto-routes 到对应 agent registry 项）
       - brief：solution.md `## Agent 架构` + tech-design.md `## Agent 实现` + contract.agent_architecture / contract.agent_implementation + `R-AGENT-*` 能力要求。
       - 每轮进入前 `harness contract patch --add-round --mission <mission-id> --stage technical_analysis --review agent_capability --json`。
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
       通过 `@dependency-validity-reviewer` native delegation调用 `dependency-validity-reviewer` subagent（Cursor auto-routes 到对应 agent registry 项）
       - brief：dependency-impact.md + tech-design.md interface_changes / data_changes 引用 + Mission Contract scope_in。
       - 每轮进入前 `harness contract patch --add-round --mission <mission-id> --stage technical_analysis --review dependency_validity --json`。
     - 分支：审查结论
       - 情况：HOLD / BLOCKED
         - 修复 dependency-impact.md / tech-design.md，立即回 round_start。
       - 情况：PASS
         - 退出循环。
</step>

<step id="step-7" n="7" goal="Artifact Gate 自检">
 - 调用 `harness contract check --artifact contracts/tech-design.contract.yaml --upstream solution.contract.yaml --upstream prd.contract.yaml --upstream interaction.contract.yaml --upstream mission-contract.contract.yaml --json`；FAIL 必须修复后再继续。
 - 调用 `harness alignment check --mission <mission-id> --stage technical_analysis --json`；检查 modules / interfaces / data / verification_strategy 是否对齐 solution decisions、domain model、交互用例实现、界面模型和路径 / 状态合同。
 - 调用 `harness gate run --stage technical_analysis --mission <mission-id> --artifact tech-design.md --json`；status != PASS 时按返回 failed_checks 修复后重跑。
</step>

<step id="step-8" n="8" goal="Stage 完成 + Work Graph 输出">
 - 调用 `harness mission stage complete technical_analysis --mission <mission-id> --json`（design-tech-check-gate-pass hook 物理阻断 — 必须有 gate PASS 报告）。
 - tech-design.md 必须写入 lane_action.output_artifact 对应路径，并在 contract YAML 的 `work_graph_artifact.source_stage_artifact` 中引用同一路径。
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
| `gate-fail` | step-7 harness gate run FAIL | 按 failed_checks 分类修复后重跑 gate run。 |

</failure_paths>

</workflow>
