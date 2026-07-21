---
name: git-workflow
description: '当需要恢复 Git 状态、准备 mission branch、创建 stage worktree、提交阶段产物、合并代码或进行分支收尾时使用。'
---

# Git 工作流 — Mission Branch + Stage Worktree

## 概述

Git 隔离粒度必须稳定：

- **Mission = 先创建并进入一个 mission branch**，例如 `mission/M001-user-auth`
- **Stage = 一个短期 stage branch + stage worktree**，例如 `stage/M001-prd`
- **Stage Gate PASS = stage branch 合并回 mission branch**
- **Root worktree = mission branch 的控制面入口**；正式阶段产物和代码仍进入 stage worktree，最终由 mission branch 受控回合到原始 base branch / PR

这个模型保证分支先于控制面状态写入：新任务先创建 mission branch，再按阶段需要创建 stage worktree；阶段完成后合并回 mission branch。

## 五个操作

| 操作 | 触发时机 | 说明 |
|------|---------|------|
| `recover` | 每次会话恢复（自动） | 读取当前 Mission / Stage 状态，定位 active stage worktree |
| `prepare` | 新 Mission 接入后（一次性） | 从当前 base branch 创建并进入 mission branch，不创建 stage worktree |
| `start-stage` | 每个阶段开始前 | 从 mission branch 创建 stage branch + stage worktree |
| `commit-artifact` | 每次 Stage Gate PASS 后（自动） | 在 stage worktree 提交产物，合并回 mission branch，清理 stage worktree |
| `close` | delivery 完成后，或用户明确要求收尾 | 决定 mission branch 去向（合并/PR/保留/丢弃） |

## Branch / Worktree 组织原则

```text
project-root/                         # 当前 checkout 为 mission/M001-user-auth，承载控制面入口
.worktrees/
  M001-intake/                        # stage/M001-intake
  M001-prd/                           # stage/M001-prd
  M001-execute/                       # stage/M001-execute

mission/M001-user-auth                # Mission 集成线，先创建并进入
stage/M001-prd                        # 阶段执行分支，PASS 后合并并删除
base branch                           # Mission 收尾时由 close 合并 / PR / 保留
```

稳定性红线：

- 新对话只执行 `recover`，不会创建新 branch 或 worktree
- 新 Mission 先创建并进入一个 mission branch；在此之前不得写 Harness runtime 控制面状态
- 每个阶段只在对应 stage worktree 内写产物和代码
- Stage Gate PASS 后才允许合并回 mission branch
- Stage Gate FAIL / BLOCKED 时保留 stage worktree 供修复，不合并
- 正常策略只允许 `stage-worktree`；仅在用户拒绝 Git 或 Git 不可用时使用 `downgraded`
- 不使用 `branch` / `shared` 作为正常策略

## Git Log = 分阶段集成档案

mission branch 上的提交历史是阶段集成史：

```text
docs(intake): finalize mission contract [M001]
docs(discovery): complete discovery brief [M001]
docs(prd): finalize product definition [M001]
docs(design): finalize tech-design [M001]
docs(breakdown): create execution brief [M001]
feat(M001): implement auth middleware
test(M001): cover auth middleware
docs(review): code review passed [M001]
docs(verify): verification passed [M001]
docs(delivery): delivery package ready [M001]
docs(retro): retrospective complete [M001]
```

阶段内部可以有多个提交；合并回 mission branch 时按阶段规模选择 fast-forward、普通 merge 或 squash，必须在 `workflow.md` 中记录采用的策略。

## 降级处理

降级只有两类合法触发场景，其余情况必须 BLOCK 而不是降级：

1. **用户明确拒绝 Git**：用户在 intake 或 prepare 阶段显式说明本项目不使用版本控制（口径如"这个项目不需要 Git"、"先不要建 branch"）。必须由用户主动声明；AI 不得自行判断。
2. **Git 不可用**：当前目录不是 Git 仓库（`git rev-parse --git-dir` 失败），或 Git 二进制不可用。

**显式不构成降级触发**（命中以下任意一条必须 BLOCK 并请求用户决策，不得自动降级）：

- 根工作区有未提交改动 → BLOCKED 并要求用户提交、stash 或确认是否丢弃；不允许"为了建 mission branch 就改成 downgraded"。
- mission branch 已存在但与当前 HEAD 不同步 → BLOCKED 要求用户确认。
- 用户没有明确说不用 Git，只是没回应 → 继续走正常 `stage-worktree`，不主动降级。

触发时的操作：

- 调用 `harness-cli` 执行 `harness approval append --mission <mission-id> --type tradeoff --status approved --comment "<触发条件> | <用户原话或环境检查输出>" --json`；不允许只写到 mission-status 文本字段。
- 在 `mission-status.yaml` 中记录 `git.strategy: downgraded` 及 `git.downgrade_reason`。
- `start-stage`、`commit-artifact`、`recover` 的 Git 操作静默跳过，但每次跳过仍要写一条 trace-log evidence（`git_op_skipped` + reason），不允许真正无痕。
- `close` 跳过所有 Git 操作。

`downgraded` 一旦记录就**锁定到本 mission 收尾**——不允许在中途切换回 `stage-worktree`，也不允许把 stage 产物伪装成已合并状态。如果用户后来同意启用 Git，必须开新的 Mission Slice 重做相关阶段。

## 生命周期约束

<HARD-GATE>
以下五条是本技能的生命周期铁律，不可跳过：

1. **recover**：每次会话恢复时必须调用。不调用直接继续工作 = 违规。
2. **prepare**：新 Mission 接入后、`git.mission_branch` 尚未就绪时必须调用。跳过 = 违规。
3. **start-stage**：任何阶段写正式产物或代码前，必须有当前阶段的 stage worktree。跳过 = 违规。
4. **commit-artifact**：每次 Stage Gate PASS 后必须调用，将该 stage 合并回 mission branch。跳过 = 违规。
5. **close**：retrospective PASS 且 `git.branch_closed != true` 时必须调用。跳过 = 违规。

以上操作的详细执行步骤见 `./workflow.md`。
</HARD-GATE>

## 集成

| 技能 / Rule | 关系 |
|-------------|------|
| `autonomy-loop` | 会话恢复调 recover；阶段开始前调 start-stage；Stage Gate PASS 后调 commit-artifact；delivery 完成或用户要求收尾时调 close |
| `intake` | 产生 mission-id / slug 后触发 prepare；正式 mission-contract 在 intake stage worktree 中完成 |
| `execute` | 执行阶段在 execute stage worktree 中按 TDD 节奏 commit |
| `stage-gate` | PASS 后触发 commit-artifact；FAIL / BLOCKED 时保留 stage worktree |
| `finishing-branch` | close 操作委托给分支收尾工作流 |

按 `workflow.md` 执行详细步骤。
