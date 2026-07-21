# harness hook 包（重构进行中 / WIP）

> **状态：未完成，且本版本不安装到任何项目。**
> `install.py` 里 `INSTALL_HOOKS_ENABLED = False`——安装时不再产出任何
> `.claude/hooks/`，`.claude/settings.json` 也不写 `hooks` 段（permission
> overlay 的 `deny/ask/allow` 不受影响，照常安装）。

## 这个包要解决什么

旧 hook 模型：87 个独立脚本散在 `.harness/common/runtime-overlay/hooks/<stage>/`，
install 时把其中 78 个全部注册进 `.claude/settings.json` 的 `hooks` 段。后果：

- 一次 `Edit` / `Bash` 会 fork 30+ 个 hook 子进程，绝大多数立刻空转返回。
- hook 运行时不知道自己属于哪个 stage，只靠 tool_name / 命令正则自我过滤。
- 大量重复逻辑（`--mission` 正则、contract YAML 读写、危险 git 检测）在
  几十个脚本里各写一份，且口径不一致。

本包把它重构成**单一 dispatcher + 包内直接引用**的形态（类比 `cli/`）：

- `.claude/settings.json` 只注册 **2 条** dispatcher 入口（PreToolUse /
  PostToolUse 各一条），全部指向 `dispatch.py`。
- `dispatch.py` 读 payload → 从 `mission-status.yaml` 解析当前 mission
  stage → 只跑该 stage 的 check，**进程内函数调用**，一次工具调用最多 1 个
  子进程。

## 包结构

```
hooks/
  dispatch.py        单一入口；settings.json 注册它
  context.py         HookContext —— 规范化的 hook payload 视图
  result.py          HookResult（allow | block）
  entry.py           HookEntry —— 注册表里的一条 check
  registry.py        REGISTRY: stage -> [HookEntry]
  lib/               共享 helper
    contracts.py       contract YAML 读写 / unwrap / pending-recheck
    commands.py        harness 命令解析 + 危险 git 检测
    runtime.py         mission-status / gate report / trace / overlay / approvals
    paths.py           glob 路径匹配
    roles.py           reviewer / worker 角色判定
  checks/            按 stage 分的 check 函数
    intake.py discovery.py prd.py design.py breakdown.py code_review.py
    execute.py verify.py delivery.py finishing_branch.py retrospective.py
    baseline.py
```

check 签名：`def check_xxx(ctx: HookContext) -> HookResult`。
每个 stage 模块导出 `ENTRIES: list[HookEntry]`。

## 当前进度（截至本次会话）

已完成：

- 地基：`context / result / entry / dispatch / registry / lib/*` 全部建好并通过冒烟测试。
- 87 个旧 hook 已迁移成 81 个 `HookEntry`（design 三 lane 的 9 个克隆合并成 3 个）。
  registry 全图导入通过，id 唯一。
- `install.py` 的 `install_hooks` 已改写为 dispatcher 模型（随后用
  `INSTALL_HOOKS_ENABLED` 关掉）。
- 测试：`tests/test_intake_hooks.py` / `test_discovery_hooks.py` /
  `test_prd_hooks.py` 已改写为走 dispatcher，59 个测试通过。

**未完成（重构恢复时要做）：**

1. 另外 9 个测试文件仍引用旧 hook 路径，未改写，会失败：
   `test_design_hooks.py`、`test_breakdown_hooks.py`、`test_code_review_m2_m4.py`、
   `test_m5_anchor.py`、`test_execute_hooks.py`、`test_verify_m2_m4.py`、
   `test_delivery_m2_m4.py`、`test_retrospective_m2_m4.py`、`test_stages_9_13.py`。
2. 旧目录 `.harness/common/runtime-overlay/hooks/`（87 脚本 + 13 个
   `hooks.json`）尚未删除——等上面的测试全部迁移完再删。
3. dispatcher 端到端验证：尚未在真实 Claude Code 里跑过 PreToolUse /
   PostToolUse 实际触发，只做了 `python3 dispatch.py` 喂 payload 的离线验证。
4. settings.json 注册形态（2 条入口的 matcher / `{matcher,command}` 格式）尚待最终确认。

完成上述后，把 `install.py` 的 `INSTALL_HOOKS_ENABLED` 翻回 `True` 即重新启用安装。

## 迁移时一并修掉的旧 bug（已在本包修正）

- **finishing-branch approvals 路径错**：旧 `deny_force_push` /
  `deny_hard_reset` / `check_cleanup_authorization` 读的是
  `harness-runtime/state/approvals.json`（少了 `/harness/` 段），导致
  boundary 批准永远找不到。新包统一走 `lib/runtime.load_approvals`，路径正确。
- **prd `mark_pending_recheck` 死代码**：旧脚本里 `_contract_path_from_prd`
  函数从未被调用。新包已丢弃。
- **`--mission` 正则不统一**：旧脚本有三种写法。新包统一为
  `lib/commands.mission_id`。
- **危险 git 检测口径分裂**：code-review / delivery / finishing-branch 各写
  一套正则、覆盖面不同。新包统一为 `lib/commands.git_danger`（按 kind 分类）。

## 旧 hook 的去向

旧 87 个脚本仍在 `.harness/common/runtime-overlay/hooks/`，作为重构未完成期间
的参照与未迁移测试的依赖；重构收尾时删除。`install.py` 已不再引用该目录。
"""HarnessV2 hook package.

A single dispatcher (`dispatch.py`) is registered as the Claude Code
PreToolUse / PostToolUse hook entry. It resolves the active mission stage and
runs only that stage's checks, in-process — replacing the legacy model of one
standalone script per check registered globally in settings.json.

Layout:
  context.py   HookContext / payload parsing
  result.py    HookResult (allow | block)
  registry.py  stage -> event -> [HookEntry]
  dispatch.py  entry point
  lib/         shared helpers (contracts, commands, runtime, paths, roles)
  checks/      per-stage check functions
"""
