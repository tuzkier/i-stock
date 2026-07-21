# Stage Gate 工作流

**Goal:** 在当前 Mission Slice 的 stage artifact 完成后执行统一 Gate 检查，确定当前产物、角色 verdict、证据和 Work Graph operation 是否满足推进条件。

**Your Role:** 你是 Gate 检查员。你逐项检查，给出 PASS / FAIL / WARN，然后给出明确结论：可以继续 / 不能继续 / 需要人确认。

**关键原则：**
- 你只检查，不修复（除非是你能自动补的简单缺失）
- 检查结果必须是结构化的，方便自治循环判断
- 不同阶段的检查项不同，按需执行

---

## 初始化

1. 调用 `harness-cli` 执行 `harness frame current --mission <mission-id> --json`，从返回的 `mission_status` 和 `mission_slice` 确定当前任务、`control_plane.lane`、`control_plane.stage` 与刚完成的 action
2. 调用 `harness-cli` 执行 `harness config snapshot --json`，获取 `execution_governance` 与 `pre_checkpoint_doc_review` 配置；不得直接读取 `harness-runtime/config/harness.yaml`
3. 从 `work_graph.lanes.<lane>.stages[]` 确认当前 action 的 `output_artifact`、operation profile 和角色策略
4. 确定当前 action 产物路径，并准备通过 `harness-cli` 调用 `harness contract check`
5. 若产物或阶段状态提供 Evidence Graph slice，准备通过 `harness-cli` 调用 `harness evidence graph check`
6. 若阶段产生控制面报告（如 project-lint / E2E / TDD toolchain），准备通过 `harness-cli` 调用 `harness gate control-reports`

---

## 执行

<workflow skill="stage-gate" version="2">

<step n="1" goal="文档结构检查（Artifact Check）">

 对刚完成阶段的产出文档，检查是否存在且结构完整。

 **检查流程：**
 ```
 文档是否存在？
 ├── 否 → FAIL: missing_artifact
 └── 是 → 文档结构是否完整？
 ├── 否 → FAIL: artifact_invalid
 └── 是 → PASS
 ```

 **附加规则（刚完成阶段为 `prd` 且 `spec.enabled=true` 时）：**

 从 `harness config snapshot --json` 返回值读取 `spec.enabled`。若为 true，除 product/product-definition.md 本身外，还必须至少存在一个 `harness-runtime/harness/stages/<mission-id>/specs/<capability>/spec.md` 文件，且符合上表差量规格的最小结构要求。否则 FAIL: `missing_delta_spec`。

 这是整条规格链的启动点 Gate——prd 产差量规格是强制的（spec.enabled=true 时），拆解及之后的阶段都依赖它。

 **各文档最小结构要求：**

 | 文档 | 必须包含 |
 |------|---------|
 | `mission-contract.md` | objective、scope_in、scope_out、acceptance_criteria、autonomy_level（执行治理级别） |
 | `discovery-brief.md` | 问题空间摘要、用户角色画像、现有方案分析、关键发现、产品定义 输入建议 |
 | product/product-definition.md | Executive Summary、Success Criteria、Product 范围、User Journeys、Functional Requirements、Non-Functional Requirements、追溯矩阵 |
 | solution.md | 问题回顾、目标驱动设计、关键决策（如有）、适配性评估、所选路线与理由、影响面、风险 |
 | interaction.md | 核心流程、关键状态、异常场景 |
 | tech-design.md | 改动概述、模块级计划、接口变化、验证策略、生产就绪要求 |
 | execution-brief.md | 任务目标、关键约束、任务项、每个任务项的完成边界、实现要点、已知风险 |
 | 差量规格（`harness-runtime/harness/stages/<id>/specs/<capability>/spec.md`，仅 `spec.enabled=true`） | 头部任务/能力/Baseline；至少一个 `## ADDED/MODIFIED/REMOVED Requirements` 段非空；每个 Requirement 至少一个 `#### Scenario`（含 WHEN/THEN） |
 | `verification-report.md` | 验证目标、验证方法、验证结果、遗留问题 |
 | `acceptance-result.md` | 交付入口、你要验收什么、结果验收清单、关键结果证据、未满足/无法验收、验收决定 |
 | `delivery-package.md` | 交付摘要、验收状态、证据链接、遗留项、下一步建议 |
 | code-review.md | 评审摘要、发现列表（High/Med/Low）、正确性、TDD 有效性、设计一致性、安全与可靠性、评审结论 |
 | retrospective.md | 执行摘要、做得好的、发现的问题、根因分析、改进行动、更新 project-context.md |

</step>

<step n="2" goal="上游有效性检查（Upstream Validity）">

 检查当前阶段的产出是否与上游文档一致，不是空壳。

 | 检查项 | 方法 |
 |--------|------|
 | AC 引用一致 | 产出文档中引用的 AC 编号是否在任务契约中存在 |
 | 技术决策一致 | 产出文档中的技术选型是否与 tech-design 一致 |
 | 范围一致 | 产出文档的覆盖范围是否在 scope_in 内 |
 | 不是模板空壳 | 文档主体内容不全是模板占位符 |

 - 只检查与当前刚完成阶段直接相关的上游，不需要追溯全链

</step>

<step n="3" goal="控制契约 Integrity（programmatic Gate / 程序化 Gate）">

 - 通过 `harness-cli` 对需要 contract 的阶段产物调用程序化 checker。优先传入外部 contract YAML；若传入 Markdown，Markdown 必须只包含 `Contract: ...` 引用，checker 会跳转到该 YAML：

 ```bash
 harness contract check \
   --artifact <contract-yaml-path> \
   --json
 ```

 - Hard gate：运行时 Stage Gate 调用不得传 `--allow-placeholders`。如果 contract YAML 仍含 `{{...}}` 或 `<...>` 占位符，checker 必须 FAIL。Markdown 内嵌 `control_contract` 不再是合法运行时契约来源。

 **需要控制契约的 v1 产物：**

 | action / stage | 人读产物 | 程序化 contract |
 |------------|----------|----------|
 | 任务契约 / 任务接入 | `harness-runtime/harness/missions/<mission-id>/mission-contract.md` | `harness-runtime/harness/missions/<mission-id>/contracts/mission-contract.contract.yaml` |
 | prd | `harness-runtime/harness/stages/<mission-id>/product/product-definition.md` | `harness-runtime/harness/stages/<mission-id>/contracts/prd.contract.yaml` |
 | 差量规格 | `harness-runtime/harness/stages/<mission-id>/specs/<capability>/spec.md` | `harness-runtime/harness/stages/<mission-id>/specs/<capability>/spec.contract.yaml` |
 | solution / 方案设计 | `harness-runtime/harness/stages/<mission-id>/solution.md` | `harness-runtime/harness/stages/<mission-id>/contracts/solution.contract.yaml` |
 | tech-design / 技术设计 | `harness-runtime/harness/stages/<mission-id>/tech-design.md` | `harness-runtime/harness/stages/<mission-id>/contracts/tech-design.contract.yaml` |
 | interaction / 交互设计 | `harness-runtime/harness/stages/<mission-id>/interaction.md` | `harness-runtime/harness/stages/<mission-id>/contracts/interaction.contract.yaml` |
 | execution-brief / 拆解 | `harness-runtime/harness/stages/<mission-id>/execution-brief.md` | `harness-runtime/harness/stages/<mission-id>/contracts/execution-brief.contract.yaml` |
 | code-review | `harness-runtime/harness/stages/<mission-id>/code-review.md` | `harness-runtime/harness/stages/<mission-id>/contracts/code-review.contract.yaml` |
 | verification / 验证 | `harness-runtime/harness/stages/<mission-id>/verification-report.md` | `harness-runtime/harness/stages/<mission-id>/contracts/verification-report.contract.yaml` |

 **判定规则：**
 - checker 返回 FAIL → Stage Gate 不能推进；AI 只能解释原因、提出修复 / 回退 / Decision Gate，不得覆盖 FAIL
 - checker 返回 WARN → 可以继续，但必须在报告中写明风险和后续处理
 - checker 返回 PASS → 继续后续 Gate
 - evidence 缺口 / WARN / FAIL 的质量分类参考 `.harness/common/protocols/quality-control/PROTOCOL.md`

 **contract-Specific evidence 语义：**
 - Intent / Behaviour：只检查 ID、字段、引用关系；不检查实现证据
 - Action：检查 `required_evidence`；`test_obligation` 显式声明优先，缺失时由 Harness policy 推导并记录 WARN，无法推导才 FAIL；不要求 evidence 已产生
 - 审查证据：检查审查员 verdict、role boundary、审查 basis、toolchain status 产物和 TDD adequacy matrix；并读取真实 `toolchain-status.json` 校验 status / missing_capabilities / decision_gate_reasons 一致性；不替代审查员专家判断
 - 验证 Evidence：检查 pass AC 同时引用 command evidence 与 result evidence；阻塞 AC 必须有原因、影响、下一步

 **Professional Roles 覆盖硬规则：**
- 若 Control Contract 声明 `role_policy.required_execution_roles`，必须存在 `execution_result`（单执行者 legacy）或 `execution_results[]`（多执行者），且每个 required execution role 都必须有对应 result；不得只用一个执行者结果代表整个角色集合
- 若 Control Contract 声明 `role_policy.required_review_roles`，必须存在对应 `role_verdicts` / legacy `reviewers` verdict
- 若任一 `obligations[].required_roles` 声明审查角色，该角色必须在 `role_verdicts` 中审查对应 obligation
- 专家缺席是 Stage Gate FAIL，不能由主 Agent 的自检、脚本 PASS、或 Markdown 审查摘要替代

 **Skip stage 与 required roles 的仲裁：**
- 阶段在 `execution_governance.levels.<autonomy_level>.skippable_stages` 中 ≠ 自动免除 reviewer。
- 跳过阶段的合法路径只有一种：**整个阶段不产生 output_artifact，Mission Slice 直接跳到下一个 lane_action**。此时本阶段无 contract、无 evidence、无 role_verdicts，Stage Gate **根本不为该阶段触发**。
- 一旦本阶段产出了 `output_artifact`（即使 mission 在 skippable_stages 中），Stage Gate **必须按 stage_policies 完整校验 required_execution_roles 与 required_review_roles**——`skippable_stages` 不允许"产物存在但 reviewer 缺席就 PASS"。
- 若用户希望"跳过阶段但保留产物"作为降级路径，必须经 `harness approval append --type tradeoff --status approved` 显式记录，并在 contract 的 `role_verdicts` 标注 `accepted_by_user=true`；Stage Gate 看到该 approval 才允许 PASS。
 - 若 Control Contract 声明 `role_policy.work_graph_lane`，Stage Gate 必须用 `work_graph.lanes` 注册表解析该 lane/stage 的角色集合。
 - checker 必须校验 contract.stage、role_policy.work_graph_lane、work_graph primary node、lane_action、output_artifact 与 `harness-runtime/harness/work-graph/mission-slices/<mission-id>.yaml` 和 `work_graph.lanes` 一致
 - TASK node 进入 execute / code-review / verify / delivery 完成链路时，checker 必须校验 node `specs.consumes` 引用 Scenario，并包含 implementation / test evidence 引用
 - 若当前 primary node 声明 `conflicts_with` / `duplicates`，必须存在 Decision Gate 记录；普通方案决策不等于 Decision Gate
 - 若 contract 把 `harness-runtime/harness/work-graph/artifacts/**` 作为正式 upstream，Stage Gate 必须确认该 artifact 的 `artifact_state.status=accepted`

 - 若当前产物包含 `evidence_graph`，或阶段目录已生成 `evidence-graph.json` / `evidence-graph.yaml`，继续通过 `harness-cli` 调用 Evidence Graph checker：

 ```bash
 harness evidence graph check \
   --graph <evidence-graph-path> \
   --json
 ```

 **Evidence Graph 硬规则：**
 - blocking obligation 缺少 required evidence → FAIL
 - evidence path 不存在或 git_ref 与当前交付上下文不一致 → FAIL
 - role_verdict 引用未知 obligation → FAIL
 - role verdict 为 HOLD / BLOCKED 且无 blocking_gaps → FAIL
 - tool evidence 为 FAIL 时，专业角色 PASS 不能覆盖程序化 FAIL
 - PASS_WITH_RISK / accepted risk 必须引用用户 Decision Gate 记录

</step>

<step n="4" goal="环境就绪检查（Environment Readiness）">

 仅在当前 Mission Slice 的目标 lane action 需要环境时检查。

 - 条件：当前 lane action / 是执行或 git-workflow 操作
 | 检查项 | 方法 | 级别 |
 |--------|------|------|
 | Git 可用 | `git --version` | FAIL（如果 git-workflow 未降级） |
 | 在 Git 仓库内 | `git rev-parse --is-inside-work-tree` | WARN |
 | 依赖已安装 | 检查 node_modules / venv / vendor 等 | WARN |
 | 测试框架就绪 | 能否运行测试命令（dry-run 或检查配置） | WARN |

 - 条件：当前 lane action / 是其他规划或文档 action
 - 跳过环境检查

</step>

<step n="5" goal="实现质量检查（质量就绪度）">

 仅在当前完成的 action 是实现时检查。

 | 检查项 | 方法 | 级别 |
 |--------|------|------|
 | 所有任务项标记完成 | execution-brief 中的任务项状态全部为完成 | FAIL |
 | 测试通过 | 运行测试命令，全部通过 | FAIL |
 | 控制面报告允许推进 | 通过 `harness-cli` 调用 `harness gate control-reports` 读取 project-lint / E2E / TDD 等 report 的 `gate_effect`；任一 `block` 时不能推进 | FAIL |
 | 无编译/类型错误 | 运行 lint 或 type check | WARN |
 | 无未提交的变更 | `git status` 干净 | WARN |

 - 控制面报告由各控制面自行生成事实和 `gate_effect`；Stage Gate 通过 `harness-cli` 消费 verdict，不重新判断具体规则。

 ```bash
 harness gate control-reports \
   --mission <mission-id> \
   --json
 ```

</step>

<step n="6" goal="Checkpoint 与文档审查状态判断">

- 确定本阶段是否需要人工 Checkpoint，优先级如下：
 1. mission-contract 的 `required_checkpoints`
 2. `harness.yaml` 的 `execution_governance.levels.<autonomy_level>.human_checkpoints`

 - 若 `autonomy_level` 是 `A1` / `A2` / `A3` 等旧值，先按 `execution_governance.legacy_level_aliases` 归一化到新治理级别；若无法归一化或找不到对应 `levels` 配置，本 Gate 返回 BLOCKED。
 - 同时读取当前治理级别的 `reviewer_pass_sufficient`：若 `control_plane.stage` 在其中，且专业 reviewer PASS、Stage Gate 无 FAIL，则可自动继续；若命中 `human_checkpoints`，仍必须暂停给人确认。
 - Checkpoint 和 reviewer-pass 判断以 `control_plane.lane` / `control_plane.stage` 和当前 `lane_action` 的组合为边界，不推导目标阶段。
 - 若当前 Mission Slice 含 `lane_action`，其 `lane`、`stage`、默认 `graph_operation`、由 `operation_profiles` 推导的 `allowed_graph_operations`、`output_artifact` 必须与 `harness-runtime/config/harness.yaml` 的 `work_graph.lanes` 当前注册表一致；Stage Gate 还必须用注册表校验 `operation`、child/target kind 和默认目标 lane 是否符合 profile。不一致时 Gate BLOCKED，避免 Board Router、阶段 skill、CLI 和 Stage Gate 分叉。

 - 条件：Checkpoint 为 true
 - 条件：pre_checkpoint_doc_review为 true
 - 结论增加：若本阶段产出为需经专业 reviewer 审查的规划文档（如 prd、solution、tech-design），应已在对应阶段技能的工作流中完成阶段专业 reviewer「审查-修复循环」；文档末尾只保留面向人的审查摘要，结构化 `role_verdicts` 必须由主流程写入外部 contract YAML 或等效可追溯控制面后再进入 Checkpoint
 - 结论增加：需要 Checkpoint（暂停请用户确认）

 - 条件：Checkpoint 为 false
 - 无需人工确认；若 reviewer / contract / evidence / quality 检查均通过，可以直接继续

</step>

<step n="7" goal="输出 Gate 报告">

 - 汇总所有检查结果，输出结构化报告：
 - 在调用 `harness gate run` 前，先**计算 AI Interpretation**：一段简短文字，说明本次 Gate 决策为什么允许 continue（或 pause/block）。重点写：哪些 reviewer / contract / evidence / control report 通过、哪些被裁定为可接受风险、降级或人工 checkpoint 状态。把这段话作为 `--ai-interpretation "<text>"` 传给 `gate run`；只有像"自动重跑、决策未变"这种确实无新信息可写的情况，才使用 `--no-interpretation "<reason>"` 显式说明跳过原因，不得让 Gate 报告留空。
 - 优先通过 `harness-cli` 调用 `harness gate run`，输入 `harness contract check --json` 输出、当前 Gate 元数据、当前 Mission Slice 路径以及上一步算出的 `--ai-interpretation`，产出：
 - `harness-runtime/harness/state/gate-reports/<mission-id>/<stage>__<operation>.json`
 - `harness-runtime/harness/state/gate-reports/<mission-id>/<stage>__<operation>.md`

 ```
 ## Stage Gate 报告

 **Stage:** <control_plane.stage>
 **Operation:** <graph_operation>
 **Mission:** <mission-id>

 ### Artifact Check
 [PASS] product/product-definition.md — 结构完整
 ...

 ### Upstream Validity
 [PASS] AC 引用一致
 ...

 ### Programmatic Contract Check
 [PASS/FAIL/WARN] check_contracts.py — <摘要>

 ### Work Graph
 Mission Slice、primary node、lane、stage、operation 摘要

 ### AI Interpretation
 程序化结果不可被 AI 覆盖。这里仅解释 FAIL/WARN 的可能原因、修复路径、是否需要 Decision Gate / accepted risk。

 ### Environment Readiness
 [PASS] Git 可用
 [WARN] 依赖未安装 — 建议先运行 npm install
 ...

 ### Quality Readiness
 [PASS] 所有 Task 完成
 [PASS] 测试全绿
 ...

 ### Gate Decision
 结论：[可以继续 / 不能继续 / 需要人确认]
 原因：...
 下一步：...
 ```

 **判定规则：**
 - Contract checker 存在任何 FAIL → **不能继续**，除非 Decision Gate 记录 accepted risk；accepted risk 不能把程序化事实改写为 PASS
 - 存在任何 FAIL → **不能继续**，列出需要修复的项
 - 只有 WARN → **可以继续**，但在报告中标注风险
 - 命中 `human_checkpoints` / `required_checkpoints` → **需要人确认**
 - 全部 PASS → **可以继续**

</step>

<step n="8" goal="Work Graph 推进（Gate PASS 后）">

 - 条件：Gate Decision 为 `continue`
 - 调用 `harness-cli` 执行 `harness gate advance --mission <mission-id> --gate-report <gate-report.json> --json`；若当前阶段 contract 含 `work_graph_artifact`，同时传入 `--contract-artifact`。
 - `harness` PATH、安装后 shim、源码/安装后 Python CLI 的入口解析统一由 `harness-cli` 处理。所有入口都不可用时 Gate BLOCKED，不得手工改 board / index / tree。
 - CLI 读取 `harness-runtime/harness/work-graph/mission-slices/<mission-id>.yaml`，校验 Gate stage 与 Mission Slice stage 一致，并要求 Mission Slice `operation`、显式 `graph_operation.type`、child/target kind 和目标 lane 都符合当前 lane action 的 `operation_profiles`；通过后生成 graph operation manifest，再调用 Work Graph 控制面更新 node、promotion canonical artifact，并重建 board/index/tree。Mission Slice 可携带 `graph_operation` payload 以应用 split / merge / block / defer / supersede / batch。
 - 若 contract 的 `work_graph_artifact.supplementary_artifacts` 声明补充产物包，Gate advance 必须把这些补充产物与主 canonical artifact 一起 promotion，并写入 node `artifact.supplementary_artifacts`；后续阶段不得只读取未被接受的 stage 目录旁路产物。
 - 若当前阶段是 prd 且 `spec.enabled=true`，Gate advance 必须把 `specs/<capability>/spec.md` 差量规格作为 产品定义 产物包的一部分绑定到 Work Graph；否则 breakdown / execute / code-review 不得消费该差量规格。
 - 若当前阶段是 interaction，Gate advance 必须把 `interaction-spec/`、`visual-interaction/` manifest 与资产作为 interaction 产物包的一部分绑定到 Work Graph；否则 execute / e2e-review 不得把这些资产视为已接受依据。下游 AI 以 `interaction-spec/` 为实现合同，`visual-interaction/prototype/index.html` 是唯一默认人类确认入口。
 - 若当前阶段是 breakdown 且 contract 声明 `atomic_task_queue.required=true`，Gate advance 生成 / 更新 TASK nodes 时必须把 `atomic_task_queue.artifact` 指向的 `execution-brief.md` 与 `Execution Units` 中对应 Parent task 的 `atomic_task_queue:` 绑定为该 TASK node 的执行单位；否则下一 execute Mission Slice 不得开始。
 - 若当前阶段是 delivery，Gate advance 前必须确认 `acceptance-result.md` 已作为用户验收 Checkpoint 产物记录，且 `delivery-package.md` 只作为内部归档；不得只因 delivery-package 存在就把 primary node 推进到 done。
 - 推进成功后，CLI 回写 `mission-status.yaml` 的 `work_graph.last_gate_report`、`last_operation_manifest`、`last_operation_status`，并把本次 Mission Slice 的 `control_plane.stage` 标记为 done。
 - Hard gate：Stage Gate 或主 Agent 不得直接编辑 board / index / tree；Gate 未 `continue` 时不得应用 graph operation。

</step>

</workflow>

---

## 触发时机

自治循环在当前 Mission Slice 的 stage artifact 完成后（Step 5 验证），调度 Stage Gate 进行产物与 Work Graph operation 检查。

不是每轮对话都跑，只在当前 Mission Slice 的 stage artifact 完成、准备应用 Work Graph operation 时触发。
