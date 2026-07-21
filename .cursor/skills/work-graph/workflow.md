# Work Graph 工作流

**Goal:** 用固定脚本维护 Work Graph，确保长期 node 事实源与派生视图一致。

**Your Role:** 你是 Work Graph 控制面执行者。你只产出或应用 graph operation，不直接手写 board / index / tree 派生视图。

---

<workflow skill="work-graph" version="2">

<step n="1" goal="读取 Work Graph 事实">
 - 调用 `harness-cli` 执行 `harness graph check --json` 或 `harness graph node show <node-id> --json` 获取 Work Graph node 事实。
 - Hard gate：不得直接读取 `nodes/**/*.yaml`、`boards/main.yaml`、`_index.yaml`、`indexes/*.yaml` 或 `trees/*.yaml` 来绕过 CLI 控制面。
</step>

<step n="2" goal="准备 graph operation manifest">
 - 条件：本次动作是状态推进、批量推进、拆分、合并、阻塞、延期、替代或 artifact promotion
  - 先写 graph operation manifest，再进入 apply。
 - `split_node` / `merge_nodes` / `block_node` / `defer_node` / `supersede_node` / `batch` 必须通过 manifest 应用，不能手写 node 关系后再重建。
 - artifact promotion 必须维护 canonical doc、可选 canonical contract、node `artifact_state` 和 `changelog.md`；未 accepted 的 canonical artifact 不能作为后续正式输入。
 - promotion 以 `work_graph_artifact.node_id` 指向的 node 为准，不绑定特定 operation 类型。
</step>

<step n="3" goal="应用固定操作">
 - 调用 `harness-cli` 执行 `harness graph apply --operation <operation.yaml> --json` 应用固定操作。
 - 创建新 node 时必须读取 `work_graph.node_kinds.<kind>.directory` 决定落盘目录。
 - manifest 可在任意成功的 operation 上携带 `work_graph_artifact`，由 CLI 统一 promotion。
</step>

<step n="4" goal="重建和校验派生视图">
 - 调用 `harness-cli` 执行 `harness graph rebuild --json` 从 node 重建 board / index / tree。
 - 调用 `harness-cli` 执行 `harness graph check --json` 校验一致性。
</step>

<step n="5" goal="Gate 判定">
 - 条件：`harness graph check` 返回 FAIL
  - Stage Gate 不得推进。
 - 条件：board / index / tree 与 node 冲突
  - 以 node 为准，先重建视图；重建后仍冲突才进入修复。
 - node ID 前缀和 node 落盘目录以 `work_graph.node_kinds` 为控制面；schema / consistency checker / operation 脚本必须消费同一注册表。
</step>

</workflow>
