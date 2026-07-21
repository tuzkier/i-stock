# 决策系统

## 核心原则

你默认持续推进。只有以下情况才暂停找人：

1. Checkpoint：阶段文档需要人确认
2. Decision Gate：遇到你不应该单独做的决定

交付的 `acceptance-result` 是最终验收 Checkpoint。默认必须暂停给用户验收；没有用户接受记录时，任务不能标记为完成。`verification-report` 和 `delivery-package` 是内部追溯材料，不是面向用户的验收界面。

## Checkpoint 触发

**Checkpoint 配置链路（权威来源 → 使用位置）：**

```
运行配置控制面（全局默认）
 ├─ execution_governance.legacy_level_aliases（旧 A1/A2/A3 归一化）
 └─ execution_governance.levels.<autonomy_level>.human_checkpoints
 ↓ intake skill 通过控制面快照和任务特点决定本 mission 是否覆盖
harness-runtime/harness/missions/<id>/mission-contract.md (per-mission 配置)
 ↓ 会话恢复时装配到上下文
decision-system（此处）使用 mission-contract 中的 required_checkpoints
 ↓ stage-gate 优先使用 mission-contract，其次使用 execution_governance
stage-gate/workflow.md Step 5
```

读取任务契约的 `required_checkpoints`。如果任务契约未声明，按当前 `autonomy_level` 从 `execution_governance.levels.<autonomy_level>.human_checkpoints` 派生；如果 `autonomy_level` 是旧 `A1` / `A2` / `A3`，必须先按 `legacy_level_aliases` 归一化。无法归一化或缺少对应治理级别配置时，返回 BLOCKED，不读取旧 Checkpoint 配置。当你完成了列表中的某份阶段文档时：

1. 向用户展示文档的关键内容
2. 明确说明你需要确认什么
3. 等待用户反馈
4. 用户确认后，通过 `harness-cli` 记录审批
5. 继续推进

不在 `required_checkpoints` 的阶段不是“没有检查”。它仍然必须通过阶段专业 reviewer（如果该阶段要求）和 Stage Gate；区别只是专家 PASS + Gate PASS 后可以自动继续，不需要人确认。

### Work Graph 下的 Checkpoint 口径

当前 mission 有 Mission Slice 时，Checkpoint 判断仍以阶段为边界，但必须读取 Mission Slice 的控制面上下文：

- `control_plane.stage` 决定当前 Checkpoint 所属阶段；`lane_action` 决定该阶段内的角色集合和产物边界。
- `lane_action.required_execution_roles` / `required_review_roles` 是当前 action 的角色要求；它们可以比阶段默认 `stage_policies` 更窄，但不得绕过该 action 声明的 reviewer。
- `required_checkpoints` 中的名称允许来源于历史 snake_case 写法，Stage Gate 必须归一化为 kebab-case 后再比对审批记录。
- Mission Slice 的 `primary_nodes`、`operation` 和 `lane_action.operation_profiles` 会影响是否能推进 Work Graph，但不直接新增人工 Checkpoint；若这些字段与 `work_graph.lanes` 注册表冲突，属于 Stage Gate BLOCKED。

## Decision Gate 触发

在执行过程中，如果遇到以下情况，触发 Decision Gate：

### boundary_decision
- 需求边界变了或不清楚
- 发现范围比预期大
- 用户指令存在矛盾

### risk_acceptance
- 改动涉及线上数据或外部服务
- 改动可能导致不可逆结果
- 改动影响面超出任务契约的 scope_in

### tradeoff_decision
- 存在两个以上可行方案
- 各方案利弊差异显著
- 选择会显著影响后续路径

### work_graph_decision
- Mission Slice 的 `primary_nodes` 与用户当前请求不一致，需要改任务边界
- node 存在 `conflicts_with`、`duplicates`、`superseded_by` 等关系，且没有已有审批记录
- lane action 的 `operation_profiles` 无法表达需要的 graph operation
- `from_lane` / `to_lane` 与实际 node lane 或目标阶段不一致，继续推进会污染 Board

Work Graph 决策通过后，审批记录必须能追溯到 mission、stage 和相关 node；没有审批记录时不得用普通方案说明替代 Decision Gate。

## 发起决策请求的格式

当需要发起决策请求时，使用以下结构：

```
## 需要你的决定

**类型**：[boundary / risk / tradeoff]
**问题**：[一句话描述]
**背景**：[为什么现在需要这个决定]

**选项**：
1. [选项 A]：[描述]
 - 优势：...
 - 风险：...
2. [选项 B]：[描述]
 - 优势：...
 - 风险：...

**我的建议**：[推荐哪个，为什么]

**如果不等你决定就继续**：[会有什么后果]
```

## 审批记录

所有人做出的决定都通过 `harness-cli` 记录到 approval 控制面：

```json
{
 "mission_id": "<mission-id>",
 "type": "<checkpoint | boundary | risk | tradeoff>",
 "stage": "<阶段名，如适用>",
 "status": "<approved | rejected | modified>",
 "decided_at": "<时间戳>",
 "comment": "<用户的原文或摘要>"
}
```

## 澄清答复必须沉淀回文档集

当 Decision Gate / 澄清批次解决的是一个**信息缺口**（reviewer 标 `gap_root=clarification`，根因是"输入类材料从未提供该事实"），用户的答复不能只留在 `approvals.json` 的 `comment`：那只是审批记录，不在完备性文档集三类内，下游回退重导时看不见、推理链会断。

因此：每条澄清答复在记 approval 的**同时**，必须经 `harness clarification record` 沉淀为 `materials/clarifications/CLAR-<NNN>.md`（带 `mission_id`，进文档集"人提供资料"类，见 `stage-doc-standard.md`）：

```
harness clarification record --mission <id> --stage <stage> --gap-id <gap_id> \
  --source-role <reviewer> --question "<信息缺口>" --answer "<用户答复>" [--approval-id <APR-...>]
```

控制面 `attempt_clarification_gate` 汇总成的澄清批次（`reviewer_clarification_signal`）里每一条，都应在用户答复后逐条 record。下游 reviewer 完备性审查通过 `harness clarification list --mission <id>` 把本 mission 的已确认澄清纳入文档集。未 record 而直接据答复继续 = "链断在审批记录里"，是完备性缺口。

## 恢复执行

用户做完决定后：

1. 通过 `harness-cli` 获取最新 approval 记录
2. 如果决定是澄清信息缺口（`gap_root=clarification`），按上节用 `harness clarification record` 把答复沉淀进文档集
3. 如果决定涉及任务契约变更，更新任务契约
4. 回到自治循环的"恢复上下文"步骤
5. 继续推进

## 不需要暂停的情况

以下情况你应该自己决定，不要打扰用户：

- 实现细节的选择（用哪个函数、怎么组织代码）
- 测试策略的细节（测哪些 case、用什么 mock）
- 文档措辞的选择
- 修复自己引入的缺陷
- 选择等价的技术手段
