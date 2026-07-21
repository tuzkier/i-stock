# Technical Analysis lane action 工作流

> **方法论参考**：`.harness/docs/methodology-reference.md` §3-5；`docs/methodologies/agent-capability-engineering.md` §1-7

下文出现的所有 `harness ...` 命令一律通过 harness-cli skill 调用。

<workflow stage="technical_analysis" version="2">

<goal>
  从 solution.md + PRD + Mission Contract 出发，按 `control_plane.stage=technical_analysis` 产出模块/接口/数据/验证策略 + 生产就绪四要素，落入 tech-design.md + contracts/tech-design.contract.yaml，由 technical-design-effectiveness-reviewer + capability-reviewer + dependency-validity-reviewer 审查通过。
</goal>

<role>
  你是技术设计者，先做模块拆分 + 接口设计 + 数据流设计 + 验证策略 + 生产就绪四要素，再写文档。每个模块必须可追溯到 solution.md 决策；每个验证策略必须可直接分解为 execution-brief 任务。Agent 实现 section 由 capability-designer 写。
</role>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `tech-design-contract-via-cli` | tech-design.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness contract fill/patch | overlay=design.technical_analysis[deny=Write(tech-design.contract.yaml)] |
| `lane-action-singularity` | 同 design slice 内只能写 tech-design.md，不得写 solution.md / interaction.md / interaction-spec/** / visual-interaction/**（capability-designer 协同写 solution.md ## Agent 架构 section 是例外） | overlay=design.technical_analysis[deny=Write(other-lane-artifacts)]<br>cli=harness solution lane-action-validate |
| `reviewer-readonly` | 3 个 reviewer (effectiveness / capability / dependency-validity / behavior / architecture) 必须在 readonly subagent 中调用 | registry=subagents/*-reviewer[readonly=true] |
| `section-level-write` | tech-designer 不得写 ## Agent 实现 section；capability-designer 只能写指定 section | frontmatter=tech-designer.write_scope_exclude_section + capability-designer.write_scope_section_only |
| `dep-impact-prerequisite` | check-dep-impact-trigger required=true 时，必须先跑 dependency-impact skill 才能进入 step-1 | cli=harness tech-design check-dep-impact-trigger |
| `fix-then-recheck` | tech-design.md 修改后必须重新过 reviewer | hook=design-tech-check-pending-recheck |

</invariants>

<entry>
  - Mission Slice control_plane.stage=technical_analysis
  - solution lane 已完成（solution.md + solution.contract.yaml 存在并 PASS）
  - dep-impact-trigger required=true 时已完成 dependency-impact skill
</entry>

<exit>
  - `tech-design-written`: tech-design.md 写入 design stage worktree
  - `contract-filled`: tech-design.contract.yaml 已填充且 harness contract check PASS（含 5 类 ID cross-contract trace）
  - `effectiveness-reviewer-pass`: technical-design-effectiveness-reviewer PASS
  - `capability-reviewer-pass`: agent_engineering.enabled=true 时 agent-capability-reviewer PASS
  - `dependency-validity-reviewer-pass`: dep-impact 触发时 dependency-validity-reviewer PASS
  - `gate-pass`: harness gate run --stage technical_analysis 返回 status=pass
</exit>

<permissions>

<!-- design stage overlay：install pipeline 经 stage overlay key 从

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Edit(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Edit(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/stages/*/contracts/tech-design.contract.yaml)` | contract 必须经 harness contract fill/patch |
| deny | `Edit(harness-runtime/harness/stages/*/contracts/tech-design.contract.yaml)` | contract 必须经 harness contract patch |
| deny | `Write(harness-runtime/harness/stages/*/solution.md)` | lane action 单一性：solution.md 属 solution lane（## Agent 架构 section 由 hook 例外放行） |
| deny | `Edit(harness-runtime/harness/stages/*/solution.md)` | lane action 单一性 |
| deny | `Write(harness-runtime/harness/stages/*/interaction.md)` | lane action 单一性：interaction.md 属 interaction lane |
| deny | `Edit(harness-runtime/harness/stages/*/interaction.md)` | lane action 单一性 |
| deny | `Write(harness-runtime/harness/stages/*/interaction-spec/**)` | lane action 单一性：interaction-spec 属 interaction lane |
| deny | `Edit(harness-runtime/harness/stages/*/interaction-spec/**)` | lane action 单一性 |
| deny | `Write(harness-runtime/harness/stages/*/visual-interaction/**)` | lane action 单一性：visual-interaction 属 interaction lane |
| deny | `Edit(harness-runtime/harness/stages/*/visual-interaction/**)` | lane action 单一性 |
| deny | `Write(harness-runtime/harness/stages/*/contracts/solution.contract.yaml)` | lane action 单一性 |
| deny | `Write(harness-runtime/harness/stages/*/contracts/interaction.contract.yaml)` | lane action 单一性 |
| allow | `Write(harness-runtime/harness/stages/*/tech-design.md)` | technical_analysis lane 主产物 |
| allow | `Bash(harness *)` | technical_analysis lane CLI 必需 |

       design.technical_analysis.json 物化（非本 XML island）；此处 <permissions>
       与 design.technical_analysis.json 内容镜像，供 workflow 自文档化 +
       XML v2 W002 一致性。capability-designer 协同写 solution.md ## Agent 架构
       section 是例外，由 M3.1 section anchor hook 精细放行。 -->

</permissions>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `tech-designer` | spawn | harness-runtime/harness/stages/${mission-id}/tech-design.md (except ## Agent 实现 section) | `.harness/common/agents/tech-designer.md` |
| `agent-capability-designer` | spawn; condition=agent_engineering.enabled=true | harness-runtime/harness/stages/${mission-id}/tech-design.md (## Agent 实现 section only), harness-runtime/harness/stages/${mission-id}/solution.md (## Agent 架构 section only) | `.harness/common/agents/agent-capability-designer.md` |
| `technical-design-effectiveness-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/technical-design-effectiveness-reviewer.md` |
| `agent-capability-reviewer` | spawn; readonly; condition=agent_engineering.enabled=true | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/agent-capability-reviewer.md` |
| `dependency-validity-reviewer` | spawn; readonly; condition=dep-impact-trigger.required=true | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/dependency-validity-reviewer.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `solution.md` | true | Memory |
| `product/product-definition.md` | true | Memory |
| `product/product-domain-model.md` | true | Memory |
| `product/product-evidence.md` | true | Evidence |
| `mission-contract.md` | true | Intent |
| `interaction.md` | conditional: interaction lane 已完成 | Memory |
| `interaction-spec/` | conditional: interaction lane 已完成且涉及 UI / user journey | Memory |
| `project-context.md` | conditional: brownfield | Context |
| `harness.yaml` | true via harness config snapshot | Memory |

</inputs>

<ddd_consumption>
 <rule>technical_analysis 必须把 product-domain-model.md 中的 aggregate / aggregate root / domain command / domain event / invariant / state machine / permission rule 映射到模块、接口、数据和验证策略。</rule>
 <rule>technical_analysis 可以选择技术实现方式，但不得反向改写产品领域模型；发现领域模型无法支撑实现时必须回流 PRD / Decision Gate。</rule>
</ddd_consumption>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `tech-design-md` | `harness-runtime/harness/stages/${mission-id}/tech-design.md` | markdown | Memory |
| `tech-design-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/tech-design.contract.yaml` | contract | Artifact Contract; validator: `harness contract check --upstream solution.contract.yaml --upstream prd.contract.yaml --upstream interaction.contract.yaml --upstream mission-contract.contract.yaml` |

</outputs>

<steps>

<step id="step-0" n="0" goal="Stage 初始化 + 双触发判断">
 - 调用 `harness mission stage start --mission <mission-id> --stage technical_analysis --json`。
 - 调用 `harness trace log-init --mission <mission-id> --stage technical_analysis --json`。
 - 调用 `harness context check --json`；PASS 则读 `project-context.md`。
 - 调用 `harness config snapshot --json`，记录 `agent_engineering.enabled` / `agent_engineering.scope`。
 - 调用 `harness frame current --mission <mission-id> --json`，校验 `mission_slice.control_plane.stage=technical_analysis`。
 - 调用 `harness tech-design check-dep-impact-trigger --mission <mission-id> --json`；required=true 时校验 dependency-impact skill 已完成（`harness-runtime/harness/stages/<mission-id>/dependency-impact.md` 存在），否则 BLOCKED 转 dependency-impact skill。
 - 调用 `harness tech-design check-capability-trigger --mission <mission-id> --json`，确定 step-2 是否启用 capability-designer 协同。
</step>

<step id="step-1" n="1" goal="tech-designer 调度 + tech-design.md 起草（不含 ## Agent 实现）">
 <dispatch role="tech-designer" mode="spawn" />
 - Task Envelope 包含：任务目标 / 输入路径（solution.md、PRD、Mission Contract、interaction.md 与 interaction-spec 如存在、project-context、dependency-impact.md 如存在）/ 输出路径 `harness-runtime/harness/stages/<mission-id>/tech-design.md` / write_scope（除 ## Agent 实现 section）/ 完成条件。
 - tech-designer 必须覆盖：模块拆分（每个 MOD-NN 必须 traces_to DEC / FR）、接口设计（INT-NN 含 kind enum + before/after for MODIFIED/REPLACED）、数据流（DATA-NN 含 migration + rollback for MODIFIED/REMOVED）、验证策略（VS-NN 含 target_ids 命中 MOD/AC/FR）、生产就绪四要素（error_handling / compatibility / observability / rollback）。
 - tech-designer 不得写 `## Agent 实现` section；M3 hook 物理阻断（当前 hook 推迟，由 reviewer 审查 + frontmatter policy notice 兜底）。
</step>

<step id="step-2" n="2" goal="条件：capability-designer 协同写 ## Agent 实现 + solution ## Agent 架构">
 - 条件：check-capability-trigger.required=true
   <dispatch role="agent-capability-designer" mode="spawn" />
   - brief：mission-contract `## Agent Engineering`、PRD agent_capability_requirements、solution.md `## Agent 架构` 当前内容、tech-design.md 当前内容（除 ## Agent 实现）、agent-capability-engineering.md §1-7。
   - capability-designer 必须协同写：solution.md `## Agent 架构` section（component / work_rights_realization 6 enum / implementation_loci layer 5 enum / traces_to_prd 命中 R-AGENT-*）+ tech-design.md `## Agent 实现` section（component / traces_to_solution_arch 命中 solution.agent_architecture[].component / traces_to_prd_capability 命中 R-AGENT-* / implementation_loci / eval_scenarios 4 kind）。
</step>

<step id="step-3" n="3" goal="contract.yaml 初始化 + 5 typed groups patch">
 - 若 contracts/tech-design.contract.yaml 不存在，调用 `harness contract init --mission <mission-id> --stage design --template tech-design --json`。
 - 调用 `harness contract add-execution-result --mission <mission-id> --stage design --role tech-designer --json`。
 - 调用 `harness contract patch` 把 modules / interface_changes (kind enum) / data_changes (kind enum) / verification_strategy / production_readiness 4 elements 从 tech-design.md 抽取写入 contract.yaml。
 - 条件：check-capability-trigger.required=true
   - 同步 patch agent_implementation[]（含 traces_to_solution_arch / traces_to_prd_capability / implementation_loci / eval_scenarios 4 kinds）+ patch solution.contract.yaml.agent_architecture[]。
</step>

<step id="step-4" n="4" goal="effectiveness reviewer 循环 (max_rounds=3)">
 - 循环：max_rounds=3；退出条件：本轮 technical-design-effectiveness-reviewer 返回 PASS
   - Round start：
     <dispatch role="technical-design-effectiveness-reviewer" mode="spawn" />
     - brief：tech-design.md + contracts/tech-design.contract.yaml + solution.md + PRD + Mission Contract + interaction.md / interaction-spec 如存在 + project-context 技术约束 + Evidence Graph obligation slice。
     - 每轮进入前调用 `harness contract patch --add-round --mission <mission-id> --stage design --review effectiveness --json`。
   - 分支：审查结论
     - 情况：HOLD / BLOCKED
       - 修复 tech-design.md，立即回 round_start（design-tech-check-pending-recheck hook 物理阻断）。
     - 情况：PASS
       - 退出循环。
 - 用户确认点：loop 达到 max_rounds 且仍有阻断
   - 使用 AskUserQuestion 询问用户：(1) 提供解决方向重置 rounds (2) 接受降级（走 `harness approval append --type tradeoff --status approved --json`） (3) BLOCKED 升级。
</step>

<step id="step-5" n="5" goal="条件：capability reviewer 循环">
 - 条件：check-capability-trigger.required=true
   - 循环：max_rounds=3；退出条件：agent-capability-reviewer 返回 PASS
     - Round start：
       <dispatch role="agent-capability-reviewer" mode="spawn" />
       - brief：solution.md `## Agent 架构` + tech-design.md `## Agent 实现` + contract.agent_architecture / contract.agent_implementation + R-AGENT requirements。
       - 每轮进入前 `harness contract patch --add-round --mission <mission-id> --stage design --review agent_capability --json`。
     - 分支：审查结论
       - 情况：HOLD / BLOCKED
         - 把 finding 交回 capability-designer 修复对应 section，立即回 round_start。
       - 情况：PASS
         - 退出循环。
</step>

<step id="step-6" n="6" goal="条件：dependency-validity reviewer 循环">
 - 条件：check-dep-impact-trigger.required=true
   - 循环：max_rounds=3；退出条件：dependency-validity-reviewer 返回 PASS
     - Round start：
       <dispatch role="dependency-validity-reviewer" mode="spawn" />
       - brief：dependency-impact.md + tech-design.md interface_changes / data_changes 引用 + Mission Contract scope_in。
       - 每轮进入前 `harness contract patch --add-round --mission <mission-id> --stage design --review dependency_validity --json`。
     - 分支：审查结论
       - 情况：HOLD / BLOCKED
         - 修复 dependency-impact.md / tech-design.md，立即回 round_start。
       - 情况：PASS
         - 退出循环。
</step>

<step id="step-7" n="7" goal="Artifact Gate 自检">
 - 调用 `harness contract check --artifact contracts/tech-design.contract.yaml --upstream solution.contract.yaml --upstream prd.contract.yaml --upstream interaction.contract.yaml --upstream mission-contract.contract.yaml --json`；FAIL 必须修复后再继续。
 - 调用 `harness alignment check --mission <mission-id> --stage technical_analysis --json`；检查 modules / interfaces / data / verification_strategy 是否对齐 solution decisions、domain model、interaction flows/states。
 - 调用 `harness gate run --stage technical_analysis --mission <mission-id> --artifact tech-design.md --json`；status != PASS 时按返回 failed_checks 修复后重跑。
</step>

<step id="step-8" n="8" goal="Stage 完成 + Work Graph 输出">
 - 调用 `harness mission stage complete technical_analysis --mission <mission-id> --json`（design-tech-check-gate-pass hook 物理阻断 — 必须有 gate PASS 报告）。
 - tech-design.md 必须写入 lane_action.output_artifact 对应路径，并在 contract YAML 的 `work_graph_artifact.source_stage_artifact` 中引用同一路径。
</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `dep-impact-not-run` | step-0 dep-impact-trigger required=true 但 dependency-impact.md 不存在 | BLOCKED；返回 skill-router 路由到 dependency-impact skill 后再回 technical_analysis。 |
| `tech-designer-blocked` | step-1 tech-designer 返回 BLOCKED | 按 BLOCKED type 路由：missing_input → 回 step-0；scope_conflict → AskUserQuestion；decision_gate → 暂停。 |
| `capability-designer-blocked` | step-2 capability-designer 返回 BLOCKED | 检查 agent_engineering.scope；scope=experimental 时降级为 WARN，scope=core 时强校验后升级 BLOCKED。 |
| `reviewer-max-rounds` | step-4/step-5/step-6 loop 达到 max_rounds | 由对应 step user_checkpoint 处理。 |
| `contract-check-fail` | step-7 contract check FAIL | 按 finding code 分类：broken_module_reference → 回 step-1 修 traces_to；broken_interface_change_reference → 回 step-1 修 INT.traces_to；broken_agent_implementation_prd_trace → 回 step-2 修 capability-designer 输出；broken_data_change_reference → 回 step-1 修 DATA.traces_to。 |
| `gate-fail` | step-7 harness gate run FAIL | 按 failed_checks 分类修复后重跑 gate run。 |

</failure_paths>

</workflow>
