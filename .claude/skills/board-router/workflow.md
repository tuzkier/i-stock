# Board Router 工作流

**Goal:** 从 Work Graph Board 选择可推进工作对象，并把一次推进包装成 Mission Slice；当多个 TASK node 来自同一 execution-brief 执行批次时，必须把它们作为同一个推进批次处理。

**Your Role:** 你是 Board 调度员。你只通过 Harness CLI 消费 Board / Index 派生视图，选择可推进 node，生成 Mission Slice，并在 Stage Gate PASS 后把推进交回控制面。

---

## CLI-first control-plane preflight

适用场景：`continue`、`status`。进入 Board Router 前先调用 `harness-cli` 读取只读控制面：`harness control status --json`、`harness control candidates --intent continue --json`。若用户或上游路由已显式确定 mission，再调用 `harness control frame --mission <mission-id> --json`、`harness control guidance --mission <mission-id> --json`、`harness control context-index --mission <mission-id> --json`。`control.candidates` 只提供候选事实，不得把 candidates 当作最终选择。若必须临时读取旧 runtime 文件，记录 `fallback_used`、`fallback_reason`、`legacy_source`、`follow_up`。

<workflow skill="board-router" version="2">

<step n="1" goal="读取 Board 调度输入">
 - 调用 `harness-cli` 执行 `harness board select --mission <mission-id> --write-slice --json`，选择可推进 node 并生成 Mission Slice skeleton。
 - 调用 `harness-cli` 执行 `harness config snapshot --json`，消费返回的 `work_graph.lanes.<lane>.stages[]` 注册表和 `work_graph.selection_strategy`。
 - Board 快照来源是 `harness-runtime/harness/work-graph/boards/main.yaml`，Index 快照来源是 `harness-runtime/harness/work-graph/_index.yaml`；只能通过 CLI 消费这两个派生视图。
 - 条件：CLI 返回 BLOCKED 或缺少 Board / Work Graph 快照
  - 停在 Gate 并报告 CLI 能力或数据缺口；不得手工读取 board / index / node YAML 代替。
</step>

<step n="2" goal="选择可推进 node 并生成 Mission Slice">
 - 按 `work_graph.selection_strategy` 选择 node：先按当前任务上下文相关性，再按 node priority、lane order、stage order、status、updated_at、node_id 等稳定顺序；同一 lane 内必须先推进更早 stage 的 ready/active node，避免单个 task 走完 execute → code-review → verify → delivery 后才处理下一个 task。
 - 选择 node 后，Mission Contract 必须写入 `work_graph.primary_nodes`。
 - 若选中的 TASK node 带有 `execution_batch_id` 或 `execution_brief_artifact`，Board Router 必须把同一 batch key、同一 lane/stage、状态为 ready/active 的 sibling TASK nodes 一并写入 `work_graph.primary_nodes`；不得只选择一个 Parent task 对应的 TASK node 后让它独自进入 code-review / verify / delivery。
 - `deferred` / `blocked` lane 不直接进入 schedulable lane；若相关性扫描发现相关候选，只写入 Mission Slice 的 `related_candidates`，用于边界、阻塞风险或后续恢复提示。
 - `harness-cli` 执行 `harness board select --write-slice` 会写入 `harness-runtime/harness/work-graph/mission-slices/<mission-id>.yaml`，作为 Mission Contract 填充的结构化输入。
</step>

<step n="3" goal="写入阶段调度语义">
 - Mission Slice 必须写入 `control_plane.lane` / `control_plane.stage` 和 `lane_action`；`control_plane` 不写 `skill`、`carrier` 或迁移字段。
 - 若 `lane_action.skill` 存在，自治循环必须调用该精确 skill；例如 `development-lane / execute` 必须进入 `execute`，不得由状态同步或主 Agent 手工补结果。
 - `solution`、`interaction`、`technical_analysis` 是真实 stage，不再归并为单一 `design` stage。
 - Board Router 不在脚本中硬编码 lane 到 stage/action/kind/operation 的映射，也不提供内置 fallback；新增或调整 stage action 时修改模板配置 `work_graph.lanes`，安装后由目标项目配置生效。
 - 条件：缺少 lane action 注册表或关键字段
  - 返回 BLOCKED，不推导默认阶段。
</step>

<step n="4" goal="Stage Gate 后应用推进">
 - Stage Gate PASS 后，调用 `harness-cli` 执行 `harness gate advance --mission <mission-id> --gate-report <gate-report.json> --json`，读取 Gate report、Mission Slice 和可选 contract artifact。
 - CLI 生成 graph operation manifest，并交给 Work Graph 控制面处理。
 - Mission Slice 若需要非线性图操作，必须携带 `graph_operation` payload；Gate 后支持 `advance_lane`、`advance_stage` 的多 primary node batch 推进、`split_node`、`merge_nodes`、`block_node`、`defer_node`、`supersede_node` 和 `batch`。
 - `lane_action.graph_operation` 是默认 operation；允许的 operation 与 child/target kind、默认目标 lane 由 `operation_profiles` 推导。显式 `graph_operation.type` 必须与 `operation` 一致。
</step>

<step n="5" goal="Gate 判定">
 - 条件：board 引用不存在的 node
  - 返回 BLOCKED。
 - 条件：node lane 与 board lane 不一致
  - 先通过 `harness-cli` 运行 `harness graph rebuild --json`；仍不一致则返回 BLOCKED。
 - 条件：`work_graph.lanes` 缺失、字段不完整、`accepts_kinds` / `operation_profiles` 不合法
  - 返回 BLOCKED。
 - 条件：Mission Slice operation 不在 lane action profile 允许范围内、child/target kind 不符合 profile，或与 graph operation payload 不一致
  - 返回 BLOCKED。
 - 条件：graph operation 脚本失败
  - 返回 BLOCKED。
</step>

</workflow>
