# Harness Core

`.harness/common/` 是 HarnessV2 的工具无关正文。

只在这里维护以下正文：

- `rules/` — 全局规则
- `skills/` — 可执行工作流
- `agents/` — sub-agent 角色定义
- `cli/` — Harness CLI 控制面实现
- `schemas/` — typed control_contract.v1 schema
- `protocols/` — 跨 stage 接口协议
- `runtime-overlay/` — stage-aware 权限 overlay
- `hooks/` — 运行时 hook 包（重构中，本版本不安装；见 `hooks/README.md`）

## Professional Roles

专业角色控制面在 `.harness/common/` 内闭环：

- 角色提示词放在 `agents/`，安装后位于 `.harness/common/agents/`。
- role policy、obligation、Evidence Graph、Gate policy schema 放在 `schemas/control_contract.v1/`。
- Stage Gate 的 resolver / checker 放在 `skills/stage-gate/scripts/`。

运行时工作流不得引用只存在于 HarnessV2 源码仓库的维护者设计目录；安装后目标项目只保证存在 `.harness/common/`、`.harness/docs/` 和 `harness-runtime/`。

`.claude/` 和 `.cursor/` 是生成出来的运行时适配目录。修改 core 后执行：

```bash
python3 scripts/sync_adapters.py
```

同步规则：

- Cursor 规则生成 `.mdc` 并补齐 frontmatter。
- Claude 规则生成普通 `.md`。
- 技能 / Agent 按当前工具路径改写引用。
- `config.json`、token cache、本地密钥文件不进入 core，也不会被同步覆盖。

Codex 不维护独立技能 / Agent 镜像，也默认不安装 `.codex/`。Codex 通过根 `AGENTS.md` 指向 `.harness/common`，并在需要时直接读取共享规则 / 技能 / Agent 正文。
