# Execution Result

> `execution-result.md` can only be produced by the `execute` skill for the Work Graph `execute / implementation` lane action.
> State sync, trace repair, Work Graph reconciliation, and manual backfill do not certify implementation or TDD completion.

- Contract: `contracts/execution-result.contract.yaml`

## Execute Session

| Field | Value |
|-------|-------|
| Skill | execute |
| Carrier | execute |
| Execute Mode | sdd |
| Mission | {{mission_id}} |
| Task Node | {{work_graph_node_id}} |

## Dispatch Summary

| Execution Unit | Primary Executors | Supporting Executors | Reviewers | Status |
|----------------|-------------------|----------------------|-----------|--------|
| {{execution_unit_id}} | {{primary_executors}} | {{supporting_executors}} | {{reviewers}} | DONE / BLOCKED |

## Baseline Evidence

| Evidence ID | Decision | Command / Reused Evidence | Result | Covers | Reason |
|-------------|----------|---------------------------|--------|--------|--------|
| {{baseline_evidence_id}} | reuse_existing_evidence / focused_baseline_run / blocked_existing_failure / toolchain_blocked / expected_missing_behavior | {{baseline_command_or_evidence_ref}} | {{baseline_result}} | {{baseline_covers}} | {{baseline_reason}} |

## TDD Evidence

| Evidence ID | Phase | Type | Command / Path | Exit Code | Signal | Covers |
|-------------|-------|------|----------------|-----------|--------|--------|
| {{red_evidence_id}} | red | red_report | {{red_command_or_path}} | {{red_exit_code}} | {{red_failure_signal}} | {{red_covers}} |
| {{green_evidence_id}} | green | green_report | {{green_command_or_path}} | 0 | pass | {{green_covers}} |
| {{regression_evidence_id}} | regression | regression_report | {{regression_command_or_path}} | 0 | pass | {{regression_covers}} |
| {{toolchain_evidence_id}} | toolchain | toolchain_status | {{toolchain_status_path}} | {{toolchain_status}} | {{toolchain_signal}} | {{toolchain_covers}} |

## Execution Results

| Role | Status | Changed Files | Evidence |
|------|--------|---------------|----------|
| execute-control-plane-executor | DONE / BLOCKED | {{control_plane_files}} | {{control_plane_evidence}} |
| {{primary_executor_role}} | DONE / BLOCKED | {{changed_files}} | {{executor_evidence}} |

## Reviewer Verdicts

| Reviewer | Verdict | Reviewed Unit | Blocking Gaps |
|----------|---------|---------------|---------------|
| spec-reviewer | PASS / HOLD / BLOCKED | {{execution_unit_id}} | {{blocking_gaps}} |
