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
 - 按顺序尝试以下入口：

 ```bash
 harness --root <project-root> <command> ... --json
 <project-root>/harness-runtime/bin/harness --root <project-root> <command> ... --json
 python3 .harness/common/cli/harness_cli.py --root <project-root> <command> ... --json
 python3 .harness/common/cli/harness_cli.py --root <project-root> <command> ... --json
 ```

 - PATH 中 `harness` 可用时优先使用它。
 - 已安装项目优先使用 `harness-runtime/bin/harness` shim。
 - HarnessV2 源码仓库可使用 `.harness/common/cli/harness_cli.py`。
 - 已安装项目可使用 `.harness/common/cli/harness_cli.py`。
 - 条件：四者都不可用
  - 返回 BLOCKED，说明已检查的路径和缺失原因。
</step>

<step n="4" goal="执行命令并记录结构化结果">
 - 命令域必须属于 `config / control / frame / mission / approval / graph / board / contract / evidence / gate / lint`。
 - workflow 消费结果时必须传 `--json`。
 - 读取 Mission 状态时优先用查询参数缩小结果：单个任务用 `harness mission status --mission <mission-id> --json`；恢复/路由先用 `harness control status --json` 与 `harness control candidates --intent continue --json`，显式确定 mission 后再用 `harness control frame --mission <mission-id> --json`、`harness control guidance --mission <mission-id> --json`、`harness control context-index --mission <mission-id> --json`；查未完成任务用 `harness mission status --open --json`；只需要 id 时加 `--ids-only`。
 - 写操作必须具备必要输入文件，例如 operation manifest、gate report、contract artifact、mission id。
 - 读写操作不可绕过 CLI 直接打开或编辑 CLI 已支持的派生视图或控制面文件。
 - 条件：调用方需要的读取/写入尚无对应 CLI 能力
  - 返回 BLOCKED 或记录 CLI 能力缺口；不得默默回退为直接读写 YAML / JSON。
 - 执行后记录完整命令、退出码、JSON `status` / `gate_effect` / `changed_files` / `artifacts` / `findings` 等关键字段，以及产物路径或 report 路径。
</step>

<step n="5" goal="CLI-first control-plane recovery">
 - 当调用方意图是 `continue`、`status`、`review`、`verify` 或 `bug_report`，先执行只读 control 查询链：`harness control status --json` → `harness control candidates --intent continue --json` → 显式确定 mission → `harness control frame --mission <mission-id> --json` → `harness control guidance --mission <mission-id> --json` → `harness control context-index --mission <mission-id> --json`。
 - `control.candidates` 是候选事实，不是调度裁决；调用方不得把 candidates 当作最终选择。
 - `control.context-index` 只输出路径、required/exists 和来源，不输出正文摘要；阶段 skill 读取这些路径后再执行自己的 workflow。
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
