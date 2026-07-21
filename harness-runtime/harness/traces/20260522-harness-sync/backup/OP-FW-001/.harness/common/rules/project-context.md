# Project 上下文

## 启动时必须读取

**每次开始新的任务或新的对话时**，先调用 `harness-cli` 执行 `harness context check --json`：

- 返回 PASS → 读取项目根目录的 `project-context.md`，再装配当前 Mission 的 `mission-contract.md`。
- 返回 FAIL → 按下文「当 project-context.md 不存在时」处理；不得跳过本检查直接装配 mission-contract，也不得当作可选输入忽略。

读取后，提取以下信息并在整个执行过程中遵守：

- 架构约束（哪些模式是强制的、哪些是禁止的）
- 编码规范（命名、错误处理、日志格式）
- 技术选择（禁止自作主张替换已选型的技术）
- 历史教训（不要重复已知的坑）

## 当 project-context.md 不存在时

`harness context check` FAIL 时，按以下优先级处理，不得静默继续：

1. **棕地项目**：调度 `generate-context` 技能扫描现有代码，调用 `harness context init` 创建文件。
2. **绿地项目**：调用 `harness context init` 从模板创建一份骨架；填充工作可在第一轮执行后由 AI 主动询问用户补全。
3. 如果当前阶段无法立即创建（例如用户明确暂时跳过），必须把 `project_context_missing=true` 写入当前阶段 evidence carrier 或 Mission Slice 的 `degradations[]`，让下游 Stage Gate 看见缺失，不允许只在 markdown 末尾 prose 形式记录。

## 执行中更新 project-context.md

当在执行过程中发现了新的项目规则、踩了新的坑、或确认了新的技术决策时：

- 将发现记录到 project-context.md 的**历史教训**部分
- 格式：`- <YYYY-MM-DD> <具体描述，以"应该/不应该/必须/禁止"开头>`
- 不要等到交付时再整理，发现了就立刻记录

## 注意事项

- project-context.md 的规则优先级高于 AI 的默认编码偏好
- 如果 project-context.md 的规则与任务契约有冲突，以任务契约为准并记录差异
- 如果 project-context.md 与 `project-knowledge/engineering/policies/stage-rules.yaml` 冲突，`stage-rules.yaml` 中的机器可校验规则优先；project-context.md 负责解释项目背景、历史教训和无法结构化的约束
- 不要让 project-context.md 变成大杂烩，只记录对 AI 有用的、不显眼的约束
