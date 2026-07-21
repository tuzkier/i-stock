# 交付工作流

> **方法论参考**：`.harness/docs/methodology-reference.md` §14（Diátaxis Framework；ADRs）§15（12-Factor App；GitOps；Progressive 交付）§16（SRE — SLO/SLI；Three Pillars of Observability；OpenTelemetry）

所有 CLI 调用通过 harness-cli skill（`--json` 模式）。

<workflow stage="delivery" version="2">

<goal>
  产出两类交付物：面向用户验收的 acceptance-result.md（证明结果是否正确），与内部归档追溯的 delivery-package.md（记录过程和交付边界）；并取得用户验收 checkpoint。
</goal>

<role>
  你是交付整理者。你把「做完了」变成「用户能验收什么、怎么验收、实际结果是什么」。你不发明内容，只从验证报告的 result_evidence、任务契约 AC 和实际可访问入口中汇总。不把未验证通过的内容算作交付，不把测试命令通过当成用户验收。
</role>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `delivery-contract-via-cli` | delivery-package.contract.yaml / acceptance-result.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness CLI | hook=delivery-check-contract-via-cli |
| `acceptance-result-human-facing` | acceptance-result.md 面向人类读者，不暴露内部流水账，不内嵌 fenced YAML contract | hook=harness-lint |
| `pass-ac-needs-result-evidence` | 任一 pass AC 缺 result_evidence 或复现步骤时不得请求用户验收 | hard_gate=acceptance-evidence-complete |
| `reviewer-readonly` | acceptance-package-reviewer 必须在 readonly subagent 中调用 | registry=subagents/acceptance-package-reviewer[readonly=true] |
| `delivery-pauses` | delivery 完成后暂停，不自动调度 retrospective / finishing-branch | hook=harness delivery handoff --pause |

</invariants>

<entry>
  - verify 阶段已完成，verification-report 通过 Stage Gate
  - Mission Slice control_plane.stage=delivery 且 stage=delivery
</entry>

<exit>
  - `acceptance-result-written`: acceptance-result.md 写入 delivery stage worktree，每个 pass AC 有 expected/actual/复现步骤/结果证据
  - `delivery-package-written`: delivery-package.md 写入 delivery stage worktree
  - `contracts-filled`: delivery-package + acceptance-result contract 已填充且 harness contract check PASS
  - `user-accepted`: approvals.json 含 type=checkpoint / stage=acceptance-result 条目
  - `handoff-pause`: harness delivery handoff --pause 已写 handoff evidence
</exit>

<permissions>

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Edit(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Write(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Edit(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/stages/*/contracts/delivery-package.contract.yaml)` | contract 必须经 harness CLI |
| deny | `Edit(harness-runtime/harness/stages/*/contracts/delivery-package.contract.yaml)` | contract 必须经 harness CLI |
| deny | `Write(harness-runtime/harness/stages/*/contracts/acceptance-result.contract.yaml)` | contract 必须经 harness CLI |
| deny | `Edit(harness-runtime/harness/stages/*/contracts/acceptance-result.contract.yaml)` | contract 必须经 harness CLI |
| deny | `Edit(harness-runtime/config/harness.yaml)` | 配置只读 |
| deny | `Edit(harness-runtime/config/model-routing.yaml)` | 配置只读 |
| allow | `Write(harness-runtime/harness/stages/*/delivery-package.md)` | delivery 主产物 |
| allow | `Edit(harness-runtime/harness/stages/*/delivery-package.md)` | delivery 主产物 |
| allow | `Write(harness-runtime/harness/stages/*/acceptance-result.md)` | delivery 验收产物 |
| allow | `Edit(harness-runtime/harness/stages/*/acceptance-result.md)` | delivery 验收产物 |
| allow | `Bash(harness *)` | delivery CLI 必需 |

</permissions>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `release-readiness-expert` | spawn | harness-runtime/harness/stages/${mission-id}/delivery-package.md, harness-runtime/harness/stages/${mission-id}/acceptance-result.md | `.harness/common/agents/release-readiness-expert.md` |
| `acceptance-package-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/acceptance-package-reviewer.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `mission-contract.md` | true | Intent |
| `execution-brief.md` | true | Memory |
| `code-review.md` | conditional: code-review 已完成 | Memory |
| `verification-report.md` | true | Memory |
| `harness.yaml` | true via harness config snapshot | Memory |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `acceptance-result-md` | `harness-runtime/harness/stages/${mission-id}/acceptance-result.md` | markdown | Memory |
| `delivery-package-md` | `harness-runtime/harness/stages/${mission-id}/delivery-package.md` | markdown | Memory |
| `delivery-package-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/delivery-package.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |
| `acceptance-result-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/acceptance-result.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |

</outputs>

<steps>

<step id="step-0" n="0" goal="阶段初始化">
 - 读取 mission-contract.md、execution-brief.md（变更文件 + 任务项完成状态）、code-review.md（评审结论）、verification-report.md（验证结论 + AC 对齐表）。
 - 调用 cli `harness mission stage start` `--mission ${mission-id} --stage delivery`，evidence=required。
 - 调用 cli `harness trace log-init` `--mission ${mission-id}`，evidence=required。
 - 调用 cli `harness frame current` `--mission ${mission-id}`，evidence=required。
 - 调用 cli `harness delivery summarize` `--mission ${mission-id}`，evidence=required。
 - 消费 typed delivery summary（ac_trace 统计 + 上游 artifact 索引）。读取当前 Mission Slice 和 `work_graph.lanes.delivery`；delivery 只能关闭或产生后续 node。
</step>

<step id="step-1" n="1" goal="专业角色调度">
 通过 `Task(subagent_type="release-readiness-expert", prompt=<Task Envelope>)` 工具调用 `release-readiness-expert` subagent
 - brief：verification evidence 路径、code-review findings 路径、AC trace、known risks、approvals、write_scope、完成条件和风险边界要求。
 通过 `Task(subagent_type="acceptance-package-reviewer", prompt=<Task Envelope>)` 工具调用 `acceptance-package-reviewer` subagent
 - 交付物生成后 dispatch reviewer，brief：acceptance-result 路径、delivery-package 路径、Evidence Graph acceptance nodes、只读约束、verdict 输出格式；结构化审查结论登记到 delivery evidence / Work Graph operation 记录，Markdown 只保留面向人的交付审查摘要。
</step>

<step id="step-2" n="2" goal="汇总交付内容与结果证据">
 - 从 execution-brief 提取完成的任务项列表和变更文件清单；从验证报告提取 AC 通过/未通过状态、command_evidence 和 result_evidence；从 code-review 提取评审结论和修复记录。
 - 组织交付摘要：一句话概括（做了什么 / 达到什么效果）、变更范围（新增/修改/删除文件数 + 关键模块）、实现方式（从 solution / tech-design 提取关键技术决策）、交付入口（用户可访问 URL / API / CLI / 测试账号 / 分支 commit）。
</step>

<step id="step-3" n="3" goal="生成面向人的 acceptance-result.md">
 - 逐条列出任务契约的验收标准（AC 编号 / 原要求预期结果 / 实际观察结果 / 复现步骤 / 结果证据 / 结论）。使用 `harness-runtime/templates/acceptance-result.md` 模板结构，写入 `harness-runtime/harness/stages/<mission-id>/acceptance-result.md`。
 - acceptance-result.md 必须面向人类读者，不暴露内部流水账，包含交付入口、验收清单、结果证据、无法验收项。如有 AC 未完全通过，标注为无法验收 / accepted-risk 候选项。
 - Hard gate `acceptance-evidence-complete`：任一 pass AC 缺少 result_evidence 或复现步骤 → HALT，不能请求用户验收，返回验证补齐实际结果证据。
</step>

<step id="step-4" n="4" goal="遗留项和后续">
 - 从以下来源收集遗留项：验证报告未通过/未覆盖的 AC、code-review 标记为可选（Low）的改进建议、execution-brief 标注的已知风险（实现中被验证为真实风险）、实现过程发现的新需求或改进机会。
 - 对每个遗留项给出：描述、严重性（必须后续处理 / 建议处理 / 可忽略）、建议处理方式。如存在后续任务需要，给出后续建议。
</step>

<step id="step-5" n="5" goal="生成 delivery-package.md">
 - 使用 `harness-runtime/templates/delivery-package.md` 模板结构，填充：交付摘要、验收状态（引用 acceptance-result.md，不重复作为用户验收物）、证据链接（指向验收结果 / 验证报告 / code-review 路径）、遗留项、下一步建议。写入 `harness-runtime/harness/stages/<mission-id>/delivery-package.md`。
 - 若 `contracts/delivery-package.contract.yaml` / `contracts/acceptance-result.contract.yaml` 不存在，调用 `harness contract init` 初始化；若已存在只能 patch。两份 md 的「控制契约」段只保留 `Contract:` 引用，禁止追加 fenced YAML contract。
</step>

<step id="step-6" n="6" goal="Work Graph 交付回流">
 - 读取 `lane_action.output_artifact`，确认 delivery-package 是本 action 的 stage artifact。acceptance-result.md 是用户验收 Checkpoint 产物，不是 delivery-package.md 的替代品；Gate / delivery evidence 必须同时记录 acceptance-result 路径、用户验收结论和 delivery-package 路径。
 - 若所有验收项通过，本 Mission Slice primary node 在 Gate PASS 后由 lane action graph operation 推进到 done。若存在必须后续处理的遗留项，交付文档声明 follow-up node 候选，Gate PASS 后由 `harness gate advance` 经 split_node / defer_node 把 follow-up 回流 Board。若存在阻断性遗留项且用户未接受风险，不得推进 primary node 到 done，记录 block_node graph operation intent 或返回修复阶段。delivery workflow 不直接编辑 Work Graph 派生视图。
</step>

<step id="step-7" n="7" goal="最终验收 Checkpoint">
 - 无论 AC 是否全部通过，都必须向用户展示 acceptance-result.md 摘要和交付入口。验收请求明确列出：一句话摘要、交付入口、AC expected vs actual 结果摘要、关键结果证据、阻断性遗留项和建议性遗留项。
 - 调用 tool: `AskUserQuestion`。
  - 问题：本次交付的验收请求，请确认
  - 候选答案：
     - 接受交付
     - 继续修复
     - 接受风险后交付（accepted_risk，需 risk_summary）
 - 条件：用户接受交付或接受风险后交付
  - 调用 cli `harness approval append` `--mission ${mission-id} --type checkpoint --stage acceptance-result --status approved`，evidence=required。
  - 更新 mission-status：checkpoints_passed 追加 acceptance-result。
 - 条件：用户要求继续修复
  - 根据用户反馈路由到 receiving-review / 执行 / bug-fix，修复后重新验证和交付。
</step>

<step id="step-8" n="8" goal="任务收尾 + handoff">
 - 调用 cli `harness delivery compute-conclusion` `--mission ${mission-id}`，evidence=required。
 - 得到 typed conclusion（delivered / continue_fix / blocked）。
 - 条件：conclusion=delivered（所有 AC 通过且无阻断性遗留项，Step 7 已取得用户验收）
  - 调用 cli `harness delivery handoff` `--mission ${mission-id} --pause`，evidence=required。
  - 调用 cli `harness mission stage complete` `--mission ${mission-id} --stage delivery`，evidence=required。
  - delivery 到此暂停。不自动调度 retrospective——finishing-branch / retrospective 入口由用户或 Board 在下一轮明确触发。
 - 条件：conclusion=delivered 但存在阻断性遗留项且用户在 Step 7 接受风险后交付
  - `harness delivery handoff --pause` 时 notes 记录 accepted risk 摘要（引用 approval id），再 `harness mission stage complete`。delivery 以 accepted risk 关闭并暂停，不自动调度 retrospective。
 - 条件：conclusion=continue_fix 或 blocked
  - 不得 stage complete；按 failure_paths 路由继续修复或发起 Decision Gate。
</step>

<step id="step-9" n="9" goal="Artifact Gate 自检">
 - 验证 acceptance-result.md 包含最小必要结构：交付入口、你要验收什么、结果验收清单、关键结果证据、未满足/无法验收、验收决定；每个 pass AC 有 expected / actual / 复现步骤 / 结果证据。
 - 验证 delivery-package.md 包含最小必要结构：交付摘要、验收状态、证据链接、遗留项、下一步建议、轻量 DORA 信号（lead time、rework count、review hold count、verification failure count、rollback/follow-up count）。验证最终验收已记录到 approvals.json；未记录时不得把 mission-status 置为完成。
 - 调用 cli `harness contract check` `--artifact harness-runtime/harness/stages/${mission-id}/delivery-package.md`，evidence=required。
 - 条件：结构不完整
  - 自行补充缺失部分，不要跳过。
</step>

<step id="step-10" n="10" goal="条件：交付包加入 Agent 能力产物">
 - 条件：agent_engineering.enabled=true
  - 参考 `docs/methodologies/agent-capability-engineering.md` §8（Agent 运维）。检查 tech-design.md 是否含 `## Agent 实现` 段落，检查是否存在 agent-eval-report.md。
  - 条件：存在 Agent 实现规格或 agent-eval-report.md
   - delivery-package.md 追加「Agent 能力产物」段：引用 solution.md `## Agent 架构` 和 tech-design.md `## Agent 实现`、引用 agent-eval-report.md 路径和整体结论、列各 Agent 组件行为分布通过状态、列制度层约束执行方式（policy/hook 路径）、说明可观测性接入方式；遗留项包含 Agent 能力已知限制。
</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `verify-evidence-missing` | verify command/result evidence 缺失 | 回 verify 补证据；delivery 不自行降级。 |
| `user-continue-fix-implementation-bug` | 用户 Step 7 选 continue_fix 且是实现缺陷 | 按 bug-fix protocol → execute → code-review → verify。 |
| `scope-adjust` | 用户要求调整 scope | 路由到 course-correction。 |
| `writing-issue` | 交付文档表达问题 | 路由到 receiving-review。 |
| `blocking-followup-not-accepted` | blocking follow-up 未接受 | 发起 Decision Gate；候选 create_graph_op / accept_as_advisory / halt_mission。 |
| `agent-capability-high-fail` | Agent 能力 High fail | 返回 execute / verify 修复；候选 return_to_execute / return_to_verify / accept_with_risk。 |
| `gate-fail` | harness gate run --stage delivery 返回 FAIL | delivery 内修复后重跑 gate。 |
| `handoff-pause-missing` | handoff pause evidence 缺失 | 停在 delivery，补 `harness delivery handoff --pause`。 |

</failure_paths>

Stage transition:

- Decided by: `control_plane.stage` from Mission Slice (Work Graph).
- Typical next:
  - `finishing-branch`：delivery 已暂停，用户 / Board 明确触发分支收尾
- Enforced by: cli=harness gate advance


</workflow>
