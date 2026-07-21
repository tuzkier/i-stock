---
name: _index
description: Harness commands index — stable triggers for permissioned update / migration / adapter changes after install.
---

# Harness Commands

Harness 安装之后，`install.py` 不再负责更新和迁移。这些动作必须按 INSTALL.md 中的权限化变更协议执行。本目录把那些流程做成稳定命令，让 AI coding agent 以同一个触发名进入同一份 procedure，不依赖自然语言转述。

## 命令清单

| 命令 | 用途 | 资产类别 |
|---|---|---|
| `harness-update` | 用新模板刷新 `.harness/common/**`、`.harness/docs/**`、`.harness/workflow-map.html` | A 类（框架） |
| `harness-migrate` | 完整模板迁移：保留 runtime 数据 + 历史结果，按权限化 operation 切换到新模板 | A+B+C+D+E |
| `harness-add-adapter` | 已安装项目追加一个新的 adapter（写入根入口 + adapter 目录） | B 类（adapter 入口） |

## 调用入口

- **Claude Code**：`.claude/commands/<name>.md` 自动作为 slash command 出现
- **Cursor**：`.cursor/commands/<name>.md` 同上
- **OpenCode**：`.opencode/command/<name>.md` 同上
- **Codex / Antigravity / Windsurf / Pi**：通过各自入口文件指向 `.harness/common/commands/<name>.md`

## 单源正文

`.harness/common/commands/` 是权威正文。各 adapter 副本由 install.py 渲染，不要直接编辑 adapter 目录下的命令文件。修改命令必须改源码仓库 `package/common/commands/`，重新运行安装。
