# 分支收尾工作流

> **方法论参考**：`.harness/docs/methodology-reference.md` §15（GitOps；Trunk-Based Development 收尾）

所有 CLI 调用通过 harness-cli skill（`--json` 模式）。

<workflow stage="finishing-branch" version="2">

<goal>
  在 delivery 完成 / retrospective PASS 后安全收尾 mission branch：按用户选择执行合并 / PR / 保留 / 丢弃，并清理已完成的 stage worktree，记录最终 Git 状态。
</goal>

<role>
  你是分支收尾执行者。你在用户选择前先验证状态（测试、worktree、发布就绪度），执行用户选择的收尾策略，并记录最终 Git 状态。所有 git 操作经 harness finishing-branch CLI，破坏性操作先 dry-run 预览再确认。
</role>

<invariants>

| ID | Check | Enforced by |
|---|---|---|
| `fb-contract-via-cli` | finishing-branch.contract.yaml 不得被 agent 直接 Write/Edit，必须经 harness contract init/patch | hook=finishing-branch-check-contract-via-cli |
| `mission-status-via-cli` | mission-status.yaml 只能经 harness mission close 更新，禁止直接 Edit/Write | hook=harness-lint |
| `no-merge-with-active-worktree` | 存在 active / BLOCKED stage worktree 时不得把 mission branch 合并回 base branch | hard_gate=active-worktree-block |
| `destructive-ops-dry-run-first` | merge / push / discard 等破坏性策略必须先 dry-run 预览 + 用户确认才能正式执行 | hard_gate=dry-run-before-execute |

</invariants>

<entry>
  - delivery 阶段已完成并暂停，用户 / Board 明确触发分支收尾
  - Mission Slice control_plane.stage=finishing-branch
</entry>

<exit>
  - `contract-filled`: finishing-branch.contract.yaml 已填充 branch_status / test_evidence / close_choice / git_ops / mission_close
  - `tests-pass`: 完整测试套件通过（harness finishing-branch run-tests）
  - `strategy-executed`: 用户选择的收尾策略已执行（merge_to_base / push_pr / keep / discard）
  - `mission-closed`: harness mission close 已记录 close strategy 到 mission-status.yaml
</exit>

<permissions>

| Effect | Pattern | Reason |
|---|---|---|
| deny | `Edit(harness-runtime/harness/mission-status.yaml)` | 只能经 harness mission close |
| deny | `Write(harness-runtime/harness/mission-status.yaml)` | 只能经 harness mission close |
| deny | `Edit(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/work-graph/**)` | 必须经 harness graph CLI |
| deny | `Write(harness-runtime/harness/stages/*/contracts/finishing-branch.contract.yaml)` | contract 必须经 harness contract init/patch |
| deny | `Edit(harness-runtime/harness/stages/*/contracts/finishing-branch.contract.yaml)` | contract 必须经 harness contract patch |
| allow | `Write(harness-runtime/harness/stages/*/finishing-branch.md)` | finishing-branch 主产物 |
| allow | `Edit(harness-runtime/harness/stages/*/finishing-branch.md)` | finishing-branch 主产物 |
| allow | `Bash(harness *)` | finishing-branch CLI 必需 |
| allow | `Bash(git status *)` | 分支状态检查 |
| allow | `Bash(git diff *)` | 分支状态检查 |
| allow | `Bash(git log *)` | 分支状态检查 |
| allow | `Bash(git branch *)` | 分支收尾必需 |
| allow | `Bash(git checkout *)` | 分支收尾必需 |
| allow | `Bash(git merge --no-ff *)` | merge_to_base 策略必需 |

</permissions>

<inputs>

| Ref | Required | Plane |
|---|---|---|
| `mission-status.yaml` | true via harness mission status | Work Graph |
| `retrospective.md` | conditional: retrospective 已完成 | Memory |
| `delivery-package.md` | conditional: delivery 已完成 | Memory |
| `harness.yaml` | true via harness config snapshot | Memory |

</inputs>

<outputs>

| Artifact | Path | Kind | Plane / validator |
|---|---|---|---|
| `finishing-branch-md` | `harness-runtime/harness/stages/${mission-id}/finishing-branch.md` | markdown | Memory |
| `finishing-branch-contract-yaml` | `harness-runtime/harness/stages/${mission-id}/contracts/finishing-branch.contract.yaml` | contract | Artifact Contract; validator: `harness contract check` |

</outputs>

<steps>

<step id="step-0" n="0" goal="初始化合约">
 - 检查 `harness-runtime/harness/stages/<mission-id>/contracts/finishing-branch.contract.yaml` 是否存在。若不存在从模板初始化。
 - 调用 cli `harness contract init` `--stage finishing-branch --mission ${mission-id} --template finishing-branch`，evidence=required。
</step>

<step id="step-1" n="1" goal="加载收尾上下文">
 - 调用 cli `harness mission status` `--mission ${mission-id}`，evidence=required。
 - 确认 mission branch、stage worktree 和 Gate 状态。读取 retrospective.md 的 Memory Update Contract（如存在），只作为项目记忆或 follow-up 输入，不触发 spec archive。
</step>

<step id="step-2" n="2" goal="验证测试">
 - 调用 cli `harness finishing-branch detect-test-cmd` `--mission ${mission-id}`，evidence=required。
 - 调用 cli `harness finishing-branch run-tests` `--mission ${mission-id} --test-cmd ${detected-cmd}`，evidence=required。
 - Hard gate `test-suite-must-pass`：完整测试套件失败时停止，显示测试失败详情，不继续到选择和执行步骤。用户必须先修复测试再重新运行此工作流。
</step>

<step id="step-3" n="3" goal="确认 Stage Worktree 状态与发布就绪度">
 - 调用 cli `harness finishing-branch status` `--mission ${mission-id}`，evidence=required。
 - 调用 cli `harness finishing-branch readiness` `--mission ${mission-id}`，evidence=required。
 - Hard gate `active-worktree-block`：存在 active / BLOCKED stage worktree 时不得把 mission branch 合并回 base branch。必须先回到对应阶段修复并通过 Stage Gate，或由用户明确选择丢弃该阶段工作。
</step>

<step id="step-4" n="4" goal="确定基础分支">
 - 从 Step 1 读取的 mission status 中获取 base_branch（git.base_branch 字段）。
 - 条件：base_branch 为空
  - 调用 tool: `AskUserQuestion`。
   - 问题：无法从 mission-status.yaml 自动读取 base_branch，请输入基础分支名（例如 main 或 master）
   - 候选答案：
      - main
      - master
</step>

<step id="step-5" n="5" goal="展示收尾选项">
 - 调用 cli `harness finishing-branch options` `--mission ${mission-id}`，evidence=required。
 - 获取可用策略列表（含 enabled 状态和 disabled_reason）。
 - 调用 tool: `AskUserQuestion`。
  - 问题：实现已完成。你想怎么做？
  - 候选答案：
     - 在本地合并 mission branch 回 base branch（merge_to_base）
     - 推送并创建 Pull Request（push_pr）
     - 保持分支现状，稍后处理（keep）
     - 丢弃这项工作（discard）
</step>

<step id="step-6" n="6" goal="执行用户选择">
 - 分支：user_choice
  - 情况：merge_to_base
   - 调用 cli `harness finishing-branch execute` `--mission ${mission-id} --strategy merge_to_base --dry-run`，evidence=required。
   - Hard gate `dry-run-before-execute`：
    - 向用户展示将执行的 git_ops 列表，请求确认后才能正式执行。
    - Enforced by: hook=harness-lint
   - 调用 tool: `AskUserQuestion`。
    - 问题：以上 git 操作将被执行，确认继续？
    - 候选答案：
       - 确认继续
       - 取消
   - 调用 cli `harness finishing-branch execute` `--mission ${mission-id} --strategy merge_to_base`，evidence=required。
  - 情况：push_pr
   - 调用 cli `harness finishing-branch pr-body` `--mission ${mission-id}`，evidence=required。
   - 调用 cli `harness finishing-branch execute` `--mission ${mission-id} --strategy push_pr --dry-run`，evidence=required。
   - 调用 tool: `AskUserQuestion`。
    - 问题：将推送 mission branch 并以生成的 PR body 创建 PR，确认继续？
    - 候选答案：
       - 确认继续
       - 取消
   - 调用 cli `harness finishing-branch execute` `--mission ${mission-id} --strategy push_pr`，evidence=required。
  - 情况：keep
   - 调用 cli `harness finishing-branch execute` `--mission ${mission-id} --strategy keep`，evidence=required。
   - 报告 mission branch、提交列表和剩余 stage worktree 位置；不做任何 git 清理。
   - 调用 tool: `AskUserQuestion`。
    - 问题：请说明保留分支的原因（将记录到 contract 中）
    - 候选答案：
       - 等待 review / 后续合并
       - 实验性分支，暂不处理
  - 情况：discard
   - 列出 mission branch、stage branch、提交列表、stage worktree 路径。
   - 调用 tool: `AskUserQuestion`。
    - 问题：此操作不可逆，确认丢弃这项工作？
    - 候选答案：
       - 确认丢弃（discard）
       - 取消
   - 调用 cli `harness finishing-branch execute` `--mission ${mission-id} --strategy discard --confirmation-id discard`，evidence=required。
</step>

<step id="step-7" n="7" goal="清理 stage worktree">
 - 条件：用户选择 merge_to_base 或 discard
  - 调用 cli `harness finishing-branch cleanup` `--mission ${mission-id} --dry-run`，evidence=required。
  - 调用 cli `harness finishing-branch cleanup` `--mission ${mission-id}`，evidence=required。
 - 条件：用户选择 keep
  - 保留 mission branch 和剩余 stage worktree；跳过清理。
</step>

<step id="step-8" n="8" goal="记录最终状态">
 - 调用 cli `harness mission close` `--mission ${mission-id} --strategy ${strategy}`，evidence=required。
 - 记录 close strategy 到 mission-status.yaml（禁止直接 Edit/Write mission-status.yaml）。把 branch_status / test_evidence / close_choice / git_ops / mission_close 写入 finishing-branch.contract.yaml。
</step>

</steps>

<failure_paths>

| Failure | Trigger | Handling |
|---|---|---|
| `contract-init-fail` | harness contract init 失败 | 记录初始化失败 finding，提示用户手动检查 harness-runtime 目录权限，然后停止。 |
| `mission-not-found` | mission-id 未在 mission-status.yaml 中找到 | FAIL：提示用户确认 mission-id 后停止。 |
| `test-suite-failed` | harness finishing-branch run-tests 失败 | FAIL：停止，显示测试失败详情，不继续到选择和执行步骤；用户先修复测试再重新运行。 |
| `active-stage-worktrees` | 存在 active / BLOCKED stage worktree | 向用户展示 active stage worktrees 列表，说明 HARD-GATE 约束，停止并等待用户解决。 |
| `delivery-package-missing` | readiness 检查发现 delivery-package 缺失 | 向用户展示告警，建议先完成 delivery 阶段。 |
| `execute-fail` | harness finishing-branch execute（merge / push / discard）失败 | 记录 git_ops 失败 finding 到 contract，停止并告知用户手动处理。 |
| `mission-close-fail` | harness mission close 失败 | FAIL：检查 effectiveness_review.last_gate_run_status 是否为 PASS，停止。 |

</failure_paths>

Stage transition:

- Decided by: `control_plane.stage` from Mission Slice (Work Graph).
- Typical next:
  - `retrospective`：finishing-branch → retrospective（H5 顺序裁决），用户 / Board 触发复盘
- Enforced by: cli=harness gate advance


<evidence_summary>
 <required_artifacts>
  finishing-branch.contract.yaml (branch_status / test_evidence / close_choice / git_ops / mission_close);
  mission-status.yaml (经 harness mission close 更新，禁止直接写入)。
 </required_artifacts>
 <evidence_items>
  harness finishing-branch status (branch_status);
  harness finishing-branch run-tests (test_evidence);
  harness finishing-branch readiness (release_readiness);
  harness finishing-branch execute (git_ops);
  harness mission close (mission_close.strategy)。
 </evidence_items>
</evidence_summary>

</workflow>
