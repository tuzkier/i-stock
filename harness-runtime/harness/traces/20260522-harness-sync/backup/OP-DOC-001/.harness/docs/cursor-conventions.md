# Cursor 模板约定

本文说明 HarnessV2 在 Cursor 中的当前接入方式。Cursor 只保留薄入口；规则、技能、Agent 的权威正文都在 `.harness/common/`。

## 当前结构

| 类型 | 路径 | 说明 |
|------|------|------|
| Cursor 入口 rule | `.cursor/rules/harness.mdc` | `alwaysApply` 入口，指向共享 Harness 正文 |
| Cursor hook | `.cursor/hooks.json` | Cursor 专属 hook 配置 |
| Cursor CLI 权限 | `.cursor/cli.json` | 允许审查类 Agent 读取默认 stage worktree 路径 `.worktrees/**` |
| 启动入口 | `AGENTS.md` | 轻量入口，指向按需导航和 `skill-router` |
| 完整导航索引 | `.harness/docs/harness-navigation.md` | 阶段、技能、Agent、runtime 路径的人类查表入口 |
| 规则 / 技能 / Agent | `.harness/common/` | 工具无关权威正文 |
| 模板配置 | `harness-runtime/config/harness.yaml` | 所有可配置项的唯一来源 |
| 任务契约 | `harness-runtime/harness/missions/<id>/mission-contract.md` | 任务目标、范围、AC 和治理级别的权威 |
| 阶段文档 | `harness-runtime/harness/stages/<id>/` | 各阶段产出的唯一权威 |
| 审批记录 | `harness-runtime/harness/state/approvals.json` | 人工审批的唯一权威 |
| 任务状态 | `harness-runtime/harness/mission-status.yaml` | 当前 Mission Slice 执行状态缓存 |
| 执行日志 | `harness-runtime/harness/state/trace-log.md` | 当前任务执行记录的唯一权威（步骤级，跨会话恢复核心） |

上表路径是当前环境的权威路径；源码仓库和安装后的目标项目会呈现不同前缀，但语义一致。

不要在 `.cursor/` 下维护技能或 Agent 镜像。Cursor 入口只负责告诉 Cursor 去读共享正文。

状态只能从这些权威文件读取，不从会话记忆或普通 markdown 文案推断。

## 入口加载方式

`.cursor/rules/harness.mdc` 是 `alwaysApply` 薄入口。它只要求 Cursor 读取根 `AGENTS.md` 的启动胶囊，不在会话启动时预加载全部规则、技能、Agent 或 runtime 状态。

需要路由时，读取 `.harness/common/skills/skill-router/SKILL.md` 和 `workflow.md`；再按其结果读取对应技能、规则、Agent、脚本或模板。

当产出阶段文档时，再按 workflow 或 Gate 要求读取 `.harness/common/rules/stage-doc-standard.md`。

规则层只管约束和调度。所有“做事”的逻辑在技能层，所有“角色化分析”在 Agent 层。

## Hook 机制

`package/adapters/cursor/hooks.json` 是 Cursor 专属 hook 源文件，安装后复制到 `.cursor/hooks.json`。

当前 hook 只作为入口能力保留。即使 hook 未实现自动续跑，自治循环仍能工作：进入恢复或阶段推进场景时，按 `core.md` 的恢复协议读取配置、mission-status、执行日志和 git-workflow 状态。

## CLI 权限

`package/adapters/cursor/cli.json` 是 Cursor 项目级 CLI 权限源文件。首次安装时写入 `.cursor/cli.json`；目标项目已有 `.cursor/cli.json` 时，安装脚本只合并缺失的 `Read(.worktrees/**)`，保留项目已有配置。

Harness 默认在 `<repo-root>/.worktrees/<mission-id>-<phase>` 创建 stage worktree。Cursor 的 readonly reviewer 在某些 protected worktree 场景下可能无法读取该路径，导致 `spec-reviewer` 无法验证代码证据。因此 Cursor adapter 默认允许：

```json
{
  "permissions": {
    "allow": [
      "Read(.worktrees/**)"
    ]
  }
}
```

不要在模板里默认加入 `Write(.worktrees/**)` 的 deny 规则。Cursor 的项目级权限不是 Harness role-specific 权限；全局禁止写 `.worktrees/**` 可能阻断执行类 Agent 在 stage worktree 中完成实现。`readonly: true` 的含义仍是审查类 Agent 不修改项目文件。

如果项目在 `project-context.md` 中声明了非默认 worktree 根目录，项目维护者需要在目标项目的 `.cursor/cli.json` 中额外加入对应 `Read(<path>/**)`。

如果目标项目已有 `deny` 规则覆盖 `.worktrees/**`，Cursor 会优先执行 deny；此时必须先调整目标项目权限，否则 reviewer 仍可能无法读取 stage worktree。

## 子 Agent 模型路由

Cursor 子 Agent 的模型候选由 `harness-runtime/config/model-routing.yaml` 的 `adapters.cursor` 配置统一维护，workflow 和 Agent 定义不得硬编码模型名。安装器会把每个 role 的首选候选模型写入 `.harness/common/agents/<role>.md` 的 frontmatter `model` 字段；只有没有候选模型时才保留 `model: inherit`。

默认分层策略：

| 层级 | 适用角色 | 默认候选 |
|------|----------|----------|
| tier-1 | 前期分析、需求、架构、交互设计、依赖影响执行角色 | `claude-opus-4-7-thinking-high` → `gpt-5.5-medium` → `gemini-3.1-pro` |
| tier-2 | 规划阶段 effectiveness reviewer | `claude-4.6-sonnet-medium-thinking` → `gpt-5.5-medium` |
| tier-3 | 任务拆解、验证、交付、代码审查、规格审查 | `claude-4.6-sonnet-medium-thinking` → `gpt-5.5-medium` |
| tier-4 | execute 阶段工程专家 | `composer-2-fast` |

Cursor 的 `model` 字段必须使用 Cursor 实际支持的精确 slug。只有展示名但没有确认 slug 的模型不得写入候选列表；候选不可用时按配置回退 `main_agent` 并记录 `model_resolution` evidence。

## 初始化流程

不要把 `HarnessV2/` 整体复制到业务项目根目录。使用安装脚本。

### Greenfield

```bash
python3 install.py /path/to/project --adapter cursor
```

安装后修改：

```text
harness-runtime/config/harness.yaml
```

设置：

```yaml
project_name: "<project-name>"
brownfield: false
```

### Brownfield

```bash
python3 install.py /path/to/project --adapter cursor
```

安装后修改：

```yaml
project_name: "<project-name>"
brownfield: true
```

已有旧版 Harness 目录时使用：

```bash
python3 install.py /path/to/project --adapter cursor
```

Brownfield 项目首次进入 Harness 流程时，AI 会调度 `generate-context` 技能扫描现有代码并生成 `project-context.md`。

## 维护 Cursor 入口

维护 HarnessV2 模板仓库时，修改公共正文后，根目录自测入口需要同步：

```bash
python3 scripts/sync_adapters.py --adapter cursor
```

修改 Cursor 专属入口源文件时，编辑：

```text
package/adapters/cursor/
```

然后再次运行同步命令。

## 多运行时关系

当前模板同时提供：

- `.harness/common/`：规则、技能、Agent 的单一正文来源
- `package/adapters/cursor/`：Cursor 薄入口
- `package/adapters/claude/`：Claude Code 薄入口
- `package/adapters/windsurf/`：Windsurf 薄入口
- `package/adapters/antigravity/`：Antigravity 薄入口
- `package/adapters/opencode/`：OpenCode 薄入口（`opencode.json` + 根 `AGENTS.md`）
- `package/adapters/pi/`：Pi Coding Agent 薄入口（`.pi/skills` + `.pi/extensions/`）
- `AGENTS.md`：Codex / OpenCode / Pi 的项目入口

Codex 的详细约定见 `.harness/docs/codex-conventions.md`。
