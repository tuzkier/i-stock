# 验证工作流

> **行为约束（铁律、禁用词、验证门控、反合理化）见 `SKILL.md`，不在此重复。**
> **方法论参考**：`.harness/docs/methodology-reference.md` §10（Test Pyramid；Testing Trophy；Contract Testing；Property-Based Testing）§12（USE Method；RED Method）

所有 CLI 调用通过 harness-cli skill（`--json` 模式）。

<workflow stage="verify" version="2">

<goal>
  对 execute / code-review 的产物逐条 AC 做 expected vs actual 验证，收集 command + result 双证据，产出 verification-report.md + verification-report.contract.yaml 和 PASS/FAIL/BLOCKED/PASS_WITH_RISK 四态结论。
</goal>

<role>
  你是验证编排者。你调度 verification-engineer 收集证据、调度 verification-effectiveness-reviewer 审查证据充分性、把每条 AC 绑定 command + result evidence，不把测试通过等同于 AC 通过，不在 verify 内直接改实现文件。
</role>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `report-contract-via-cli` | verification-report.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness contract init/patch | hook=verify-check-contract-via-cli |
| `report-not-fenced` | verification-report.md 不得内嵌 fenced YAML evidence_contract / execution_result / role_verdicts 段 | hook=harness-lint |
| `required-evidence-id-from-upstream` | command_evidence/result_evidence 的 required_evidence_id 必须引用 breakdown execution-brief required_evidence[].id，verify 不自创 | hook=verify-check-evidence-id-referenced |
| `reviewer-readonly` | verification-effectiveness-reviewer 必须在 readonly subagent 中调用 | registry=subagents/verification-effectiveness-reviewer[readonly=true] |
| `no-impl-edit-in-verify` | verify 阶段不直接修改实现文件 / 测试文件，失败路径回流 bug-fix / execute | hard_gate=failure-path-routing |
| `true-e2e-primary-evidence` | UI AC pass 必须有真实浏览器路径 primary result evidence；API/mock/DB/internal state 只能作为 setup 或 cross_check 辅助证据 | cli=harness verify true-e2e-check |

</invariants>

<entry>
  - execute / code-review 已完成，对应产物通过 Stage Gate
  - Mission Slice control_plane.stage=verify
</entry>

<exit>
  - `report-written`: verification-report.md 写入 verify stage worktree
  - `contract-filled`: verification-report.contract.yaml 已填充且 harness contract check PASS
  - `ac-trace-complete`: 每条 pass AC 同时引用 command evidence + result evidence；阻塞 AC 含原因/影响/下一步
  - `reviewer-pass`: verification-effectiveness-reviewer 已审查证据充分性
  - `gate-pass`: harness verify gate run 返回 status=pass
</exit>

<permissions>

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Edit(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Write(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Edit(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/stages/*/contracts/verification-report.contract.yaml)` | contract 必须经 harness contract init/patch |
| deny | `Edit(harness-runtime/harness/stages/*/contracts/verification-report.contract.yaml)` | contract 必须经 harness contract patch |
| deny | `Edit(harness-runtime/config/harness.yaml)` | 配置只读 |
| deny | `Edit(harness-runtime/config/model-routing.yaml)` | 配置只读 |
| allow | `Write(harness-runtime/harness/stages/*/verification-report.md)` | verify 主产物 |
| allow | `Edit(harness-runtime/harness/stages/*/verification-report.md)` | verify 主产物 |
| allow | `Bash(harness *)` | verify CLI 必需 |

</permissions>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `verification-engineer` | spawn | harness-runtime/harness/stages/${mission-id}/verification-report.md | `.harness/common/agents/verification-engineer.md` |
| `verification-effectiveness-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/verification-effectiveness-reviewer.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `mission-contract.md` | true | Intent |
| `execution-brief.md` | true | Memory |
| `code-review.md` | conditional: code-review 已完成 | Memory |
| `project-context.md` | conditional: brownfield | Context |
| `harness.yaml` | true via harness config snapshot | Memory |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `verification-report-md` | `harness-runtime/harness/stages/${mission-id}/verification-report.md` | markdown | Memory |
| `verification-report-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/verification-report.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |

</outputs>

<steps>

<step id="step-0" n="0" goal="阶段进入 + Trace 初始化 + 验证范围预计算">
 - CLI-first preflight（verify / continue / status 场景）：调用 `harness control status --json`、`harness control candidates --intent continue --json`；显式确定 mission 后再 `harness control frame --json`、`harness control guidance --json`、`harness control context-index --mission ${mission-id} --json`；guidance 指向缺 artifact / review / gate / approval 时先处理；临时读旧文件记录 fallback_used / fallback_reason / legacy_source / follow_up。
 - 读取 mission-contract.md（验收标准）、execution-brief.md（任务项清单 + 变更文件 + required_evidence 三元组）、code-review.md（如存在，findings 状态）、project-context.md（测试约定，调 `harness context check`），并调用 `harness knowledge resolve --stage verify --json` 获取 specs、testing patterns、verification runbooks 和 lessons。
 - 调用 cli `harness mission stage start` `--stage verify --mission ${mission-id}`，evidence=required。
 - 调用 cli `harness trace log-init` `--mission ${mission-id} --stage verify`，evidence=required。
 - 调用 cli `harness verify compute-scope` `--mission ${mission-id}`，evidence=required。
 - 消费 compute-scope 返回的 ac_list / task_list / test_layers / e2e_obligations / project_lint_enabled / required_evidence_matrix。required_evidence_matrix 是从 execution-brief 透传的 breakdown required_evidence 三元组，是 command_evidence / result_evidence required_evidence_id 的主键查表基准；verify 不自创 required_evidence_id。
 - 检查 compute-scope 返回的 execute_failure_ref；若 execute 已 FAIL（stop_event 命中 / authorized_paths 越界 / command_evidence.result=fail），直接进入 failure_paths 的 blocked-execute-failure 路径，不重跑双证据校验。
 - **frontend_engineering 路线感知**：如果 `harness config snapshot` 的 `prototype.delivery_mode=frontend_engineering`：
   - 读取上游 `contracts/prototype-as-frontend.contract.yaml`（interaction stage 产物）的 `e2e_locator_obligations[]` 和 `api_contract_draft.endpoints[]` 作为验证范围基线。
   - 本阶段是该路线下"真后端 e2e + AC 验证"的统一落地点（interaction stage 只做 walkthrough，没跑过 e2e against 真后端）。
   - Playwright e2e **必须 against 真后端**跑（不是 against MSW）；MSW 在本阶段不作为证据。
   - 每个 user path 的 e2e 至少要命中一个 locator obligation；缺失即 AC 未充分验证。
   - 上游 contract 的 `downstream_handoff.verify[]` 段作为 required_evidence 清单。
</step>

<step id="step-1" n="1" goal="专业角色调度">
 - 调用 cli `harness verify dispatch-worker` `--mission ${mission-id}`，evidence=required。
 通过 `Task(subagent_type="verification-engineer", prompt=<Task Envelope>)` 工具调用 `verification-engineer` subagent
 - brief：Mission Contract AC、Execution Brief evidence obligations（含 required_evidence 三元组）、Code Review evidence、命令/结果证据路径；外部 contract 必须写入 execution_result；command_evidence[].required_evidence_id 和 result_evidence[].required_evidence_id 必须引用 breakdown required_evidence[].id，不自创 ID。
 - 调用 cli `harness verify dispatch-reviewer` `--mission ${mission-id}`，evidence=required。
 通过 `Task(subagent_type="verification-effectiveness-reviewer", prompt=<Task Envelope>)` 工具调用 `verification-effectiveness-reviewer` subagent
 - brief：verification-report 路径、外部 verification contract 路径、command evidence 路径、result evidence 路径、AC trace、Evidence Graph slice 路径；拒绝 main_agent_fallback 自动 PASS；审查结论由 reviewer 返回 role_verdict，主流程经 `harness contract add-verdict` 写入 role_verdicts。
</step>

<step id="step-2" n="2" goal="识别验证范围">
 - 以 Step 0 compute-scope 返回的 ac_list / task_list / test_layers 为权威输入，补充人工解释。确认测试层级：单元（`harness verify run-tests --layer unit`）、集成（`--layer integration`）、E2E（`harness verify e2e-status`）。project-context 无测试命令时检测项目测试框架推导命令。
 - 条件：e2e.enabled=true
  - 检查 execution-brief 是否存在显式 e2e_obligation；缺失则由 E2E resolver 根据 AC / UI surface / risk / 变更文件 / 历史 tests/e2e/ 推导并在 e2e-plan.json 标 obligation_source / inferred_fields。检查 code-review.md 是否已引用 e2e_status.status_artifact；已引用则优先读同一路径校验状态，不重新解释审查员 verdict。无 UI 变更任务项时允许 E2E 义务结论为 N/A，但必须由 e2e-status.json 记录 N/A / no_ui_scope 原因。
 - 条件：e2e.enabled=false
  - 调用 tool: `AskUserQuestion`。
   - 问题：e2e.enabled=false：E2E 已关闭，请确认接受此风险
   - 候选答案：
      - 接受关闭 E2E（写 approval_id 后继续）
      - 重新开启 E2E（返回执行 harness verify e2e-status）
  - 无 approval 时不得通过；调 `harness approval append --mission <id> --type checkpoint --stage verify --reason "e2e.enabled=false accepted"` 记录用户接受。
</step>

<step id="step-3" n="3" goal="运行测试并收集证据">
 - 调用 cli `harness verify run-tests` `--mission ${mission-id} --layer unit --command ${cmd}`，evidence=required。
 - 调用 cli `harness verify run-tests` `--mission ${mission-id} --layer integration --command ${cmd}`，evidence=required。
 - 所有测试必须通过 `harness verify run-tests` 或 `harness evidence command collect`，禁止绕开 collector 直接汇总。若 project_lint.enabled=true，在 command evidence 生成后运行 `harness lint project --mission <id> --command-evidence <path>`；gate_effect=block 是项目约束缺口，不得口头改写为 PASS。
 - 记录每轮测试：运行命令、cwd、started_at、ended_at、exit code、通过/失败数、失败原始错误输出、覆盖率（如工具支持）。
 - 条件：存在测试失败
  - 分析失败原因：实现缺陷 → 记录失败点继续收集完整证据，调 `harness verify failure-path --kind bug_fix`，按 bug-fix PROTOCOL 路由 bug-fix → execute → code-review → verify，不在 verify 内改实现文件；测试本身问题（环境/配置）→ 记为验证障碍，修复后重跑。
 - 条件：e2e.enabled=true
  - 调用 cli `harness verify e2e-status` `--mission ${mission-id}`，evidence=required。
  - 消费 status / obligations / runs / artifacts / missing_capabilities / decision_gate_reasons。e2e-status FAIL → 工具/报告/产物缺口返回执行或 code-review 补齐，真实用户结果不符返回执行修复，受影响 AC 不得通过；WARN → 记录缺失能力 / flaky_signals / skipped_tests，影响 P0/P1 AC 时按 quality-control Hard Gate 处理；PASS → 引用 runs/artifacts 作为 E2E evidence 来源，仍需 AC 追溯证明 expected/actual 匹配。
  - 条件：e2e-status.json.status 为 BLOCKED
   - 调用 tool: `AskUserQuestion`。
    - 问题：E2E 状态为 BLOCKED，请选择处理方式
    - 候选答案：
       - 接受受限验证（标 PASS_WITH_RISK，需 approval_id）
       - 回 code-review 补 E2E 事实包
       - 回 execute 修复测试环境
   - 发起 Decision Gate：引用 decision_gate_reasons / 受影响 obligations / 缺失产物 / 下一步选项；E2E 章节写 BLOCKED，相关 AC ac_trace 写 blocked_reason / impact / next_step。
</step>

<step id="step-4" n="4" goal="对齐验收标准">
 - 逐条比对 AC 与测试证据（AC 编号 / 描述 / 单元集成证据 / E2E 场景覆盖 / E2E 证据 / 结论）。涉及 UI 的 AC E2E result evidence 是必要的，不能仅凭单元测试通过、API 响应、mock response、DB check、internal state check 或 e2e-status PASS 通过。
 - 为每条 AC 提取「预期结果」（来自任务契约 Given/When/Then 或量化指标）和「实际观察结果」（来自一次真实运行 / 截图 / 录屏 / API 响应 / CLI 输出 / 数据状态 / 文件 diff 摘要）。
 - 调用 cli `harness contract check-ac-trace` `--mission ${mission-id} --artifact harness-runtime/harness/stages/${mission-id}/contracts/verification-report.contract.yaml --upstream harness-runtime/harness/stages/${mission-id}/contracts/execution-brief.contract.yaml`，evidence=required。
 - 校验每条 pass AC 同时引用 command + result evidence、UI AC 有 screenshot/video/dom、每条 evidence 的 required_evidence_id 在 execution-brief required_evidence 中有对应 id；FAIL 必须修复，不得降级 PASS_WITH_RISK。
 - 调用 cli `harness verify true-e2e-check` `--mission ${mission-id}`，evidence=required。
 - true-e2e-check 校验 UI AC 的 primary evidence kind 只能是 dom / dom_snapshot / screenshot / video / trace / accessibility_snapshot；API evidence 只能标记 setup 或 cross_check；mock 必须有 API contract / fixture parity evidence。无法自动化真实用户路径时必须记录 Decision Gate 或 accepted risk，不能静默降级。
 - 调用 cli `harness alignment check` `--mission ${mission-id} --stage verify`，evidence=required。
 - alignment check 校验 AC evidence 回溯到 execution-brief、interaction-spec、domain model 和 mission contract；程序化 FAIL 必须修复或回上游阶段。
 - AC 标记 pass 必须同时满足：至少一个 command evidence 证明检查已运行、至少一个 result evidence 证明用户可观察结果符合预期、expected 与 actual 语义逐项匹配。按交付类型收集结果证据（UI/浏览器、API、CLI/脚本、数据/后台任务、文档/配置）。没有自动化测试覆盖的 AC 说明手动验证步骤和结果；未能验证的 AC 明确标注原因。每条 AC 结论写入 ac_trace；pass 引用 ≥1 command + ≥1 result evidence ID；阻塞写 blocked_reason / impact / next_step。
 - 条件：AC 证据不足或 evidence 缺口影响交付判断
  - 读取 `.harness/common/protocols/quality-control/PROTOCOL.md`，将缺口分类 Hard Gate / Soft Gate / Observation；Hard Gate 不得继续。
 - 条件：code-review.md 存在未 fixed / accepted_risk 的 high finding
  - 调用 tool: `AskUserQuestion`。
   - 问题：code-review 存在未关闭的 High finding，请选择
   - 候选答案：
      - 回 receiving-review（默认）
      - 接受风险（需 approval_id 记录）
      - 回 execute 修复
  - 结论不得为通过；按用户选择走对应 failure path；无用户决策时默认路由到 receiving_review。
</step>

<step id="step-5" n="5" goal="生成 verification-report.md">
 - 使用 `harness-runtime/templates/verification-report.md` 模板结构，按 Verification Evidence Contract（验证证据契约）填充。若 `contracts/verification-report.contract.yaml` 不存在，调用 `harness contract init --mission <id> --stage verify --template verification-report --json` 初始化；control_contract.type=evidence_contract、subtype=verification_evidence，Verification Evidence Contract 含 command_evidence / result_evidence / ac_trace / nfr_trace。
 - result_evidence[] 记录 expected / actual / reproduce / 产物 / result；command_evidence[].artifact 指向 evidence store JSON；command_evidence[].required_evidence_id 和 result_evidence[].required_evidence_id 引用 breakdown execution-brief.contract.yaml.tasks[].required_evidence[].id，不自创。
 - 填充章节：验证目标 / 验证方法 / 验证结果（AC 对齐表 + 测试统计 + expected/actual 对照）/ E2E 验证结果（引用 e2e-status.json、E2E 统计、场景 AC 对齐、html report、追溯/video/screenshot、N/A 原因、BLOCKED Decision Gate 记录）/ 未覆盖范围 / 遗留问题。verification-report.md 的「控制契约」段只保留 `Contract:` 引用，禁止追加 fenced YAML contract。
 - 写入 `harness-runtime/harness/stages/<mission-id>/verification-report.md`；将验证 evidence contract 字段、execution_result、role_verdicts 经 harness-cli 写入外部 contract。
 - 调用 cli `harness verify detect-contradictions` `--mission ${mission-id} --artifact harness-runtime/harness/stages/${mission-id}/contracts/verification-report.contract.yaml`，evidence=required。
 - 检测 ac_trace.conclusion 与 command/result/e2e/role_verdict 的结构矛盾（如 command_evidence.result=fail 但 AC pass）；FAIL 时必须修复，不自动降级。
</step>

<step id="step-6" n="6" goal="验证结论与后续">
 - 调用 cli `harness verify compute-conclusion` `--mission ${mission-id}`，evidence=required。
 - 返回 PASS / FAIL / BLOCKED / PASS_WITH_RISK 四态结论和 failure_path。
 - 分支：结论
  - 情况：PASS
   - 可以进入 Stage Gate；Gate PASS 后由 lane action graph operation 推进 delivery lane。
  - 情况：PASS_WITH_RISK
   - 调用 tool: `AskUserQuestion`。
    - 问题：验证结论为 PASS_WITH_RISK，存在未关闭 residual risk，请确认是否接受
    - 候选答案：
       - 接受 residual risk（写 approval_id）
       - 不接受，返回对应 failure path 修复
   - 无 approval 时 compute-conclusion 不能返回 PASS_WITH_RISK；调 `harness approval append --type risk --stage verify` 记录用户接受。
  - 情况：FAIL
   - 调 `harness verify failure-path --kind <bug_fix|execute>`；列需修复 AC 清单；返回执行技能修复后重新运行验证；不在 verify 内改实现文件。
  - 情况：BLOCKED
   - 调用 tool: `AskUserQuestion`。
    - 问题：验证结论为 BLOCKED，请选择处理方式
    - 候选答案：
       - 接受当前范围风险（需 approval_id）
       - 补环境后重跑
       - 缩小交付范围（回 execute 更新任务项）
   - 调 `harness verify failure-path --kind decision_gate`；发起 Decision Gate 让用户决定是否接受当前验证范围。
</step>

<step id="step-7" n="7" goal="Artifact Gate 自检">
 - 验证 verification-report.md 包含最小必要结构：验证目标 / 验证方法 / 验证结果 / 遗留问题；前部含 `Contract:` 引用且不含 fenced YAML contract / ## evidence_contract / ## execution_result / ## role_verdicts。
 - 验证外部 contract 包含验证证据契约，所有 pass AC 同时引用 command + result evidence；阻塞 AC 都含原因/影响/下一步。验证 E2E 验证结果章节已按实际填写。
 - 调用 cli `harness verify gate run` `--mission ${mission-id}`，evidence=required。
 - gate run 内部聚合 contract check-ac-trace、verify true-e2e-check、verify detect-contradictions 和通用 gate run，输出 typed failed_checks；程序化 FAIL 必须修复后再进入交付。
 - 条件：结构不完整
  - 自行补充缺失部分，不要跳过。
</step>

<step id="step-8" n="8" goal="条件：执行 agent-eval 技能">
 - 条件：agent_engineering.require_agent_eval=true
  - 调用 cli `harness verify agent-eval-status` `--mission ${mission-id}`，evidence=required。
  - 参考 `docs/methodologies/agent-capability-engineering.md` §7。确认 tech-design.md `## Agent 实现` 声明的 Agent 组件均已实现且 execution-brief 对应 Agent 任务项全部打钩。
  - 条件：tech-design.md 存在 Agent 实现规格且 Agent 实现完成
   - 调用 skill `agent-eval` `mission=${mission-id}`。
   - 分支：eval 结论
    - 情况：全部通过
     - verification-report.md Agent 行为验证段填写：通过，引用 eval 报告路径。
    - 情况：有能力未达标（High 严重性）
     - verification-report.md 记录 agent-eval 未通过 + 失败列表；调 `harness verify failure-path --kind execute` 返回执行修复后重新运行验证。
  - 条件：agent_engineering.enabled=true 但 tech-design.md 缺少 Agent 实现规格
   - verification-report.md 记录：缺少 tech-design `## Agent 实现`，agent-eval 阻塞；返回设计/tech-design 补齐实现规格。
</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `bug-fix` | compute-conclusion 返回 FAIL，ac_trace 有 conclusion=fail 条目（实现缺陷） | 调 `harness verify failure-path --kind bug_fix`；按 bug-fix PROTOCOL 走 reproduction evidence → root cause → fix → regression evidence；完成后重走 execute → code-review → verify。 |
| `blocked-execute-failure` | compute-scope execute_failure_ref 非空（execute 已 FAIL evidence 命中） | 调 `harness verify failure-path --kind execute`；verify 直接进入 BLOCKED 结论，不重跑双证据校验；触发 retrospective + bug-fix；execution-result.contract.yaml.failure_state 必须在 ac_trace.execute_failure_ref 中显式引用。 |
| `decision-gate` | compute-conclusion 返回 BLOCKED，decision_gate_reasons 非空（测试环境受阻） | 调 `harness verify failure-path --kind decision_gate`；引用 decision_gate_reasons / 受影响 obligations / 缺失产物；调 `harness approval append --type risk --stage verify` 记录用户决策，无 approval 不得继续。 |
| `receiving-review` | code-review High finding 未 fixed / accepted_risk | 调 `harness verify failure-path --kind receiving_review`；路由回 receiving-review，直到 High finding 全部 closed 或 approved 后再回 verify。 |
| `execute-evidence-missing` | check-ac-trace 强校验 FAIL（VERIFY_EVIDENCE_ID_NOT_IN_UPSTREAM）且 execute_failure_ref 为空 | 调 `harness verify failure-path --kind execute`；路由回 execute 补齐缺失 evidence，不允许 verify 自行降级 PASS_WITH_RISK；execute 补完后重回 verify 重跑 Step 3-7。 |

</failure_paths>

Stage transition:

- Decided by: `control_plane.stage` from Mission Slice (Work Graph).
- Typical next:
  - `delivery`：verification 结论 PASS 或 PASS_WITH_RISK（approval 已记录）
- Enforced by: cli=harness gate advance


</workflow>
