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

## 命令入口

优先级从高到低：

```bash
harness --root <project-root> <command> ... --json
<project-root>/harness-runtime/bin/harness --root <project-root> <command> ... --json
python3 .harness/common/cli/harness_cli.py --root <project-root> <command> ... --json
python3 .harness/common/cli/harness_cli.py --root <project-root> <command> ... --json
```

若四种入口都不可用，返回 BLOCKED，并说明缺失的 CLI 路径；不得用手工编辑替代控制面写入。

## 常用命令域

| 命令域 | 用途 |
|--------|------|
| `harness config snapshot` | 读取运行配置、执行模式、规格开关、模型路由摘要、Work Graph lane action 注册表 |
| `harness control status/candidates/frame/guidance/context-index` | Agent-facing 只读恢复查询；先看全局状态和候选，再按显式 mission 读取 frame、guidance 和路径索引 |
| `harness frame current/explain` | 读取当前 Mission Slice、lane action 和节点上下文 |
| `harness mission create-slice/status/stage/close` | 创建、读取、推进或关闭 Mission Slice |
| `harness approval append/latest/require` | 写入或检查 Checkpoint / Decision Gate 记录 |
| `harness graph apply/plan/rebuild/check/node show` | 应用 Work Graph operation、重建或检查派生视图 |
| `harness board select` | 从 Board 选择 node 并创建 Mission Slice |
| `harness contract init/patch/check/add-*` | 初始化、更新、检查 control contract |
| `harness evidence graph/add/link/command/visual` | 构建 Evidence Graph、收集命令证据、登记可视化证据 |
| `harness gate run/advance/report/control-reports` | 运行 Gate、渲染报告、Gate PASS 后推进 Work Graph |
| `harness lint runtime/graph/project` | 检查 Harness runtime、Work Graph 或项目约束 |
| `harness knowledge init/check/index/resolve/promote` | 初始化项目知识库、检查索引、按阶段解析需读知识、生成任务收尾知识固化候选计划；具体提炼由 Agent 完成 |
| `harness trace log-init/step-enter/step-exit` | 写入 per-mission JSONL trace（机器可读跨 session evidence）|
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
