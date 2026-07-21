---
name: _index
description: Harness commands index — stable triggers for permissioned update / migration / adapter changes after install.
---

# Harness Commands

本目录把若干 Harness 流程做成稳定命令，让 AI coding agent / 用户以同一个触发名进入同一份 procedure，不依赖自然语言转述。命令分两类：**运行时触发**（如 `harness-run`，把当前任务显式送进 Harness 流程，不改框架资产）与**安装后维护**（如 `harness-upgrade` / `harness-add-adapter`，按 INSTALL.md 权限化变更协议刷新框架正文 / adapter / runtime 结构）。

## 命令清单

| 命令 | 用途 | 资产类别 |
|---|---|---|
| `harness-run` | 显式触发 Harness 流程的前门动词：打印可见启动声明 → 无条件路由 → 按意图分派到 intake / board-router / bug-fix 等阶段技能，强制"这件事走 Harness、不直接执行" | 运行时触发（无 mutation） |
| `harness-upgrade` | 把已安装项目升级到新版本模板：一份持久化、可断点续跑的升级 checklist，刷新框架正文与 runtime 结构、对 `harness.yaml` 做三方迁移（保留项目设置）、按已装 adapter 重渲染入口、验证 + 留回滚点 | A+B+C+D+E |
| `harness-add-adapter` | 已安装项目追加一个新的 adapter（写入根入口 + adapter 目录） | B 类（adapter 入口） |

> 旧的 `harness-update`（只能动框架正文、碰不了 yaml）与 `harness-migrate`（钝刀全量替换 yaml）已退役合并进 `harness-upgrade`——真实版本升级几乎总是同时动框架正文和 yaml 结构，二者拆开互相漏接。追加 adapter 仍是独立动作（加能力，非升版本），保留 `harness-add-adapter`。

## 调用入口

- **Claude Code**：`.claude/commands/<name>.md` 自动作为 slash command 出现
- **Cursor**：`.cursor/commands/<name>.md` 同上
- **OpenCode**：`.opencode/command/<name>.md` 同上
- **Codex / Antigravity / Windsurf / Pi**：通过各自入口文件指向 `.harness/common/commands/<name>.md`

## 单源正文

`.harness/common/commands/` 是权威正文。各 adapter 副本由 install.py 渲染，不要直接编辑 adapter 目录下的命令文件。修改命令必须改源码仓库 `package/common/commands/`，重新运行安装。
