# Stage Gate Report

**Mission:** 20260522-stock-watch-system
**Stage:** verify
**Operation:** advance_lane
**Decision:** continue_with_warnings
**Gate Effect:** warn

## Programmatic Contract Check

| Level | Code | Message |
|-------|------|---------|
| PASS | contract_valid | Control Contract integrity checks passed |

## Work Graph

- Mission Slice: `harness-runtime/harness/work-graph/mission-slices/20260522-stock-watch-system.yaml`
- Primary Nodes: `TASK-STOCK-WATCH-T002, TASK-STOCK-WATCH-T003, TASK-STOCK-WATCH-T004, TASK-STOCK-WATCH-T005, TASK-STOCK-WATCH-T006`
- Lane/Stage: `verification-lane/verify`
- Operation: `advance_lane`

## Approvals

- Required Checkpoints: ``
- Approved Checkpoints: `discovery, prd`
- Missing Checkpoints: ``

## AI Interpretation

verify gate 已通过：verification-report contract check PASS、acceptance_trace PASS、true-e2e PASS、detect-contradictions PASS，build/unit-replay/E2E 新鲜证据均为 PASS；仅 alignment 的 CMD-* 证据别名与旧脚本兼容存在可解释 WARN，不影响 verify gate failed_checks。
