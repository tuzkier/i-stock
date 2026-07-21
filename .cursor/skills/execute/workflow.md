# 执行工作流

> **行为约束（铁律、禁用词、反合理化、执行模式选择）见 `SKILL.md`，不在此重复。**
> **方法论参考**：`.harness/docs/methodology-reference.md` §7（TDD — Kent Beck；BDD — Dan North；ATDD；Trunk-Based Development）§13（Refactoring Catalog — Fowler；Code Smells）
> **内部计划生成器**：`execute/dispatch-plan.md` — 每个 Atomic Task 执行或分派前生成 dispatch plan。

<workflow stage="execute" version="2">

<goal>
  按 SDD 模式逐个 Atomic Task 实现 execution-brief 的任务项：生成 dispatch plan，派发工程岗位执行 Agent，跑 reviewer 审查循环，产出 execution-result.md + execution-result.contract.yaml。每个 Atomic Task 必须保留其关联的 `SUC-xx-OP-xx` 系统操作追溯，执行阶段不得新增、删除或改写未授权系统操作。
</goal>

<role>
  你是执行编排者。当前执行单位始终是当前 Parent task 内的 Atomic Task，不是 Parent task 本身。你为每个 Atomic Task 生成 dispatch plan、判断依赖与 write scope、规划可并行批次、派发执行 / 审查子 Agent、按状态码仲裁、写入 evidence。
</role>

<stage_capability>

执行阶段对应 RUP 构建阶段（Construction）中的实现工作流、测试工作流和变更集控制。它的核心能力不是“把代码写出来”，而是回答“授权的原子任务是否被准确实现，并留下能证明实现成立的证据”。

| 能力 | 本阶段必须判断什么 | 失败时 |
|---|---|---|
| 输入合格性判断 | execution-brief、Parent task 内嵌 atomic_task_queue、关联 `SUC-xx-OP-xx`、authorized_paths、prohibited_paths、stop_if、required_evidence 是否足以开始执行 | BLOCKED，回 breakdown / Stage Gate |
| 执行授权判定 | 当前执行单元是否是单个 Atomic Task，且系统操作、变更范围、测试义务、停止条件都来自已授权任务边界 | 停止实现，不得把 Parent task 当直接执行单位，不得补造系统操作 |
| 原子任务实现判断 | 每个 Atomic Task 是否被转化为代码 / 测试 / 配置 / 文档变更，且只完成该任务声明的 `SUC-xx-OP-xx` 或明确不涉及系统操作的验证行为 | 退回对应执行 Agent 修正 |
| 测试驱动证据判断 | baseline / red / green / refactor / regression 证据是否能证明错误实现会失败、正确实现已通过 | HOLD，补测试或补证据 |
| 边界与偏差判断 | changed files / changed surface 是否落在授权路径内；偏差、阻塞、return condition 和 stop event 是否被记录并处理 | 触发 Decision Gate 或回上游阶段 |
| 专业角色调度判断 | dispatch plan 是否按专业 surface 调用 role package，且 reviewer 只读审查覆盖全部执行单元 | BLOCKED 或重新 dispatch |
| 实现结果交接判断 | execution-result 是否记录 dispatch、TDD evidence、执行结果、审查结论、变更面、偏差 / 阻塞 / 回流命中，足以支撑 code-review / verify | 不得完成 execute |

</stage_capability>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `result-contract-via-cli` | execution-result.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness contract init/patch | hook=execute-check-contract-via-cli |
| `upstream-readonly` | execution-brief.md 及其 contract 是上游产物，execute 阶段只读 | hook=execute-check-upstream-artifact-readonly |
| `atomic-task-is-unit` | execute 执行单位是 Atomic Task；缺少已审查并绑定 TASK node 的 parent-local atomic_task_queue 即前置条件未满足，BLOCKED | hard_gate=atomic-queue-prerequisite |
| `stop-if-boundary` | 实现不得越界写 authorized_paths 外路径 / 触碰 prohibited_paths / 新增外部依赖 / 引入未授权 public behavior / 与设计约束冲突 | hook=execute-check-stop-changes-outside-authorized + execute-check-stop-new-external-dependency + execute-check-stop-new-public-behavior + execute-check-stop-design-constraint-conflict |
| `reviewer-readonly` | spec-reviewer / 条件 reviewer 必须在 readonly subagent 中调用 | registry=subagents/*-reviewer[readonly=true] |

</invariants>

<entry>
  - breakdown 阶段已完成，execution-brief 通过 Stage Gate 并 advance 为 TASK node
  - Mission Slice control_plane.stage=execute 且 lane_action.skill=execute
</entry>

<exit>
  - `result-written`: execution-result.md 写入 execute stage worktree
  - `contract-filled`: execution-result.contract.yaml 已填充且 harness contract check PASS
  - `all-tasks-done`: execution-brief 全部 Atomic Task 完成 + reviewer 合规
  - `no-regression`: 全套单元/集成测试 0 regression；e2e.enabled=true 时 E2E 0 failures / 0 skipped
  - `gate-pass`: harness execute gate run 返回 status=pass
  - `prototype-fidelity`: 如该 mission 有 interaction 产物，前端/交互 Atomic Task 的实现忠于注入的 behavior-graph（page_state / step / edge）与对应 SURF；任何偏离均已走 Decision Gate 同步契约或登记 `prototype_coverage_exemptions`，无静默漂移
</exit>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `frontend-engineer` | spawn |  | `.harness/common/agents/frontend-engineer.md` |
| `backend-engineer` | spawn |  | `.harness/common/agents/backend-engineer.md` |
| `client-engineer` | spawn |  | `.harness/common/agents/client-engineer.md` |
| `security-engineer` | spawn |  | `.harness/common/agents/security-engineer.md` |
| `integration-engineer` | spawn |  | `.harness/common/agents/integration-engineer.md` |
| `data-engineer` | spawn |  | `.harness/common/agents/data-engineer.md` |
| `refactoring-expert` | spawn |  | `.harness/common/agents/refactoring-expert.md` |
| `interaction-engineer` | spawn |  | `.harness/common/agents/interaction-engineer.md` |
| `test-engineer` | spawn |  | `.harness/common/agents/test-engineer.md` |
| `debugging-expert` | spawn |  | `.harness/common/agents/debugging-expert.md` |
| `integration-impact-expert` | spawn |  | `.harness/common/agents/integration-impact-expert.md` |
| `spec-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/spec-reviewer.md` |
| `data-migration-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/data-migration-reviewer.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `execution-brief.md` | true | Memory |
| `specs/` | conditional: spec.enabled=true | Artifact Contract |
| `project-context.md` | conditional: brownfield | Context |
| `harness.yaml` | true via harness config snapshot | Memory |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `execution-result-md` | `harness-runtime/harness/artifacts/${mission-id}/execute/execution-result.md` | markdown | Memory |
| `execution-result-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/execution-result.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |

</outputs>

<steps>

<step id="step-0" n="0" goal="阶段初始化 + SDD 模式确认">
- 调用 `harness mission document --mission <mission-id> --type task-order --json` 解析任务下单文档路径，确认 `exists=true` 后读取返回的 `path`。
 - 调用 `harness context check --json`；PASS 则读取 `project-context.md`；FAIL 时按 `project-context` 规则处理并记录 `inputs_missing.project_context=true`，不得静默继续。
 - 调用 `harness knowledge resolve --stage execute --json`，读取返回的 project-knowledge 路径；重点消费 specs、engineering conventions/patterns/testing 和 operations verification runbooks。不得全量读取 project-knowledge。
 - 调用 `harness frame current --mission <mission-id> --json`，确认 `control_plane.lane`/`stage`、`lane_action.skill`、`lane_action.carrier`、`primary_nodes`、`related_nodes`、`operation`、`output_artifact`。必须返回 `resume_source=mission_slice`；否则 HALT 要求 board-router 重建 Mission Slice。
 - 确认当前 Mission Slice 已处于 execute lane/action，且 `primary_nodes` 覆盖同一 `execution_batch_id` / `execution_brief_artifact` 下所有仍处于当前 execute lane/stage 的 sibling TASK nodes；若只包含单个 Parent task 对应的 TASK node 而遗漏同批 sibling，HALT 回到 board-router 重建 Mission Slice。
 - 确认当前 Mission Slice 的 TASK node 来自已通过 Stage Gate / `harness gate advance` 的 breakdown 产物包；若仍是 breakdown slice、gate 未 advance 或任一 primary TASK node 缺 Execution Units / parent-local atomic_task_queue 绑定，HALT 回到 stage-gate。
 - 调用 `harness config snapshot --json`，获取 `execute_mode`、`spec.enabled` 和执行模型策略摘要。若 `execute_mode != sdd`，HALT 报告配置错误。
 - 读取 execution-brief 的 Execution Units，为每个 Parent task 建立 Parent task → parent-local Atomic Task queue 映射，并提取每个 Atomic Task 的 `SUC-xx-OP-xx` 追溯；映射失败、系统操作覆盖缺失、队列为空、status 非 ready 或边界冲突时 HALT/BLOCKED，回到 breakdown / Stage Gate 修复。
 - 条件：spec.enabled=true
  - 扫描 `harness-runtime/harness/artifacts/<mission-id>/product/specs/` 加载本任务全部差量规格文件（旧 `stages/<mission-id>/specs/` 仅作兼容读取）；它们构成硬行为边界——实现的可观测行为必须落在 ADDED/MODIFIED Scenario 内。
 - 会话恢复时先确认 baseline evidence：优先复用上一轮 execution-result.contract.yaml / trace / green / regression / toolchain evidence（记 `baseline_decision=reuse_existing_evidence`）；无可信 baseline 时只运行当前 Atomic Task 声明的 focused baseline command。不得无条件先跑全量 regression。
 - Hard gate `sdd-prerequisites`：`execute_mode=sdd` 时跳过 dispatch plan / 角色包解析 / 亲自完成规格审查 = 执行错误。无法用 subagent dispatch 调用执行或审查子 Agent 时阶段返回 BLOCKED。当前执行单位始终是 Atomic Task，不是 Parent task。
 - Hard gate `atomic-queue-prerequisite`：缺少已审查并绑定到 TASK node 的 parent-local atomic_task_queue = 执行前置条件未满足；execute 不得自动补队列。若计划修复生成/更新了 parent-local atomic_task_queue，当前 execute 回合不得继续实现，必须回 breakdown Stage Gate。
 - **frontend_engineering 路线感知**：如果 `harness config snapshot` 的 `prototype.delivery_mode=frontend_engineering`：
   - 读取上游 `interaction-spec/` 与 `contracts/prototype-as-frontend.contract.yaml`（interaction stage 产物）作为前端基线参考；从中提取 `interaction_spec.path/status/trace_refs`、`frontend_project.root`、`frontend_changeset.surfaces[]`、`frontend_changeset.spec_conformance`、`e2e_locator_obligations[]`、`api_contract_draft.endpoints[]`、`downstream_handoff` 字段。PRD / Domain Model / 验收场景 / 条件与 interaction-spec 共同约束前端行为；`frontend-changeset.md` 只作为实现 patch 和交接证据。
   - 标注本 mission 的"前端就绪状态"为 `ready`，作为后续 Task Envelope 注入字段。
   - frontend Task 的 surface 标签应限于 `frontend_integration` / `frontend_test_hardening` / `frontend_bug_fix`；如 breakdown 产出了 `frontend_ui`（新前端 UI 需求），停下来发起 Decision Gate——通常意味着产品定义 / interaction 阶段有缺口，应该回去补，不在 execute 现做。
   - 派发 `frontend-engineer` 子 Agent 时，Task Envelope 必须包含：
     - `delivery_mode=frontend_engineering`
     - `frontend_ready_state=ready`
     - `frontend_project_root` = 上游 contract 解析值
     - `upstream_contract_ref` = `contracts/prototype-as-frontend.contract.yaml`
     - `interaction_spec_ref` = 上游 contract 解析值或 `interaction-spec/`
     - 严格边界提醒：不擅自重构 interaction 阶段已就绪的前端骨架；原型/前端反馈导致的 UI 表达调整必须先同步 interaction-spec / interaction.md，产品语义变化必须回 PRD / Decision Gate；新前端 UI 需求需 Decision Gate；`lib/types/` 改动需 Decision Gate（同时影响后端）
 - **默认（interactive_prototype）路线原型契约感知**：如该 mission 有 interaction 阶段产物（`prototype.delivery_mode` 非 frontend_engineering，且存在 `interaction-spec/behavior-graph.yaml` + `interaction-spec/surface-model.md`）：
   - 加载 `behavior-graph.yaml`（SSOT）与 `surface-model.md`，按当前 mission 范围解析其 `page_state`（稳定 id `PS-<surf>-<state>`）、`surface`（`SURF-xxx`，含 create/modify/extend/retire + baseline）、`step`（`SUC-xx-FLOW-xx.<state>`）、`flow`、`edge`，作为 UI/交互实现基准。`PS-`/`SURF-` 是可追溯 ref，下游实现应忠于其定义，不得静默漂移或自由重设计界面。
   - 对每个 Atomic Task，若其作用面是 UI/交互（surface 标 `frontend_*` / `interaction_*`，或由 `frontend-engineer` / `interaction-engineer` 子 Agent 承接），在 Step 2 Task Envelope 中注入该任务覆盖的 `page_state` / `step` / `edge` 子集与对应 `SURF` 的 surface-model 条目（含 create/modify/extend/retire + baseline）；非 UI / 无原型产物的任务不注入，门自动跳过。
   - 若实现需偏离注入的 behavior-graph（改写 page_state / step / 重设计 surface），停止实现，先同步 behavior-graph.yaml / surface-model.md 并经 Decision Gate；契约可登记 `prototype_coverage_exemptions: [{id, reason}]` 作为合法 N/A 出口，无理由不得豁免。
</step>

<step id="step-1" n="1" goal="SDD 批次规划">
 - 为待执行队列生成执行批次。为每个执行单位生成 dispatch plan（按 `execute/dispatch-plan.md`），提取 `write_scope` / `read_scope` / `depends_on` / `surfaces` / `risk` / `required_evidence` / `parallel_group` / `conflict_risk`。
 - 每个 dispatch plan 的 `execution_unit_id` 必须是当前 Mission Slice `primary_nodes` 中某个 TASK node 的 `parent_local_atomic_task_queue.atomic_task_ids[]` 内的单个 Atomic Task ID；不得用 Parent task ID、范围表达式（如 `AT-01..AT-03`）或列表字符串聚合多个 Atomic Tasks。dispatch plan 必须包含该 Atomic Task 的 `SUC-xx-OP-xx` 追溯或明确写 `不涉及系统操作：原因...`。Stage Gate 会按 Mission Slice batch 的 expected set 校验 dispatch plan、TDD evidence 和 reviewer coverage。
 - 建立依赖图：Parent task 顺序、Atomic Task depends_on、差量规格依赖、共享测试 fixture、共享数据迁移、公共接口变更都是依赖边。
 - 建立文件锁：任意两个执行单位 write_scope 相交，或其一修改另一的测试/fixture/生成物，必须进入不同批次。
 - 将无依赖边、write_scope 不相交、conflict_risk 非 high 的执行单位放入同一 parallel batch；其余串行。无法确认独立性时按串行处理并记 `parallelization_decision: conservative_serial`。
 - Hard gate `batch-no-write-scope-overlap`：同一批次内不得存在重叠 write_scope、未解析依赖、共享迁移、共享状态机核心文件或同一测试文件的并发编辑。批次返回后必须先检查 changed files 是否越界再运行批次级验证。
</step>

<step id="step-2" n="2" goal="解析并派发工程岗位 Agent">
 - 按当前执行单位和 `execute/dispatch-plan.md` 生成 dispatch plan，含 primary_executors / supporting_executors / reviewers / write_scope / read_scope / depends_on / parallel_group / conflict_risk / required_evidence。
 - 条件：dispatch_plan.blocked=true
  - 停止派发执行子 Agent，先处理 blockers 或进入 Decision Gate。
 - 为当前执行单位更新 TodoWrite：每个 primary_executors[] / supporting_executors[] / reviewers[] 角色都有独立 checklist item。
 - 并行调用当前执行单位的全部 primary_executors（如 frontend-engineer / backend-engineer / client-engineer / security-engineer / integration-engineer / data-engineer / debugging-expert / refactoring-expert）。多个 primary 编辑同一 write_scope 或有先后依赖时才按 dependency order 串行并记录原因。
 通过 `@backend-engineer` native delegation调用 `backend-engineer` subagent（Cursor auto-routes 到对应 agent registry 项）
 - 并行调用可独立工作的 supporting_executors（test-engineer / interaction-engineer / debugging-expert / integration-impact-expert）；supporting expert 只补充专业证据，不替代 primary 的完成报告。
 - 子 Agent 上下文包：role prompt package 完整原文（prompt 第一段）+ Task Envelope（声明 execution_context.skill=execute、write_scope / read_scope、完成条件、停止条件）+ Parent task 完整描述文本 + 当前 Atomic Task 片段（关联 `SUC-xx-OP-xx`、文件路径 / 代码模式参考 / 接口数据契约 / fixture / 验证命令 / 事务状态边界 / 证据要求 / 停止条件）+ 场景上下文 + 项目编码约定摘要 + 相关现有代码 + 并行协作边界（write_scope、禁止编辑范围、「不要 revert 或覆盖他人改动、需要越界返回 BLOCKED」）+ 解析出的 role 列表 + required evidence。
 - 原型契约约束（仅默认 interactive_prototype 路线、本 mission 有 interaction 产物且当前 Atomic Task 作用面为 UI/交互时）：在 Task Envelope / 上下文包中注入 Step 0 解析的该任务覆盖的 behavior-graph `page_state`（`PS-<surf>-<state>`）/ `step`（`SUC-xx-FLOW-xx.<state>`）/ `edge` 子集与对应 `SURF` 的 surface-model 条目，作为前端/交互实现基准；明确告知「前端/交互实现须忠于注入的 behavior-graph，不得静默漂移或自由重设计界面；需偏离时停止并返回 BLOCKED，由编排者走 Decision Gate 同步契约或登记 `prototype_coverage_exemptions`」。非 UI / 无原型产物任务不注入。
 - 规格约束（仅 spec.enabled=true）：传任务项引用的差量规格 Scenario GIVEN/WHEN/THEN 原文，明确告知「未在 Scenario 声明的可观测行为一律不得实现，遇到返回 BLOCKED」。
 - 模型解析：不在本 workflow 写具体模型名；按 `harness config snapshot` 模型路由摘要解析 role 候选模型（执行类走 execution 候选）；命名 sub-agent 在当前 adapter 无法 dispatch 时不允许任何回退，必须 BLOCK；在 evidence 记录 model_resolution。
</step>

<step id="step-3" n="3" goal="处理执行专业 Agent 响应">
 - 分支：执行子 Agent 状态码
  - 情况：DONE
   - 进入 Step 4 规格合规审查。
  - 情况：DONE_WITH_CONCERNS
   - 审查 concerns：影响正确性 → 回答问题后重新派发；仅是观察 → 记录后进入 Step 4。
  - 情况：NEEDS_CONTEXT
   - 提供缺失信息，重新 dispatch 同一执行子 Agent。
  - 情况：BLOCKED
   - 评估原因：补充上下文 / 拆分任务项 / 升级给用户。
</step>

<step id="step-4" n="4" goal="审查循环（条件 reviewer + spec-reviewer，直至确认合规）">
 - 循环：id=reviewer-loop；无轮次放行（producer-fixable 缺口不设通过上限，轮次只记录修复历史）；退出条件：本轮 reviewers 在等同严格度下全部 PASS/合规
  - 并行调用 dispatch plan 的全部 reviewers（readonly），含条件 reviewer（如 security-reviewer / data-migration-reviewer）和固定 spec-reviewer。reviewer 是同一审查 barrier 的只读角色，不得逐个串行等待。
  通过 `@spec-reviewer` native delegation调用 `spec-reviewer` subagent（Cursor auto-routes 到对应 agent registry 项）
  - 传递：任务项规格文本 + dispatch plan + 执行子 Agent 完成报告 + supporting evidence + 变更文件列表 / diff。
  - 分支：审查结论
   - 情况：全部 PASS / 合规
    - 退出循环，进入 Step 5。
   - 情况：任一 HOLD / 不合规
    - 将不合规项反馈给对应 primary/supporting 执行子 Agent 要求修复，立即重新调用完整 reviewers 列表全量审查。
    - Hard gate `no-skip-recheck`：
     - 修复完成 ≠ 合规。只有 dispatch plan 全部 reviewer 重新审查后结论合规/PASS 才能退出循环。禁止修复后跳过重审或只重审部分 reviewer。
     - Enforced by: hook=execute-check-gate-pass
 - 条件：卡死——同一不合规项在执行子 Agent 修复后，reviewer 仍以相同根因连续 HOLD 且无实质进展（按缺口本质判断，不是"轮次到点"）
  - 不得降级通过。按 `core.md`「严格审查不变量」重新归因：producer 能补则留在循环升级修复策略 / 升级 reviewer 模型继续修；本质是任务边界 / 上游设计缺失则回 breakdown 修订。
  - 仅当确需用户拍板才能解时，调用 tool: `AskUserQuestion`。
   - 问题：execute 审查发现以下不合规项在反复修复后仍无法在当前范围内解决（已附完整清单与卡点根因），需要你决策方向
   - 候选答案（**不含"接受当前结果 / 降级通过"**）：
      - 给出修复方向，留在审查循环继续修
      - 回 breakdown 修订任务边界
      - 升级 BLOCKED，终止本阶段
  - 残留风险只能由用户在充分披露后于 Decision Gate 显式拥有并记 approval；审查循环本身永不把不合规项自动转为通过。
</step>

<step id="step-5" n="5" goal="任务项完成记录 + 继续">
 - 标记任务项完成，更新 TodoWrite，记录执行日志，继续下一个 Atomic Task / 批次。
</step>

<step id="step-6" n="6" goal="SDD 完成 + execute artifact 产出 + Stage exit">
 - 所有任务项完成后运行全套单元/集成测试确认无回归；若 `e2e.enabled=true` 运行 `npx playwright test` 全套 E2E（0 failures、0 skipped，无 test.skip() 残留）。
 - 进入 Definition of Done 检查（含 E2E DoD 项）。如该 mission 有 interaction 产物：DoD 须确认每个前端/交互 Atomic Task 的实现忠于注入的 behavior-graph（覆盖的 page_state / step / edge 与对应 SURF）；存在偏离时须有对应 Decision Gate 记录或契约 `prototype_coverage_exemptions: [{id, reason}]` 条目，禁止静默漂移 / 自由重设计界面。
 - 读取当前 Mission Slice `lane_action.output_artifact`，必须解析为 `execution-result.md`；用 `harness-runtime/templates/execution-result.md` 结构基线写入 execute session / dispatch summary / baseline evidence / TDD evidence / 执行角色结果 / changed files / reviewer verdicts / 下游证据路径。
 - 若 `contracts/execution-result.contract.yaml` 不存在，调用 `harness contract init --mission <mission-id> --stage execute --template execution-result --json` 初始化；将 control_contract.type=action_contract / role_policy / work_graph_artifact / execute_session / execution_results[] / role_verdicts[] / tdd_evidence[] 写入 contract。
 - execute artifact 自检：验证 execution-result.md 含 Execute Session / Dispatch Summary / TDD Evidence / Execution Results / Reviewer Verdicts；验证外部 contract 覆盖全部 required execution roles 和 required review roles。
 - 调用 cli `harness contract check` `--artifact harness-runtime/harness/artifacts/${mission-id}/execute/execution-result.md`，evidence=required。
 - 调用 cli `harness execute gate run` `--mission ${mission-id}`，evidence=required。
 - Hard gate `gate-pass-before-complete`：未 gate PASS 前不得 stage complete；`execute-check-gate-pass` hook 物理阻断。
 - 调用 cli `harness mission stage complete` `--mission ${mission-id} --stage execute`，evidence=required。
</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `path-outside-authorized` | PreToolUse Edit/Write 路径不在当前 Atomic Task authorized_paths 内 | hook 拒绝写入并记录 stop event；若必须扩授权，调 `harness execute stop-event record --kind path_outside_authorized` 进入 Decision Gate，不得临时扩大授权。 |
| `prohibited-path-hit` | Edit/Write 命中 prohibited_paths | 直接 deny；用 course-correction 回退或回 breakdown 重新设计 task 边界。 |
| `new-external-dependency` | 实现过程发现需新增项目级依赖（package.json / requirements.txt 等） | stop_if 触发；调 `harness execute stop-event record --kind new_external_dependency` 进入 Decision Gate。 |
| `design-constraint-conflict` | 实现触碰 solution / tech-design 已声明的 forbidden_paths 或 constraint | HALT；回 design 或 Decision Gate。 |
| `reviewer-blocked` | spec-reviewer 等 reviewer-class subagent 返回 BLOCKED | 写入 role_verdicts.status=BLOCKED；按 reviewer-blocked 流程补证据或 AskUserQuestion。 |
| `fix-attempts-stuck` | TDD red→green 反复未通过：同一根因连续 HOLD 且 producer 本轮 diff 未触及对应章节 / 测试（与 review-stuck 同款卡死判据，非"次数到点"） | 卡死重新归因，不降级通过、不 accept_partial（与 step-4「无轮次放行」对齐）：producer 能补则升级修复策略 / restart_baseline 继续修；本质是任务边界 / 上游设计缺失则回 breakdown 或 escalate_to_design；需用户拍板则 AskUserQuestion（候选仅：继续修 / restart_baseline / 回 breakdown / 升级 BLOCKED，不含降级通过 / accept_partial）。残留风险仅由用户在 Decision Gate 显式拥有并记 approval。 |
| `review-stuck` | 同一不合规项修复后仍以相同根因连续 HOLD 且无实质进展（连续 2 轮 reviewer `blocking_gap` 指向同一 obligation 且 `finding_type` 相同、producer 本轮 diff 未触及对应章节；非轮次到点） | 重新归因：producer 能补则继续修；任务边界问题回 breakdown；需用户拍板则 AskUserQuestion（候选仅：继续修 / 回 breakdown / 升级 BLOCKED，不含降级通过）。残留风险仅由用户在 Decision Gate 显式拥有并记 approval。 |
| `gate-run-fail` | harness execute gate run 返回 FAIL | 按 phase_results.failed_checks 修复；execute-check-gate-pass hook 阻断未 PASS 时 stage complete。 |
| `dangerous-command-unsanctioned` | PreToolUse Bash 命中 dangerous_command_decisions 未签字 | deny；调 `harness approval append --type dangerous_command_decision` 后重试。 |

</failure_paths>

Stage transition:

- Decided by: `control_plane.stage` from Mission Slice (Work Graph).
- Typical next:
  - `code-review`：当前 Mission Slice 所有 primary TASK nodes 的 Parent / Atomic Tasks 全部完成且 execution-result gate PASS，batch 进入代码审查
  - `verify`：code-review 完成或并行
- Enforced by: cli=harness gate advance

</workflow>
