---
name: harness-add-adapter
description: 在已安装 Harness 的项目中追加一个新的 adapter（写入根入口 + adapter 目录 + 渲染 agents / skills / commands 副本），不动现有 adapter 与 runtime 数据。
argument-hint: "<adapter-name> [upstream-source-path]"
scope: post-install
requires:
  - <upstream-source>/INSTALL.md
  - .harness/common/rules/core.md
asset_class: B
permission: approve-adapter
---
<!-- Generated for adapter `cursor` from .harness/common/commands/. Edit the source, then re-run install. -->

# /harness-add-adapter

为已安装 Harness 的项目追加一个 adapter（claude / cursor / codex / opencode / windsurf / antigravity / pi）。`install.py` 首次安装支持 `--adapter`，但安装后追加 adapter 同样必须走权限化变更——本命令把这件事固化为稳定 procedure。

## 触发条件

- 项目已经安装过 Harness
- 用户希望让一个新的 AI coding agent 也能调用同一份 Harness 控制面
- 当前项目缺少该 adapter 的入口文件或 `.<adapter>/` 目录

## 严格不做

- 不动其它已存在的 adapter 入口（既有 `AGENTS.md` / `CLAUDE.md` / `.cursor/**` 等不在本次范围里）
- 不动 `.harness/common/**` 框架正文（那是 `/harness-upgrade` 的事）
- 不动 runtime 数据
- 不重新渲染已有 adapter 的 agents / skills / commands 副本

## 参数

- `$1` adapter 名（必填，必须在 `{claude, cursor, codex, opencode, windsurf, antigravity, pi}` 内）
- `$2` 上游 HarnessV2 源码路径（可选；缺省时要求用户提供，不要自己猜）

## 执行 procedure

### 1. 前置检查

- 校验 adapter 名合法
- 目标项目存在 `.harness/common/rules/core.md`
- 目标项目**尚未**有该 adapter 的根入口文件（如 claude → `CLAUDE.md`、windsurf → `.windsurfrules`）。若已存在，停下并提示走 `/harness-upgrade` 或人工 diff
- 上游 `<upstream>` 存在 `install.py` 与对应 `package/adapters/<adapter>/adapter.json`

### 2. 列出待写入路径

读 `<upstream>/package/adapters/<adapter>/adapter.json` 中的 `installs`，再结合 install.py 的渲染规则推导：

| 类 | 路径 | 来源 |
|---|---|---|
| 入口文件 | `AGENTS.md` / `CLAUDE.md` / `ANTIGRAVITY.md` / `.windsurfrules` / `opencode.json` 等（按 adapter） | `<upstream>/package/adapters/<adapter>/` |
| adapter 目录 | `.<adapter>/**`（除 codex 外） | adapter 目录拷贝 + install.py 的渲染 |
| Agents 副本 | `.<adapter>/agents/**`（仅 claude / cursor / opencode） | 由源码 agents 目录渲染 |
| Skills 副本 | `.<adapter>/skills/**`（仅 claude / cursor / opencode） | 由源码 skills 渲染 |
| Commands 副本 | `.<adapter>/commands/**` 或 `.opencode/command/**`（仅原生支持的 adapter） | 由源码 commands 渲染 |
| Hooks / cli | `.cursor/hooks.json`、`.cursor/cli.json`、`.claude/settings.local.json` 等（按 adapter） | adapter 目录 + 已有合并规则 |

写入 `harness-runtime/harness/traces/<YYYYMMDD>-add-adapter-<adapter>/plan.md`，逐项标注 operation / source / verification。

### 3. Decision Gate

plan 末尾追加 explicit user approval：

```markdown
## Explicit User Approval
- Approved operation ids:
- Rejected operation ids:
- Accepted risks:
```

等待用户填回。

### 4. 执行

允许的两种执行方式（用户在 plan 中选一种）：

**A. 委托 install.py**（推荐）
- 在 `<upstream>` 下运行 `python3 install.py <target> --adapter <adapter> --entry-policy keep`
- `--entry-policy keep` 保护其它 adapter 的入口文件
- 但仍会写入新 adapter 的入口（install.py 的 keep 仅跳过已存在文件，对不存在的新入口仍然创建）

**B. 显式 operation**
- 按 plan 表逐项写入
- 写入前备份目标路径到 `backup/<op-id>/`
- 每完成一项打 `[done]`

### 5. 验证

```bash
harness-runtime/bin/harness --root . control status --json
```

- 列出新 adapter 的入口文件、agents 数量、skills 数量、commands 数量
- 抽样运行一个 read-only 子 Agent 调度（如 `discovery-effectiveness-reviewer`）确认 adapter 能识别 Harness 角色
- 结果落 `verify.log`

### 6. 收尾

- 读 `<upstream-source>/INSTALL.md` 确认新 adapter 已在安装说明中覆盖
- 在 plan 末尾追加 `## Result` 区块

## 输出契约

- `harness-runtime/harness/traces/<YYYYMMDD>-add-adapter-<adapter>/plan.md`
- `harness-runtime/harness/traces/<YYYYMMDD>-add-adapter-<adapter>/backup/**`
- 新增的 adapter 入口与 `.<adapter>/**` 目录

## 拒绝执行的情形

- adapter 名非法
- 目标 adapter 入口已存在
- 上游 adapter.json 缺失
- 用户未给出 Approved operation ids
