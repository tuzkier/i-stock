# Harness Workflow 作者约定

本文定义 Harness skill `workflow.md` 的标准写法。目标是让 workflow 同时满足两类读者：

- 人类和 Agent 能快速读懂执行流程。
- Harness / adapter / lint 能稳定识别关键控制点、权限边界、产物和 gate。

## 核心风格

Harness workflow 采用 XML 外层 + Markdown 内文的混合结构：

- XML 外层用于表达 workflow 的一级语义边界。
- Markdown 表格、列表和段落用于表达 section 内部内容。
- 只有确实被 install / adapter / lint / hook 明确消费的控制点，才使用更细的 XML 标签。普通步骤、条件、循环、分支、CLI 调用、gate 说明、失败恢复策略都写成 Markdown。

推荐外层结构：

```xml
<workflow stage="..." version="...">

<goal>
...
</goal>

<role>
...
</role>

<invariants>
| ID | Check | Enforced by |
|---|---|---|
</invariants>

<entry>
- ...
</entry>

<exit>
- ...
</exit>

<permissions>
| Effect | Pattern | Reason |
|---|---|---|
</permissions>

<subagents>
| Role | Mode | Scope | Package |
|---|---|---|---|
</subagents>

<inputs>
| Ref | Required | Plane |
|---|---|---|
</inputs>

<outputs>
| Artifact | Path | Kind |
|---|---|---|
</outputs>

<steps>
<step id="step-0" n="0" goal="初始化">
- ...
</step>
</steps>

<failure_paths>
| Failure | Trigger | Handling |
|---|---|---|
</failure_paths>

</workflow>
```

## 标签边界

稳定保留的一级标签：

| 标签 | 用途 |
|---|---|
| `<workflow>` | workflow 元数据和根节点 |
| `<goal>` / `<role>` | 当前技能的任务目标和执行身份 |
| `<invariants>` | 必须持续成立的约束 |
| `<entry>` / `<exit>` | 阶段进入和退出条件 |
| `<permissions>` | 权限覆盖的自文档化镜像 |
| `<subagents>` | 子 Agent role、读写权限和 prompt package |
| `<inputs>` / `<outputs>` | 必读输入与产物输出 |
| `<steps>` / `<step>` | 执行步骤边界 |
| `<failure_paths>` | 失败路径和恢复策略 |

允许保留的细粒度标签：

| 标签 | 使用条件 |
|---|---|
| `<dispatch>` | 需要调度子 Agent，或需要 adapter 改写 native dispatch |

默认禁用的标签：

| 标签 | 约束 |
|---|---|
| `<call>` / `<check>` / `<loop>` / `<branch>` / `<case>` / `<hard_gate>` / `<HARD-GATE>` / `<user_checkpoint>` | 默认改用 Markdown 列表；只有新增并登记了明确解析器 / hook owner 时才允许 |
| `<action>` | 不要逐句包裹普通动作；用 Markdown 列表 |
| `<invariant>` / `<condition>` / `<criterion>` / `<deny>` / `<allow>` / `<input>` / `<artifact>` / `<failure>` / `<recovery>` / `<stage_transition>` / `<next>` | 默认改用 Markdown 表格或列表；除非已有解析器明确消费这些标签并在 lint allowlist 中登记 |

`<permissions>` 内部使用 Markdown 表格时，install pipeline 会读取 `Effect / Pattern / Reason` 三列并投影为 runtime overlay；不需要再写 `<deny>` / `<ask>` / `<allow>` 行级标签。

## 步骤写法

推荐写法：

```xml
<step id="step-0" n="0" goal="初始化">

- 调用 `harness mission stage start --mission <mission-id> --stage <stage> --json`。
- 调用 `harness config snapshot --json`，读取 stage policy、model routing 和 spec 开关。
- 调用 `harness frame current --mission <mission-id> --json`，校验当前 lane。

</step>
```

不推荐写法：

```xml
<step id="step-0" n="0" goal="初始化">
  <action>调用 ...</action>
  <action>调用 ...</action>
  <action>调用 ...</action>
</step>
```

`Task Envelope` 不要塞进一个超长 `<action>`。推荐用标题和列表表达：

```xml
<dispatch role="interaction-designer" mode="spawn" />

Task Envelope 必须包含：

- 任务目标。
- 输入路径和已读取摘要。
- 输出路径和 write_scope。
- 完成条件。
```

## 密度预算

这些是作者侧预算，不是为了压缩内容，而是为了保证 workflow 可读：

- 普通 lane workflow 目标控制在 300-350 行以内；复杂 orchestrator 可以更长，但应通过拆分引用文件或 mode 文件降低主流程负担。
- `<action>` 密度应很低。目标是不超过每 100 行 2 个；若明显超过，应改用 Markdown 列表。
- section 内部避免堆叠一行一个 XML 标签；能用表格表达的规则、权限、输入输出、失败路径，优先用表格。
- 单个动作描述如果超过约 80 个中文字符，优先拆成列表。
- 长 prompt、审查清单、示例模板、领域方法论放到 `references/`、`harness-runtime/templates/`、`modes/` 或专门文档中，workflow 只保留入口和控制点。

## 迁移规则

将旧 workflow 迁移到本约定时，必须保持语义等价：

- 不改变 CLI 命令、gate、hook、overlay、输入输出和子 Agent 权限。
- 不删除已经存在的 failure path。
- 如果发现实质缺口，可以在迁移中补齐，但要在变更说明中单独列出。
- 先迁移暴露问题的 workflow，再逐步推广到其它 workflow，避免一次性大面积改写造成语义漂移。

## 文案与原型约束

涉及 prototype、HTML / SVG 变体、preview 或用户可见界面文案时：

- 默认使用中文。
- 品牌名、产品专名、代码标识、行业通用英文缩写或上游明确指定的外语文案可以保留原文。
- 例外项必须在对应 consistency report 或审查记录中说明来源和理由。
