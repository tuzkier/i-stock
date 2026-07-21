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

<permissions>

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Edit(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Write(harness-runtime/harness/mission-status.yaml)` | 必须经 harness mission CLI |
| deny | `Edit(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/stages/*/contracts/code-review.contract.yaml)` | contract 必须经 harness contract init/patch |
| deny | `Edit(harness-runtime/harness/stages/*/contracts/code-review.contract.yaml)` | contract 必须经 harness contract patch/add-verdict |
| deny | `Edit(harness-runtime/config/harness.yaml)` | 配置只读 |
| deny | `Edit(harness-runtime/config/model-routing.yaml)` | 配置只读 |
| allow | `Write(harness-runtime/harness/stages/*/code-review.md)` | code-review 主产物 |
| allow | `Edit(harness-runtime/harness/stages/*/code-review.md)` | code-review 主产物 |
| allow | `Bash(harness *)` | code-review CLI 必需 |
| allow | `Bash(git diff *)` | 变更范围基线 |
| allow | `Bash(git status *)` | 变更范围基线 |
| allow | `Bash(git log *)` | 变更范围基线 |

</permissions>

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
| `code-review-md` | `harness-runtime/harness/stages/${mission-id}/code-review.md` | markdown | Memory |
| `code-review-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/code-review.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |

</outputs>

<steps>

<step id="step-0" n="0" goal="trace 初始化 + 控制面 preflight">
 - CLI-first preflight（review / continue / status 场景）：调用 `harness control status --json`、`harness control candidates --intent continue --json`；显式确定 mission 后再 `harness control frame/guidance/context-index --mission <id> --json`。guidance 指向缺失 artifact / review evidence / 待 Gate / approval 时先返回对应控制处理；临时读旧 runtime 文件时记录 fallback_used / fallback_reason / legacy_source / follow_up。
 - 读取 mission-contract.md（验收标准）、tech-design.md（设计意图）、execution-brief.md（变更文件清单）、solution.md / tech-design.md 指导契约（decisions / forbidden_paths / modules / interface_changes / data_changes / verification_strategy）。
 - 调用 `harness frame current --mission <mission-id> --json`，提取 mission_status、control_plane.stage=code-review、required_execution_roles、required_review_roles、primary_nodes、related_nodes、operation、output_artifact。审查范围必须覆盖 Mission Slice 节点。
 - 确定变更范围基线：从 `mission_status.git.baseline_commit` 读基线；有则 `git diff <baseline>..HEAD`，无则降级到 execution-brief 变更文件记录。
 - 调用 `harness config snapshot --json` 读 spec.enabled；为 true 时扫描 `harness-runtime/harness/stages/<mission-id>/specs/` 加载全部差量规格文件。
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
 - **frontend_engineering 路线额外检查**：如果 `harness config snapshot` 的 `prototype.delivery_mode=frontend_engineering` 且本轮变更涉及前端代码：
   - 本阶段是 frontend_engineering 路线下"质量门"的统一落地点（interaction stage 不做这些）。
   - 必须强制评：完整 a11y audit（含键盘焦点 / 焦点可见 / aria 完整 / 对比度 / 屏幕阅读器路径）、lint 达项目阈值、typecheck strict、coverage 达项目阈值、Playwright e2e 充分性。
   - e2e-reviewer 在 frontend_engineering 路线下**强制启用**（不论 e2e.enabled）；本阶段还要审查 Playwright e2e spec 是否覆盖上游 prototype-as-frontend contract 的 `e2e_locator_obligations[]`。
   - 若上游 `contracts/prototype-as-frontend.contract.yaml` 存在，本轮 reviewer brief 必须包含其 `downstream_handoff.code_review[]` 段作为质量门清单。
</step>

<step id="step-2" n="2" goal="审查-修复循环">
 - 循环：id=reviewer-loop；max_rounds=3；退出条件：本轮汇总后无 High 级别问题
  - 每轮重新收集变更范围（git diff 或 execution-brief 列表），读 project-context.md，并调用 `harness knowledge resolve --stage code-review --json` 按角色提取约束、规格、工程样板和历史教训摘要。
  - 调用 cli `harness trace round-enter` `--mission ${mission-id} --round ${N}`，evidence=required。
  - 为 Step 1 启用的每个子 Agent 准备独立 brief（互不可见）：correctness-reviewer（mission AC + product Scenario + delta specs + execution task + changed implementation diff + related tests，输出 role_boundary / review_basis / behavior_matrix / blocking_gaps）；tdd-reviewer（Toolchain Status JSON + AC + execution-brief + verification_strategy + 工具报告 + 测试文件 + 实现 diff + Red/Green/Regression evidence + 差量规格 Scenario，先读 toolchain-status.json 缩小范围，输出 Role Boundary + Test Adequacy Matrix）；security-reviewer（变更代码 + mission 权限/用户/数据范围 + tech-design 安全约束 + project security policy + dependency/config diff，按 threat_matrix 输出可利用风险）；architecture-reviewer（solution + tech-design + project-context + dependency-impact evidence + changed diff，对照 modules/interface_changes/data_changes/state_flow/forbidden_paths 输出 architecture_matrix）；data-migration-reviewer（migration/schema/repair diff + tech-design data_changes/migration plan + dry-run + invariant checks + rollback/recovery evidence，输出 migration_safety_matrix）；e2e-reviewer（E2E methodology + e2e-status.json + AC + execution-brief e2e_obligation + interaction.md / interaction-spec + E2E 测试 + UI 实现 + E2E 报告，输出 Role Boundary + E2E Coverage Matrix）；agent-behavior-reviewer（solution `## Agent 架构` + tech-design `## Agent 实现` + Agent definition/skill/tool/MCP/policy/hook/runtime/eval diff，输出 work_rights_matrix + enforcement_matrix）。
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
 - 条件：达到 max_rounds 后仍有 High 问题
  - 调用 tool: `AskUserQuestion`。
   - 问题：已达最大审查轮次（3 轮），仍有 High 问题未解决，请指示
   - 候选答案：
      - 提供修复方向（按指导修复后继续，轮次重置）
      - 接受遗留问题（记 approved tradeoff，stage gate 降级通过）
      - 终止审查，升级 Decision Gate
  - 条件：用户选择接受遗留问题
   - 调用 cli `harness approval append` `--mission ${mission-id} --type tradeoff --stage code-review --status approved`，evidence=required。
   - 外部 contract role_verdicts 保留完整未解决 High 并标注 accepted_by_user=true。
</step>

<step id="step-3" n="3" goal="写入评审报告并更新状态">
 - 使用 `harness-runtime/templates/code-review.md` 模板，填充：启用的审查员、各 Agent 发现、分级表、轮次记录、结论 Approved。
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
| `max-rounds-exhausted` | 3 轮后仍有 High finding | Step 2 AskUserQuestion：提供修复方向 / 接受遗留 / Decision Gate。 |
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
