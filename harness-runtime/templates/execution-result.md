# 执行结果: {{mission_id}}

> `execution-result.md` 只能由 `execute` skill 为 Work Graph `execute / implementation` lane action 产出。
> 状态同步、trace 修复、Work Graph 对齐和手工补写不能证明实现完成，也不能证明 TDD 完成。

- Contract: contracts/execution-result.contract.yaml
- 上游执行授权: `execution-brief.md`
- 执行原则: 单个 Atomic Task 是唯一实现单位；Parent task 只作为交付边界和排序边界。

## 执行会话（Execute Session）

| 字段 | 值 |
|-------|-------|
| Skill | execute |
| Carrier | execute |
| Execute Mode | sdd |
| Mission | {{mission_id}} |
| Task Node | {{work_graph_node_id}} |
| Parent Task | {{parent_task_id}} |
| Atomic Task Queue | {{atomic_task_queue_id}} |

## 调度摘要（Dispatch Summary）

| Execution Unit | Parent Task | Primary Executors | Supporting Executors | Reviewers | Status | Boundary Result |
|----------------|-------------|-------------------|----------------------|-----------|--------|-----------------|
| {{execution_unit_id}} | {{parent_task_id}} | {{primary_executors}} | {{supporting_executors}} | {{reviewers}} | DONE / BLOCKED | {{boundary_result}} |

## 授权边界检查

| Execution Unit | Authorized Paths | Prohibited Paths | Changed Files | Changed Surface | Stop If Result | Boundary Result |
|----------------|------------------|------------------|---------------|-----------------|----------------|-----------------|
| {{execution_unit_id}} | {{authorized_paths}} | {{prohibited_paths}} | {{changed_files}} | {{changed_surface}} | {{stop_if_result}} | in_boundary / blocked / decision_gate |

## 基线证据（Baseline Evidence）

| Evidence ID | Decision | Command / Reused Evidence | Result | Covers | Reason |
|-------------|----------|---------------------------|--------|--------|--------|
| {{baseline_evidence_id}} | reuse_existing_evidence / focused_baseline_run / blocked_existing_failure / toolchain_blocked / expected_missing_behavior | {{baseline_command_or_evidence_ref}} | {{baseline_result}} | {{baseline_covers}} | {{baseline_reason}} |

## TDD 证据（TDD Evidence）

| Evidence ID | Execution Unit | Phase | Type | Command / Path | Exit Code | Signal | Covers |
|-------------|----------------|-------|------|----------------|-----------|--------|--------|
| {{red_evidence_id}} | {{execution_unit_id}} | red | red_report | {{red_command_or_path}} | {{red_exit_code}} | {{red_failure_signal}} | {{red_covers}} |
| {{green_evidence_id}} | {{execution_unit_id}} | green | green_report | {{green_command_or_path}} | 0 | pass | {{green_covers}} |
| {{regression_evidence_id}} | {{execution_unit_id}} | regression | regression_report | {{regression_command_or_path}} | 0 | pass | {{regression_covers}} |
| {{toolchain_evidence_id}} | {{execution_unit_id}} | toolchain | toolchain_status | {{toolchain_status_path}} | {{toolchain_status}} | {{toolchain_signal}} | {{toolchain_covers}} |

## 执行结果（Execution Results）

| Role | Execution Unit | Status | Changed Files | Changed Surface | Evidence | Concerns |
|------|----------------|--------|---------------|-----------------|----------|----------|
| {{primary_executor_role}} | {{execution_unit_id}} | DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED | {{changed_files}} | {{changed_surface}} | {{executor_evidence}} | {{executor_concerns}} |
| {{supporting_executor_role}} | {{execution_unit_id}} | DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED | {{supporting_changed_files}} | {{supporting_changed_surface}} | {{supporting_evidence}} | {{supporting_concerns}} |

## 偏差、阻塞与回流

| Item | Execution Unit | Type | Trigger | Handling | Target Stage / Decision |
|------|----------------|------|---------|----------|-------------------------|
| {{deviation_id}} | {{execution_unit_id}} | deviation | {{deviation_trigger}} | {{deviation_handling}} | {{deviation_target}} |
| {{blocker_id}} | {{execution_unit_id}} | blocker | {{blocker_trigger}} | {{blocker_handling}} | {{blocker_target}} |
| {{return_condition_hit}} | {{execution_unit_id}} | return_condition_hit | {{return_condition_trigger}} | {{return_condition_handling}} | {{return_condition_target_stage}} |
| {{stop_event_id}} | {{execution_unit_id}} | stop_event | {{stop_event_trigger}} | {{stop_event_handling}} | {{stop_event_decision}} |

## 审查结论（Reviewer Verdicts）

| Reviewer | Verdict | Reviewed Unit | Reviewed Evidence | Blocking Gaps |
|----------|---------|---------------|-------------------|---------------|
| spec-reviewer | PASS / HOLD / BLOCKED | {{execution_unit_id}} | {{reviewed_evidence}} | {{blocking_gaps}} |
| {{conditional_reviewer}} | PASS / HOLD / BLOCKED | {{execution_unit_id}} | {{conditional_reviewed_evidence}} | {{conditional_blocking_gaps}} |
