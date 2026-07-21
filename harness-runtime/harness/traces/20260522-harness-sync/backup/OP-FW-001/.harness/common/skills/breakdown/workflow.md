# 拆解工作流

> **方法论参考**：`.harness/docs/methodology-reference.md` §6（OpenSpec propose 工作流；Vertical Slicing — 每个任务项是可独立交付的价值纵切片）

下文出现的所有 `harness ...` 命令一律通过 harness-cli skill 调用（默认带 `--json`、消费 typed payload；详见 `.harness/common/skills/harness-cli/SKILL.md`）。

<workflow stage="breakdown" version="2">

<goal>
  将全套上游文档压缩为唯一执行计划产物 execution-brief.md，并在首次写盘时为每个 Parent task 产出内嵌 atomic_task_queue。Parent task 是交付切片 / TASK node 边界；Atomic Task 是 execute 的实际执行单位。简单 Parent task 也必须至少含 1 个 Atomic Task；不得先写 Parent task 骨架再把 Atomic Task Queue 当作常规补丁追加。
</goal>

<role>
  你是上下文压缩引擎。你从上游 prd / solution / tech-design 中提炼执行者必须知道的一切，丢掉执行者不需要知道的一切，再把高层目标分解为精确、有序的任务项。任务项拆得好，执行者照着干就不会出错；拆得差，再好的 TDD 循环也救不了方向错误。
</role>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `brief-contract-via-cli` | execution-brief.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness contract fill/patch/add-verdict | hook=breakdown-check-contract-via-cli |
| `brief-not-fenced` | execution-brief.md 不得内嵌 fenced YAML action_contract / execution_result / role_verdicts 段 | hook=harness-lint |
| `atomic-queue-first-write` | execution-brief.md 首次写盘时每个 Parent task 必须已含 ready 状态的 atomic_task_queue + Atomic Task detail，禁止先写 Parent 骨架再补 | hook=breakdown-check-first-write-completeness |
| `parallel-barrier` | delivery-slicer 与 test-planning-expert 并行 barrier 必须双双 DONE 才能集成 | hook=breakdown-check-barrier-complete |
| `reviewer-readonly` | execution-plan-effectiveness-reviewer 必须在 readonly subagent 中调用 | registry=subagents/execution-plan-effectiveness-reviewer[readonly=true] |

</invariants>

<entry>
  - design 阶段已完成（solution / tech-design + 各 contract PASS）
  - skill-router 已判定本消息属 breakdown 阶段
</entry>

<exit>
  - `brief-written`: execution-brief.md 写入 breakdown stage worktree，每个 Parent task 含 atomic_task_queue.status=ready
  - `contract-filled`: execution-brief.contract.yaml 已填充且 harness contract check PASS
  - `reviewer-pass`: execution-plan-effectiveness-reviewer PASS 或用户降级 approval 已记录
  - `spec-coverage`: spec.enabled=true 时 harness execution-brief check-coverage --spec-mode strict PASS
  - `gate-pass`: harness execution-brief gate run 返回 quality_check + artifact_gate 双 PASS
</exit>

<permissions>

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Edit(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Edit(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/stages/*/contracts/execution-brief.contract.yaml)` | contract 必须经 harness contract fill/patch |
| deny | `Edit(harness-runtime/harness/stages/*/contracts/execution-brief.contract.yaml)` | contract 必须经 harness contract patch/add-verdict |
| deny | `Edit(harness-runtime/config/harness.yaml)` | 配置只读 |
| deny | `Edit(harness-runtime/config/model-routing.yaml)` | 配置只读 |
| allow | `Write(harness-runtime/harness/stages/*/execution-brief.md)` | breakdown 主产物 |
| allow | `Edit(harness-runtime/harness/stages/*/execution-brief.md)` | breakdown 主产物 |
| allow | `Bash(harness *)` | breakdown CLI 必需 |

</permissions>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `delivery-slicer` | spawn | harness-runtime/harness/stages/${mission-id}/execution-brief.md | `.harness/common/agents/delivery-slicer.md` |
| `test-planning-expert` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/test-planning-expert.md` |
| `execution-plan-effectiveness-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/execution-plan-effectiveness-reviewer.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `mission-contract.md` | true | Intent |
| `product/product-definition.md` | true | Memory |
| `product/product-domain-model.md` | true | Memory |
| `product/product-evidence.md` | true | Evidence |
| `solution.md` | true | Memory |
| `tech-design.md` | true | Memory |
| `interaction.md` | conditional: interaction lane 已完成 | Memory |
| `interaction-spec/` | conditional: interaction lane 已完成且涉及 UI / user journey | Memory |
| `project-context.md` | conditional: brownfield | Context |
| `harness.yaml` | true via harness config snapshot | Memory |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `execution-brief-md` | `harness-runtime/harness/stages/${mission-id}/execution-brief.md` | markdown | Memory |
| `execution-brief-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/execution-brief.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |

</outputs>

<steps>

<step id="step-0" n="0" goal="阶段初始化">
 - 调用 `harness mission stage start breakdown --json` → `harness trace log-init`，建立本阶段 trace。
 - 读取上游文档：`harness-runtime/harness/missions/<mission-id>/mission-contract.md`、`harness-runtime/harness/stages/<mission-id>/product/product-definition.md`、`harness-runtime/harness/stages/<mission-id>/product/product-domain-model.md`、`harness-runtime/harness/stages/<mission-id>/product/product-evidence.md`、`harness-runtime/harness/stages/<mission-id>/solution.md`、`harness-runtime/harness/stages/<mission-id>/tech-design.md`、`harness-runtime/harness/stages/<mission-id>/interaction.md` 与 `interaction-spec/`（如存在），以及 `harness-runtime/harness/stages/<mission-id>/frontend-changeset.md` 与 `contracts/prototype-as-frontend.contract.yaml`（如存在，frontend_engineering 路线）。拆分必须覆盖 DDD 模型中的 domain command、invariant、state transition、permission rule 和 exception / compensation case；UI / user journey 任务必须以 interaction-spec 的 surface-index / surface-changeset / flow / state / scenario / validation / view-model 合同（interactive_prototype 路线）或 frontend-changeset.md + e2e_locator_obligations（frontend_engineering 路线）生成执行边界，不得只按页面或文件机械拆分。
 - **frontend_engineering 路线 surface 标签约束**：如果 `harness config snapshot` 的 `prototype.delivery_mode=frontend_engineering` 且上游 `contracts/prototype-as-frontend.contract.yaml` 存在：
   - 前端相关任务的 surface 标签**只允许**：`frontend_integration`（MSW → 真 API 切换 + 联调）、`frontend_test_hardening`（写 e2e + 单元 / 组件测试）、`frontend_bug_fix`（修联调暴露的 bug）。
   - 不允许在 execute 阶段产出 `frontend_ui` 标签的任务——这意味着新前端 UI 需求，应该回 interaction stage 处理；若上游产物提示存在此类需求，停下来发起 Decision Gate。
   - 每个 `frontend_test_hardening` 任务必须引用 contract 的 `e2e_locator_obligations[]` 中至少一个 `path_id` 作为实现目标。
 - 调用 `harness context check --json`；PASS 则读取 `project-context.md`；FAIL 时按 `project-context` 规则处理，并在 breakdown evidence 中记录 `inputs_missing.project_context=true`，不得静默继续。
 - 调用 `harness config snapshot --json`，获取 `spec.enabled`、执行模型策略摘要和 lane action 注册表；不得直接读取 `harness-runtime/config/harness.yaml` 或 `model-routing.yaml`。
 - 条件：spec.enabled=true
  - 从 `harness config snapshot` 读取 breakdown 附加约束摘要；调用 `harness spec diff list --mission <mission-id> --json` 列出全部差量规格 Scenario 及其覆盖状态，作为后续 Step 3c 全局覆盖检查的输入。
 - 从 `harness frame current --mission <mission-id> --json` + `harness config snapshot --json` 取得 breakdown 阶段 role policy；默认执行子 Agent 为 `delivery-slicer` / `test-planning-expert`，审查子 Agent 为 `execution-plan-effectiveness-reviewer`。
 - 从 tech-design.contract.yaml 派生 `agent_engineering` 触发判定，供 Step 9 条件触发消费。
 - 使用当前 Mission Slice 和 lane action 快照；breakdown 的任务项必须能映射为 TASK node 候选，不能只停留在 Markdown 列表。
</step>

<step id="step-1" n="1" goal="专业角色调度">
 - 调度子 Agent `delivery-slicer`（writable，写 execution-brief.md 草稿与 atomic_task_queue）+ `test-planning-expert`（readonly，返回 task-level test obligation constraints / matrix）。两者并行工作，但语义不同：`delivery-slicer` 负责切片和队列结构；`test-planning-expert` 不等待最终 execution-brief，而是基于上游 AC / Scenario / domain model / tech-design / interaction-spec / risk / optional task candidate map 产出可合并的测试义务约束。
 <dispatch role="delivery-slicer" mode="spawn" />
 <dispatch role="test-planning-expert" mode="spawn" />
 - `delivery-slicer` brief：PRD、solution、tech-design、delta specs 和 project-context；产出 execution-brief.md 草稿，每个 Parent task 内嵌 atomic_task_queue + Test/E2E Obligation 占位块，并返回 task candidate map（task_id、surface、AC/Scenario trace、risk、authorized_paths）。`test-planning-expert` brief：同一组上游材料 + delivery-slicer task candidate map（若主流程已经能提供；否则传空并要求按 AC/surface/risk 产出约束）；返回 task-level / atomic-level test obligation matrix（不写盘），每个任务项至少声明 Red / Green / Regression obligation、required evidence、blocking threshold，或 accepted alternative + approval need。
 - 等待两个子 Agent 返回后，由主流程按 `parent_task_id` / `atomic_task_id` / surface / AC trace 把 test-planning-expert 的 obligation matrix 合并到 delivery-slicer 写出的 execution-brief.md（替换占位块），形成内存中完整的 breakdown planning packet；此时不得发布只含 Parent task、仅占位 obligation 或未合并测试义务的中间 execution-brief，也不得把 Atomic Task Queue 推迟给常规后置补丁。
 - 外部 `contracts/execution-brief.contract.yaml` 后续写盘时必须写入每个执行角色的 `execution_result`（含 delivery-slicer 与 test-planning-expert 两条），不得只保留其中一个。
</step>

<step id="step-2" n="2" goal="从上游文档提炼执行上下文">
 - 从任务契约提取：验收标准、约束、交付要求。
 - 从 prd 提取：每条 FR 的核心内容（去掉分析过程，只保留结论）。
 - 从 solution 提取：已确定的方案选择（去掉被否决的方案）。
 - 从 solution.md 的 Solution 指导契约提取 decisions、forbidden_paths、risks，作为任务项设计约束。
 - 从 tech-design 提取：模块划分和职责、接口定义、实现策略和顺序、对现有系统的影响点。
 - 从 tech-design.md 的技术指导契约提取 MOD / IF / DATA / VS ID，作为任务项 `traces_to` 的技术约束来源。
 - 调用 `harness knowledge resolve --stage breakdown --json`，读取返回的 project-knowledge 路径；重点提取 engineering/task-splitting、engineering/patterns、engineering/testing 中的本项目样板间和拆分约定。
 - 从 project-context / project-knowledge/context 提取：编码规范要点、技术选择限制、已知的坑。
</step>

<step id="step-3a" n="3a" goal="Parent task 分解 + 顺序 + 依赖">
 - 基于 tech-design 的实现策略，将工作分解为有序 Parent task 候选项。Parent task 是交付切片 / TASK node 边界。确定 Parent task 之间的顺序与依赖：前一个的产出是后一个的前提。
 - 本子步骤只产出 Parent task 骨架（目标 / 完成边界 / 顺序 / 依赖）；Atomic Task Queue 在 Step 3b 同步成形——不得把 3a 的 Parent task 骨架直接写盘。
</step>

<step id="step-3b" n="3b" goal="每个 Parent task 的 atomic_task_queue 12 字段">
 - 为每个 Parent task 设计内嵌 Atomic Task Queue。Parent task 和 Atomic Tasks 必须一起成形；不得先确认 Parent task 再启动常规二次拆解。
 - 每个 Parent task 必须包含：目标 / 完成边界 / 实现约束 / 测试要求 / 相关文件 / 规格引用（仅 spec.enabled=true，格式 `<capability>/spec.md#<Requirement>/<Scenario>`）/ required evidence（红绿测试 + 回归 + lint/typecheck/build；验收与高风险行为还需测试有效性证据）/ test_obligation（按 tdd-toolchain.md 声明 risk_level / surfaces / required_capabilities / evidence_required / accepted alternatives）/ stop conditions（至少含范围越界、差量规格未授权新行为、设计约束冲突、新外部依赖）/ guide 引用（至少一个 DEC-/MOD-/IF-/DATA-/VS- ID）/ atomic_task_queue（至少 1 个 Atomic Task，每个 Atomic Task 有同 ID 详情块）/ 队列完整性（每个 Atomic Task 满足 single_action / explicit_inputs_outputs / parent_task_coverage / ac_scenario_coverage / code_pattern_references / interface_or_data_contracts / test_fixtures_and_seed_data / validation_commands / transaction_or_state_boundaries / evidence_requirements / stop_conditions / migration_or_route_boundaries）。
 - 分解原则：Parent task 是生产可验收纵切片，不只覆盖 demo happy path；Atomic Task 足够小可在一个 TDD 循环完成；Parent / Atomic Task 之间有明确依赖；每个 Atomic Task 完成后系统处于可测试状态；不创建只有「准备」「清理」意义、无可验证输出的 Atomic Task。
 - 每个 Parent task 自带 completion checklist：测试写完且失败（红）/ 实现写完且测试通过（绿）/ 代码结构合理无多余实现（重构）/ 无回归 / 验收与高风险行为已有测试有效性证据 / test_obligation required capabilities 均有工具或等价证据。
</step>

<step id="step-3c" n="3c" goal="spec 全局覆盖检查">
 - 条件：spec.enabled=true
  - 全局覆盖检查：Step 0 `harness spec diff list` 列出的每一份差量规格文件里每个 ADDED/MODIFIED Scenario，都必须至少被一个任务项的「规格引用」覆盖。机器判定走 `harness execution-brief check-coverage --mission <mission-id> --spec-mode strict --json`。
  - 未被覆盖的 Scenario → 补任务项或合并到既有任务项；不得遗漏。
  - Hard gate `spec-scenario-coverage`：不允许「这个 Scenario 太小所以不单独写任务项」式的合理化。Scenario 是行为契约单位，要么被测试覆盖，要么从差量规格里拿掉（回 PRD 修改）。
</step>

<step id="step-4" n="4" goal="准备产物包结构">
 - 使用 `harness-runtime/templates/execution-brief.md` 模板结构准备待写入内容，但本步骤只组装内存结构，不写盘。
 - 根据 Step 3 的粒度策略准备以下章节：外部控制契约（初始化并填充 `contracts/execution-brief.contract.yaml`，type 必须为 action_contract，每个任务项记录 id / traces_to / authorized_paths / prohibited_paths / required_evidence / test_obligation / stop_if / dependencies）/ TL;DR / 任务目标 / 硬性约束 / 接口与数据变更速查 / Atomic Task Queue 策略 / 已知风险与注意事项 / Execution Units（Parent task + 内嵌 atomic_task_queue）/ Definition of Done / 验收标准速查 / 上游文档引用。execution-brief.md 的「控制契约」段只保留 `Contract: contracts/execution-brief.contract.yaml` 引用和 Authority 说明，禁止追加 fenced YAML contract。
 - Parent task 不得承载文件级行动、代码模式参考、fixture 细节、execute-time validation commands 或 Atomic Task 顺序；调度元数据只进入同一 Parent task 内的 `atomic_task_queue.execution_units[]`，执行说明进入同 ID 的 Atomic Task detail 块。不得只输出表格或只输出 atomic_task_ids，也不得在 detail 块里重复维护第二份 YAML 调度元数据。
 - 不得在 breakdown workflow 内手工把当前 Mission Slice 标记完成或进入 execute；`execution-brief.md` 是产物名，不作为调度 stage key。阶段完成、Work Graph 推进和下一张 Mission Slice 只能由 Stage Gate 后的 `harness gate advance` 写入。
</step>

<step id="step-5" n="5" goal="TASK node 输出计划">
 - 读取 `lane_action.output_artifact`，确认 execution-brief 是本 action 的 stage artifact。
 - 每个可独立执行的任务项必须具备 TASK node 候选信息：稳定 task id、title、lane 初始值、依赖输入 node、对应 delta spec Scenario 和授权路径。
 - TASK node 候选信息必须声明 Parent task 与内嵌 Atomic Tasks 的绑定：parent_task_id、execution_brief_artifact、execution_units_section、parent_local_atomic_task_queue、Atomic Task id 列表、执行顺序和审查状态。
 - 若一个 TECH / SOL node 拆成多个 TASK node，记录 `split_node` graph operation intent；若多个设计 node 合并成一个执行批次，记录 `merge_nodes` graph operation intent。
 - Stage Gate PASS 后由 `harness gate advance` 创建或更新 TASK nodes、promotion execution-brief artifact，把 Execution Units 中对应 Parent task 的 atomic_task_queue 绑定到 TASK node，随后重建 board / index / tree 并写入下一张 Mission Slice。breakdown workflow 不直接编辑 Work Graph 派生视图，也不手工改 Mission Slice。
</step>

<step id="step-6" n="6" goal="一次性写盘 + reviewer 派发">
 - 写入 `harness-runtime/harness/stages/<mission-id>/execution-brief.md`；这是唯一执行计划产物。写盘时每个 Parent task 必须已包含 `atomic_task_queue.status: ready` 和至少一个 Atomic Task details。
 - Hard gate `no-incomplete-brief-to-gate`：禁止写入「缺 Atomic Task Queue、等待 writing-plans 补齐」的 execution-brief 作为 Stage Gate 候选产物。若队列缺失或不完整，继续在 breakdown 内修复；无法补齐时发起 Decision Gate 或 BLOCKED。
 - 若 `contracts/execution-brief.contract.yaml` 不存在，调用 `harness contract init --mission <mission-id> --stage breakdown --template execution-brief --json` 初始化；若已存在只能 patch。
 - 将任务项 action contract 字段、全部执行角色的 execution_results[] 写入 contract 的 control_contract。
 - 写盘完成后，并行调用 role policy 返回的全部 review roles；默认至少调用 execution-plan-effectiveness-reviewer。
 <dispatch role="execution-plan-effectiveness-reviewer" mode="spawn" />
 - Task Envelope：已写入的 execution-brief 路径（每个 Parent task 都含 atomic_task_queue）、外部 action contract 路径、Evidence Graph obligations、只读约束和 stop conditions；审查结论由 reviewer 返回 role_verdict 建议，主流程经 `harness contract add-verdict` 写入 role_verdicts。
 - 循环：id=reviewer-loop；max_rounds=3；退出条件：execution-plan-effectiveness-reviewer 返回 PASS / 无阻断
  - 每轮进入前调用 `harness contract patch --add-round --json`。
  - 分支：审查结论
   - 情况：HOLD / BLOCKED
    - 修复 execution-brief 阻断性问题，立即重新 dispatch reviewer 全量审查。
    - Hard gate `no-skip-recheck`：
     - 修复完成 ≠ 审查通过。只有 reviewer 确认无阻断且 pending_reviewer_recheck=false 才能退出。
     - Enforced by: hook=breakdown-check-pending-recheck
   - 情况：PASS
    - 退出循环。
 - 条件：达到 max_rounds 后仍有阻断
  - 调用 tool: `AskUserQuestion`。
   - 问题：breakdown 审查循环已达 max_rounds=3，请选择处理方式
   - 候选答案：
      - 接受当前 brief（记录 tradeoff approval 后继续）
      - 回 tech-design 修订
      - 回 design 阶段
      - 重新审查
  - 把答复经 `harness approval append --type breakdown_user_checkpoint --stage breakdown --answer <enum>` 写入 typed payload，不得直接落 markdown。
</step>

<step id="step-7" n="7" goal="质量自检（中间 lint，可重复调）">
 - 调用 cli `harness execution-brief self-check` `--mission ${mission-id}`，evidence=required。
 - 逐项检查：每条 AC 是否至少对应一个任务项输出；任务项顺序是否合理；每个任务项测试要求是否足够具体；每个任务项是否在 Action Contract 声明 required evidence 和 test_obligation；每个 Parent task 是否有内嵌 atomic_task_queue 且每个 Atomic Task 有同 ID 详情块；每个任务项 traces_to 是否引用真实存在的 ID；执行者是否只靠 execution-brief 即可理解边界并进入 dispatch plan 生成；spec.enabled=true 时差量规格每个 ADDED/MODIFIED Scenario 是否都有任务项引用且「规格引用」路径真实存在。
 - 条件：发现缺口
  - 补充缺失内容，不需要回到上游修改。
</step>

<step id="step-8" n="8" goal="Artifact Gate 自检（人类可读 checklist）">
 - Step 7 self-check + Step 10 `harness execution-brief gate run` 已合并为单一 phase 化 gate（quality_check + artifact_gate）。本步骤保留作为人类可读 checklist，机器判定以 gate run 输出为准。
 - 验证 execution-brief.md 包含必要结构：任务目标、硬性约束、任务项（带 checkbox 且每个任务项有完成边界）、Definition of Done。
 - 验证 execution-brief.md 前部包含 `Contract: contracts/execution-brief.contract.yaml` 引用，且不包含 fenced YAML contract / ## action_contract / ## execution_result / ## role_verdicts 段落。
 - 验证外部 contract 包含 `control_contract.type: action_contract`，且每个任务项有 traces_to / required_evidence / tdd_scope / test_obligation / stop_if。
 - 验证本文件包含 Execution Units、每个 Parent task 的 parent-local atomic_task_queue、每个 Atomic Task 的同 ID detail heading；缺失则 FAIL: missing_atomic_task_queue / missing_atomic_task_detail。
 - 调用 cli `harness contract check` `--artifact harness-runtime/harness/stages/${mission-id}/execution-brief.md`，evidence=required。
 - 条件：结构不完整
  - 自行补充缺失部分，不要跳过。
</step>

<step id="step-9" n="9" goal="条件：为 Agent 实现规格生成任务项">
 - 条件：agent_engineering.enabled=true
  - 参考 `docs/methodologies/agent-capability-engineering.md` §6（正确工作顺序）。
  - 读取 `harness-runtime/harness/stages/<mission-id>/tech-design.md` 的 `## Agent 实现` 段落（由 agent-capability-designer 产出并经 agent-capability-reviewer 审查）。
  - 条件：tech-design.md 存在 Agent 实现规格
   - 对每个 Agent 组件生成对应实现任务项并追加到 execution-brief：实现 Agent 定义文件 / 实现技能/tool/MCP 承载物 / 实现 policy/hook 制度层约束 / 接入 runtime / 编写 eval 测试脚本。每个任务项 traces_to 至少引用一个 tech-design ID 或 `## Agent 实现` 段落稳定组件 ID。
  - 条件：agent_engineering.enabled=true 但 tech-design.md 缺少 Agent 实现规格
   - HALT：返回 design 阶段调用 agent-capability-designer / agent-capability-reviewer 补齐 `## Agent 实现`，不得自行发明 capability-specs 目录。
</step>

<step id="step-10" n="10" goal="Stage exit gate">
 - 调用 cli `harness alignment check` `--mission ${mission-id} --stage breakdown`，evidence=required。
 - alignment check 校验 tasks / atomic units 追溯到 AC、domain command、invariant、state transition、tech-design IDs；程序化 FAIL 必须回 breakdown 修正，不得由 reviewer 覆盖。
 - 调用 cli `harness execution-brief gate run` `--mission ${mission-id}`，evidence=required。
 - 只有 phase_results 中 quality_check 与 artifact_gate 双双 PASS、且 failed_checks 为空，才可推进。
 - Hard gate `gate-pass-before-complete`：未 gate PASS 前不得调用 `harness mission stage complete breakdown`；`breakdown-check-gate-pass` hook 物理阻断；M2.1 CLI 是该 gate 的唯一入口。
 - 调用 cli `harness mission stage complete breakdown` `--mission ${mission-id}`，evidence=required。
</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `worker-blocked` | delivery-slicer 或 test-planning-expert 返回 BLOCKED | 在外部 contract 写入 execution_results[].status=BLOCKED，记录 concerns，发起 Decision Gate（harness approval append --type tradeoff）。 |
| `parallel-barrier-violation` | 仅一个并行 worker 返回 DONE | barrier 未达成，breakdown-check-barrier-complete hook 阻断 stage advance；重新派发缺失角色或 BLOCKED。 |
| `reviewer-blocked` | execution-plan-effectiveness-reviewer 返回 BLOCKED | 触发 AskUserQuestion，候选：接受当前 brief / 回 tech-design / 回 design / 重新审查。 |
| `max-rounds-exhausted` |  | = max_rounds"> AskUserQuestion 必触发；用户答 accept / return_to_tech_design / return_to_design / re_review；用 harness approval append --type breakdown_user_checkpoint 写入。 |
| `contract-check-fail` | harness contract check --upstream 返回 FAIL | 按 FAIL code 修复 traces_to / atomic_task_queue / required_evidence 后重审。 |
| `spec-coverage-fail` | harness execution-brief check-coverage --spec-mode strict 返回 FAIL | 补任务项覆盖未覆盖 Scenario；若 Scenario 不应实施则回 PRD 修订差量规格。 |
| `agent-engineering-halt` | step-9 触发 HALT（tech-design 缺 Agent 实现规格） | 回 design 阶段补齐；不在 breakdown 内自行发明 capability-specs。 |
| `parallel-write-scope-conflict` | 两 worker 输出的 tasks[].authorized_paths 并集出现重叠且未声明依赖 | 回 tech-design 或在 breakdown 内拆分任务 / 标 must_serialize。 |
| `writing-plans-boundary-violation` | 在 stage!=breakdown 或非 --mode internal-carrier 时调用 writing-plans | breakdown-check-writing-plans-boundary hook 阻断；若用户手动 --manual-replan 必须带 trace-log 留痕。 |

</failure_paths>

Stage transition:

- Decided by: `control_plane.stage` from Mission Slice (Work Graph).
- Typical next:
  - `execute`：execution-brief gate PASS，TASK node 已就绪
- Enforced by: cli=harness gate advance


</workflow>
