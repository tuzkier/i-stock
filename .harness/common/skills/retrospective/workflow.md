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

<stage_capability>
  retrospective 对应 RUP 项目管理中的迭代评估和环境工作流中的流程改进。它的核心问题是：本次需求实现链路暴露了哪些可复用改进、哪些知识必须沉淀、哪些交付真实性问题必须回流处理。

| 能力 | 本阶段必须完成的判断 |
|---|---|
| 输入合格性判断 | 确认交付包、验收结果、阶段门报告、审查 / 验证发现和工作图历史是否足以支撑复盘；缺失项必须标 N/A，不得假设全阶段链路都存在。 |
| 链路偏差判断 | 对比计划路径和实际路径，识别阶段返工、等待、范围偏移、证据补交和角色调度偏差，并说明偏差原因。 |
| 失败模式判断 | 区分偶发问题、重复问题和系统性缺口，把跨阶段失败归因到规则、模板、工作流、检查器、测试、Agent prompt 或项目知识。 |
| 交付真实性回查判断 | 复盘不重新定义交付范围；但若发现交付证据、验收路径或风险披露不足以支撑 delivered 结论，必须触发重新验证或 course-correction。 |
| 知识沉淀判断 | 判断哪些产品知识、行为规格、设计决策、工程样板、运行手册或教训值得进入 project-knowledge / project-context，并保留来源和置信度。 |
| 流程改进定位判断 | 每条改进必须指向具体规则、模板、工作流、检查器、测试、Agent prompt 或 project-knowledge 路径，不能只写泛泛建议。 |
| 跟进行动判断 | 把未能当场完成的改进转成明确的 follow-up：目标、触发条件、证据、Owner 和阻断等级必须可执行。 |
| 不归责事实判断 | 复盘只分析事实链路和系统条件，不做个人归责；结论必须能被证据追溯。 |
| 下次迭代反馈判断 | 把本次经验转成下一次 intake / discovery / 产品定义 / 方案 / 执行 / 验证可复用的输入，而不是停留在本次任务总结。 |

</stage_capability>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `retro-contract-via-cli` | retrospective.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness contract init/patch | hook=harness-lint |
| `retro-not-fenced` | retrospective.md 不得内嵌 fenced YAML memory_update_contract / execution_result / role_verdicts 段 | hook=check_retrospective_markdown |
| `project-context-via-cli` | project-context.md 只能经 harness project-context add-lesson 写入，禁止直接 Edit | hook=deny_direct_project_context_edit |
| `planning-analyst-zero-write` | planning-analyst 是 data-producer-class（零写入），只输出分析结果，不写任何文件 | registry=subagents/planning-analyst[write_mode=zero] |

</invariants>

<entry>
  - delivery 已完成并形成可验收交付包，或用户 / Board 明确触发复盘
  - 若 finishing-branch 已先执行，复盘只消费其 Git / PR 事实，不把版本控制结果当作交付真实性证据
</entry>

<exit>
  - `retro-written`: retrospective.md 写入 retrospective stage worktree
  - `contract-filled`: retrospective.contract.yaml 含 Memory Update Contract 且 decisions 非空，harness contract check PASS
  - `lessons-persisted`: project-knowledge promotion candidate plan 已生成，Agent 已把必要长期知识提炼进 project-knowledge，必要教训已追加到 project-context.md（harness project-context lint 无 FAIL）
  - `harness-gap-emitted`: harness retrospective harness-gap-emit 已记录本次复盘发现的 harness gap
</exit>

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
| `retrospective-md` | `harness-runtime/harness/artifacts/${mission-id}/retrospective/retrospective.md` | markdown | Memory |
| `retrospective-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/retrospective.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |
| `project-knowledge-promotion` | `harness-runtime/harness/artifacts/${mission-id}/retrospective/knowledge-promotion-plan.md` + `project-knowledge/operations/knowledge-promotions/${mission-id}.md` | markdown | Memory |
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
 - 给 planning-analyst 的 brief 必须包含：mission-contract.md 原文或摘要、实际产生的 stage artifacts 列表（N/A 项明确标出）、interaction.md 的「沉淀候选」、interaction-spec/interaction-contract.md「一致性体检」摘要、contracts/interaction.contract.yaml 的 knowledge_promotion_candidates / prd_feedback（如存在）、quality-control / bug-fix 协议记录和 code-review findings、project-context 历史教训（仅选取相关部分）、retrospective-data 的 cross_stage_failures 和 trace_event_count 汇总。
</step>

<step id="step-2" n="2" goal="dispatch 规划分析 Agent">
 <dispatch role="planning-analyst" mode="spawn" />
 - brief（Task Envelope）：Step 1 准备的材料；Task：对本次 Mission 执行规划偏差分析，输出 (1) 规划 vs 实际偏差列表（含预估误差原因）(2) 跨阶段失败模式分析 (3) 改进建议（按优先级排序，每条指明 target_kind: workflow|hook|schema|lint_check|agent_prompt|methodology）；输出格式 structured markdown，section: planning_delta / failure_patterns / improvement_proposals；约束：只输出分析，不写任何文件（data-producer-class 零写入）。
 - 等待 planning-analyst 返回结果。
</step>

<step id="step-3" n="3" goal="综合报告，写复盘文档">
 - 使用 `harness-runtime/templates/retrospective.md` 模板，综合 planning-analyst 的规划偏差分析、code-review / verify 结果、quality-control / bug-fix 协议记录：执行摘要 / 复盘输入与链路边界 / 计划偏差 / 跨阶段失败模式 / 交付真实性回查 / 流程、模板与检查器改进 / 知识沉淀 / 跟进行动 / 外部 Memory Update Contract（合并 quality-control / bug-fix / retrospective 的 MEM-NNN 候选写入 contract decisions，applied 必须有 target_ref，proposed/延后必须有 reason）。
 - 从 mission retrospective-data、code-review、verification-report、delivery contract 提取轻量 DORA 信号：lead time、rework count、review hold count、verification failure count、rollback/follow-up count；写入 retrospective.md 和 retrospective.contract.yaml，用于趋势分析，不作为单次绩效评价。
 - retrospective.md 的「控制契约」段只保留 `Contract: contracts/retrospective.contract.yaml` 引用和 Authority 说明，禁止追加 fenced YAML contract。写入 `harness-runtime/harness/artifacts/<mission-id>/retrospective/retrospective.md`。
 - 若 `contracts/retrospective.contract.yaml` 不存在，调用 `harness contract init --mission <mission-id> --stage retrospective --template retrospective --json` 初始化；若已存在只能 patch。将 memory update decisions、planning analysis summary 和 evidence refs 写入 contract 的 control_contract。
</step>

<step id="step-4" n="4" goal="更新 project-context.md">
 - 调用 `harness knowledge promote --mission <mission-id> --write-plan --apply --json` 生成本次任务的 project-knowledge 固化候选计划，并执行确定性沉淀：已接受差量规格进入 `project-knowledge/specs/<capability>/spec.md`，同时写入 `project-knowledge/operations/knowledge-promotions/<mission-id>.md` 作为沉淀账本。注意：promote **不复制**主可操作原型——原型住在项目持有的独立原型工程目录（`prototype_project_root`，默认建议 `prototype/`），随 Mission 分支合并晋升；其 provenance 由该目录 git log 提供，本次晋升内容记录在 knowledge-promotions 账本，不在 `project-knowledge/` 下另立原型台账。
 - 由主 Agent 基于候选计划、沉淀账本和阶段产物继续做语义提炼，把稳定产品知识、行为规格、设计决策、工程样板、运行手册或教训写入 `project-knowledge/<domain>/...`。interaction 阶段通过审查的 prototype project patch、系统 surface、原型模式、界面信息架构、领域对象到界面的映射、可复用交互约束和 interaction-spec consistency decision 必须作为候选评估；主可操作原型本体不进 `project-knowledge/`（随分支合并留在独立原型工程目录），稳定 surface 细节同步到 `project-knowledge/product/ui-surfaces/`、**稳定区域树 / 布局骨架随 `harness knowledge promote` 并入项目级累积图 `product/system-use-cases/behavior-graph.yaml#regions`**、**本次确认的可复用设计 token / 基础组件 / 业务组件（绑 OBJ/SUC）/ 布局与交互约定增量并入 `project-knowledge/product/design-system/` 对应分层文件（业务组件→`business-components.md`、基础组件→`base-components.md`、token→`design-spec.md` 名注册 + `prototype/tokens.css` 真值、原则/框架→对应文件）；逐条 dedup：新→追加、一致→升 confidence、冲突→不覆盖记待人决策；只沉淀可复用、不沉淀一次性样式；每条保留 source mission / status / confidence，绝不整份覆盖**，若它们确立或改变用户可观察行为，且 `spec.enabled=true`，必须同步评估是否进入 `project-knowledge/specs/<capability>/spec.md`。不得整份复制 stage artifact；每条新增/修改知识必须保留 source mission、status、confidence。
 - Hard gate `knowledge-promotion-applied`：Mission 结束前必须存在 `project-knowledge/operations/knowledge-promotions/<mission-id>.md`，`harness knowledge promote --mission <mission-id> --apply --json` 不得返回 FAIL；若 deterministic apply 返回 manual merge WARN，必须在 retrospective.md 和 retrospective.contract.yaml 记录目标、原因、处理人和后续决策，不能静默结束 Mission。
 - 提炼完成后调用 `harness knowledge index --json` 更新 `_index.md`，再调用 `harness knowledge check --json` 校验。
 - 从复盘中提炼需要持久化的教训，调用 `harness project-context add-lesson --lesson "<具体教训>" --source <mission-id>` 写入。教训类型包括：新发现的项目约束、需要避免的已知坑、需要更新的技术选择、质量控制/缺陷修复协议中提出的记忆决策（applied / proposed / 延后）。格式 `- <YYYY-MM-DD> <具体教训> (source: <mission-id>)`。
 - 若教训或样板间对团队长期有用，同步在 retrospective.contract.yaml 的 Memory Update Contract 中记录 target=project-knowledge，target_ref 指向 `project-knowledge/<domain>/...` 或 knowledge-promotion-plan 中的候选项。
 - 条件：project-context.md 不存在
  - 使用 `harness-runtime/templates/project-context.md` 模板创建，并填入本次教训。
</step>

<step id="step-5" n="5" goal="Artifact Gate 自检">
 - 验证 retrospective.md 包含最小必要结构：执行摘要、复盘输入与链路边界、计划偏差、跨阶段失败模式、交付真实性回查、流程 / 模板 / 检查器改进、知识沉淀、跟进行动、project-context 更新确认；前部含 `Contract:` 引用且不含 fenced YAML contract / ## memory_update_contract / ## execution_result / ## role_verdicts。
 - 验证外部 contract 包含 Memory Update Contract 且 decisions 非空。
 - 调用 cli `harness contract check` `--artifact harness-runtime/harness/artifacts/${mission-id}/retrospective/retrospective.md`，evidence=required。
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
