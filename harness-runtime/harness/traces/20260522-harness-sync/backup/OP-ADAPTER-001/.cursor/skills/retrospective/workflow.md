# Retrospective 工作流

> **方法论参考**：`.harness/docs/methodology-reference.md` §13（复盘 — Blameless Postmortem；规划偏差分析）

所有 CLI 调用通过 harness-cli skill（`--json` 模式）。

<workflow stage="retrospective" version="2">

<goal>
  从规划偏差、质量缺口、协议记录和执行事实中综合形成复盘报告，产出 retrospective.md + retrospective.contract.yaml，并将教训与长期知识更新计划经 CLI 写入 project-knowledge / project-context。
</goal>

<role>
  你是复盘编排者。你收集 mission 全程数据、dispatch 规划分析 Agent、结合质量控制 / 缺陷修复协议记录，产出最终复盘文档。你消费 mission 全程数据，不重新产生 stage 产物。
</role>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `retro-contract-via-cli` | retrospective.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness contract init/patch | hook=harness-lint |
| `retro-not-fenced` | retrospective.md 不得内嵌 fenced YAML memory_update_contract / execution_result / role_verdicts 段 | hook=check_retrospective_markdown |
| `project-context-via-cli` | project-context.md 只能经 harness project-context add-lesson 写入，禁止直接 Edit | hook=deny_direct_project_context_edit |
| `planning-analyst-zero-write` | planning-analyst 是 data-producer-class（零写入），只输出分析结果，不写任何文件 | registry=subagents/planning-analyst[write_mode=zero] |

</invariants>

<entry>
  - finishing-branch 已完成（H5 顺序裁决 finishing-branch → retrospective）
  - 用户 / Board 明确触发复盘
</entry>

<exit>
  - `retro-written`: retrospective.md 写入 retrospective stage worktree
  - `contract-filled`: retrospective.contract.yaml 含 Memory Update Contract 且 decisions 非空，harness contract check PASS
  - `lessons-persisted`: project-knowledge promotion candidate plan 已生成，Agent 已把必要长期知识提炼进 project-knowledge，必要教训已追加到 project-context.md（harness project-context lint 无 FAIL）
  - `harness-gap-emitted`: harness retrospective harness-gap-emit 已记录本次复盘发现的 harness gap
</exit>

<permissions>

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Edit(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Write(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Edit(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/stages/*/contracts/retrospective.contract.yaml)` | contract 必须经 harness contract init/patch |
| deny | `Edit(harness-runtime/harness/stages/*/contracts/retrospective.contract.yaml)` | contract 必须经 harness contract patch |
| allow | `Write(harness-runtime/harness/stages/*/retrospective.md)` | retrospective 主产物 |
| allow | `Edit(harness-runtime/harness/stages/*/retrospective.md)` | retrospective 主产物 |
| allow | `Edit(harness-runtime/project-context.md)` | 教训持久化（经 add-lesson CLI 写入后的文件落点） |
| allow | `Bash(harness *)` | retrospective CLI 必需 |

</permissions>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `planning-analyst` | spawn readonly | （data-producer-class：write_mode=zero，只输出分析结果，不写文件） | `.harness/common/agents/planning-analyst.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `mission-contract.md` | true | Intent |
| `project-context.md` | conditional: brownfield | Context |
| `mission-artifacts` | true via harness mission artifacts | Memory |
| `retrospective-data` | true via harness mission retrospective-data | Feedback |
| `harness.yaml` | true via harness config snapshot | Memory |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `retrospective-md` | `harness-runtime/harness/stages/${mission-id}/retrospective.md` | markdown | Memory |
| `retrospective-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/retrospective.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |
| `project-knowledge-promotion` | `harness-runtime/harness/stages/${mission-id}/knowledge-promotion-plan.md` | markdown | Memory |
| `project-context-lessons` | `project-context.md` | markdown | Memory |

</outputs>

<steps>

<step id="step-0" n="0" goal="数据收集">
 - 调用 cli `harness mission artifacts` `--mission ${mission-id}`，evidence=required。
 - 调用 cli `harness mission retrospective-data` `--mission ${mission-id}`，evidence=required。
 - 读取 `harness-runtime/harness/missions/<mission-id>/mission-contract.md`、`project-context.md`（历史教训和项目约束摘要）。基于 `mission artifacts` 返回的 exists=true 列表确定本次实际产生过的 stage artifacts，缺失项标 N/A，不假设固定全阶段链路都存在。如存在协议 coverage 报告，读取 `harness-runtime/harness/state/protocol-coverage.md` 作为记忆决策输入。
</step>

<step id="step-1" n="1" goal="准备复盘 brief">
 - 读取并汇总以下材料（基于 Step 0 确认存在的文件）：mission-contract.md、本 Mission 实际被 Gate 接受的 stage artifacts（prd / interaction / interaction-spec / visual-interaction / solution / tech-design / execution-brief / code-review / verification-report / acceptance-result / delivery，缺失项标 N/A）、quality-control / bug-fix 协议记录和 code-review findings、retrospective-data 返回的 cross_stage_failures / trace_event_count / per-stage effectiveness_review、project-context 历史教训。
 - 给 planning-analyst 的 brief 必须包含：mission-contract.md 原文或摘要、实际产生的 stage artifacts 列表（N/A 项明确标出）、interaction.md 的「沉淀候选」、interaction-spec/consistency-report.md 摘要、contracts/interaction.contract.yaml 的 knowledge_promotion_candidates / prd_feedback（如存在）、quality-control / bug-fix 协议记录和 code-review findings、project-context 历史教训（仅选取相关部分）、retrospective-data 的 cross_stage_failures 和 trace_event_count 汇总。
</step>

<step id="step-2" n="2" goal="dispatch 规划分析 Agent">
 通过 `@planning-analyst` native delegation调用 `planning-analyst` subagent（Cursor auto-routes 到对应 agent registry 项）
 - brief（Task Envelope）：Step 1 准备的材料；Task：对本次 Mission 执行规划偏差分析，输出 (1) 规划 vs 实际偏差列表（含预估误差原因）(2) 跨阶段失败模式分析 (3) 改进建议（按优先级排序，每条指明 target_kind: workflow|hook|schema|lint_check|agent_prompt|methodology）；输出格式 structured markdown，section: planning_delta / failure_patterns / improvement_proposals；约束：只输出分析，不写任何文件（data-producer-class 零写入）。
 - 等待 planning-analyst 返回结果。
</step>

<step id="step-3" n="3" goal="综合报告，写复盘文档">
 - 使用 `harness-runtime/templates/retrospective.md` 模板，综合 planning-analyst 的规划偏差分析、code-review / verify 结果、quality-control / bug-fix 协议记录：执行摘要 / 做得好的 / 发现的问题（合并去重质量缺口、缺陷记录和规划偏差）/ 根因分析 / 改进行动（按优先级排序，每条对应一个 learning_proposal_contract 记录，target_kind 必须是枚举值之一）/ 外部 Memory Update Contract（合并 quality-control / bug-fix / retrospective 的 MEM-NNN 候选写入 contract decisions，applied 必须有 target_ref，proposed/延后必须有 reason）。
 - 从 mission retrospective-data、code-review、verification-report、delivery contract 提取轻量 DORA 信号：lead time、rework count、review hold count、verification failure count、rollback/follow-up count；写入 retrospective.md 和 retrospective.contract.yaml，用于趋势分析，不作为单次绩效评价。
 - retrospective.md 的「控制契约」段只保留 `Contract: contracts/retrospective.contract.yaml` 引用和 Authority 说明，禁止追加 fenced YAML contract。写入 `harness-runtime/harness/stages/<mission-id>/retrospective.md`。
 - 若 `contracts/retrospective.contract.yaml` 不存在，调用 `harness contract init --mission <mission-id> --stage retrospective --template retrospective --json` 初始化；若已存在只能 patch。将 memory update decisions、planning analysis summary 和 evidence refs 写入 contract 的 control_contract。
</step>

<step id="step-4" n="4" goal="更新 project-context.md">
 - 调用 `harness knowledge promote --mission <mission-id> --write-plan --json` 生成本次任务的 project-knowledge 固化候选计划。该 CLI 只做确定性候选发现，不做语义提炼，也不自动写入长期知识正文。
 - 由主 Agent 基于候选计划和阶段产物进行语义提炼，把稳定产品知识、行为规格、设计决策、工程样板、运行手册或教训写入 `project-knowledge/<domain>/...`。interaction 阶段通过审查的 prototype project patch、系统 surface、原型模式、界面信息架构、领域对象到界面的映射、可复用交互约束和 interaction-spec consistency decision 必须作为候选评估；稳定原型项目结构优先沉淀到 `project-knowledge/product/prototype/`，稳定 surface 细节同步到 `project-knowledge/product/ui-surfaces/`，若它们确立或改变用户可观察行为，且 `spec.enabled=true`，必须同步评估是否进入 `project-knowledge/specs/<capability>/spec.md`。不得整份复制 stage artifact；每条新增/修改知识必须保留 source mission、status、confidence。
 - 提炼完成后调用 `harness knowledge index --json` 更新 `_index.md`，再调用 `harness knowledge check --json` 校验。
 - 从复盘中提炼需要持久化的教训，调用 `harness project-context add-lesson --lesson "<具体教训>" --source <mission-id>` 写入。教训类型包括：新发现的项目约束、需要避免的已知坑、需要更新的技术选择、质量控制/缺陷修复协议中提出的记忆决策（applied / proposed / 延后）。格式 `- <YYYY-MM-DD> <具体教训> (source: <mission-id>)`。
 - 若教训或样板间对团队长期有用，同步在 retrospective.contract.yaml 的 Memory Update Contract 中记录 target=project-knowledge，target_ref 指向 `project-knowledge/<domain>/...` 或 knowledge-promotion-plan 中的候选项。
 - 条件：project-context.md 不存在
  - 使用 `harness-runtime/templates/project-context.md` 模板创建，并填入本次教训。
</step>

<step id="step-5" n="5" goal="Artifact Gate 自检">
 - 验证 retrospective.md 包含最小必要结构：执行摘要、做得好的、发现的问题、根因分析、改进行动、project-context 更新确认；前部含 `Contract:` 引用且不含 fenced YAML contract / ## memory_update_contract / ## execution_result / ## role_verdicts。
 - 验证外部 contract 包含 Memory Update Contract 且 decisions 非空。
 - 调用 cli `harness contract check` `--artifact harness-runtime/harness/stages/${mission-id}/retrospective.md`，evidence=required。
 - 调用 cli `harness mission status` `--mission ${mission-id}`，evidence=required。
 - 验证 `harness knowledge check --json` 无 FAIL；验证 project-context.md 已追加本次教训（`harness project-context lint` 无 FAIL）。
 - 调用 cli `harness retrospective harness-gap-emit` `--mission ${mission-id}`，evidence=required。
 - 条件：结构不完整
  - 自行补充缺失部分，不要跳过。
</step>

<step id="step-6" n="6" goal="条件：分析 Agent 行为漂移与 eval 有效性">
 - 条件：agent_engineering.enabled=true
  - 调用 cli `harness agent-eval drift` `--mission ${mission-id}`，evidence=required。
  - 参考 `docs/methodologies/agent-capability-engineering.md` §8（Agent 运维 — 漂移检测）。
  - 条件：存在 agent-eval-report.md
   - 从 agent-eval-report.md 提取各 Agent 组件行为分布指标，与历史 eval 基线对比分析行为漂移；retrospective.md 追加「Agent 能力复盘」段（各 Agent 组件 eval 通过率是否满足阈值 / 哪些场景类别表现最弱 / 是否行为退化 / solution `## Agent 架构` 或 tech-design `## Agent 实现` 是否需调整 / Eval 输入集是否有代表性）；将 Agent 能力相关教训追加到 project-context.md。
  - 条件：不存在 agent-eval-report.md
   - 在复盘中记录：agent-eval 未执行，建议在下次任务中补充。
</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `empty-artifact-list` | harness mission artifacts 返回空 artifact 列表 | 记录 findings 并继续；空列表表示本次 Mission 未产生任何已接受产物，复盘仍可针对过程记录（trace 和 approvals）展开。 |
| `planning-analyst-blocked` | planning-analyst dispatch BLOCKED（无法调用子 Agent） | Stage 停在 Gate，报告 BLOCKED；不得由主 Agent 自审自批替代；record_planning_analyst_dispatch hook 会记录 BLOCKED 事件到 trace JSONL。 |
| `markdown-hook-block` | check_retrospective_markdown hook 阻断写入（forbidden section 或 fenced YAML） | 删除违规内容，仅保留 `Contract: contracts/retrospective.contract.yaml` 引用，重新写入；不绕过 hook。 |
| `project-context-edit-block` | deny_direct_project_context_edit hook 阻断直接 Edit | 必须通过 `harness project-context add-lesson` CLI 写入，不得直接 Edit project-context.md。 |
| `contract-edit-block` | deny_direct_contract_edit hook 阻断 | 必须用 `harness contract patch` CLI。 |
| `template-mutation-block` | deny_direct_template_mutation hook 阻断 | 不得修改 template source；报告 BLOCKED。 |
| `contract-check-fail` | harness contract check 返回 FAIL | 修复 retrospective.md 结构后再调用 gate。 |

</failure_paths>

Stage transition:

- Decided by: `control_plane.stage` from Mission Slice (Work Graph).
- Typical next:
  - `(mission-close)`：retrospective 完成，mission 全程收尾
- Enforced by: cli=harness gate advance


<evidence_summary>
 本 workflow 执行完成后，以下 evidence 必须可被验证：
 harness mission artifacts 返回 count >= 0（即使空也表示已执行 Step 0）；
 harness mission retrospective-data 返回 PASS；
 planning-analyst dispatch 记录在 trace JSONL（PostToolUse hook）；
 retrospective.md 含最小必要结构；
 retrospective.contract.yaml decisions 非空；
 harness project-context lint 无 FAIL（教训已追加）；
 harness contract check --artifact retrospective.md 返回 PASS；
 harness mission status 记录 retrospective 结果。
</evidence_summary>

</workflow>
