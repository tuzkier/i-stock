# 任务接入工作流

将用户意图转化为已绑定 Work Graph 的 Mission Contract。reviewer + gate 双 PASS 后才向用户确认。

下文出现的所有 `harness ...` 命令一律通过 harness-cli skill 调用（默认带 `--json`、消费 typed payload、不直接拼 Bash 底层脚本，详见 `.harness/common/skills/harness-cli/SKILL.md`）。

<workflow stage="intake" version="2">

<permissions>

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Edit(harness-runtime/harness/mission-status.yaml)` |  |
| deny | `Edit(harness-runtime/harness/work-graph/**)` |  |
| deny | `Edit(harness-runtime/harness/work-graph/mission-slices/**)` |  |
| deny | `Edit(harness-runtime/harness/work-graph/nodes/**)` |  |
| deny | `Write(harness-runtime/harness/mission-status.yaml)` |  |
| deny | `Write(harness-runtime/harness/work-graph/**)` |  |
| deny | `Bash(git push --force *)` |  |
| deny | `Bash(git push --force-with-lease *)` |  |
| deny | `Bash(git reset --hard *)` |  |
| deny | `Bash(rm -rf /*)` |  |
| ask | `Bash(git checkout -b *)` |  |
| ask | `Bash(git push *)` |  |
| ask | `Bash(git rebase *)` |  |
| allow | `Bash(harness *)` |  |
| allow | `Bash(python3 .claude/hooks/**)` |  |

</permissions>

### Phase 0 — Intake Mode Gate & Control Preflight

<step n="0" phase="0" goal="判断是否进入正式 intake；正式 intake 时初始化控制面">

先做语义角色判断，不得把最近一句用户消息直接当任务目标。把用户当前消息和必要上下文拆成：

- `actual_task_goal`：用户真正想达成的外部结果；完成后系统 / 产品 / 代码 / 行为应处于什么状态。
- `agent_instruction`：用户要求 Agent 怎么工作，例如“仔细读”“看下”“分析”“开始推进”。
- `process_constraint`：用户要求 Harness 怎么治理，例如完整流程、受控推进、不要用“最小实现”。
- `source_material`：用户提供的文档、链接、截图或讨论材料。
- `discussion_output`：PRD、方案、任务契约、调研文档等讨论 / 阶段中间产物。
- `correction`：用户指出理解错、目标错、范围错。
- `execution_confirmation`：“开始吧”“继续推进”“按这个来”等执行确认。

- Hard gate `actual-task-goal-required`：
没有明确 `actual_task_goal` 时，即使用户说“开始推进”“继续”“按这个来”，也不得进入 formal_intake；这些话只能确认已识别目标，不能生成目标。只问一个短问题澄清真实外部结果，例如“你要推进的是哪个可交付结果？”

- Hard gate `meta-instruction-not-objective`：
`agent_instruction`、`process_constraint`、`source_material`、`discussion_output`、`correction` 不得写入 Mission Objective / Work Graph node title / success_definition.deliverables。它们只能进入输入材料、约束、非目标、confirmation source 或纠偏记录。

根据语义角色和当前对话判断 `intake_mode`：

- `discussion`：缺少 `actual_task_goal`，或只有想法、要求、问题、约束、阅读要求、资料提供、纠偏意见、流程要求。
- `formal_intake`：已存在明确 `actual_task_goal`，且用户自然表达执行确认，例如“开始吧”“就这么做”“帮我实现”“按这个来”“继续推进”。

- 条件：intake_mode=discussion
不得调用以下命令或写入以下控制面：
- `harness control status`
- `harness control candidates`
- `harness config snapshot`
- `harness context check`
- `harness mission status --open`
- `harness mission new-id`
- `harness trace log-init`
- `git-workflow prepare`
- `harness mission init`
- `harness graph node create`
- `harness mission create-slice`
- `harness board select --write-slice`
- 写 `mission-contract.md` / `intent-framing.yaml` / Gate report

只做内部接入前判断。用户可见输出必须是普通对话，不得像调研访谈、执行前对齐模板，也不得暴露 Harness 内部控制面或契约格式：
- 不说 `pre-intake frame`、`Mission`、`Work Graph`、`Mission Slice`、`contract`、`AC-01`、`US-01`、`GWT`、“正式接入”、“接入任务”等内部术语
- 不说“我先不建任务”“你可以确认接入任务”“等你确认后我再纳入 Harness”这类流程提示，除非用户主动问 Harness 状态
- 不用表格化模板、编号化验收项或“候选 A/B/C”强行包装普通讨论
- 正常回应用户的想法或要求，不要固定套用“你是想用 X 解决 Y / 我会先按 A 做”句式
- 如果想更准确地完成，只用一句自然语言提示用户可以说明期待的验收标准包含哪些
- 只有缺失信息会导致执行方向明显不同，才问 1 个简短问题；不要做用户画像、场景调研、边界设计访谈或一次性问卷
- 结构化字段只在用户自然表达执行意图后写入 `intent-framing.yaml` 和 Mission Contract，不提前暴露给用户

用户未提供 `actual_task_goal` 且未等价自然表达执行确认时，workflow 在此返回，不进入 Phase 1。

- 条件：intake_mode=formal_intake
构造 typed `raw_intake_brief`，必须分栏记录：
- `actual_task_goal`
- `source_materials`
- `agent_instructions`
- `process_constraints`
- `discussion_outputs`
- `corrections`
- `execution_confirmation`
- `explicit_non_goals`
- `open_intent_gap`

只有 `actual_task_goal` 能进入 objective、Work Graph node title、success_definition.deliverables 和 acceptance criteria。

调 `harness control status --json` + `harness control candidates --intent continue --json`。有可恢复 active mission 候选时返回用户决定，不得自作主张。

调 `harness config snapshot --json`，取 `project_name` / `default_mode` / `brownfield` / `execution_governance` / `escalation` / `work_graph`。

调 `harness context check --json`。FAIL 时按 project-context 规则处理或记 `inputs_missing.project_context=true`。

调 `harness mission status --open --json` 列未完成 mission。

control 查询不可用时按旧 runtime 文件读取，记录 `fallback_used` / `fallback_reason` / `legacy_source` / `follow_up`。

</step>

### Phase 1 — Intent & Work Graph Binding

<step n="1" phase="1" goal="确立 mission identity 并完成 Work Graph 绑定">

读 typed `raw_intake_brief`，只从 `actual_task_goal` 识别核心意图，判断绿地 / 棕地。此时不得写 mission-contract.md 也不得 dispatch framing expert。

- Hard gate `execution-intent-before-runtime-write`：
没有用户自然表达执行确认时，Phase 1 BLOCKED；不得创建 mission-id、trace、mission branch、Work Graph node、Mission Slice 或任何任务契约产物。

- Hard gate `actual-task-goal-before-runtime-write`：
`raw_intake_brief.actual_task_goal` 为空，或只能从阅读动作、流程要求、讨论产物、纠偏反馈推断目标时，Phase 1 BLOCKED；回 Phase 0 discussion。

- 条件：用户意图模糊或范围不清
调 AskUserQuestion 三候选问题：
- Q1：期望完成后看到什么具体结果？
- Q2：最终交付物和交付标准是什么？
- Q3：哪些东西明确不需要做？有什么已知约束或依赖？

回答追加到 typed `raw_intake_brief`。若回答后仍缺少 `actual_task_goal`、交付标准、范围边界或验证口径，回 Phase 0 discussion；runtime 不支持结构化 AskUserQuestion 时降级自然语言提问。

调 `harness mission new-id --slug <slug> --json` 取 `mission_id`（禁止 agent 自拼）。

调 `harness trace log-init --mission <mission_id> --stage intake --json`。
调 `harness trace step-enter --mission <mission_id> --step phase-1 --json`。

调 `git-workflow prepare` 创建 `mission/<mission_id>` 分支并进入。

- Hard gate `git-prepare-before-runtime-write`：
git-workflow prepare 之前不得写 mission-status.yaml / Work Graph node / Mission Slice / Gate report。

调 `harness mission init --json`（已存在则 PASS-noop，不传 `--replace`）。
调 `harness mission stage start --mission <mission_id> --stage intake --json`。
调 `harness graph rebuild --json` + `harness graph check --json`。

- Hard gate `work-graph-ready-before-framing`：
`work_graph.lanes` 缺失或 `harness graph check` FAIL：Phase 1 BLOCKED，不得进入 Phase 2。

调 `harness board select --mission <mission_id> --query <raw_intake_brief> --no-write --json` 查重复 / 相关 / 冲突 node。

- 条件：已有 node 与本任务等价
记录为 seed node。
- 条件：是新需求
调 `harness graph node create --node-id <id> --kind <kind> --title <title> --lane <lane> --status <status> --mission-id <mission_id> --json`。kind 来自 `harness config snapshot` 的 `work_graph.node_kinds`：需求 → `REQ-*` / `EPIC-*`；缺陷 → `BUG-*`；调研 → `RESEARCH-*`。创建后再调 `harness graph rebuild` + `harness graph check`。

调 board-router 为 mission-id 创建 / 恢复 Mission Slice：`harness mission create-slice` 或 `harness board select --write-slice`。

- Hard gate `mission-slice-required`：
Mission Slice 缺 `work_graph.primary_nodes` 或无法创建 / 关联 seed node：Phase 1 BLOCKED。

调 `harness trace step-exit --mission <mission_id> --step phase-1 --status pass --json`。

</step>

### Phase 2 — Framing

<step n="2" phase="2" goal="dispatch framing expert 产出 intent framing">

调 `harness trace step-enter --mission <mission_id> --step phase-2 --json`。

通过 `@mission-framing-expert` native delegation调用 `mission-framing-expert` subagent（Cursor auto-routes 到对应 agent registry 项）

Task Envelope：typed `raw_intake_brief` 摘要（必须包含 `actual_task_goal` 与各类非目标语料）、project-context 路径、`harness config snapshot` 摘要、seed node YAML 路径、Mission Slice 路径、输出路径 `harness-runtime/harness/missions/<mission_id>/intent-framing.yaml`、write_scope、完成条件。不粘贴 config snapshot 全文 / Mission Slice JSON / workflow 正文。

intent-framing.yaml 结构遵循 `harness-runtime/templates/contracts/intent-framing.example.yaml`，AC `given` / `when` / `then` 平铺，不嵌套 `gwt:`。

intent-framing.yaml 必须包含 `intent_role_analysis`：
- `actual_task_goal`：真实任务目标，Objective / deliverables / AC 只能从这里派生
- `source_materials`：输入材料
- `agent_instructions`：工作方式要求
- `process_constraints`：Harness 流程 / 治理约束
- `discussion_outputs`：讨论或阶段中间产物
- `corrections`：用户纠偏
- `execution_confirmation`：执行确认来源
- `excluded_from_objective`：明确列出未进入目标的语料及原因

如果 `actual_task_goal` 为空或不清楚，framing expert 必须返回 `NEEDS_DECISION`，不得生成可 PASS 的 intent framing。

intent-framing.yaml 必须包含 `intake_decision` 和 `success_definition`：
- `intake_decision.confirmed=true`
- `intake_decision.confirmation_source` 记录用户自然表达执行意图的原话或等价摘要
- `success_definition.desired_effect` 描述完成后要达到的效果
- `success_definition.deliverables[]` 描述最终交付物和格式
- `success_definition.validation_evidence[]` 描述后续 verify / delivery 用来证明达标的证据类型
- `success_definition.non_goals[]` 记录明确不做的内容；若没有，写空数组并在 scope_out 中解释

intent-framing.yaml 的每条 `user_stories[]` 必须包含产品故事握手字段：
- `role` / `goal` / `value`
- `story_context.user`：用户或用户分层，不只写系统角色名
- `story_context.problem`：该用户遇到的问题、痛点或当前失败状态
- `story_context.scenario`：触发场景 / 使用上下文 / 关键动作，不得留给 PRD 自行推断
- `story_context.value`：为什么值得做，允许与故事 `value` 一致但必须明确
- `story_context.success_metrics[]`：至少一条可观察成功信号，包含 `signal` 与 `target`

runtime 无 native subagent registry 时降级 `main_agent_fallback` 并标 `block_auto_pass`，不得让主 Agent 自演 framing 同时 verdict PASS。

- Hard gate `framing-expert-not-main-agent`：
framing expert 不可调度时停在 Gate 报告角色不可用，主流程不得自演。

调 `harness trace step-exit --mission <mission_id> --step phase-2 --status pass --json`。

</step>

### Phase 3 — Governance Decision

<step n="3" phase="3" goal="主流程完成 governance 决策">

调 `harness trace step-enter --mission <mission_id> --step phase-3 --json`。

复核 framing expert 的治理风险建议。治理级别判断的是“AI 是否被授权自主推进”，不得只用文件数、用户角色数或模块数代替风险判断。按本文末治理风险矩阵执行：

1. 先检查 hard triggers；命中任一项即 `high` / `受控推进`。
2. 再评估核心风险维度；任一核心维度为 high 即 `high` / `受控推进`。
3. 无 high 但存在 medium 核心风险，或只有规模信号较大但核心风险可控，则 `medium` / `专家确认`。
4. 全部核心风险 low、范围局部、可逆且自动验证充分，才可 `low` / `快速执行`。

文件数、角色数、模块数只写入 `scale_signals`，不得把“文件少”作为降低安全 / 数据 / 外部依赖 / Agent 行动权风险的理由。最终治理理由写回 intent-framing.yaml 的 `governance_assessment`。

设 `autonomy_level`：

| 治理风险 | autonomy_level | 含义 |
|------|--------|------|
| low | 快速执行 | 允许跳过 `skippable_stages` 内的阶段 |
| medium | 专家确认 | 专家 reviewer + Stage Gate PASS 通常即可继续 |
| high | 受控推进 | 默认不跳过，按配置决定人工确认点 |

canonical 中文值，A1 / A2 / A3 等 legacy alias 由 `harness contract fill` CLI 端 reject。

从 `harness.yaml` 的 `execution_governance.levels.<level>` 取 `skippable_stages` / `reviewer_pass_sufficient` / `human_checkpoints`。

- Hard gate `autonomy-level-must-exist`：
找不到对应级别：Phase 3 BLOCKED，不得回退到旧 `checkpoints`。

设 `required_checkpoints`：默认 = 治理级别的 `human_checkpoints`；可因风险 / 用户要求 / 范围变化显式增减，理由记 intent-framing.yaml。若 AI 建议从 `受控推进` 降级，或从默认 checkpoint 中移除阶段，必须在 Phase 6 明确展示给用户确认；用户同意后通过 approval 记录为 `risk_acceptance` 或 `tradeoff`。

设 escalation_triggers：从 `harness config snapshot` 的 escalation 摘要派生。

- 条件：agent_engineering.enabled=true 且 Agent 行动权 / Agent 复杂度 >= medium
intent framing 标记涉及 Agent 组件。最终 Mission Contract 的 `## Agent Engineering` 段必须声明后续 design 阶段对 `agent-capability-designer` 与 `agent-capability-reviewer` 的 dispatch 计划，并在 solution.md `## Agent 架构` 完成工作权决策、在 tech-design.md `## Agent 实现` 完成承载物实现规格。

decision（governance_risk / autonomy_level / governance_assessment / required_checkpoints / escalation_triggers）写回 intent-framing.yaml。

调 `harness trace step-exit --mission <mission_id> --step phase-3 --status pass --json`。

</step>

### Phase 4 — Contract Construction

<step n="4" phase="4" goal="生成最终 Mission Contract">

调 `harness trace step-enter --mission <mission_id> --step phase-4 --json`。

调 `git-workflow start-stage(intake)` 创建 `stage/<mission_id>-intake` 和 intake stage worktree。

- Hard gate `stage-worktree-required`：
mission-contract.md 必须写入 intake stage worktree（除 `git.strategy == downgraded`）。
- Hard gate `mission-slice-still-bound`：
Mission Slice 缺失 / `primary_nodes` 空 / `control_plane.stage` 空 / seed node 不存在：Phase 4 BLOCKED。

用 `harness-runtime/templates/mission-contract.md` 模板，合并 intent framing + Mission Slice，写入 `harness-runtime/harness/missions/<mission_id>/mission-contract.md`，必须包含：

- 外部 contract 引用：`Contract: contracts/mission-contract.contract.yaml`，禁止追加 fenced YAML / `intent_contract` / `execution_result` / `role_verdicts` 段
- TL;DR、Objective、用户故事（`US-*` 稳定 ID + 角色 / 目标 / 价值 + 产品故事上下文：用户 / 问题 / 场景 / 成功指标 + AC 追溯，不用 GWT 代替）
- 范围内 / 范围外、验收标准（GWT 格式）
- 执行治理级别（canonical 中文）、治理风险依据（hard triggers / dimensions / scale signals / decision rule）、可跳过阶段、专家确认足够阶段、Required checkpoints
- Work Graph：`primary_nodes` / `related_nodes` / `operation` / `from_lane` / `to_lane`
- control_plane：`lane` / `stage`；execution snapshot 在 `lane_action`
- Role policy override（仅 mission 调整时记录 + 理由）
- Escalation / Constraints / 交付预期

调 `harness contract fill --mission <mission_id> --stage intake --artifact harness-runtime/harness/missions/<mission_id>/contracts/mission-contract.contract.yaml --intent-framing harness-runtime/harness/missions/<mission_id>/intent-framing.yaml --template mission-contract --json`。自动同步 `autonomy_level` 到 mission-status entry。

`execution_result` / `role_verdicts` 用 `harness contract add-execution-result` / `harness contract add-verdict`，不塞进 intent-framing.yaml。

fill 未覆盖的实验字段或 mission slice 绑定才用 `harness contract patch`，写明被修改字段；不得用 patch 重做整段业务字段。

调 `harness trace step-exit --mission <mission_id> --step phase-4 --status pass --json`。

</step>

### Phase 5 — Review & Gate

<step n="5" phase="5" goal="reviewer 循环 + gate 自检">

调 `harness trace step-enter --mission <mission_id> --step phase-5 --json`。

- 循环：id=reviewer-loop；max_rounds=3；退出条件：reviewer 返回 PASS / 无阻断

调 `harness trace step-enter --mission <mission_id> --step phase-5-review --rounds <n> --json`。

通过 `@mission-contract-effectiveness-reviewer` native delegation调用 `mission-contract-effectiveness-reviewer` subagent（Cursor auto-routes 到对应 agent registry 项）

Task Envelope：mission-contract.md 路径、mission-contract.contract.yaml 路径、Mission Slice 路径、seed node YAML 路径、typed raw intake brief 摘要、Phase 0 语义角色判断、Phase 3 治理风险结论、project-context 范围 / 约束摘要。不粘贴 Mission Contract 全文或 contract YAML 全文。

要求 role_verdict 覆盖：执行意图来源是否存在、`task_goal_fidelity`（objective / deliverables / AC / Work Graph title 是否只来自真实任务目标）、downstream guesswork test（下游是否还需要自行发明用户 / 场景 / scope / 验证口径）、invented scope detection（是否把未授权扩张写入 scope in）、success_definition 是否足以指导验收、交付标准是否清楚、用户故事是否包含用户 / 问题 / 场景 / 价值 / 成功指标并追溯 AC、scope in/out 防蔓延、AC 是否可观察 / 可复现 / 可形成 expected vs actual / 可被 evidence 引用、验证证据是否能支撑最终验收、`autonomy_level` / Checkpoint 与治理风险匹配、Work Graph 绑定完整性、blocking_gaps。

- 分支：审查结论
- 情况：HOLD / BLOCKED / 有阻断
修复 mission-contract.md 与 contract.yaml。调 `harness trace step-exit --mission <mission_id> --step phase-5-review --rounds <n> --status fail --json`，回 loop 头重审全文。

- Hard gate `no-skip-recheck-after-fix`：
reviewer 重审 PASS 之前不得退出循环。
- 情况：PASS / 无阻断
调 `harness trace step-exit --mission <mission_id> --step phase-5-review --rounds <n> --status pass --json`，退出循环进入 gate 自检。


- 条件：达 max_rounds 仍有阻断
调 AskUserQuestion，3 候选：

- **A：调整范围 / AC** → 按用户指导修改 mission-contract.md，重置 round 后回 loop 头
- **B：接受降级** → 调 `harness approval append --mission <mission_id> --type tradeoff --stage intake --status approved --comment "<用户原话>" --json`；contract.yaml 的 `role_verdicts` 保留未解决 findings 并标 `accepted_by_user=true`
- **C：升级 Decision Gate** → 调 `harness approval require --mission <mission_id> --type tradeoff --stage intake --json`，工作流暂停

审查摘要附加到 mission-contract.md 末尾；structured `role_verdicts` 通过 `harness contract add-verdict` 写入 contract.yaml。

调 `harness contract check-recheck-pending --artifact harness-runtime/harness/missions/<mission_id>/contracts/mission-contract.contract.yaml --json`。FAIL 回 reviewer loop 头。

调 `harness gate run --stage intake --mission <mission_id> --mission-slice <slice-path> --artifact harness-runtime/harness/missions/<mission_id>/mission-contract.md --ai-interpretation "intake artifact gate self-check after reviewer PASS" --json`。

- Hard gate `gate-before-user-confirm`：
Gate FAIL 时不得进入 Phase 6。按返回的 `failed_checks` 修复 → 回 Phase 4 → 回 Phase 5 reviewer 循环 → 再跑 gate run。

调 `harness trace step-exit --mission <mission_id> --step phase-5 --status pass --json`。

</step>

### Phase 6 — User Acknowledge & Stage Exit

<step n="6" phase="6" goal="向用户确认并落 stage exit">

调 `harness trace step-enter --mission <mission_id> --step phase-6 --json`。

调 `harness contract summary --mission <mission_id> --format user --json`，用返回的 `user_text` 作为摘要展示给用户（不自由组织文字）。

治理级别是授权边界，Phase 6 必须让用户明确确认：建议治理级别、hard triggers、核心风险维度、required checkpoints。若用户选择降低治理级别、移除 checkpoint 或接受未解决风险，必须调用 `harness approval append --type risk_acceptance|tradeoff --stage intake --status approved --comment "<用户原话>" --json` 后再 stage complete。

调 AskUserQuestion，4 候选：

- **A：确认开始** → 任务契约阶段完成，自治循环接管后续调度
- **B：调整范围 / scope** → 修改 mission-contract.md / intent-framing.yaml，回 Phase 5
- **C：调整 AC** → 同 B
- **D：调整 autonomy / checkpoints** → 同 B

- 条件：仅文字微调（不触及 ID 或结构）
重新调 `harness contract summary --format user` 展示并再问，无需回 Phase 5。

调 `harness mission stage complete --mission <mission_id> --stage intake --json`。
调 `harness trace step-exit --mission <mission_id> --step phase-6 --status pass --json`。
调 `harness trace step-exit --mission <mission_id> --step stage-exit --status pass --json`。

</step>

</workflow>

---

## Failure Paths

任何 phase 的 HARD-GATE BLOCKED 或 gate FAIL 都必须落显式 `harness trace step-exit`。

| 失败类型 | 触发 phase | 恢复路径 |
|---------|-----------|---------|
| git clean worktree 前置失败 | Phase 1 | 解决 worktree 冲突 → 重跑 `git-workflow prepare` → 回 Phase 1 |
| Work Graph runtime 未初始化或 `harness graph check` FAIL | Phase 1 | 修 work-graph 配置 → 重跑 `harness graph rebuild` + `harness graph check` → 回 Phase 1 |
| Mission Slice 缺 `primary_nodes` | Phase 1 | 重新走 `harness board select` 或 `harness mission create-slice` → 回 Phase 1 |
| framing expert 不可调度 | Phase 2 | 停在 Gate 报告角色不可用；按 `harness control candidates` 决定切 runtime 或升级 Decision Gate |
| autonomy_level 收到 legacy alias | Phase 3 / 4 | `harness contract fill` 返回 `LEGACY_LEVEL_REJECTED` 时按 `suggested_value` 改 intent-framing.yaml → 重跑 fill |
| reviewer max_rounds 用尽 | Phase 5 | AskUserQuestion 三选项（调整 / 降级 / Decision Gate） |
| `contract check-recheck-pending` FAIL | Phase 5 | 回 reviewer loop 头重新调 reviewer |
| `gate run --stage intake` FAIL | Phase 5 末尾 | 按 `failed_checks` 修复 → 回 Phase 4 → 回 Phase 5 reviewer 循环 → 再跑 gate run；超过 2 次仍 FAIL 进 Decision Gate |
| 用户 Phase 6 选 B / C / D | Phase 6 | 回 Phase 5 reviewer 循环 + gate 自检 |
| 用户拒绝确认且无具体调整方向 | Phase 6 | 调 `harness approval require --type checkpoint` 标记 Decision Gate，工作流暂停 |

---

## Phase 3 治理风险矩阵

### Hard triggers（命中任一项即 high / 受控推进）

- 权限、认证、授权边界、安全、隐私、合规、支付、计费、额度或滥用防护。
- 数据删除、数据迁移、数据一致性、不可逆写入、生产数据或跨租户 / 工作区边界。
- 新外部 API / 服务、真实账号或密钥、非白名单工具、外部依赖不可控。
- 需求边界不清，需要产品 / 业务 / 安全取舍，或存在多个合理路线且选错代价高。
- Agent 新能力设计、工具权 / 写入权 / 外部调用权 / 行动权扩大，或 Agent 边界责任不清。
- 自动验证不足以支撑验收，需要人工判断或用户接受风险。

### 核心风险维度

| 维度 | low | medium | high |
|------|-----|--------|------|
| 决策权 | 实现路径明确，无业务取舍 | 有技术取舍但 reviewer 可判断 | 需要产品 / 业务 / 安全 / 风险接受决策 |
| 可逆性 | 易回滚，无持久副作用 | 回滚有成本但可控 | 难回滚、污染数据或影响用户状态 |
| 影响面 | 局部内部逻辑 | 跨模块或用户可见 | 核心链路、全局行为或多租户边界 |
| 验证可靠性 | 自动测试 / 命令证据可充分覆盖 | 需要组合证据或人工抽查 | 自动证据不足，必须人工验收或接受风险 |
| 数据 / 权限风险 | 不涉及敏感数据、权限或持久化 | 普通数据读写或非敏感权限调整 | 权限、认证、隐私、迁移、删除、一致性 |
| 外部依赖 | 无外部依赖变化 | 已有依赖的新用法 | 新外部 API / 服务、真实账号、密钥或非白名单工具 |
| Agent 行动权 | 无 Agent 行为 / 权限变化 | 调整已有 Agent 行为但边界清楚 | 新 Agent 能力、工具权、写入权、外部调用权或责任边界变化 |
| 不确定性 | AC 清晰且可直接测试 | 需要 PRD / 方案细化 | 需要调研才能确定需求或方案 |

### 规模信号（辅助，不可单独降低风险）

| 信号 | low | medium | high |
|------|-----|--------|------|
| 变更范围 | ≤ 3 文件 | 4-10 文件 | > 10 文件或新模块 |
| 用户角色 | 单一角色 | 2 个角色 | 3+ 角色 |
| 模块跨度 | 单模块 | 2-3 个模块 | 跨子系统 / 跨应用 |

判定规则：hard trigger 或任一核心风险 high → `受控推进`；无 high 但任一核心风险 medium，或规模信号 medium/high 但核心风险可控 → `专家确认`；全部核心风险 low 且规模 low → `快速执行`。
