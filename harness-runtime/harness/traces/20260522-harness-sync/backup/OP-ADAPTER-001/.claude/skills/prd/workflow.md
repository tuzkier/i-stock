# 产品定义工作流

> **方法论参考**：`.harness/docs/methodology-reference.md` §2（BDD/Given-When-Then；User Story Mapping；领域建模；规格驱动开发；IEEE 29148）。
> `prd` 是历史 stage key，不再代表产物文件名；本阶段主产物是 `product/product-definition.md`。

下文出现的所有 `harness ...` 命令一律通过 harness-cli skill 调用（默认带 `--json`、消费 typed payload、不直接拼 Bash 底层脚本，详见 `.harness/common/skills/harness-cli/SKILL.md`）。

<workflow stage="prd" version="3">

<goal>
  从 Mission Contract 出发，产出产品定义包：主产品定义、证据记录、DDD 产品领域模型、外部行为契约和审查结论。目标是让 solution / interaction / technical_analysis / breakdown / verify 不再猜测业务问题、范围、规则或验收口径。
</goal>

<role>
  你是产品定义编排者。你不把 PRD 当成单一文档目标，也不把所有产品能力塞进一个全能专家。默认先调度业务领域建模、验收场景设计和范围策略子专家产出专业分析，再由 senior-product-expert 综合成产品定义包，最后调度只读 reviewer 审查。文档是结果，产品判断是核心。
</role>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `product-definition-package` | prd 阶段必须产出 product/product-definition.md、product/product-evidence.md、product/product-domain-model.md 和 contracts/prd.contract.yaml |  |
| `prd-contract-not-fenced` | product-definition.md / product-evidence.md / product-domain-model.md 不得内嵌 fenced YAML contract / behaviour_contract / execution_result / role_verdicts | hook=harness-lint |
| `api-contract-draft-required-for-frontend-engineering` | 当 `prototype.delivery_mode=frontend_engineering` 且 mission 涉及 UI 时，必须产出 `api-contract-draft.md` | Step 5a |
| `prd-contract-via-cli` | prd.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness contract fill/patch | hook=prd-check-contract-via-cli |
| `reviewer-readonly` | product-definition-reviewer 必须在 readonly subagent 中调用 | registry=subagents/product-definition-reviewer[readonly=true] |
| `mission-boundary` | 产品定义不得补造 Mission 未授权目标；发现目标、范围、成功定义缺口时返回 NEEDS_DECISION 并回 Mission / 用户决策 |  |
| `product-not-technical-architecture` | product-domain-model 是产品领域模型，不得决定数据库、接口、框架、存储或部署方案 |  |
| `ddd-domain-model` | product-domain-model 必须按 DDD 覆盖战略建模、战术建模、规则约束、追溯和下游消费指引；不适用项必须说明原因 | cli=harness prd domain-model-lint |
| `measurable-requirements` | 所有 FR/NFR/Rule/Scenario 必须有可观察或可量化验收标准；禁止模糊形容词、实现泄漏 | cli=harness prd anti-pattern-scan |

</invariants>

<entry>
  - mission-contract 已完成 intake / discovery（或 discovery 被跳过）
  - Mission Contract 至少包含真实任务目标、产品故事上下文、成功定义、范围边界、约束和验证口径
  - skill-router 已判定本消息属 prd 阶段
</entry>

<exit>
  - `package-written`: 产品定义包 markdown 产物写入 prd stage worktree
  - `contract-filled`: prd.contract.yaml 已填充且 harness contract check PASS
  - `reviewer-pass`: product-definition-reviewer PASS 或用户降级 approval 已记录
  - `gate-pass`: harness gate run --stage prd 返回 status=pass
  - `spec-sync`: spec.enabled=true 时差量规格已产出且 delta-lint PASS
</exit>

<permissions>

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Write(harness-runtime/harness/stages/*/contracts/prd.contract.yaml)` |  |
| deny | `Edit(harness-runtime/harness/stages/*/contracts/prd.contract.yaml)` |  |
| allow | `Write(harness-runtime/harness/stages/*/product/product-definition.md)` |  |
| allow | `Write(harness-runtime/harness/stages/*/product/product-evidence.md)` |  |
| allow | `Write(harness-runtime/harness/stages/*/product/product-domain-model.md)` |  |
| allow | `Write(harness-runtime/harness/stages/*/product/business-object-analysis.md)` |  |
| allow | `Write(harness-runtime/harness/stages/*/product/acceptance-scenarios.md)` |  |
| allow | `Write(harness-runtime/harness/stages/*/product/scope-strategy.md)` |  |
| allow | `Write(harness-runtime/harness/stages/*/api-contract-draft.md)` | 仅在 prototype.delivery_mode=frontend_engineering 时由 Step 5a 产出 |
| allow | `Write(harness-runtime/harness/stages/*/specs/**/spec.md)` |  |
| allow | `Bash(harness *)` |  |

</permissions>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `business-domain-modeler` | spawn | harness-runtime/harness/stages/${mission-id}/product/business-object-analysis.md | `.harness/common/agents/business-domain-modeler.md` |
| `acceptance-scenario-designer` | spawn | harness-runtime/harness/stages/${mission-id}/product/acceptance-scenarios.md | `.harness/common/agents/acceptance-scenario-designer.md` |
| `product-scope-strategist` | spawn | harness-runtime/harness/stages/${mission-id}/product/scope-strategy.md | `.harness/common/agents/product-scope-strategist.md` |
| `senior-product-expert` | spawn | harness-runtime/harness/stages/${mission-id}/product/product-definition.md, harness-runtime/harness/stages/${mission-id}/product/product-evidence.md, harness-runtime/harness/stages/${mission-id}/product/product-domain-model.md, harness-runtime/harness/stages/${mission-id}/specs/**/spec.md | `.harness/common/agents/senior-product-expert.md` |
| `product-definition-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/product-definition-reviewer.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `mission-contract.md` | true | Intent |
| `project-context.md` | conditional: brownfield | Context |
| `discovery-brief.md` | conditional: discovery 已完成 | Context |
| `project-knowledge/_index.md` | conditional: 长期知识存在 | Memory |
| `project-knowledge/specs/_index.md` | conditional: spec.enabled=true | Memory |
| `gitnexus evidence` | conditional: brownfield 或涉及现有代码/架构/影响面 | Context |
| `harness.yaml` | true via harness config snapshot | Memory |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `product-definition` | `harness-runtime/harness/stages/${mission-id}/product/product-definition.md` | markdown | Memory |
| `product-evidence` | `harness-runtime/harness/stages/${mission-id}/product/product-evidence.md` | markdown | Evidence |
| `product-domain-model` | `harness-runtime/harness/stages/${mission-id}/product/product-domain-model.md` | markdown | Memory |
| `business-object-analysis` | `harness-runtime/harness/stages/${mission-id}/product/business-object-analysis.md` | markdown | Evidence / Memory |
| `acceptance-scenarios` | `harness-runtime/harness/stages/${mission-id}/product/acceptance-scenarios.md` | markdown | Evidence |
| `scope-strategy` | `harness-runtime/harness/stages/${mission-id}/product/scope-strategy.md` | markdown | Evidence |
| `prd-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/prd.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |

</outputs>

<steps>

<step id="step-0" n="0" goal="Stage 初始化">
 - 调用 `harness mission stage start --mission <mission-id> --stage prd`；stage 必须来自 Mission Slice `control_plane.stage`，不使用额外 stage。
 - 调用 `harness trace log-init --mission <mission-id> --stage prd --json` 初始化 trace。
 - 调用 `harness context check --json`；PASS 则读取 `project-context.md`；FAIL 时按 `project-context` 规则处理，并在 evidence 中记录 `inputs_missing.project_context=true`，不得静默继续。
 - 调用 `harness config snapshot --json`，记录 `spec.enabled` 和 `agent_engineering.enabled`；不得直接读取 `harness-runtime/config/harness.yaml`。
 - 若项目存在长期知识，先读取 `project-knowledge/_index.md` 或调用 `harness knowledge resolve --stage prd --json` 获取本阶段相关知识，不得全量读取知识库。
 - 若 `spec.enabled=true`，读取 `project-knowledge/specs/_index.md` 并解析当前能力基线；产品定义必须标注新增/修改/移除的能力与既有 spec 的关系。
 - 若是棕地项目，或 Mission / discovery 涉及现有代码、架构、调用链、模块边界、影响面，叠加 `gitnexus-exploring` / `gitnexus-impact-analysis` 作为证据来源；不可用时在 `product-evidence.md` 与 contract degradations 中记录降级原因和补救动作。
 - 使用 `harness frame current --mission <mission-id> --json` 返回的 Mission Slice 快照；消费 `work_graph.primary_nodes`、stage `output_artifact`、`graph_operation` 和 role policy。
 - 若 Mission Contract 缺真实任务目标、用户/问题/场景/价值/成功指标、成功定义、范围边界或验证口径，停止并回 Mission 决策；不得让产品专家补造。
</step>

<step id="step-1" n="1" goal="专业子专家产出产品定义输入">
 通过 `Task(subagent_type="business-domain-modeler", prompt=<Task Envelope>)` 工具调用 `business-domain-modeler` subagent
 - Task Envelope 包含：Mission Contract、discovery-brief（如有）、knowledge resolve 摘要、project-context、业务参考材料、输出路径 `product/business-object-analysis.md`、write_scope、完成条件。
 - business-domain-modeler 必须识别业务对象、属性、状态属性、引用角色、数量关系、版本 / deactive 规则和业务规则；不得写技术设计。
 - 条件：business-domain-modeler 返回 NEEDS_DECISION / BLOCKED
  - 记录阻塞原因，向用户发起 Decision Gate；不得让 senior-product-expert 猜测业务对象后继续。

 通过 `Task(subagent_type="acceptance-scenario-designer", prompt=<Task Envelope>)` 工具调用 `acceptance-scenario-designer` subagent
 - Task Envelope 包含：Mission Contract、discovery-brief（如有）、business-object-analysis 路径、风险 / 依赖摘要、输出路径 `product/acceptance-scenarios.md`、write_scope、完成条件。
 - acceptance-scenario-designer 必须把用户场景、业务规则、领域对象状态变化转成 Scenario / Rule / GWT / AC 和验证证据类型；不得写测试实现。
 - 条件：acceptance-scenario-designer 返回 NEEDS_DECISION / BLOCKED
  - 记录阻塞原因，向用户发起 Decision Gate；不得让 senior-product-expert 补造可观察验收口径。

 通过 `Task(subagent_type="product-scope-strategist", prompt=<Task Envelope>)` 工具调用 `product-scope-strategist` subagent
 - Task Envelope 包含：Mission Contract、discovery-brief（如有）、business-object-analysis 路径、acceptance-scenarios 路径、knowledge / spec / GitNexus evidence 摘要、输出路径 `product/scope-strategy.md`、write_scope、完成条件。
 - product-scope-strategist 必须产出 In / Out / Later / Decision Needed、范围理由、依赖风险和下游边界；不得默认按“最小实现”收缩范围。
 - 条件：product-scope-strategist 返回 NEEDS_DECISION / BLOCKED
  - 记录阻塞原因，向用户发起 Decision Gate；不得继续综合。
</step>

<step id="step-2" n="2" goal="资深产品专家综合产品定义包">
 通过 `Task(subagent_type="senior-product-expert", prompt=<Task Envelope>)` 工具调用 `senior-product-expert` subagent
 - Task Envelope 包含：Mission Contract、project-context、discovery-brief（如有）、knowledge resolve 摘要、spec baseline 摘要、GitNexus evidence（如有）、`business-object-analysis.md`、`acceptance-scenarios.md`、`scope-strategy.md`、模板 `product-definition.md` / `product-evidence.md` / `product-domain-model.md`、输出路径、write_scope、完成条件。
 - senior-product-expert 必须按内部 workflow 完成：Mission readiness → evidence gathering → problem diagnosis → specialist synthesis → product domain model → scope/tradeoffs → product definition → package completeness check。
 - 必须写入 `product/product-definition.md`、`product/product-evidence.md` 和 `product/product-domain-model.md`。领域模型是产品阶段核心产物；必须消费业务对象分析中的核心对象、状态、引用关系和规则；不适用的 DDD 要素必须说明原因，但不得为了填空引入虚假聚合或技术实现概念。
 - `product/product-definition.md` 是主产品定义正文。Markdown 只能引用外部 `contracts/prd.contract.yaml`，不得内嵌 contract YAML。
 - 主流程从 senior-product-expert 返回摘要中提取 behaviour contract 字段，通过 `harness contract init` / `harness contract patch` 写入 contract。
 - 条件：senior-product-expert 返回 NEEDS_DECISION / BLOCKED
  - 调用 `harness contract add-execution-result` 或 `harness contract patch` 记录阻塞原因，向用户发起 Decision Gate；不得继续审查或下游推进。
</step>

<step id="step-3" n="3" goal="反模式自检">
 - 调用 cli `harness prd anti-pattern-scan` `--artifact harness-runtime/harness/stages/${mission-id}/product/product-definition.md`，evidence=required。
 - 调用 cli `harness prd domain-model-lint` `--artifact harness-runtime/harness/stages/${mission-id}/product/product-domain-model.md --product-definition harness-runtime/harness/stages/${mission-id}/product/product-definition.md`，evidence=required。
 - 条件：findings 非空
  - 按 typed `{rule, location, evidence}` 逐条修复 product-definition.md / product-evidence.md / product-domain-model.md
  - 重新调用 `harness prd anti-pattern-scan` 和 `harness prd domain-model-lint`，直到 `status=PASS`
</step>

<step id="step-4" n="4" goal="Contract 初始化与状态更新">
 - 调用 cli `harness contract init` `--mission ${mission-id} --stage prd --template prd`，evidence=required。
 - 通过 `harness contract patch` 写入 `product_definition_package`、`domain_model`、`covers_intent`、`user_story_mapping`、`functional_requirements`、`non_functional_requirements`、`business_rules`、`product_metrics`、`risks`、`dependencies`、`execution_result`。
 - 调用 cli `harness prd domain-model-lint` `--artifact harness-runtime/harness/stages/${mission-id}/product/product-domain-model.md --product-definition harness-runtime/harness/stages/${mission-id}/product/product-definition.md --contract harness-runtime/harness/stages/${mission-id}/contracts/prd.contract.yaml`，evidence=required。
 - 调用 `harness contract check --artifact contracts/prd.contract.yaml --upstream mission-contract.contract.yaml --json`；FAIL 必须修复后再继续。
</step>

<step id="step-5" n="5" goal="Work Graph 产物绑定">
 - 确认本阶段 stage 来自 `work_graph.lanes`，不得另造映射。
 - 绑定 Mission Slice primary node + stage output_artifact + graph_operation + work_graph_artifact。主产物为 `product/product-definition.md`；supplementary artifacts 包含证据、领域模型和可选 specs。
 - PRD workflow 只写 stage 目录和外部 contract；Work Graph 写入在 Gate PASS 后的 `harness gate advance`。
</step>

- 条件：`prototype.delivery_mode=frontend_engineering` 且 mission 涉及 UI（`harness interaction check-ui-trigger` 返回 requires_interaction=true）
 <step id="step-5a" n="5a" goal="产出 api-contract-draft.md（前端契约草案）">
  - 模板：`harness-runtime/templates/api-contract-draft.md`。
  - 写入路径：`harness-runtime/harness/stages/${mission_id}/api-contract-draft.md`。
  - 内容：endpoint 总览（method / path / 描述 / traces_to AC / 鉴权幂等限流备注）+ shared types 草图（领域实体、状态枚举、Request / Response 形状）+ 错误码 + 演示分支 scenarios + 鉴权/权限/数据边界 + 非 endpoint 形态 + open questions。
  - 这是 interaction stage（prototype-as-frontend 路线）frontend-prototype-engineer 抽 `lib/types/` draft 的输入；粒度是草案，不是完整 OpenAPI。
  - 同步在 `prd.contract.yaml` 的 `supplementary_artifacts` 段引用此文件。
  - 不在 frontend_engineering 路线时跳过此步。
 </step>

- 条件：spec.enabled=true
 <step id="step-6" n="6" goal="产出差量规格（行为契约增量）">
  - 参考 `project-knowledge/specs/_index.md` 格式说明 + `harness-runtime/templates/delta-spec.md` 模板。
  - 从 discovery brief 或 product-definition.md 的 capabilities / FR 反推能力清单。
  - 对每个能力产出差量规格：定位基线 → 分类 Requirement（ADDED/MODIFIED/REMOVED）→ 写 Scenario（四级标题 `####`，GIVEN/WHEN/THEN）→ 写入 `stages/<mission-id>/specs/<capability>/spec.md`。
  - 调用 cli `harness spec delta-lint` `--mission ${mission-id} --capability ${capability-name}`，evidence=required。
  - 条件：delta-lint FAIL
   - 按 `findings` 修正差量规格后重新 lint
  - 同步更新 `prd.contract.yaml` capabilities[] 的 delta_spec / requirement_ids / scenario_ids / traces_to。
 </step>

- 条件：agent_engineering.enabled=true
 <step id="step-7" n="7" goal="补充 Agent 能力 Requirements">
  - 检查 Mission Contract `## Agent Engineering` 段落和 product-definition.md 的 Agent Capability Requirements。
  - 条件：存在 Agent 组件标记
   - 调用 cli `harness prd agent-cap-eval` `--mission ${mission-id} --component ${name} --work-rights ${list} --priority ${P}`，evidence=required。
   - 与 contract `agent_capability_requirements[]` 同步。
 </step>

<step id="step-8" n="8" goal="Artifact Gate 自检">
 - 调用 cli `harness gate run` `--stage prd --mission ${mission-id} --artifact harness-runtime/harness/stages/${mission-id}/product/product-definition.md --mission-slice ${path}`，evidence=required。
 - 条件：gate status=FAIL
  - 按 `failed_checks` 逐条修复产品定义包或 contract，重新 `gate run` 直到 PASS。
</step>

<step id="step-9" n="9" goal="产品定义有效性审查（审查-修复循环）">
 - 循环：id=reviewer-loop；max_rounds=3；退出条件：product-definition-reviewer 返回 PASS / 无阻断
  - 调用 `harness contract patch --add-round --json`，自动维护 `effectiveness_review.rounds_used += 1`。
  通过 `Task(subagent_type="product-definition-reviewer", prompt=<Task Envelope>)` 工具调用 `product-definition-reviewer` subagent
  - Task Envelope：product-definition.md、product-evidence.md、product-domain-model.md、business-object-analysis.md、acceptance-scenarios.md、scope-strategy.md、contract 路径、Mission Contract、探索简报、project-context、差量规格路径、只读约束、产品定义审查清单、verdict 格式。

  - 分支：审查结论
   - 情况：HOLD / BLOCKED
    - 修复产品定义包阻断性问题，记录发现和修复内容。
    - 调用 `harness contract patch --add-round --json` 设置 `pending_reviewer_recheck=true`。
    - 立即重新 dispatch product-definition-reviewer 全量审查。
    - Hard gate `no-skip-recheck`：
     - 修复完成不等于审查通过。只有 reviewer 确认无阻断且 pending_reviewer_recheck=false 才能退出。
     - Enforced by: hook=prd-check-pending-recheck
   - 情况：PASS
    - 审查通过，退出循环。

 - 条件：达到 max_rounds 后仍有阻断
  - 调用 tool: `AskUserQuestion`。
   - 问题：产品定义审查循环已达 max_rounds=3，最近 verdict 为 ${last_verdict}，请选择处理方式：
   - 候选答案：
      - 接受当前产品定义包（记录 tradeoff approval 后继续）
      - 调整 Mission Contract scope（回 intake）
      - 补充领域模型或范围策略后重审
      - 重新审查（升级 reviewer 模型 / 切换 mode）
  - 条件：用户选择接受
   - 调用 cli `harness approval append` `--mission ${mission-id} --type tradeoff --stage prd --status approved`，evidence=required。

 - 审查摘要附加到 product/product-definition.md 末尾；role_verdicts 通过 `harness contract add-verdict` 写入 contract。
</step>

<step id="step-10" n="10" goal="Stage exit">
 - 确认 Step 8 gate run PASS 且 Step 9 reviewer PASS / approval 后，调用 `harness mission stage complete --mission <mission-id> --stage prd --json` 写完整 exit evidence。
</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `product-specialist-blocked` | business-domain-modeler / acceptance-scenario-designer / product-scope-strategist 返回 BLOCKED / NEEDS_DECISION | 记录业务对象、验收口径或范围策略缺口，向用户发起 Decision Gate；不得由 senior-product-expert 猜测后继续。 |
| `senior-product-expert-blocked` | senior-product-expert 返回 BLOCKED / NEEDS_DECISION | 记录真实问题、业务目标、成功定义、领域规则、范围取舍、风险接受或 Mission fit 缺口，向用户发起 Decision Gate；不得默认按“最小实现”降级。 |
| `reviewer-blocked` | product-definition-reviewer 返回 BLOCKED / HOLD | 按 Step 9 审查-修复循环处理；达到 max_rounds 后仍有阻断 → AskUserQuestion。 |
| `contract-check-fail` | harness contract check FAIL | 按 findings 逐条修复 contract 字段；不得用 --allow-placeholders 跳过。 |
| `gate-run-fail` | harness gate run FAIL | 按 failed_checks 逐条修复，重新 gate run。 |

</failure_paths>

Stage transition:

- Decided by: `control_plane.stage` from Mission Slice (Work Graph).
- Typical next:
  - `interaction`：UI / 用户旅程 / 状态交互 / 原型需要独立设计；发生在产品定义之后、solution 之前
  - `solution`：需要方案路线选择 / tradeoff / 架构级产品到技术路线映射
  - `technical_analysis`：需要技术设计
  - `breakdown`：低复杂度且已具备足够产品定义和实现边界
- Enforced by: cli=harness gate advance


</workflow>
