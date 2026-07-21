# Harness 自检工作流

**Goal:** 对 HarnessV2 模板进行机械化自洽性检查，发现结构缺失、引用失效、文档与实现不一致等问题。

**Your Role:** 你是检查员。你逐项检查，报告问题，不修复（除非用户要求）。

---

## 检查类别

### 1. 结构完整性（structure）

检查必要文件和目录是否存在：

| 检查项 | 期望 |
|--------|------|
| `AGENTS.md` | 存在 |
| `.harness/common/rules/` | 非空 |
| `.harness/common/skills/` | 非空 |
| `.harness/common/agents/` | 非空 |
| `.cursor/hooks.json` | 存在 |
| `harness-runtime/config/harness.yaml` | 存在 |
| `harness-runtime/templates/` | 非空 |
| `harness-runtime/harness/` | 存在 |
| `project-knowledge/engineering/policies/stage-rules.yaml` | **当 `spec.enabled=true` 时**：文件存在 |
| `project-knowledge/specs/_index.md` | **当 `spec.enabled=true` 时**：文件存在 |

### 2. 交叉引用（references）

检查轻量入口和按需导航索引中的引用是否有效：

| 检查项 | 方法 |
|--------|------|
| `AGENTS.md` 中的规则 / 文档路径 | 文件是否存在 |
| `.harness/docs/harness-navigation.md` 技能索引中的技能路径 | `SKILL.md` 是否存在 |
| `.harness/docs/harness-navigation.md` Agent 索引中的 Agent 路径 | `.md` 文件是否存在 |
| 技能工作流中引用的 Agent 路径 | 文件是否存在 |
| 技能工作流中引用的模板路径 | 文件是否存在 |

### 3. 规则卫生（规则）

| 检查项 | 方法 |
|--------|------|
| 每个 `.mdc` 有 YAML frontmatter | 解析 frontmatter |
| `alwaysApply` 值与 AGENTS.md 标注一致 | 交叉对比 |
| 无重复 description | 比对所有 rule 的 description |
| 核心规则存在 | core、自治循环、decision-system、mission-tracking、project-context |

### 4. 技能契约（contracts）

| 检查项 | 方法 |
|--------|------|
| 每个技能有 `SKILL.md`（`workflow.md` 可选） | 文件存在检查 |
| `SKILL.md` frontmatter 有 `name` 和 `description` | 解析 frontmatter |
| 工作流中引用的模板存在 | 路径检查 |
| **CSO 合规**：description 只写触发条件，不总结工作流 | 人工判断：description 中是否包含"执行步骤"描述而非"何时使用"条件 |
| **CSO 合规**：description 包含至少一个症状关键词 | 检查是否有 "当"、"遇到"、"用户说" 等触发模式 |
| **CSO 合规**：description 无过度泛化 | 不应出现"所有"、"任何时候"等无差别匹配词 |

### 5. Agent 契约（Agent）

| 检查项 | 方法 |
|--------|------|
| 每个 Agent `.md` 有 frontmatter | 解析 frontmatter |
| frontmatter 有 `name` 和 `description` | 字段检查 |
| 每个 Agent 在 `.harness/docs/harness-navigation.md` 或 `.harness/common/agents/` 中有对应条目 | 交叉对比 |

### 6. 状态一致性（状态）

| 检查项 | 方法 |
|--------|------|
| `harness-runtime/harness/mission-status.yaml` 格式可解析 | YAML 解析 |
| 活跃任务的 stages 字段只记录当前 Mission Slice stage | 与当前 Mission Slice 的 `control_plane.stage` 比对 |
| 阶段状态值合法 | 只允许 pending / in-progress / 完成 / skipped |
| 任务状态值合法 | 只允许 pending / active / 审查 / 完成 / cancelled |
| 如果有活跃任务，`harness-runtime/harness/state/trace-log.md` 存在 | 文件存在检查 |
| 执行日志的"当前位置"章节与mission-status 一致 | 阶段名匹配 |

### 7. 模板覆盖（模板）

| 检查项 | 方法 |
|--------|------|
| Stage Gate 工作流中定义的每种文档在模板/ 中有模板 | 交叉对比 |
| 模板中的必填章节在 Stage Gate 的最小结构要求中有对应 | 交叉对比 |

### 7a. 原型路线配置（prototype-delivery-mode）

| 检查项 | 方法 |
|--------|------|
| `harness.yaml` 顶层有 `prototype.delivery_mode` | YAML 解析；缺失 → FAIL（默认 `interactive_prototype` 也必须显式写出，避免 CLI 解析回落歧义） |
| `prototype.delivery_mode` 取值合法 | 必须是 `interactive_prototype` 或 `frontend_engineering`；其它值 → FAIL |
| interaction stage `mode_variants` 两条路线齐全 | `professional_roles.stage_policies.interaction.mode_variants` 和 `work_graph.lanes.product-definition-lane.stages[interaction].mode_variants` 各自必须包含 `interactive_prototype` 与 `frontend_engineering` 两个 key |
| `mode_variants` 引用的 role 文件存在 | `interactive_prototype` 需 `interaction-designer.md` + `interaction-reviewer.md`；`frontend_engineering` 需 `frontend-prototype-engineer.md` + `frontend-reviewer.md` |
| `delivery_mode=frontend_engineering` 时 `prototype.frontend_engineering.frontend_project_root` 已配置 | 字段存在且非空；未配置 → WARN（CLI 会 fallback 到 `apps/web`） |
| skill 配套齐全 | `.harness/common/skills/interaction/SKILL.md` 与 `.harness/common/skills/prototype-as-frontend/SKILL.md` 都存在且各自的 workflow.md 存在 |
| contract template 配套齐全 | `harness-runtime/templates/contracts/interaction.contract.yaml` 与 `prototype-as-frontend.contract.yaml` 都存在 |
| skill-router 已声明双路线分派 | `.harness/common/skills/skill-router/SKILL.md` 与 `workflow.md` 中各自包含 `prototype-as-frontend` 字符串 |
| `delivery_mode=frontend_engineering` 时 PRD 模板齐全 | `harness-runtime/templates/api-contract-draft.md` 存在 |

### 8. Runtime 控制面一致性（control-plane-runtime）

检查控制契约、协议索引、工作流引用和脚本是否互相对齐：

| 检查项 | 方法 |
|--------|------|
| v1 contract 模板存在 | 任务契约 / prd / execution-brief / 验证报告 / 差量规格 |
| 程序化脚本存在 | `stage-gate/scripts/check_contracts.py`、`verify/scripts/collect_command_evidence.py`、`harness-lint/scripts/check_runtime_consistency.py` |
| 协议 runtime 正文存在 | `.harness/common/protocols/README.md`、quality-control、bug-fix |
| dedicated 协议技能存在 | `quality-control`、`bug-fix` |
| 工作流调用点存在 | Stage Gate、验证、code-review、执行、retrospective、skill-router |
| runtime 资产不引用维护者设计稿 | `package/` 下不得引用维护者架构草稿目录 |
| schema validator 可用 | `.harness/common/schemas/control_contract.v1/` 存在，`check_contracts.py` 能加载 schema |
| 协议 coverage 可生成 | `.harness/common/skills/harness-lint/scripts/check_protocol_coverage.py --root .` |
| drift patch 可生成 | `.harness/common/skills/harness-lint/scripts/generate_drift_patch.py` 针对 runtime consistency findings 产出审查 patch |

---

## 执行

<workflow skill="harness-lint" version="2">

<step n="1" goal="逐类执行检查">
 - 按上述 7 个类别依次检查
 - 若 `.harness/common/skills/harness-lint/scripts/check_runtime_consistency.py` 存在，运行 `python3 .harness/common/skills/harness-lint/scripts/check_runtime_consistency.py --root .` 并把结果纳入第 8 类
 - 运行 `python3 .harness/common/skills/harness-lint/scripts/check_protocol_coverage.py --root .`，生成协议 coverage 报告；引用减少是 WARN，非自动 FAIL
 - 自检模板 contract 时，调用 `check_contracts.py` 必须显式传 `--allow-placeholders`；运行时 Stage Gate 不得传该 flag
 - 若 runtime consistency 有 FAIL，可选运行 `.harness/common/skills/harness-lint/scripts/generate_drift_patch.py` 生成 drift patch 供审查员审阅；generator 不直接 apply
 - 每项检查记录结果：PASS / FAIL / WARN
</step>

<step n="2" goal="输出报告">
 - 按以下格式输出：

 ```
 ## HarnessV2 Lint Report

 ### Structure
 [PASS] AGENTS.md exists
 [PASS] .harness/common/rules/ non-empty (9 files)
 ...

 ### References
 [PASS] All startup and navigation paths are valid
 [FAIL] Skill "xyz" references template that doesn't exist: harness-runtime/templates/xyz.md
 ...

 ### Summary
 Total: XX checks
 Passed: XX
 Failed: XX
 Warnings: XX
 ```

 - 如果有 FAIL，列出修复建议
</step>

</workflow>

---

## 触发时机

- 用户手动说"检查 harness"或"lint"
- 新任务完成 retrospective 后
- 模板结构有变更时（新增技能、Agent、rule）
