# 代码评审工作流

> **行为约束（铁律、反合理化、HARD-GATE 顺序）见 `SKILL.md`，不在此重复。**
> **方法论参考**：`.harness/docs/methodology-reference.md` §8（Google 代码评审 Practices；Conventional Comments）§11（OWASP Top 10/ASVS；STRIDE Threat Modeling；Secure by 设计）

所有 harness 控制面调用通过 `harness-cli` skill 包装（默认 `--json`），不直接裸 Bash。

<workflow stage="code-review" version="2">

<goal>
  对 execute 阶段的变更并行调度 correctness / tdd / 条件 security / architecture / e2e / agent-behavior 审查员，跑审查-修复循环至无 High，产出 code-review.md + code-review.contract.yaml。
</goal>

<role>
  你是审查编排者。你收集变更范围、按特征选择审查员、并行派发只读 reviewer、合并去重报告、校验角色归属、驱动审查-修复循环。退出循环的唯一条件是本轮汇总后无 High 级别问题。
</role>

<stage_capability>

代码审查阶段对应 RUP 构建阶段后段的实现质量审查、测试审查，以及配置与变更管理中的变更集确认。它的核心能力不是“看代码有没有问题”，而是回答“实现是否忠实于需求、设计和执行授权，并且未关闭风险是否足以阻断验证泳道推进”。

| 能力 | 本阶段必须判断什么 | 失败时 |
|---|---|---|
| 输入合格性判断 | execution-result、execution-brief、tech-design、产品定义包、变更 diff、测试证据和必要规格是否足以建立审查依据 | BLOCKED，回 execute 或补审查依据 |
| 变更集承接判断 | changed files / changed surface / 偏差 / 阻塞 / 回流命中是否与 execute 产物一致，且审查范围覆盖实际变更 | HOLD，补齐 diff 或回 execute 修正结果记录 |
| 需求忠实性判断 | 实现是否满足验收场景 / 条件、系统责任、差量规格和任务项声明的用户可观察行为，且没有新增未授权行为 | High finding，回执行修复 |
| 设计一致性判断 | 实现是否遵守方案路线、技术设计、模块边界、接口契约、数据 / 状态流、禁止路径和风险处理计划 | High finding 或 Decision Gate |
| 测试有效性判断 | TDD / E2E / 条件测试证据是否能发现错误实现，而不是只证明命令通过 | HOLD，补测试或补 fault evidence |
| 专业风险判断 | 安全、数据迁移、Agent 行为、前端 E2E 等条件风险是否由对应只读 reviewer 给出角色边界和矩阵结论 | BLOCKED 或补充对应 reviewer |
| 修复闭环判断 | High finding 是否 fixed 或 accepted risk，修复后是否重新全量审查，风险是否有处理引用 | 不得推进到验证泳道 |
| 验证交接判断 | code-review.md 是否把审查依据、角色选择、发现、修复轮次、开放风险和验证关注点交给 verify | 不得完成 code-review |

</stage_capability>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `review-contract-via-cli` | code-review.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness contract init/patch/add-verdict | hook=code-review-check-contract-via-cli |
| `review-not-fenced` | code-review.md 不得内嵌 fenced YAML evidence_contract / execution_result / role_verdicts 段 | hook=harness-lint |
| `reviewers-readonly` | 全部审查员（correctness / tdd / security / architecture / e2e / agent-behavior）必须在 readonly subagent 中调用 | registry=subagents/*-reviewer[readonly=true] |
| `reviewer-rigor` | 每个审查员必须输出 role_boundary + review_basis + 角色最小矩阵；缺失则该审查无效必须重审 | hard_gate=reviewer-rigor-contract |
| `no-skip-recheck` | 修复后必须重新调用全部审查员全量确认，不能改完即止 | hard_gate=no-skip-recheck |

</invariants>

<entry>
  - execute 阶段已完成，execution-result 通过 Stage Gate
  - Mission Slice control_plane.stage=code-review
</entry>

<exit>
  - `review-written`: code-review.md 写入 code-review stage worktree
  - `contract-filled`: code-review.contract.yaml 已填充且 harness contract check PASS
  - `no-open-high`: 无 High finding 保持 open（已 fixed 或 accepted_risk approval 已记录）
  - `tdd-verdict`: tdd-reviewer 已给出 verdict + Test Adequacy Matrix
  - `gate-pass`: harness review check-ready 返回 status=pass
</exit>

<subagents>

| Role | Mode | Scope / restrictions | Package |
|---|---|---|---|
| `correctness-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/correctness-reviewer.md` |
| `tdd-reviewer` | spawn readonly | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/tdd-reviewer.md` |
| `security-reviewer` | spawn; readonly; condition=变更涉及认证 / 授权 / 加密 / 用户输入 / API 暴露 | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/security-reviewer.md` |
| `architecture-reviewer` | spawn; readonly; condition=变更涉及新模块 / 跨模块调用 / 接口变化 / 依赖引入 | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/architecture-reviewer.md` |
| `e2e-reviewer` | spawn; readonly; condition=e2e.enabled=true 且变更含 E2E 测试文件或 UI 实现 | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/e2e-reviewer.md` |
| `agent-behavior-reviewer` | spawn; readonly; condition=agent_engineering.enabled=true 且变更含 Agent 定义 / 技能 / policy / hook 文件 | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/agent-behavior-reviewer.md` |
| `data-migration-reviewer` | spawn; readonly; condition=变更涉及 schema / DDL / migration / backfill / bulk data rewrite / data repair / recovery script | disallowed_tools: Edit, Write, MultiEdit, NotebookEdit, Bash | `.harness/common/agents/data-migration-reviewer.md` |

</subagents>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `mission-contract.md` | true | Intent |
| `tech-design.md` | true | Memory |
| `execution-brief.md` | true | Memory |
| `execution-result.md` | true | Memory |
| `specs/` | conditional: spec.enabled=true | Artifact Contract |
| `project-context.md` | conditional: brownfield | Context |
| `harness.yaml` | true via harness config snapshot | Memory |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `code-review-md` | `harness-runtime/harness/artifacts/${mission-id}/code-review/code-review.md` | markdown | Memory |
| `code-review-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/code-review.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |

</outputs>

<steps>

<step id="step-0" n="0" goal="trace 初始化 + 控制面 preflight">
 - CLI-first preflight（review / continue / status 场景）：调用 `harness control status --json`、`harness control candidates --intent continue --json`；显式确定 mission 后再 `harness control frame/guidance/context-index --mission <id> --json`。guidance 指向缺失 artifact / review evidence / 待 Gate / approval 时先返回对应控制处理；临时读旧 runtime 文件时记录 fallback_used / fallback_reason / legacy_source / follow_up。
 - 读取 mission-contract.md（初始验收条件）、产品定义包（验收场景 / 条件、系统责任、质量与运行约束）、tech-design.md（设计意图）、execution-brief.md（变更文件清单）、execution-result.md（changed files / changed surface / 偏差 / 阻塞 / 回流命中）、solution.md / tech-design.md 指导契约（decisions / forbidden_paths / modules / interface_changes / data_changes / verification_strategy）。
 - 调用 `harness frame current --mission <mission-id> --json`，提取 mission_status、control_plane.stage=code-review、required_execution_roles、required_review_roles、primary_nodes、related_nodes、operation、output_artifact。审查范围必须覆盖 Mission Slice 节点。
 - 确定变更范围基线：从 `mission_status.git.baseline_commit` 读基线；有则 `git diff <baseline>..HEAD`，无则降级到 execution-brief 变更文件记录。
 - 调用 `harness config snapshot --json` 读 spec.enabled；为 true 时扫描 `harness-runtime/harness/artifacts/<mission-id>/product/specs/` 加载全部差量规格文件（旧 `stages/<mission-id>/specs/` 仅作兼容读取）。
 - 运行 TDD Toolchain 控制面：依次执行 `.harness/common/skills/code-review/scripts/toolchain_resolver.py` → `.harness/common/skills/code-review/scripts/toolchain_runner.py` → `.harness/common/skills/code-review/scripts/normalize_toolchain_status.py` 生成 toolchain-status.json，再经 `harness-cli` skill 调用 `harness review toolchain-status --mission <id> --json` 查询。E2E 义务推导用 `.harness/common/skills/code-review/scripts/e2e_obligation_policy.py`。
 - 运行 E2E 控制面：依次执行 `.harness/common/skills/code-review/scripts/e2e_resolver.py` → `.harness/common/skills/code-review/scripts/e2e_runner.py` → `.harness/common/skills/code-review/scripts/normalize_e2e_status.py` 生成 e2e-status.json，再经 `harness-cli` skill 调用 `harness review e2e-status --mission <id> --json` 查询。e2e-reviewer 审查方法论见 `.harness/docs/e2e-effectiveness-reviewer-methodology.md`。
 - 遇 toolchain / e2e status BLOCKED 时，本 Step 后续 ask-user check 用 AskUserQuestion 让用户在「跳过 / 补运行 / Decision Gate」之间选择；所有 harness 控制面调用统一经 harness-cli skill 包装。
 - 调用 cli `harness trace log-init` `--mission ${mission-id} --stage code-review`，evidence=required。
 - 调用 cli `harness trace round-enter` `--mission ${mission-id} --round 1`，evidence=required。
 - 条件：toolchain status == BLOCKED
  - 调用 tool: `AskUserQuestion`。
   - 问题：TDD Toolchain 尚未运行（toolchain-status.json 缺失），请确认
   - 候选答案：
      - 继续审查（跳过 TDD 工具链，缺失能力记 BLOCKED）
      - 先补运行 toolchain_runner.py 再返回
      - 发起 Decision Gate
 - 条件：e2e status == BLOCKED 且 e2e.enabled=true
  - 调用 tool: `AskUserQuestion`。
   - 问题：E2E 控制面尚未运行（e2e-status.json 缺失），请确认
   - 候选答案：
      - 继续审查（跳过 E2E 工具链）
      - 先补运行 e2e_runner.py 再返回
 - 调用 cli `harness review select-reviewers` `--mission ${mission-id}`，evidence=required。
 - 调用 cli `harness review snapshot-diff` `--mission ${mission-id}`，evidence=required。
</step>

<step id="step-1" n="1" goal="选择审查员角色（本轮任务一次）">
 - 根据变更范围特征决定启用哪些审查员：correctness-reviewer + tdd-reviewer 始终启用；security-reviewer（认证/授权/加密/用户输入/API 暴露/secret/敏感数据）；architecture-reviewer（新模块/跨模块调用/接口变化/依赖引入/数据流或状态流变化）；data-migration-reviewer（schema / DDL / migration / backfill / bulk data rewrite / data repair / recovery script）；e2e-reviewer（e2e.enabled=true 且变更含 E2E 测试文件或 UI 实现）；agent-behavior-reviewer（agent_engineering.enabled=true 且变更含 Agent 定义 / skill / tool / MCP / policy / hook / runtime 配置 / eval）。
 - 规则：correctness-reviewer 始终参与；tdd-reviewer 始终参与且其 HOLD 等同 High finding，阻断推进 verification lane；其它 reviewer 只能由明确变更特征触发，不得以「宁多不漏」额外启用；最终报告记录选择理由。
 - **interactive_prototype 路线界面忠诚度强制**：如果 `harness config snapshot` 的 `prototype.delivery_mode=interactive_prototype`（默认路线）、本轮变更含 UI 实现、且本 mission 有原型产物（interaction stage 产出的 `behavior-graph.yaml`）：必须启用 e2e-reviewer，并在其 brief 中追加"界面忠诚度"维度——核验实现的页面 / 状态 / 流程忠于 behavior-graph SSOT（surface 对应 SURF-xxx、页面状态对应 PS-<surf>-<state>、步骤 / 流程对应 SUC-xx-FLOW-xx.<state> 与 edge），实现既不得静默漂移 / 自由重设计界面，也不得遗漏 behavior-graph 声明的页面状态与流程；若实现对某原型决策显式改写，须确认其已经决策门并在下游契约登记 `prototype_coverage_exemptions` 豁免，否则记 High finding。该 mission 无 behavior-graph（非 UI / 未跑 interaction）时本规则跳过。
 - **frontend_engineering 路线额外检查**：如果 `harness config snapshot` 的 `prototype.delivery_mode=frontend_engineering` 且本轮变更涉及前端代码：
   - 本阶段是 frontend_engineering 路线下"质量门"的统一落地点（interaction stage 不做这些）。
   - 必须强制评：完整 a11y audit（含键盘焦点 / 焦点可见 / aria 完整 / 对比度 / 屏幕阅读器路径）、lint 达项目阈值、typecheck strict、coverage 达项目阈值、Playwright e2e 充分性。
   - e2e-reviewer 在 frontend_engineering 路线下**强制启用**（不论 e2e.enabled）；本阶段还要审查 Playwright e2e spec 是否覆盖上游 prototype-as-frontend contract 的 `e2e_locator_obligations[]`。
   - 若上游 `contracts/prototype-as-frontend.contract.yaml` 存在，本轮 reviewer brief 必须包含其 `downstream_handoff.code_review[]` 段作为质量门清单。
</step>

<step id="step-2" n="2" goal="审查-修复循环">
 - 循环：id=reviewer-loop；无轮次放行（producer-fixable 缺口不设通过上限，轮次只记录修复历史）；退出条件：本轮汇总后审查员在等同严格度下确认无 High 级别问题
  - 每轮重新收集变更范围（git diff 或 execution-brief 列表），读 project-context.md，并调用 `harness knowledge resolve --stage code-review --json` 按角色提取约束、规格、工程样板和历史教训摘要。
  - 调用 cli `harness trace round-enter` `--mission ${mission-id} --round ${N}`，evidence=required。
  - 为 Step 1 启用的每个子 Agent 准备独立 brief（互不可见）：correctness-reviewer（mission 验收条件 + 产品定义验收场景 / 条件 + 差量规格 + execution task + execution-result changed surface + changed implementation diff + related tests，输出 role_boundary / review_basis / behavior_matrix / blocking_gaps）；tdd-reviewer（Toolchain Status JSON + 验收场景 / 条件 + execution-brief + execution-result TDD evidence + verification_strategy + 工具报告 + 测试文件 + 实现 diff + Red/Green/Regression evidence + 差量规格 Scenario，先读 toolchain-status.json 缩小范围，输出 Role Boundary + Test Adequacy Matrix）；security-reviewer（变更代码 + mission 权限/用户/数据范围 + tech-design 安全约束 + project security policy + dependency/config diff，按 threat_matrix 输出可利用风险）；architecture-reviewer（solution + tech-design + project-context + dependency-impact evidence + changed diff，对照 modules/interface_changes/data_changes/state_flow/forbidden_paths 输出 architecture_matrix）；data-migration-reviewer（migration/schema/repair diff + tech-design data_changes/migration plan + dry-run + invariant checks + rollback/recovery evidence，输出 migration_safety_matrix）；e2e-reviewer（E2E methodology + e2e-status.json + 验收场景 / 条件 + execution-brief e2e_obligation + interaction.md / interaction-spec + E2E 测试 + UI 实现 + E2E 报告，输出 Role Boundary + E2E Coverage Matrix；若由 interactive_prototype 路线界面忠诚度规则启用，brief 额外附 behavior-graph.yaml（SURF / PS / SUC-FLOW / edge SSOT）+ surface-model.md + 下游契约 `prototype_coverage_exemptions`，要求其在报告中给出"界面忠诚度"维度，核验实现页面 / 状态 / 流程忠于 behavior-graph，对静默漂移 / 自由重设计 / 缺失页面状态记 High finding）；agent-behavior-reviewer（solution `## Agent 架构` + tech-design `## Agent 实现` + Agent definition/skill/tool/MCP/policy/hook/runtime/eval diff，输出 work_rights_matrix + enforcement_matrix）。
  <dispatch role="correctness-reviewer" mode="spawn" />
  <dispatch role="tdd-reviewer" mode="spawn" />
  - 并行 dispatch Step 1 选定的全部审查员；等待全部返回，合并报告、去重、统一 High/Med/Low 分级。
  - 调用 cli `harness contract check-finding-ownership` `--mission ${mission-id}`，evidence=required。
  - 调用 cli `harness contract detect-conflicts` `--mission ${mission-id}`，evidence=required。
  - Hard gate `reviewer-rigor-contract`：
   - 任一审查员缺少 role_boundary / review_basis / 角色最小矩阵（correctness=behavior_matrix，tdd=Test Adequacy Matrix，security=threat_matrix，architecture=architecture_matrix，data-migration=migration_safety_matrix，e2e=coverage_matrix，agent-behavior=work_rights_matrix/enforcement_matrix）→ 该审查无效，重新 dispatch 对应子 Agent 要求补齐；finding 职责归属不清或与其它审查员/验证/Stage Gate 重复 → 重新归类，不得冒充该审查员的 High。
   - Enforced by: hook=harness-lint
  - 条件：判定为「实现与设计根本偏离」
   - 调用 tool: `AskUserQuestion`。
    - 问题：审查发现实现与设计存在根本性偏离，请确认
    - 候选答案：
       - 终止代码评审，回退执行阶段重新实现（结论 Blocked）
       - 发起 Decision Gate 提交设计变更申请
       - 接受偏离（提供理由，记录 approved tradeoff）
  - 分支：审查结论
   - 情况：存在 High 问题
    - 读取 `.harness/common/protocols/quality-control/PROTOCOL.md`，将 HOLD / High finding 分类 Hard Gate，记录 evidence / 影响 / 修复 carrier；列 High 清单修复代码（必要时调用执行能力）。High 来源为 tdd-reviewer 时优先补测试 / 补 Red-Green evidence / 补 fault injection 等价证明，不得降低断言 / 删测试 / 跳测试解除 HOLD。立即回到循环开头重新审查。
    - Hard gate `no-skip-recheck`：
     - 修复完成 ≠ 审查通过。只有审查员重新审查后确认无 High 才能退出循环。禁止修复后跳过重审。
     - Enforced by: hook=harness-lint
   - 情况：无 High 问题
    - 调用 `harness contract add-round`、`harness trace round-exit --status pass`，退出循环。
 - 条件：卡死——同一 High finding 在执行者修复后，审查员仍以相同根因连续 HOLD 且无实质进展（按缺口本质判断，不是"轮次到点"）
  - 不得降级通过。按 `core.md`「严格审查不变量」重新归因该缺口：
   - 本质是 producer 能补但反复没补对 → 留在修复循环，升级修复策略 / 换执行能力继续修，不退出循环。
   - 本质是真实信息缺失（`gap_root=clarification`）或需要用户在路线 / 范围上拍板才能解 → 调用 tool: `AskUserQuestion`。
    - 问题：审查发现以下 High 问题在反复修复后仍无法在当前范围内解决（已附完整未解决 High 清单与卡点根因），需要你决策方向
    - 候选答案（**不含"接受遗留 / 降级通过"**）：
       - 给出修复方向，留在审查循环继续修
       - 改任务范围 / 回退上游重导（记录 scope 变更或回退）
       - 升级 BLOCKED，终止本阶段
  - 残留风险只能由用户在 Decision Gate 上**显式拥有**：仅当用户在充分披露完整未解决 High 清单后明确选择承担该风险，才调用 cli `harness approval append` `--mission ${mission-id} --type tradeoff --stage code-review --status approved`，evidence=required；外部 contract role_verdicts 保留完整未解决 High 并标注 accepted_by_user=true 且写明 disclosed_risk。审查循环本身永不把未解决 High 自动转为通过。
</step>

<step id="step-3" n="3" goal="写入评审报告并更新状态">
 - 使用 `harness-runtime/templates/code-review.md` 模板，填充：审查依据、变更集承接、启用的审查员、各 Agent 发现、分级表、轮次记录、修复闭环、验证交接和结论 Approved。
 - 若 `contracts/code-review.contract.yaml` 不存在，调用 `harness contract init --mission <mission-id> --stage code-review --template code-review --json` 初始化；若已存在只能 patch。
 - 外部 contract 中为每个审查员分配 REV-NNN、每个 finding 分配 FND-NNN，finding 写 severity / category / evidence / traces_to / status / resolution_ref；每个审查员写 role_boundary + review_basis + 角色矩阵摘要；写 toolchain_status.status_artifact 指向 toolchain-status JSON；data-migration-reviewer 启用时写 migration_safety_matrix / accepted_risks_required；e2e.enabled=true 时写 e2e_status.status_artifact + e2e_review（methodology_ref / verdict / role_boundary / coverage_matrix / blocking_gaps / non_blocking_risks）。
 - tdd-reviewer 启用时 code-review.md 写 `## TDD 有效性审查` 段（verdict / Test Adequacy Matrix / Blocking Gaps / Non-blocking Risks）；e2e-reviewer 启用时写 `## E2E Control Plane Status` + `## E2E 审查` 段。
 - 审查员返回 HOLD 时保留对应 open finding；High finding 未 fixed 或 accepted_risk 时不得通过 Stage Gate 推进 verification lane。
 - code-review.md 的「控制契约」段只保留 `Contract: contracts/code-review.contract.yaml` 引用和 Authority 说明，禁止追加 fenced YAML contract。写入 `harness-runtime/harness/stages/<mission-id>/code-review.md`。
 - 将 review evidence contract 字段、toolchain / E2E status、finding 状态和结构化 reviewer verdicts 经 `harness contract patch` / `add-verdict` 写入 contract。
</step>

<step id="step-4" n="4" goal="Artifact Gate 自检 + Stage exit">
 - 验证 code-review.md 包含最小必要结构：评审摘要、发现列表（High/Med/Low）、正确性、设计一致性、安全与可靠性、评审结论；前部含 `Contract:` 引用且不含 fenced YAML contract / ## evidence_contract / ## execution_result / ## role_verdicts。
 - 验证外部 contract 包含审查证据契约且 findings status 完整；High finding 不得保持 open。e2e.enabled=true 时验证 e2e_status / e2e_review contract 字段 + code-review.md 含 E2E 人读正文，e2e_review.methodology_ref 引用 e2e-effectiveness-reviewer-methodology.md。
 - 调用 cli `harness contract check` `--artifact harness-runtime/harness/stages/${mission-id}/code-review.md`，evidence=required。
 - 调用 cli `harness review check-ready` `--mission ${mission-id}`，evidence=required。
 - 调用 cli `harness gate run` `--stage code-review --mission ${mission-id} --artifact harness-runtime/harness/stages/${mission-id}/code-review.md --json`，evidence=required。
 - 条件：gate status != PASS
  - 按 failed_checks 修复 code-review.md 或 contract 后重新运行 gate；不得完成阶段。
 - 调用 cli `harness mission stage complete` `--mission ${mission-id} --stage code-review --json`，evidence=required。
 - 条件：结构不完整
  - 自行补充缺失部分，不要跳过。
</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `toolchain-blocked` | harness review toolchain-status 返回 BLOCKED | Step 0 AskUserQuestion：跳过 / 补运行 toolchain_runner.py / Decision Gate。 |
| `e2e-blocked` | harness review e2e-status 返回 BLOCKED 且 e2e.enabled=true | Step 0 AskUserQuestion：跳过 / 补运行 e2e_runner.py。 |
| `design-deviation` | correctness-reviewer 或 architecture-reviewer 发现根本性 design deviation | Step 2 AskUserQuestion：回退执行 / 设计变更申请 / 接受偏离记 approved tradeoff。 |
| `review-stuck` | 同一 High finding 修复后仍以相同根因连续 HOLD 且无实质进展（非轮次到点） | Step 2 重新归因：producer 能补则继续修；需用户拍板则 AskUserQuestion（候选仅：继续修 / 改范围回退 / 升级 BLOCKED，不含降级通过）。残留风险仅由用户在 Decision Gate 显式拥有并记 approval。 |
| `contract-write-fail` | harness contract init/patch 返回 FAIL | FAIL，停止工作流，报告合同层错误。 |
| `invalid-reviewer-result` | 审查员缺少 role_boundary / review_basis / 最小矩阵 | 重调对应审查员，不得以无效结果作通过。 |
| `stage-gate-fail` | harness contract check 返回 FAIL | 自行修复后重新检查，不跳过。 |

</failure_paths>

Stage transition:

- Decided by: `control_plane.stage` from Mission Slice (Work Graph).
- Typical next:
  - `verify`：code-review 无 open High，进入验证
- Enforced by: cli=harness gate advance

</workflow>
