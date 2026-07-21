# Project Lint 工作流

**Goal:** 对目标项目运行可配置、确定性的项目级规范 / 规约检查，发现越界修改、缺少验证证据和项目自定义工程规则违规。

**Your Role:** 你是项目约束检查员。你只报告确定性 finding，不替代 code-review、security-reviewer、architecture-reviewer 或 eval。

---

## 初始化

1. 调用 `harness-cli` 判断当前目录是否可执行 `harness lint project`；源码仓库和已安装目标项目都应优先使用该 CLI 语义入口。
2. 读取项目 lint profile：`project-knowledge/engineering/policies/project-lint.yaml`
3. 调用 `harness-cli` 执行 `harness context check --json`；PASS 则读取 `project-context.md`，FAIL 时记录 `inputs_missing.project_context=true` 到 lint report，不得静默继续。然后读取 `harness-runtime/config/harness.yaml`
4. 收集本次变更文件：
   - 优先使用 execution-brief / trace 中声明的 changed files
   - 否则使用 `git diff --name-only HEAD`
5. 若 verify 已生成 command evidence，读取 `harness-runtime/harness/traces/<mission-id>/cmd/*.json`
6. 若项目 profile 启用 `prototype_trace` 且当前 mission 有 visual-interaction manifest，运行原型 trace 规约检查；仅当项目 profile 显式配置 trace / agent 等扩展段落时，才运行对应 Agent / trace 扩展检查。

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

 - 若项目 profile 显式启用 trace 检查且有 trace 文件，传入：

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
 - 项目 profile 声明的工具命令缺失、越界修改、证据缺失、外部工程规则失败 → `project-lint`
 - 项目 profile 启用的原型设计规约（trace 脊柱 + FLOW / STATE / viewport 覆盖 + operable 原型规则）→ `project-lint`
 - Agent 轨迹循环 / AGENTS 入口完整性 / Harness 模板一致性 → 对应 Harness / Agent 专项检查，不归默认 project-lint

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
- `interaction` / 原型阶段产出 `visual-interaction-manifest.json` 后（原型 trace 规约当场卡口）
- execute 修改业务代码后
- bug-fix 修复落地代码后
- verify 收集 command evidence 后
- Stage Gate 做质量就绪度检查时
- 用户手动要求项目级 lint

## Stage Gate 硬卡口（按产物类型自动强制）

`harness gate run` 内部恒会调用控制面报告 checker，checker 自己读取 `harness.yaml` 的 `project_lint`，按当前阶段产物类型强制要求 fresh project-lint 报告：

- `enabled=true` 且 `require_for_code_change=true` 且当前 diff 含代码改动时：缺报告 → FAIL `missing_required_control_report`；报告 `changed_files` 未覆盖当前 diff → FAIL `stale_control_report`。
- `enabled=true` 且 `require_for_prototype=true` 且 mission 存在 `visual-interaction-manifest.json` 时：缺报告 → FAIL `missing_required_control_report`；报告 `prototype_manifest_mtime` 早于当前 manifest（陈旧）→ FAIL `stale_control_report`。

这两条让 project-lint 在**原型阶段和执行阶段**都成为硬卡口，而不只在 verify。`gate_effect=block` 一律不得口头改写为通过。
