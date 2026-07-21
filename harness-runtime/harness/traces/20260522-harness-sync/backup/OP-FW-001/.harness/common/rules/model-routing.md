# 模型路由规则

公共 workflow 不写具体模型名。模型 ID 是 adapter 私有命名空间，由 `harness-cli config snapshot --json` 暴露摘要；调用方不直接读取 `model-routing.yaml`。

## 解析顺序

1. 当前 adapter 的 `roles.<role>.candidates` 或 `roles.<role>.inherit`。
2. 没有角色专属配置 → 执行类 Agent 走 `defaults.execution`，审查类 Agent 走 `defaults.review`。
3. 按候选顺序选择当前 adapter 支持的第一个模型名。
4. 候选模型**全部不可用**时，按下文「降级语义」处理。

## 降级语义

降级只覆盖一种情况：**已经被成功 dispatch 的 sub-agent，其候选模型在当前 adapter 上全部不被支持**。

| YAML 中 `fallback` 取值 | 含义 |
|------------------------|------|
| 未设置 / `null` | 不允许降级，本次调用 BLOCKED；返回上层由 stage workflow 决定是否升级或暂停 |
| `default_model` | 改用 adapter 的 `defaults.<kind>` 候选；仍不可用则 BLOCKED |
| `main_agent` | 由当前 coding agent 以同一 role prompt package 就地执行（仍要遵循该角色的 Output Contract）；必须写 evidence |

**绝对不允许**用 `fallback` 处理另一类失败场景：**命名 sub-agent 在当前 adapter 上根本无法 dispatch**（例如 Claude Code 没注册该 subagent_type）。这种情况必须 BLOCK 当前阶段，不能用 `main_agent` 顶替；判定与处置见 `autonomy-loop.md`。

## Evidence

每次 sub-agent 调用必须记录 `model_resolution` evidence：

- `requested_role`：声明的角色名
- `adapter`：当前 adapter
- `candidates`：实际尝试的模型候选列表
- `selected`：选中的模型名（或 `null`）
- `fallback_used`：`none` / `default_model` / `main_agent`
- `reason`：触发降级或失败的原因

## Adapter 调用要求

- **Codex**：`spawn_agent` 默认会继承父 Agent 模型，因此调用前必须从 `harness config snapshot --json` 的 `model_routing.roles[role]` 解析候选模型，并在调用时显式传 `model=<selected_model>`。省略 `model` 只允许在配置没有候选且 fallback 已记录为 `main_agent` 时发生。
- **Cursor**：安装器把 `.harness/common/agents/<role>.md` 渲染为 `.harness/common/agents/<role>.md` 时，必须把 `adapters.cursor.roles.<role>.candidates[0]` 或对应 default candidates[0] 写入 frontmatter `model`；没有候选时才写 `model: inherit`。
- **Claude / OpenCode / 其他 adapter**：使用各自 runtime 原生 dispatch 方式；若 runtime 支持调用时模型参数，应按同一解析结果显式传入。若不支持或候选为空，必须在 `model_resolution` evidence 中说明 selected/fallback，而不能静默假定已使用配置模型。

## 默认策略

| Agent 类型 | 候选来源 | 备注 |
|-----------|----------|------|
| 执行类 Agent | adapter 的 `defaults.execution` | 不默认使用高级模型 |
| 审查类 Agent | adapter 的 `defaults.review` | 默认优先高级模型 |
| 公共 workflow | 只声明角色名和输出契约 | 不写 `model: "fast"` 或任何具体模型 ID |
