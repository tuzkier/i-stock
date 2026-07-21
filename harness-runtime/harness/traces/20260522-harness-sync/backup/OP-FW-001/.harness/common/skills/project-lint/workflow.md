# Project Lint 工作流

**Goal:** 对目标项目运行可配置、确定性的项目级约束检查，发现 Agent 越界修改、缺少验证证据、指令入口缺口和执行轨迹违规。

**Your Role:** 你是项目约束检查员。你只报告确定性 finding，不替代 code-review、security-reviewer、architecture-reviewer 或 eval。

---

## 初始化

1. 调用 `harness-cli` 判断当前目录是否可执行 `harness lint project`；源码仓库和已安装目标项目都应优先使用该 CLI 语义入口。
2. 读取项目 lint profile：`project-knowledge/engineering/policies/project-lint.yaml`
3. 调用 `harness-cli` 执行 `harness context check --json`；PASS 则读取 `project-context.md`，FAIL 时记录 `inputs_missing.project_context=true` 到 lint report，不得静默继续。然后读取 `AGENTS.md`、`harness-runtime/config/harness.yaml`
4. 收集本次变更文件：
   - 优先使用 execution-brief / trace 中声明的 changed files
   - 否则使用 `git diff --name-only HEAD`
5. 若 verify 已生成 command evidence，读取 `harness-runtime/harness/traces/<mission-id>/cmd/*.json`
6. 若存在执行轨迹 JSON，作为 trace lint 输入

---

## 执行

<workflow skill="project-lint" version="2">

<step n="0" goal="安装后初始化候选 profile（按需）">

 - 条件：`project-knowledge/engineering/policies/project-lint.yaml` 缺失，或用户要求初始化项目 lint
 - 运行 bootstrap 脚本：

 ```bash
 python3 .harness/common/skills/project-lint/scripts/bootstrap_project_lint.py --root .
 ```

 - 源码仓库调试时使用 `.harness/common/skills/project-lint/scripts/bootstrap_project_lint.py`。
 - bootstrap 只写 `project-knowledge/engineering/policies/generated/project-lint.generated.yaml` 候选项；不确定的架构边界不得自动晋升为 blocking 规则。

</step>

<step n="1" goal="运行确定性项目检查">

 - 调用 `harness-cli` 执行 project-lint CLI：

 ```bash
 harness lint project \
   --mission <mission-id> \
   --json
 ```

 - 若 verify 阶段已有 command evidence，传入：

 ```bash
 --command-evidence harness-runtime/harness/traces/<mission-id>/cmd
 ```

 - 若有 trace 文件，传入：

 ```bash
 --trace harness-runtime/harness/traces/<mission-id>/trace.json
 ```

</step>

<step n="2" goal="解释结果">

 - Project lint 只解释确定性结果，不用 AI 覆盖 FAIL。

 **判定规则：**
 - `gate_effect=block`：必须修复或进入 Decision Gate；不能宣称项目约束通过
 - `gate_effect=warn`：可以继续，但验证报告和 Stage Gate 必须引用风险
 - `gate_effect=allow`：项目 lint 约束通过

 **finding 归属边界：**
 - 代码行为正确性 → `correctness-reviewer`
 - 测试是否能抓错 → `tdd-reviewer`
 - 安全语义风险 → `security-reviewer`
 - 架构设计是否合理 → `architecture-reviewer`
 - 工具命令缺失、越界修改、证据缺失、轨迹循环 → `project-lint`

</step>

<step n="3" goal="写入报告">

 - CLI 默认在有 mission-id 时写入：

 ```text
 harness-runtime/harness/traces/<mission-id>/project-lint/project-lint-report.json
 harness-runtime/harness/traces/<mission-id>/project-lint/project-lint-report.md
 ```

 - verify、quality-control、stage-gate 消费该报告的 `control` / `gate_effect` / `findings`，不重新解释底层事实。

</step>

</workflow>

---

## 触发时机

- `generate-context` 生成或更新项目 lint profile 后
- execute 修改业务代码后
- verify 收集 command evidence 后
- Stage Gate 做质量就绪度检查时
- 用户手动要求项目级 lint
