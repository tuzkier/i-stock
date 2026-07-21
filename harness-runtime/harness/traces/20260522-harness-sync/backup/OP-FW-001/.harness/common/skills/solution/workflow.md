# Solution lane action 工作流

> **方法论参考**：`.harness/docs/methodology-reference.md` §3（C4 Model、ADRs、DDD、Arc42）

下文出现的所有 `harness ...` 命令一律通过 harness-cli skill 调用（默认带 `--json`、消费 typed payload；详见 `.harness/common/skills/harness-cli/SKILL.md`）。

<workflow stage="solution" version="2">

<goal>
  从产品定义包 + 可选 interaction/prototype + Mission Contract 出发，按 `control_plane.stage=solution` 产出方案路线、关键决策、风险边界，落入 solution.md + contracts/solution.contract.yaml，由 solution-effectiveness-reviewer 审查通过。
</goal>

<role>
  你是方案设计者，先做判断（路线合理性、决策证据、风险边界），再写文档。只有在存在多条实质可行路线时，才做有理有据的方案选择。
</role>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `solution-contract-via-cli` | solution.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness contract fill/patch | overlay=design.solution[deny=Write(solution.contract.yaml)] |
| `lane-action-singularity` | 同 design slice 内只能写 solution.md，不得写 tech-design.md / interaction.md / interaction-spec/** / visual-interaction/** | overlay=design.solution[deny=Write(other-lane-artifacts)]<br>cli=harness solution lane-action-validate |
| `reviewer-readonly` | solution-effectiveness-reviewer 必须在 readonly subagent 中调用 | registry=subagents/solution-effectiveness-reviewer[readonly=true] |
| `anti-demo-anti-minimum-change` | solution.md 不得把先做 demo / 最小改动作为正式路径 | cli=harness solution decision-scan |
| `fix-then-recheck` | solution.md 修改后必须重新过 solution-effectiveness-reviewer，禁止跳过 | hook=design-solution-check-pending-recheck |

</invariants>

<entry>
  - Mission Slice control_plane.stage=solution
  - prd 阶段已完成（产品定义包 + prd.contract.yaml 存在并 PASS）
  - 若 interaction 条件命中，则 interaction/prototype 阶段已完成或已被显式跳过并记录原因
</entry>

<exit>
  - `solution-written`: solution.md 写入 design stage worktree
  - `contract-filled`: solution.contract.yaml 已填充且 harness contract check PASS（含 cross-contract trace）
  - `reviewer-pass`: solution-effectiveness-reviewer PASS 或用户降级 approval 已记录
  - `decision-scan-pass`: harness solution decision-scan 返回 status=PASS（无反 demo / 反最小改动 / 模糊 mitigation）
  - `lane-action-clean`: harness solution lane-action-validate 返回 status=PASS（无 cross-lane write）
  - `gate-pass`: harness gate run --stage solution 返回 status=pass
</exit>

<permissions>

<!-- design stage overlay：install pipeline 经 stage overlay key 从

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Edit(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Edit(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/stages/*/contracts/solution.contract.yaml)` | contract 必须经 harness contract fill/patch |
| deny | `Edit(harness-runtime/harness/stages/*/contracts/solution.contract.yaml)` | contract 必须经 harness contract patch |
| deny | `Write(harness-runtime/harness/stages/*/tech-design.md)` | lane action 单一性：tech-design.md 属 technical_analysis lane |
| deny | `Edit(harness-runtime/harness/stages/*/tech-design.md)` | lane action 单一性 |
| deny | `Write(harness-runtime/harness/stages/*/interaction.md)` | lane action 单一性：interaction.md 属 interaction lane |
| deny | `Edit(harness-runtime/harness/stages/*/interaction.md)` | lane action 单一性 |
| deny | `Write(harness-runtime/harness/stages/*/interaction-spec/**)` | lane action 单一性：interaction-spec 属 interaction lane |
| deny | `Edit(harness-runtime/harness/stages/*/interaction-spec/**)` | lane action 单一性 |
| deny | `Write(harness-runtime/harness/stages/*/visual-interaction/**)` | lane action 单一性：visual-interaction 属 interaction lane |
| deny | `Edit(harness-runtime/harness/stages/*/visual-interaction/**)` | lane action 单一性 |
| deny | `Write(harness-runtime/harness/stages/*/contracts/tech-design.contract.yaml)` | lane action 单一性 |
| deny | `Write(harness-runtime/harness/stages/*/contracts/interaction.contract.yaml)` | lane action 单一性 |
| allow | `Write(harness-runtime/harness/stages/*/solution.md)` | solution lane 主产物 |
| allow | `Bash(harness *)` | solution lane CLI 必需 |

       design.solution.json 物化（非本 XML island）；此处 <permissions> 与
       design.solution.json 内容镜像，供 workflow 自文档化 + XML v2 W002 一致性。 -->

</permissions>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `solution-architect` | spawn | harness-runtime/harness/stages/${mission-id}/solution.md | `.harness/common/agents/solution-architect.md` |
| `solution-effectiveness-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/solution-effectiveness-reviewer.md` |
| `agent-capability-designer` | spawn; condition=agent_engineering.enabled=true | harness-runtime/harness/stages/${mission-id}/solution.md (## Agent 架构 section only) | `.harness/common/agents/agent-capability-designer.md` |
| `agent-capability-reviewer` | spawn; readonly; condition=agent_engineering.enabled=true | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/agent-capability-reviewer.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `product/product-definition.md` | true | Memory |
| `product/product-evidence.md` | true | Evidence |
| `product/product-domain-model.md` | true | Memory |
| `interaction.md` | conditional: interaction stage 已完成 | Memory |
| `interaction-spec/` | conditional: interaction stage 已完成且涉及 UI / user journey | Memory |
| `visual-interaction-manifest.json` | conditional: interaction stage 已完成 | Evidence |
| `mission-contract.md` | true | Intent |
| `project-context.md` | conditional: brownfield | Context |
| `discovery-brief.md` | conditional: discovery 已完成 | Context |
| `project-knowledge/specs/_index.md` | conditional: spec.enabled=true | Memory |
| `harness.yaml` | true via harness config snapshot | Memory |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `solution-md` | `harness-runtime/harness/stages/${mission-id}/solution.md` | markdown | Memory |
| `solution-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/solution.contract.yaml` | contract | Artifact Contract; validator: `harness contract check --upstream prd.contract.yaml --upstream interaction.contract.yaml --upstream mission-contract.contract.yaml` |

</outputs>

<steps>

<step id="step-0" n="0" goal="Stage 初始化 + lane action 验证">
 - 调用 `harness mission stage start --mission <mission-id> --stage solution --json`。
 - 调用 `harness trace log-init --mission <mission-id> --stage solution --json` 初始化 trace。
 - 调用 `harness context check --json`；PASS 则读取 `project-context.md`；FAIL 时按 `project-context` 规则处理，不得静默继续。
 - 调用 `harness config snapshot --json`，记录 `agent_engineering.enabled` 决定 Step 4 是否触发。
 - 若 interaction trigger 为 true 但 interaction 产物缺失，BLOCKED 并返回 board-router/interaction；不得绕过原型直接做 solution。
 - 调用 `harness frame current --mission <mission-id> --json`，校验 `mission_slice.control_plane.stage=solution`；不一致时 BLOCKED。
 - 调用 `harness solution lane-action-validate --mission <mission-id> --json`；status != PASS 时 BLOCKED 并报告 cross-lane writes。
</step>

<step id="step-1" n="1" goal="solution-architect 调度 + solution.md 起草">
 <dispatch role="solution-architect" mode="spawn" />
 - Task Envelope 包含：任务目标 / 输入路径（product/product-definition.md、product/product-evidence.md、product/product-domain-model.md、interaction.md / interaction-spec / visual manifest 如存在、Mission Contract、project-context、discovery-brief、相关 specs）/ 输出路径 `harness-runtime/harness/stages/<mission-id>/solution.md` / write_scope（仅 solution.md）/ 完成条件。方案必须显式消费 DDD 模型中的 bounded context、context map、policy、domain event 和 aggregate consistency boundary；若存在 interaction-spec，方案不得忽略其系统 surface baseline / changeset、信息架构、surface / flow / state / scenario / validation 合同，不得打穿产品定义的限界上下文。
 - solution-architect 必须按目标驱动设计，识别决策点；只有存在 ≥2 条实质可行路线时才列候选方案。每个 decision 必须有 chosen + rationale + traces_to。
 - solution-architect 只写 solution.md 并返回 DONE / BLOCKED；contract.yaml 由主流程通过 CLI 写。
</step>

<step id="step-2" n="2" goal="contract.yaml 初始化 + execution_result 写入">
 - 若 `harness-runtime/harness/stages/<mission-id>/contracts/solution.contract.yaml` 不存在，调用 `harness contract init --mission <mission-id> --stage design --template solution --json`。
 - 调用 `harness contract add-execution-result --mission <mission-id> --stage design --role solution-architect --json`，把 solution-architect 返回的 execution_result 写入 contract.yaml。
 - 调用 `harness contract patch` 把 decisions[] / forbidden_paths[] / risks[] 从 solution.md 抽取的结构化内容写入 contract.yaml。
</step>

<step id="step-3" n="3" goal="anti-pattern + lane scan">
 - 调用 `harness solution decision-scan --artifact harness-runtime/harness/stages/<mission-id>/solution.md --json`。findings 非空 ⇒ 把 location + rule + message 反馈给 solution-architect，回 step-1 修复。
 - 调用 `harness solution lane-action-validate --mission <mission-id> --json`，再次确认未越界。
</step>

<step id="step-4" n="4" goal="reviewer 循环 (max_rounds=3)">
 - 循环：max_rounds=3；退出条件：本轮 solution-effectiveness-reviewer 返回 PASS
   - Round start：
     <dispatch role="solution-effectiveness-reviewer" mode="spawn" />
     - brief：solution.md + solution.contract.yaml + 产品定义包 + interaction/prototype（如有）+ mission-contract.md + project-context 摘要 + Evidence Graph obligation slice。
     - 每轮进入前调用 `harness contract patch --add-round --mission <mission-id> --stage design --review effectiveness --json`。
   - 分支：审查结论
     - 情况：HOLD / BLOCKED / 有阻断性发现
       - 修复 solution.md 中的阻断性问题，记录本轮发现与修复。
       - 立即回到 round_start 重新审查（design-solution-check-pending-recheck hook 物理阻断 advance）。
     - 情况：PASS / 无阻断性发现
       - 退出循环。调用 `harness contract patch --reviewer-verdict PASS --mission <mission-id> --stage design --json`。
 - 用户确认点：loop 达到 max_rounds 且仍有阻断
   - 使用 AskUserQuestion 询问用户：选择 (1) 提供解决方向重置 rounds 继续 (2) 接受降级（走 `harness approval append --type tradeoff --status approved --comment <用户原话>` 写入 contract.role_verdicts.accepted_by_user=true） (3) BLOCKED 升级。
</step>

<step id="step-5" n="5" goal="条件：Agent 能力设计 (## Agent 架构 section)">
 - 条件：agent_engineering.enabled=true
   <dispatch role="agent-capability-designer" mode="spawn" />
   - brief：mission-contract `## Agent Engineering`、产品定义包 agent_capability_requirements、solution.md 当前内容、agent-capability-engineering.md 摘要。
   - capability-designer 只更新 solution.md `## Agent 架构` section（write_scope_section_only 由 frontmatter + M3 hook 兜底；当前 hook 推迟至 backlog 时由 reviewer 审查覆盖）。
   - capability-designer 输出后 patch contract.agent_architecture[]，每条含 component / work_rights_realization / implementation_loci / traces_to_prd（必须命中 prd.contract.yaml 的 R-AGENT-* IDs）。
   - 循环：max_rounds=3；退出条件：agent-capability-reviewer 返回 PASS
     - Round start：
       <dispatch role="agent-capability-reviewer" mode="spawn" />
       - brief：solution.md `## Agent 架构` + contract.agent_architecture[] + prd.contract.yaml.agent_capability_requirements + agent-capability-engineering.md 摘要。
     - 分支：审查结论
       - 情况：HOLD / BLOCKED
         - 把阻断性发现交回 capability-designer 修复对应 section，立即回 round_start。
       - 情况：PASS
         - 退出循环。
</step>

<step id="step-6" n="6" goal="Artifact Gate 自检">
 - 调用 `harness contract check --artifact contracts/solution.contract.yaml --upstream prd.contract.yaml --upstream interaction.contract.yaml --upstream mission-contract.contract.yaml --json`。若 interaction 未产出则省略该 upstream。FAIL 必须修复后再继续；含 broken_decision_reference / broken_agent_architecture_trace 等 finding 必须修。
 - 调用 `harness alignment check --mission <mission-id> --stage solution --json`；检查 decisions 是否对齐 PRD、domain model、interaction-spec。UNKNOWN_DOMAIN_REF / BROKEN_UPSTREAM_TRACE / UNAUTHORIZED_BEHAVIOR_EXPANSION / TERMINOLOGY_DRIFT / MISSING_ALIGNMENT_EVIDENCE 不得由 reviewer 口头覆盖。
 - 调用 `harness gate run --stage solution --mission <mission-id> --artifact solution.md --json`；status != PASS 时按返回 failed_checks 修复后重跑。
</step>

<step id="step-7" n="7" goal="Stage 完成 + Work Graph 输出">
 - 调用 `harness mission stage complete solution --mission <mission-id> --json`（design-solution-check-gate-pass hook 物理阻断 — 必须有 gate PASS 报告）。
 - 当前 lane action 产物 solution.md 必须写入 lane_action.output_artifact 对应路径，并在 contract YAML 的 `work_graph_artifact.source_stage_artifact` 中引用同一路径。
 - Stage Gate PASS 后由 harness-cli 应用 graph operation；本工作流不直接编辑 Work Graph 派生视图。
</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `solution-architect-blocked` | solution-architect 返回 BLOCKED | 记录 BLOCKED 原因到 contract.execution_result；按 BLOCKED type（missing_input / scope_conflict / decision_gate）路由：missing_input → 回 step-0 补输入；scope_conflict → AskUserQuestion 拍板范围；decision_gate → 暂停等用户。 |
| `reviewer-max-rounds` | step-4 loop 达到 max_rounds | 由 step-4 user_checkpoint 处理（不重复实现）。 |
| `contract-check-fail` | step-6 contract check FAIL | 按 finding code 分类：broken_decision_reference → 回 step-1 修 traces_to；broken_agent_architecture_trace → 回 step-5 修 capability-designer 输出；schema_validation_failed → 修字段后重跑。 |
| `gate-fail` | step-6 harness gate run FAIL | 按 failed_checks 分类修复后重跑 gate run；连续 3 次 FAIL 时升级 BLOCKED。 |
| `lane-action-cross-write` | step-3 lane-action-validate FAIL | 移除 cross-stage 写入（git restore），如确实需要 → 切换 Mission Slice stage 后再做。 |

</failure_paths>

</workflow>
