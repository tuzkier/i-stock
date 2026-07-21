# 方案阶段（solution）泳道动作工作流

> **思路来源**：RUP 的细化阶段（Elaboration），尤其是用例驱动、以架构为核心、尽早处理高风险问题；补充参考 `.harness/docs/methodology-reference.md` §3（C4 Model、架构决策记录 ADR、领域驱动设计 DDD、Arc42）

下文出现的所有 `harness ...` 命令一律通过 harness-cli skill 调用（默认带 `--json`，读取结构化返回；详见 `.harness/common/skills/harness-cli/SKILL.md`）。

<workflow stage="solution" version="2">

<goal>
  从产品定义包、系统行为描述、可选交互 / 原型产物、任务契约和探索事实出发，明确本次需求应该走哪条实现路线、为什么走这条路线、哪些做法不能采用、关键风险怎么处理，以及交给技术分析阶段（technical_analysis）继续展开的内容，使后续技术分析无需重新选择路线。
</goal>

<role>
  你是方案架构师。先判断现有材料能不能支撑路线选择，再根据系统行为描述、用例、质量与运行约束、领域边界、domain model、现有架构和风险确定路线与边界。方案阶段不写完整技术设计，不拆执行任务，不把“简单 / 快 / 改动少”作为架构理由。

  方案阶段必须留下方法执行痕迹：输入合格性判断、上游约定落地、路线驱动因素、关键决策、候选路线取舍、选定路线边界、风险处理和技术分析交接。不能只补段落标题或只列名称。
</role>

<stage_capability>

方案阶段对应 RUP 细化阶段的架构候选、关键机制和架构重要决策工作。它的核心能力不是写一个方向结论，而是回答“在约束和风险下为什么选择这条路线”。

| 能力 | 判断问题 | 产物要求 |
|---|---|---|
| 输入合格性判断 | 产品定义包、系统行为描述、交互产物、任务契约、探索事实、项目上下文和风险材料是否足以支持路线选择。 | 在 `solution.md` 写出路线选择前检查；输入不足时回流产品定义、交互、探索或决策门，不补造需求或事实。 |
| 路线驱动因素判断 | 哪些系统行为、用户目标、质量与运行约束、领域边界、现有架构约束和高优先级风险会改变实现路线。 | 把上游约定转成具名路线压力；不得只复制上游需求。 |
| 系统操作覆盖与自洽校验 | 选定路线是否保留 `SUC-xx-FLOW-xx` 流步骤和 `SUC-xx-OP-xx` 的触发、目标系统操作、对象 / 状态迁移 / 规则和可观察结果。 | 在 `solution.md` 产出一张「`SUC-xx-OP` → 承载决策 / 承载方式 / 自洽结论」覆盖矩阵（与 behavior-graph 的 `SURF` `traces_to` 承载同构），逐条核每个系统操作是否被某决策承载；方案只能决定承载方式和风险处理，不能重新定义系统行为。漏 OP 即覆盖缺口需补。 |
| 关键决策判断 | 哪些问题必须在方案阶段拍板，哪些可以交给技术分析细化。 | 只记录会影响系统边界、关键机制、禁用做法、风险处理或后续技术分析方向的决策。 |
| 候选路线比较判断 | 是否存在真实候选路线；如果只有一条合理路线，其他路线为什么不成立。 | 对候选路线按承载方式、取舍、适用条件、主要风险和验证难度比较；不得制造同义反复候选。 |
| 选定路线边界判断 | 选定路线的系统边界、关键机制、领域边界、集成方向、数据 / 状态方向和验证重点是什么。 | 明确后续技术分析不得重新选择的架构路线和禁止路径。 |
| 风险处理判断 | 每个高优先级风险本轮是验证、接受、阻断、降级还是回流。 | 写清风险处理方式、依据、后续责任阶段和必需证据；不得只写“后续缓解”。 |
| 技术分析交接判断 | 技术分析是否能在当前方案路线内继续展开模块、接口、数据、依赖、迁移、错误处理和验证策略。 | 写清交给技术分析继续展开的问题、来源决策和停止 / 回流条件。 |

</stage_capability>

<invariants>

| ID | 检查 | 约束来源 |
|---|---|---|
| `solution-contract-via-cli` | `solution.contract.yaml` 不得由子 Agent 直接写入或编辑，必须经 `harness contract fill/patch` | overlay=design.solution[deny=Write(solution.contract.yaml)] |
| `lane-action-singularity` | 同一设计切片内只能写 `solution.md`，不得写 `tech-design.md` / `interaction.md` / `interaction-spec/**` / `visual-interaction/**` | overlay=design.solution[deny=Write(other-lane-artifacts)]<br>cli=harness solution lane-action-validate |
| `reviewer-readonly` | `solution-effectiveness-reviewer` 必须以只读子 Agent 调用 | registry=subagents/solution-effectiveness-reviewer[readonly=true] |
| `anti-demo-anti-minimum-change` | `solution.md` 不得把先演示出来或局部小改作为正式架构路线 | cli=harness solution decision-scan |
| `fix-then-recheck` | `solution.md` 修改后必须重新过 `solution-effectiveness-reviewer`，禁止跳过 | hook=design-solution-check-pending-recheck |

</invariants>

<entry>
  - Mission Slice control_plane.stage=solution
  - 产品定义阶段已完成（产品定义包 + `prd.contract.yaml` 存在并 PASS）
  - 若 interaction 条件命中，则交互 / 原型阶段已完成或已被显式跳过并记录原因
  - 行为规格、质量与运行约束、现状事实和风险材料足以支持路线选择；不足时先回流上游，不得在方案中自行补假设
</entry>

<exit>
  - `solution-written`: `solution.md` 写入设计阶段工作区
  - `contract-filled`: `solution.contract.yaml` 已填充且 `harness contract check` PASS（含跨契约追踪）
  - `reviewer-pass`: `solution-effectiveness-reviewer` 在等同严格度下 PASS；或卡死后用户在 Decision Gate 上显式拥有残留风险的 approval 已记录（审查循环本身永不因轮次自动放行）
  - `decision-scan-pass`: `harness solution decision-scan` 返回 `status=PASS`（没有把演示、局部小改或含糊的风险处理当作正式方案）
  - `lane-action-clean`: `harness solution lane-action-validate` 返回 `status=PASS`（无跨泳道写入）
  - `architecture-baseline-ready`: `solution.md` 明确选定路线、架构边界、关键机制、禁用做法，以及后续阶段不得重新选择的路线
  - `risk-treatment-ready`: 每个高优先级风险都说明本轮是验证、接受、阻断、降级还是回流
  - `technical-analysis-handoff-ready`: 技术分析阶段（technical_analysis）能基于当前方案继续细化模块、接口、数据、依赖和验证策略
  - `gate-pass`: harness gate run --stage solution 返回 status=pass
</exit>

<subagents>

| 角色 | 模式 | 范围 / 限制 | 角色包 |
|---|---|---|---|
| `solution-architect` | spawn | harness-runtime/harness/artifacts/${mission-id}/solution/solution.md | `.harness/common/agents/solution-architect.md` |
| `solution-effectiveness-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/solution-effectiveness-reviewer.md` |
| `agent-capability-designer` | spawn; condition=agent_engineering.enabled=true | 仅限 `solution.md` 的 `## Agent 架构` 段，记录会影响系统路线的 Agent 边界，不写完整实现规格 | `.harness/common/agents/agent-capability-designer.md` |
| `agent-capability-reviewer` | spawn; readonly; condition=agent_engineering.enabled=true | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/agent-capability-reviewer.md` |

</subagents>

<inputs>

| 输入 | 必需性 | 用途 |
|---|---|---|
| `product/product-definition.md` | true | 系统责任、范围决策和质量与运行约束 |
| `product/use-case-model.md` | true | 业务用例、已确认系统用例、系统行为描述和界面承载要求 |
| `product/acceptance-scenarios.md` | true | 验收场景 / 条件和下游追溯锚点 |
| `product/product-evidence.md` | true | 产品证据与范围取舍 |
| `product/product-domain-model.md` | true | 领域边界、规则和不变量 |
| `interaction.md` | conditional: interaction stage 已完成 | 用户路径和界面状态 |
| `interaction-spec/use-case-realization.md` | conditional: interaction stage 已完成且涉及界面 / 用户旅程 | 用例到交互实现基线 |
| `interaction-spec/behavior-graph.yaml` | conditional: interaction stage 已完成且涉及界面 / 用户旅程 | 原型契约 SSOT；提供 `SURF-xxx` 界面、`PS-<surf>-<state>` 页面状态等可追溯 ref，方案决策须 `traces_to` 承载本 mission 的每个 SURF |
| `interaction-spec/surface-model.md` | conditional: interaction stage 已完成且涉及界面 / 用户旅程 | 界面边界、信息架构和领域到界面映射 |
| `interaction-spec/interaction-contract.md` | conditional: interaction stage 已完成且涉及界面 / 用户旅程 | 路径、状态、交互和端到端验证要求 |
| `visual-interaction-manifest.json` | conditional: interaction stage 已完成 | 可视化证据 |
| `mission-contract.md` | true | 任务目标、非目标和治理约束 |
| `project-context.md` | conditional: brownfield | 现有架构和工程约束 |
| `discovery-brief.md` | conditional: discovery 已完成 | 事实、未知和风险 |
| `project-knowledge/specs/_index.md` | conditional: spec.enabled=true | 行为规格索引 |
| `harness.yaml` | true via harness config snapshot | 项目配置 |

</inputs>

<outputs>

| 产物 | 路径 | 类型 | 说明 / 校验方式 |
|---|---|---|---|
| `solution-md` | `harness-runtime/harness/artifacts/${mission-id}/solution/solution.md` | markdown | 面向人读的路线选择、关键决策和边界说明；必须包含方法执行记录和方案约定模板的填写结果 |
| `solution-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/solution.contract.yaml` | contract | 供程序读取的方案契约；validator: `harness contract check --upstream prd.contract.yaml --upstream interaction.contract.yaml --upstream mission-contract.contract.yaml` |

</outputs>

<steps>

<step id="step-0" n="0" goal="阶段初始化 + 泳道动作验证">
 - 调用 `harness mission stage start --mission <mission-id> --stage solution --json`。
 - 调用 `harness trace log-init --mission <mission-id> --stage solution --json` 初始化 trace。
 - 调用 `harness context check --json`；PASS 则读取 `project-context.md`；FAIL 时按 `project-context` 规则处理，不得静默继续。
 - 调用 `harness config snapshot --json`，记录 `agent_engineering.enabled` 决定 Step 4 是否触发。
 - 若 interaction trigger 为 true 但交互产物缺失，BLOCKED 并返回 board-router/interaction；不得绕过原型直接做 solution。
 - 调用 `harness frame current --mission <mission-id> --json`，校验 `mission_slice.control_plane.stage=solution`；不一致时 BLOCKED。
 - 调用 `harness solution lane-action-validate --mission <mission-id> --json`；status != PASS 时 BLOCKED 并报告跨泳道写入。
</step>

<step id="step-1" n="1" goal="solution-architect 调度 + 起草路线和关键决策">
 通过 `Task(subagent_type="solution-architect", prompt=<Task Envelope>)` 工具调用 `solution-architect` subagent
	 - Task Envelope：任务目标 / 输入路径（`product/product-definition.md`、`product/use-case-model.md`、`product/acceptance-scenarios.md`、`product/product-evidence.md`、`product/product-domain-model.md`、`interaction.md`、`interaction-spec/use-case-realization.md`、`interaction-spec/behavior-graph.yaml`（如该 mission 已完成 interaction 且涉及界面，作为原型契约 SSOT 必读）、`interaction-spec/surface-model.md`、`interaction-spec/interaction-contract.md`、可视化清单如存在、任务契约、project-context、discovery-brief、相关规格）/ 输出路径 `harness-runtime/harness/artifacts/<mission-id>/solution/solution.md` / write_scope（仅 `solution.md`）/ 完成条件。输入摘要必须显式列出 `SUC-xx-FLOW-xx` 流步骤和 `SUC-xx-OP-xx` 系统操作；若有 behavior-graph，还须列出本 mission 的 `SURF-xxx` 界面与 `PS-<surf>-<state>` 页面状态，供方案决策 `traces_to` 承载。
 - 边界约束：若存在三份交互规格，solution-architect 不得忽略已确定的用例实现基线、界面约定、界面变更范围、信息架构、流程、状态、场景和验证要求。
 - 边界约束：若该 mission 有 behavior-graph，方案对原型决策【要么承载（某决策 `traces_to` 对应 `SURF-xxx`）、要么显式改写并经决策门 + 在契约 `prototype_coverage_exemptions` 登记 `{id, reason}` 豁免】，禁止静默漂移或自由重设计界面；本 mission 每个 SURF 未被任何决策承载会被 solution gate 报 `SURFACE_NOT_CARRIED`。
	 - 边界约束：solution-architect 可以选择系统行为的承载方式，但不得新增、删除或改写产品定义包的 `SUC-xx-OP-xx` 目标系统操作；发现系统操作无法承载时返回 BLOCKED 或回流产品定义。
 - **系统操作覆盖矩阵（必产）**：solution.md 必须含一张覆盖矩阵，列出本 mission 范围内每个 `SUC-xx-OP-xx`，逐行写「承载决策（命中某 `DEC-` / 决策条目）/ 承载方式（复用 / 扩展 / 新建 / 隔离等路线动作）/ 自洽结论（该决策是否保留该 OP 的触发、目标系统操作、对象 / 状态迁移、规则与可观察结果）」。该矩阵与 behavior-graph `SURF-xxx` 的 `traces_to` 承载校验同构：未被任何决策承载的 OP 即覆盖缺口，必须补承载决策或经决策门显式登记 N/A；不得遗漏、不得用同义复述把 OP 含糊带过。（建议后续加 `SUC-OP 覆盖门`，与 `SURFACE_NOT_CARRIED` 同构，对未承载 OP 报 FAIL。）
 - BLOCKED 路由：材料不足时返回 BLOCKED 或要求回流上游，不得在方案中自行补假设。只写 `solution.md` 并返回 DONE / BLOCKED；contract.yaml 由主流程通过 CLI 写。
</step>

<step id="step-2" n="2" goal="contract.yaml 初始化 + execution_result 写入">
 - 若 `harness-runtime/harness/stages/<mission-id>/contracts/solution.contract.yaml` 不存在，调用 `harness contract init --mission <mission-id> --stage solution --template solution --json`。
 - 调用 `harness contract add-execution-result --mission <mission-id> --stage solution --role solution-architect --json`，把 solution-architect 返回的 execution_result 写入 contract.yaml。
 - 调用 `harness contract patch` 把 decisions[] / forbidden_paths[] / risks[] 从 `solution.md` 抽取的结构化内容写入 contract.yaml。这里仅保持现有契约写入路径，不在本阶段扩展控制面字段。
</step>

<step id="step-3" n="3" goal="anti-pattern + lane scan">
 - 调用 `harness solution decision-scan --artifact harness-runtime/harness/artifacts/<mission-id>/solution/solution.md --json`。findings 非空 ⇒ 把 location + rule + message 反馈给 solution-architect，回 step-1 修复。
 - 调用 `harness solution lane-action-validate --mission <mission-id> --json`，再次确认未越界。
</step>

<step id="step-4" n="4" goal="审查循环（无轮次放行）">
 - 循环：无轮次放行（producer-fixable 缺口不设通过上限，轮次只记录修复历史）；退出条件：本轮 solution-effectiveness-reviewer 在等同严格度下返回 PASS
   - Round start：
     通过 `Task(subagent_type="solution-effectiveness-reviewer", prompt=<Task Envelope>)` 工具调用 `solution-effectiveness-reviewer` subagent
     - brief：`solution.md` + `solution.contract.yaml` + 产品定义包 + 交互 / 原型产物（如有，含 `behavior-graph.yaml`）+ mission-contract.md + project-context 摘要 + 证据图（Evidence Graph）中的下游验证要求 + RUP 方案能力检查点（材料是否足以决策、上游约定是否落到方案、方法执行记录是否完整、路线是否成立、风险是否有处理方式、技术分析是否能继续展开）。若该 mission 有 behavior-graph，存在未被任何决策承载、又未在 `prototype_coverage_exemptions` 登记理由的 `SURF-xxx`（原型承载缺口 / `SURFACE_NOT_CARRIED`），按阻断性发现走 HOLD。
     - 每轮进入前调用 `harness contract patch --add-round --mission <mission-id> --stage solution --review effectiveness --json`。
   - 分支：审查结论
     - 情况：HOLD / BLOCKED / 有阻断性发现
       - 修复 solution.md 中的阻断性问题，记录本轮发现与修复。
       - 立即回到 round_start 重新审查（design-solution-check-pending-recheck hook 物理阻断 advance）。
     - 情况：PASS / 无阻断性发现
       - 退出循环。调用 `harness contract patch --reviewer-verdict PASS --mission <mission-id> --stage solution --json`。
 - 用户确认点：卡死——同一阻断在修复 solution.md 后，reviewer 仍以相同根因连续 HOLD 且无实质进展（按缺口本质判断，不是"轮次到点"）
   - 不得降级通过。按 `core.md`「严格审查不变量」重新归因：producer 能补则留在循环升级修复策略继续修；本质是上游缺失则回流上游。仅当确需用户拍板才能解时，使用 AskUserQuestion，候选（**不含"接受降级 / 降级通过"**）：(1) 给出解决方向留在循环继续修 (2) 改范围 / 回流上游重导 (3) 升级 BLOCKED。残留风险只能由用户在充分披露后于 Decision Gate 显式拥有（走 `harness approval append --type tradeoff --status approved --comment <用户原话>` 写入 contract.role_verdicts.accepted_by_user=true）；审查循环本身永不把未解决阻断自动转为通过。
</step>

<step id="step-5" n="5" goal="条件：Agent 能力是否影响架构路线">
 - 条件：agent_engineering.enabled=true
   通过 `Task(subagent_type="agent-capability-designer", prompt=<Task Envelope>)` 工具调用 `agent-capability-designer` subagent
   - brief：mission-contract `## Agent Engineering`、产品定义包 agent_capability_requirements、solution.md 当前内容、agent-capability-engineering.md 摘要。
   - capability-designer 只更新 `solution.md` 的 `## Agent 架构` section，内容限定为会影响系统路线的判断：组件是否需要作为独立能力、责任边界、工作权方向、禁止越界点、需要技术分析阶段（technical_analysis）细化的约束和评估要求。
   - 本阶段不得把 Agent 能力写成完整实现规格，不展开评估（eval）场景细节，不替技术分析阶段（technical_analysis）设计具体 policy / hook / runtime guard。完整约束机制和评估场景由 technical_analysis 条件子流程完成。
   - capability-designer 输出后 patch contract.agent_architecture[]，每条含 component / work_rights_realization / implementation_loci / traces_to_prd（必须命中 prd.contract.yaml 的 R-AGENT-* IDs）。这里保持现有结构化写入，不新增控制面语义。
   - 循环：无轮次放行（producer-fixable 缺口不设通过上限）；退出条件：agent-capability-reviewer 在等同严格度下返回 PASS
     - Round start：
       通过 `Task(subagent_type="agent-capability-reviewer", prompt=<Task Envelope>)` 工具调用 `agent-capability-reviewer` subagent
       - brief：solution.md `## Agent 架构` + contract.agent_architecture[] + prd.contract.yaml.agent_capability_requirements + agent-capability-engineering.md 摘要。
     - 分支：审查结论
       - 情况：HOLD / BLOCKED
         - 把阻断性发现交回 capability-designer 修复对应 section，立即回 round_start。
       - 情况：PASS
         - 退出循环。
</step>

<step id="step-6" n="6" goal="Artifact Gate 自检">
 - 调用 `harness contract check --artifact contracts/solution.contract.yaml --upstream prd.contract.yaml --upstream interaction.contract.yaml --upstream mission-contract.contract.yaml --json`。若 interaction 未产出则省略该 upstream。FAIL 必须修复后再继续；含 broken_decision_reference / broken_agent_architecture_trace 等 finding 必须修。
 - 调用 `harness alignment check --mission <mission-id> --stage solution --json`；检查 decisions 是否对齐产品定义包、领域模型和三份交互规格。UNKNOWN_DOMAIN_REF / BROKEN_UPSTREAM_TRACE / UNAUTHORIZED_BEHAVIOR_EXPANSION / TERMINOLOGY_DRIFT / MISSING_ALIGNMENT_EVIDENCE 不得由审查员口头覆盖。
 - 调用 `harness gate run --stage solution --mission <mission-id> --artifact solution.md --json`；status != PASS 时按返回 failed_checks 修复后重跑。若该 mission 有 behavior-graph，gate 会对本 mission（mission-local 分母）每个 `SURF-xxx` 校验承载覆盖率：未被任何决策 `traces_to` 承载、又未登记 `prototype_coverage_exemptions` 时报 `SURFACE_NOT_CARRIED`（FAIL）；按 finding 回 step-1 补承载决策或登记豁免。
</step>

<step id="step-7" n="7" goal="Stage 完成 + Work Graph 输出">
 - 调用 `harness mission stage complete solution --mission <mission-id> --json`（design-solution-check-gate-pass hook 物理阻断 — 必须有 gate PASS 报告）。
 - 当前泳道动作产物 `solution.md` 必须写入 lane_action.output_artifact 对应路径，并在 contract YAML 的 `work_graph_artifact.source_stage_artifact` 中引用同一路径。
 - Stage Gate PASS 后由 harness-cli 应用 graph operation；本工作流不直接编辑 Work Graph 派生视图。
</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `solution-architect-blocked` | solution-architect 返回 BLOCKED | 记录 BLOCKED 原因到 contract.execution_result；按 BLOCKED type（missing_input / scope_conflict / decision_gate）路由：missing_input → 回 step-0 补输入；scope_conflict → AskUserQuestion 拍板范围；decision_gate → 暂停等用户。 |
| `review-stuck` | step-4 loop 卡死（修复后仍以相同根因连续 HOLD 无实质进展，非轮次到点） | 由 step-4 user_checkpoint 处理（重新归因；需用户拍板则 AskUserQuestion，候选仅：继续修 / 改范围回流上游 / 升级 BLOCKED，不含降级通过）。 |
| `contract-check-fail` | step-6 contract check FAIL | 按 finding code 分类：broken_decision_reference → 回 step-1 修 traces_to；broken_agent_architecture_trace → 回 step-5 修 capability-designer 输出；schema_validation_failed → 修字段后重跑。 |
| `gate-fail` | step-6 harness gate run FAIL | 按 failed_checks 分类修复后重跑 gate run；连续 3 次 FAIL 时升级 BLOCKED。 |
| `lane-action-cross-write` | step-3 lane-action-validate FAIL | 移除跨阶段写入（git restore），如确实需要 → 切换 Mission Slice stage 后再做。 |

</failure_paths>

</workflow>
