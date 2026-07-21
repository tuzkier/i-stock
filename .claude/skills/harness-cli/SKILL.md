---
name: harness-cli
description: '当需要调用 Harness CLI、执行 `harness ...` 命令、读写 Harness 控制面状态、运行 Control/Gate/Board/Work Graph/Contract/Evidence/Lint/Mission/Approval/Frame 命令时使用；可通过 CLI 完成的控制面操作必须先进入此技能，不直接拼接底层脚本或手写控制面文件。'
---

# Harness CLI

Harness CLI 是 Harness 控制面命令和 CLI 支持的结构化运行时文件访问的统一入口。凡是工作流、Agent 或用户请求中出现可由 `harness` 命令完成的动作，或需要读取/修改 CLI 已支持的 Harness 控制面文件，都先使用本技能解析能力、选择可执行入口、执行并消费结果。

## 何时使用

- 用户明确说“运行 harness cli”“用 harness 命令”“看 harness 状态”“检查 Gate”“推进 Board”“重建 Work Graph”“收集 evidence”等。
- 任意 Harness workflow 要调用 `harness ...` 命令。
- 任意规则或 workflow 需要读取/修改 Harness CLI 已支持的结构化控制面文件，例如配置快照、当前 Mission 状态、Mission Slice、Board / Work Graph 派生状态、approval、contract、Gate report、Evidence Graph、project-lint report、project-knowledge 索引。
- 需要通过 CLI 处理以下控制面对象：
  - `config`
  - `control`
  - `frame`
  - `mission`
  - `approval`
  - `graph`
  - `board`
  - `contract`
  - `evidence`
  - `gate`
  - `lint`
  - `knowledge`
- 需要写入或推进 Work Graph node、board/index/tree 派生视图、Mission Slice、Gate report、Evidence Graph、control contract、approval、project-lint report。

## 何时不使用

- 运行目标项目自己的普通测试、构建、lint、typecheck，且这些命令不通过 Harness evidence collector 收集。
- 阅读自由文本阶段文档或解释 Harness 概念，不需要调用 CLI。
- Git 操作；由 `git-workflow` 或当前 coding agent 的 Git 流程处理。
- 外部 API 文档查询；使用 `query-api-docs`。

## 固定规则

- 只要 Harness CLI 可用，不直接调用 `.harness/common/skills/*/scripts/` 或 `.harness/common/skills/*/scripts/` 下的底层脚本。
- 只要 CLI 能处理，不直接读写这些控制面文件：配置、Work Graph node 和派生视图、Mission Slice、当前 Mission 状态、Gate report、Evidence Graph、control contract、approval、project-lint report。
- 规则层和阶段 workflow 不写“读取某个 YAML / JSON 后再判断”的执行口径；应写“调用 `harness-cli` 获取对应控制面快照 / 执行对应控制面写入”。
- 工作流消费命令结果时默认传 `--json`，并记录命令、退出码、关键输出和产物路径。
- CLI 返回 FAIL / BLOCKED 时，不把结果改写为 PASS；按调用阶段进入 `quality-control`、`bug-fix`、`stage-gate` 或原 workflow 的阻塞处理。
- 命令涉及目标项目时必须显式确认 root：源码仓库默认 `harness-runtime/` 资产；已安装项目默认 `harness-runtime/` 和 `.harness/common/`。
- 不因为 PATH 中没有 `harness` 就降级为手改文件；必须按 `workflow.md` 的入口解析顺序找 shim 或 Python CLI。
- 若某个控制面文件尚无 CLI 读写能力，不得把它伪装成已被 `harness-cli` 覆盖；调用方必须记录 CLI 能力缺口，选择补齐 CLI 能力或在当前 workflow 中明确声明一次性降级风险。

## 状态汇报与命令顺序纪律

用户可见状态必须把四类事实分开说清楚：

- `Harness CLI 可用性`：入口是否存在、命令是否能执行、返回码和 typed payload 状态。
- `Mission 运行时状态`：当前是否有 active/open Mission、Mission Slice 是否存在、stage 是否可推进。
- `新任务注册状态`：本轮是否尚未创建 Mission、是否已生成 mission-id、是否已绑定 Work Graph node / Mission Slice。
- `Graphify 状态`：代码索引是否可用、新鲜、已索引；Graphify 未索引只是探索证据降级，不代表 Harness CLI 不可用。

`harness control status` 或 `harness control candidates` 返回空 active/open/candidates 时，只能解释为“没有可恢复 Mission / continue 候选”。如果用户给的是新任务，下一步是正式接入并创建新 Mission，不得写成“没有 active Mission 所以不能继续”或“Harness CLI 不能用”。

控制面写命令必须按依赖顺序串行执行。只有互不依赖的只读查询可以并行；任何会写入 Work Graph、Mission Slice、mission-status、trace、approval、Gate report 或 evidence 的命令完成前，不得并行读取其产物或继续执行依赖命令。典型顺序：`graph node create` → `graph rebuild/check` → `mission create-slice` / `board select --write-slice` → `mission stage start`。

## 命令入口

先按 `<project-root>` 的目录形态选择入口，不得把 PATH 中裸 `harness` 是否存在作为已安装项目或源码仓库的可用性判断。优先级从高到低：

```bash
python3 <project-root>/.harness/common/cli/harness_cli.py --root <project-root> <command> ... --json
<project-root>/harness-runtime/bin/harness --root <project-root> <command> ... --json
harness --root <project-root> <command> ... --json
```

上面第一行在源码仓库中指向模板内 CLI，安装到目标项目后指向 `.harness/common/cli/harness_cli.py`。`harness-runtime/bin/harness` 只是兼容 shim；只有项目内 Python CLI 和本地 shim 都不存在时，才探测 PATH 中的全局 `harness`。若入口都不可用，返回 BLOCKED，并说明缺失的 CLI 路径；不得用手工编辑替代控制面写入。

## 常用命令域

| 命令域 | 用途 |
|--------|------|
| `harness config snapshot` | 读取运行配置、执行模式、规格开关、模型路由摘要、Work Graph lane action 注册表 |
| `harness control status/candidates/frame/guidance/context-index` | Agent-facing 只读恢复查询；先看全局状态和候选，再按显式 mission 读取 frame、guidance 和路径索引 |
| `harness frame current/explain` | 读取当前 Mission Slice、lane action 和节点上下文 |
| `harness mission create-slice/status/stage/close/document` | 创建、读取、推进或关闭 Mission Slice；按 Mission id + 文档类型直接解析规范产物路径 |
| `harness approval append/latest/require` | 写入或检查 Checkpoint / Decision Gate 记录 |
| `harness graph apply/plan/rebuild/check/node show/node create` | 应用 Work Graph operation、重建或检查派生视图，或创建带 lane/stage 的种子节点 |
| `harness board select` | 从 Board 选择 node 并创建 Mission Slice |
| `harness contract init/fill/patch/check/record-review/add-*` | 初始化、更新、检查 control contract；实时 reviewer 结论用 `record-review`，`add-verdict --verdict-file` 只导入已存在的完整 role_verdict manifest |
| `harness evidence graph/add/link/command/visual` | 构建 Evidence Graph、收集命令证据、登记可视化证据 |
| `harness gate run/advance/transition/report/control-reports` | 运行 Gate、渲染报告、Gate PASS 后推进 Work Graph；正常阶段切换优先用 `gate transition` 一次串联 run/advance/next-slice，阶段正文和契约 YAML 分离时同时传 `--artifact` 与 `--contract-artifact` |
| `harness lint runtime/graph/project` | 检查 Harness runtime、Work Graph 或项目约束 |
| `harness knowledge init/check/index/resolve/promote` | 初始化项目知识库、检查索引、按阶段解析需读知识、生成任务收尾知识固化候选计划；`promote --apply` 执行确定性沉淀（规格、主原型入口、promotion ledger），复杂语义提炼由 Agent 补齐 |
| `harness trace log-init/report/step-enter/step-exit` | 写入或统计 per-mission JSONL trace（机器可读跨 session evidence）；确认某阶段写过几次 trace 时用 `trace report --stage <stage>` |
| `harness todo report/sync` | 从 trace 派生 TodoWrite 形态进度，供新 session 恢复 todo list |

按 `workflow.md` 执行入口解析、执行和结果处理。

## TodoWrite ↔ trace 桥接纪律

`harness trace step-*` 是机器可读跨 session evidence（JSONL append-only），TodoWrite 是 session 内人可读 progress（runtime tool）。两者**互补不重叠**，调用方需遵守桥接纪律：

| 触发时机 | 必须做 |
|---|---|
| Milestone 实施开始 | TodoWrite mark in_progress + `harness trace step-enter --step <milestone-id> --note <description>` |
| Milestone 完成 | TodoWrite mark completed + `harness trace step-exit --step <milestone-id> --status pass` |
| Milestone BLOCKED | TodoWrite mark in_progress（保留可见）+ `harness trace step-exit --step <milestone-id> --status blocked --note <reason>` |
| 新 session 接手既有 mission | 先 `harness todo sync --mission <id> --json`，把返回的 todos[] 直接 feed TodoWrite 重建进度 |
| 跨 session 进度审计 | `harness todo report --mission <id> --json` 看 summary（completed / in_progress / blocked 计数）|

约束：

- **`harness todo sync` 是单向桥（trace → todo）**。不存在 `--to-trace` 反向操作 — trace 是 event-sourced，只接受真实 step-enter / step-exit 事件，不接受从 TodoWrite snapshot 回填的合成事件。
- 若 `harness trace log-init` 未跑过，`step-enter` 会 FAIL；workflow Phase 0 必须先 init。
- TodoWrite mark 与 `harness trace step-*` 必须**配对**，避免单边记录导致跨 session 状态对不上。
- `harness todo report` 输出含 `warnings[]`：`trace_log_missing` / `malformed_record:*` / `unknown_exit_status:*` 都是非致命警告，调用方应展示给用户。

## Agent-facing Control 查询协议

当用户表达 `continue`、`status`、`review`、`verify`、`bug_report` 等恢复或状态意图时，调用方先用只读 control 查询建立事实边界，再进入具体阶段技能：

```bash
harness control status --json
harness control candidates --intent continue --json
harness control frame --mission <mission-id> --json
harness control guidance --mission <mission-id> --json
harness control context-index --mission <mission-id> --json
```

约束：

- `harness control status` 只返回运行时状态、Work Graph 摘要、Gate / approval 缺口和一致性 finding。
- `harness control candidates --intent continue` 只返回候选和排序原因；调用方不得把 candidates 当作最终选择，必须由用户意图、显式 mission 或后续 workflow 决定。
- `harness control frame --mission`、`harness control guidance --mission`、`harness control context-index --mission` 必须在 mission 已显式确定后调用。
- `control.context-index` 只给路径索引和存在性，不内联阶段正文，不替代阶段 skill 读取自身输入。
- 阶段 skill 或 Agent 只知道 Mission id 和所需文档类型时，必须用 `harness mission document --mission <mission-id> --type <document-type>` 解析路径；不得从 board / node YAML / stage 目录手工拼路径。常用类型：`task-order`、`product-definition`、`interaction`、`solution`、`tech-design`、`verification-report`、`delivery-package`。
- 若 control 查询不可用而 workflow 临时读取旧 runtime 文件，必须在阶段产物或执行日志中记录 `fallback_used`、`fallback_reason`、`legacy_source`、`follow_up`，并把 `follow_up` 指向补齐 CLI 能力或迁移旧入口；不得静默降级。

## Mission 状态查询

`harness mission status --json` 会读取 `mission-status.yaml` 并返回全部 Mission 状态；需要缩小结果时不要直接解析 YAML，使用 CLI 查询参数：

- `--mission <mission-id>`：返回单个 Mission，并附带 Mission Slice 快照。
- `--active`：仅返回仍有 active Mission Slice 的 Mission。
- `--open`：仅返回未关闭 Mission。
- `--status <status>`：按 Mission `status` 查询，可重复。
- `--current-stage <stage>`：按 `current_stage` 查询，可重复。
- `--stage <stage>` + `--stage-status <status>`：按 `stages` 中的阶段及其状态查询。
- `--ids-only`：只返回匹配的 `mission_ids`，不返回完整 Mission payload。
# Harness CLI 工作流

**Goal:** 为所有 Harness 控制面读写选择正确 CLI 入口，执行结构化命令，并把结果交还调用方。

**Your Role:** 你是 Harness CLI 执行代理。你不解释阶段语义，不替代 stage skill；只负责 root 判定、入口选择、命令执行、结果分类和禁止降级。

---

<workflow skill="harness-cli" version="2">

<step n="1" goal="判断是否必须走 CLI">
 - 条件：用户或阶段 workflow 明确要求运行 `harness ...`
  - 进入本工作流。
 - 条件：需要读取或修改 Harness CLI 已支持的控制面结构化状态或对应 YAML / JSON 文件
  - 进入本工作流。
 - 条件：需要执行 Control、Gate、Board、Work Graph、Contract、Evidence、Lint、Mission、Approval 或 Frame 命令
  - 进入本工作流。
 - 条件：需要读取运行配置快照、执行模式、规格开关、模型路由摘要或 lane action 注册表
  - 进入本工作流。
 - 条件：只是目标项目自己的普通命令，且不需要写入 Harness evidence store
  - 返回调用方继续原流程。
</step>

<step n="2" goal="确认 root 和环境">
 - 判断当前目录：HarnessV2 源码仓库存在 `.harness/common/cli/harness_cli.py`；已安装目标项目存在 `.harness/common/cli/harness_cli.py` 或 `harness-runtime/bin/harness`。
 - 确认 `<project-root>`：用户显式指定路径时使用该路径，否则使用当前 workspace root。
 - 命令需要产物路径时，使用相对 `<project-root>` 的 Harness runtime 路径，不混用源码仓库和已安装项目路径。
</step>

<step n="3" goal="选择可执行入口">
 - 先按 `<project-root>` 的目录形态选择入口，不得把 PATH 中裸 `harness` 是否存在作为已安装项目或源码仓库的可用性判断。
 - 条件：`<project-root>/.harness/common/cli/harness_cli.py` 存在
  - 优先使用项目内 Python CLI：

 ```bash
 python3 <project-root>/.harness/common/cli/harness_cli.py --root <project-root> <command> ... --json
 ```

 - 条件：项目内 Python CLI 不存在，且 `<project-root>/harness-runtime/bin/harness` 存在
  - 使用本地 shim 作为兼容 fallback：

 ```bash
 <project-root>/harness-runtime/bin/harness --root <project-root> <command> ... --json
 ```

 - 条件：以上项目本地入口都不存在，且 PATH 中 `harness` 可用
  - 才允许使用全局 `harness --root <project-root> <command> ... --json`。
 - 条件：以上入口都不可用
  - 返回 BLOCKED，说明已检查的路径和缺失原因。
</step>

<step n="4" goal="执行命令并记录结构化结果">
 - 命令域必须属于 `config / control / frame / mission / approval / graph / board / contract / evidence / gate / lint`。
 - workflow 消费结果时必须传 `--json`。
 - 读取 Mission 状态时优先用查询参数缩小结果：单个任务用 `harness mission status --mission <mission-id> --json`；恢复/路由先用 `harness control status --json` 与 `harness control candidates --intent continue --json`，显式确定 mission 后再用 `harness control frame --mission <mission-id> --json`、`harness control guidance --mission <mission-id> --json`、`harness control context-index --mission <mission-id> --json`；查未完成任务用 `harness mission status --open --json`；只需要 id 时加 `--ids-only`。
 - 只知道 Mission id 和文档类型时，读取正文前先调用 `harness mission document --mission <mission-id> --type <document-type> --json`，使用返回的 `path`；不得从 board / node YAML / stage 目录手工反推产物路径。
 - 写操作必须具备必要输入文件，例如 operation manifest、gate report、contract artifact、mission id。
 - 读写操作不可绕过 CLI 直接打开或编辑 CLI 已支持的派生视图或控制面文件。
 - 条件：调用方需要的读取/写入尚无对应 CLI 能力
  - 返回 BLOCKED 或记录 CLI 能力缺口；不得默默回退为直接读写 YAML / JSON。
 - 执行后记录完整命令、退出码、JSON `status` / `gate_effect` / `changed_files` / `artifacts` / `findings` 等关键字段，以及产物路径或 report 路径。
</step>

<step n="5" goal="CLI-first control-plane recovery">
 - 当调用方意图是 `continue`、`status`、`review`、`verify` 或 `bug_report`，先执行只读 control 查询链：`harness control status --json` → `harness control candidates --intent continue --json` → 显式确定 mission → `harness control frame --mission <mission-id> --json` → `harness control guidance --mission <mission-id> --json` → `harness control context-index --mission <mission-id> --json`。
 - `control.candidates` 是候选事实，不是调度裁决；调用方不得把 candidates 当作最终选择。
 - `control.context-index` 只输出路径、required/exists 和来源，不输出正文摘要；其中 Mission 阶段文档路径来自 `mission_document_rule`，阶段 skill 读取这些路径后再执行自己的 workflow。
 - 条件：某项 control 查询缺失或返回 BLOCKED，但当前 workflow 仍必须临时读取旧 runtime 文件
  - 结构化记录 fallback：`fallback_used: true`、`fallback_reason: <为什么 control 查询不可用>`、`legacy_source: <读取的旧文件或旧命令>`、`follow_up: <补齐 CLI 能力或迁移旧入口的动作>`。
</step>

<step n="6" goal="分类 CLI 结果">
 - 分支：CLI 结果
  - 情况：PASS / 退出码 0
   - 调用方继续原 workflow，并消费 JSON 产物。
  - 情况：WARN
   - 调用方记录风险；若当前 Gate 或策略要求 fail-on-warn，则按失败处理。
  - 情况：FAIL
   - 调用方停止推进，进入对应修复或 quality-control 流程。
  - 情况：BLOCKED
   - 调用方停在当前 Gate / 阶段，报告缺失依赖或不可恢复原因。
  - 情况：非 JSON 或解析失败
   - 视为 BLOCKED；不得从非结构化输出里猜测 PASS。
</step>

<step n="7" goal="禁止降级">
 - Hard gate：`harness gate advance` 不可用时，不得手改 board / index / tree。
 - Hard gate：`harness graph apply/rebuild/check` 不可用时，不得手写 Work Graph 派生视图。
 - Hard gate：`harness contract check` 不可用时，不得人工宣称 contract PASS。
 - Hard gate：`harness evidence graph check` 不可用时，不得人工宣称证据链完整。
 - Hard gate：`harness approval require` 不可用时，不得跳过人类 Checkpoint。
 - 如果确需修复 CLI 自身，另起缺陷修复或执行任务，修复后重新运行本 workflow。
</step>

</workflow>
