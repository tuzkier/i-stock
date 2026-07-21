---
name: harness-upgrade
description: 把已安装 Harness 的项目升级到新版本模板——一份持久化、可断点续跑的升级 checklist，按权限化 operation 刷新框架正文与 runtime 结构、对 harness.yaml 做三方迁移（保留项目设置）、按已装 adapter 重渲染入口，并验证 + 留回滚点。取代旧的 /harness-update 与 /harness-migrate。
argument-hint: "[upstream-source-path]"
scope: post-install
requires:
  - <upstream-source>/INSTALL.md
  - .harness/common/rules/core.md
asset_class: A+B+C+D+E
permission:
  - approve-framework
  - approve-runtime-structure
  - approve-adapter
  - approve-runtime-data
  - approve-project-knowledge
---
<!-- Generated for adapter `claude` from .harness/common/commands/. Edit the source, then re-run install. -->

# /harness-upgrade

把已安装项目升级到新版本 HarnessV2 模板。**不区分「小刷新」和「大迁移」**——同一条 checklist 跑到底，由版本 diff 决定哪些 Phase 有活：补丁级只动几项，大版本则连 yaml 结构、adapter、历史结果一起处理。

**这取代旧的 `/harness-update`（只能动框架正文、碰不了 yaml）和 `/harness-migrate`（钝刀全量替换 yaml）。** 真实版本升级几乎总是同时动框架正文和 yaml 结构，二者拆开反而互相漏接；本命令把它们合成一条带 yaml 三方迁移的统一流程。

## 触发条件

- 项目已安装 Harness（存在 `.harness/common/rules/core.md`）
- 用户拿到新版本 HarnessV2 源码（`release` 分支克隆或对应 tag），想升级
- 追加 AI 工具入口是另一件事，走 `/harness-add-adapter`，不在本命令范围

## 严格不做（红线）

<HARD-GATE>
- **不重跑 `install.py --force`** 去整目录覆盖——它会无脑覆盖 `harness.yaml`，冲掉 `project_name` / `brownfield` / 各开关。yaml 必须走 `harness config diff/migrate` 三方迁移。
- **runtime 数据 / 项目知识 / 外部资料默认只读**：`harness-runtime/harness/**`、`project-knowledge/**`、`materials/**` 不得 replace 或 delete；只能由 OP-RESULT-* / OP-KNOWLEDGE-* 类 operation **新增** 带 `source_link` 的副本，绝不原地改写历史结果。
- **不绕过 Decision Gate**：任一写入 operation 必须先拿到用户 Approved ids。
- **工作树不干净不启动**：有 uncommitted 改动时停下，要求提交或显式接受风险。
</HARD-GATE>

## Runtime 数据保留清单（迁移期默认只读）

| 路径 | 内容 |
|---|---|
| `harness-runtime/harness/missions/**` | 任务契约实例 |
| `harness-runtime/harness/stages/**`、`artifacts/**` | 各阶段结果 |
| `harness-runtime/harness/traces/**` | 执行证据、升级记录、回退记录 |
| `harness-runtime/harness/state/**` | approvals、trace-log、状态缓存 |
| `harness-runtime/harness/work-graph/**` | Work Graph 节点 / board / index |
| `harness-runtime/harness/deliveries/**`、`memory/**` | 交付归档 / 历史沉淀 |
| `project-knowledge/**` | 项目长期知识库 |
| `materials/**` | 人提供的外部录入资料 |

---

## 升级 checklist（持久化、可断点续跑）

把下面这份 checklist 写入 `harness-runtime/harness/traces/<YYYYMMDD>-harness-upgrade/checklist.md`，**逐项推进、逐项打勾**（`[ ]` → `[x]`，带时间戳）。会话中断后重入本命令时，先读这份 checklist 跳到第一个未完成项续跑，不重做已完成项。每个 Phase 的写入 operation 都先备份到 `traces/<date>-harness-upgrade/backup/<op-id>/`。

```markdown
# Harness 升级 checklist — <YYYYMMDD>
源上游: <upstream>   当前版本: <cur> → 目标版本: <target>

## Phase 0 准备
- [ ] 工作树干净（或用户显式接受风险）
- [ ] 上游校验：<upstream> 存在 install.py 与 package/common/rules/core.md
- [ ] 版本比对：current(harness_template.version) vs target(<upstream>/VERSION)
- [ ] 备份 .harness/ 与 harness-runtime/config/harness.yaml 到 backup/

## Phase 1 框架正文（A 类，纯框架所有 → 整体 replace）
- [ ] OP-FW-001  .harness/common/**            ← <upstream>/package/common/**
- [ ] OP-DOC-001 .harness/docs/**              ← <upstream>/package/docs/**
- [ ] OP-DOC-002 .harness/workflow-map.html    ← <upstream>/package/workflow-map.html

## Phase 2 runtime 结构资产（C 类 → replace）
- [ ] OP-RT-001  harness-runtime/bin/**        ← <upstream>/package/harness-runtime/bin/**
- [ ] OP-RT-002  harness-runtime/templates/**  ← <upstream>/package/harness-runtime/templates/**
- [ ] OP-RT-003  harness-runtime/scripts/**    ← <upstream>/package/harness-runtime/scripts/**
- [ ] OP-RT-004  harness-runtime/config/model-routing.yaml + 其它 config 静态资产

## Phase 3 ★ harness.yaml 三方迁移（核心，逐键决策）
- [ ] OP-CFG-001 config diff → 生成逐键 todolist（见下）
- [ ] OP-CFG-002 用户对 requires_decision 项决策
- [ ] OP-CFG-003 config migrate → 写合并后的 harness.yaml（保留项目值）
- [ ] OP-CFG-004 写戳 harness_template 版本/commit

## Phase 4 adapter 入口（B 类，按已装 adapter 重渲染 → approve-adapter）
- [ ] OP-ADP-001 重渲染当前已装 adapter 的入口与 .<adapter>/ 副本（不新增 adapter）

## Phase 5 历史结果 / 知识沉淀 / 能力回填（D/E 类，仅相关变更时；只新增不原地改）
- [ ] OP-RESULT-001  如新模板产物结构变化 → 生成带 source_link 的适配副本
- [ ] OP-KNOWLEDGE-001 legacy project-spec/specs/** → project-knowledge/specs/**（move + 保留 metadata）
- [ ] OP-DS-001 设计系统蒸馏回填（仅当本次升级**引入/扩展 design-system 能力** 且项目为 **brownfield + 有界面**（`ui_presence=no_signal` 须向用户确认，默认按有 UI 推）且 `project-knowledge/product/design-system/` 为空/占位）→ approve-project-knowledge

## Phase 6 验证 + 回滚点
- [ ] control / knowledge / graphify status 通过
- [ ] checklist 末尾写 Upgrade Summary
```

---

## 执行 procedure

### Phase 0 — 准备

1. 工作树干净检查；不干净则停下。
2. 询问上游 HarnessV2 模板本地路径（参数 `$1` 或交互获取），下文记为 `<upstream>`。未给出则停下要求提供，不要猜。校验 `<upstream>/install.py` 与 `<upstream>/package/common/rules/core.md` 存在。
3. 版本比对：读 `<upstream>/VERSION` 与本项目 `harness-runtime/config/harness.yaml` 的 `harness_template.version`。**相同则停下报告「已是同一版本」**，不进入 operation。
4. 备份 `.harness/` 与 `harness-runtime/config/harness.yaml` 到 `traces/<date>-harness-upgrade/backup/phase0/`。
5. 生成 checklist 文件（上面的模板，填入实际版本号）。

### Phase 1 — 框架正文（replace）

- 这些是**纯框架所有、无混合归属**，整体替换，低风险。逐 op 先备份再 replace，打勾。

### Phase 2 — runtime 结构资产（replace）

- `bin/`（CLI 正文）、`templates/`、`scripts/`、`config/` 下的**静态框架资产**（如 `model-routing.yaml`、`config-ownership.yaml`——它们纯框架所有，以新模板为准 replace）。
- **只有 `harness.yaml` 不在本 Phase**——它是唯一的混合归属文件（框架结构 + 项目设置），交 Phase 3 做三方迁移。`config-ownership.yaml` 必须在本 Phase 先刷新到新版本，Phase 3 的 diff/migrate 才用上新版归属与 renames。

### Phase 3 — harness.yaml 三方迁移（核心）

这一步用 CLI 做机器 diff，agent 只决策冲突项：

1. **OP-CFG-001 算 diff**：
   ```bash
   harness-runtime/bin/harness --root . config diff --upstream <upstream> --json
   ```
   输出每个键的分类（见下表）与 `requires_decision` 清单，写进 checklist 的 Phase 3 区块作为逐键 todolist。

   | 分类 | 含义 | 默认动作 |
   |---|---|---|
   | `auto_managed` | 元数据（harness_template） | 采用上游（Phase 3.4 再写戳） |
   | `unchanged` | 框架键，新旧相同 | 无变化 |
   | `adopt_framework` | 框架键，值变了 | 采用上游（diff 展示旧→新） |
   | `new_framework_key` | 框架键，新模板新增 | 采用上游 |
   | `removed_framework` | 框架键，新模板删除 | 丢弃 |
   | `keep_unchanged` | 项目键，当前==上游默认 | 保留（无需决策） |
   | `keep_customized` | 项目键，当前≠上游默认 | **默认保留**，requires_decision |
   | `new_project_key` | 新增的项目级键 | 默认采用上游默认，requires_decision |
   | `renamed` | 键改名（归属清单 renames） | 默认迁值到新键，requires_decision |
   | `orphan_project` | 项目键在新模板无归宿 | 默认丢弃，requires_decision |

2. **OP-CFG-002 决策**：把 `requires_decision` 项展示给用户，逐项取决策动作。写一个决策文件 `traces/<date>-harness-upgrade/config-decisions.yaml`：
   ```yaml
   decisions:
     project_name: keep            # 或 adopt_default
     e2e.enabled: keep
     some.renamed.old: migrate     # 或 drop
     some.orphan.key: drop         # 或 relocate:<new.path>
     some.new_project.key: adopt_default   # 或 set:<value>
   ```
   - `keep_unchanged` / `unchanged` / `adopt_framework` / `new_framework_key` / `removed_framework` 无需进决策文件（按默认走）。
   - 没有任何 requires_decision 项时，可直接 `--accept-defaults`，跳过决策文件。

3. **OP-CFG-003 合并写盘**：
   ```bash
   # 先 dry-run 复核
   harness-runtime/bin/harness --root . config migrate --upstream <upstream> \
     --decisions harness-runtime/harness/traces/<date>-harness-upgrade/config-decisions.yaml \
     --dry-run --json
   # 复核无误后原地写（自动生成 harness.yaml.bak）
   harness-runtime/bin/harness --root . config migrate --upstream <upstream> \
     --decisions .../config-decisions.yaml --json
   ```
   - 合并以**新模板为基底**（框架结构整体刷新、采用新版键序），再把保留 / 迁移的项目值覆盖回去。
   - **不提供 `--decisions` 也不加 `--accept-defaults` 时，命令会 FAIL 并列出 pending**——这是 Decision Gate，别用 `--accept-defaults` 草率跳过有实际冲突的项。

4. **OP-CFG-004 写戳版本**：把 `harness_template.version` 设为 `<upstream>/VERSION`、`source_commit` 设为 upstream 的 git short SHA。

### Phase 4 — adapter 入口（按已装 adapter 重渲染）

- 只重渲染**当前已装**的 adapter 入口与 `.<adapter>/` 副本（agents / skills / commands），不新增 adapter（那是 `/harness-add-adapter`）。
- 委托方式：在 `<upstream>` 下 `python3 install.py <target> --adapter <每个已装 adapter> --entry-policy overwrite`，或按显式 operation 逐项 replace。`--entry-policy` 由用户在 plan 中选（保守用 `keep` 仅补缺、激进用 `overwrite` 刷新）。

### Phase 5 — 历史结果 / 知识沉淀 / 能力回填（条件）

- 仅当新模板**产物结构变化**（artifact 路径 / schema 改了）时才需要：盘点旧 `harness-runtime/harness/` 结果，生成带 `source_link` 的适配副本（**绝不原地改写**），写入 `traces/<date>-harness-upgrade/`。
- legacy `harness-runtime/project-spec/specs/**`（如有）move 进 `project-knowledge/specs/**`，保留 source metadata。

- **OP-DS-001 设计系统蒸馏回填（能力回填，条件触发）**：当本次升级**首次引入或扩展了 `design-system` 能力**（升级后出现/更新了 `project-knowledge/product/design-system/` 模板与 `prototype-check` 的 `design_system` 门），而项目是**既有项目 + 有界面**、且其 `design-system/` 各分层目录仍为空 / 占位时，做一次**初版蒸馏回填**——否则既有既有项目升上来后设计系统空着没人填，原型无组件可装配。
  - 触发判定：`config snapshot` 看 `brownfield=true`；界面存在性按 generate-context 的 `ui_presence` **机械判定 + 命中证据**（信号集见 generate-context，覆盖 Web 前端 / 服务端模板 `.cshtml`·`.razor`·JSP·Thymeleaf 等 / 桌面 XAML / 样式层 / jQuery + CSS / `prototype/`）——`confirmed_ui` 即满足；`no_signal` **不得静默判为非 UI**，须按"默认有 UI"向用户确认，仅用户确认无界面才记为不满足；`design-system/` 的 base/business/shell 机器段解析为空（占位）。三项判完后任一不成立才跳过本 OP。
    - **严禁主观二分覆盖机械结果**：`ui_presence=confirmed_ui` 时**不存在跳过路径**，哪怕是 jQuery + 服务端模板这类栈、哪怕零设计 token。「无设计系统 / 无 token」≠「非 UI」≠「可跳过」——缺 token 标「待补」。❌ 反模式（命中即违规）："主要是 .NET 后端，无现有设计系统，跳过"、"非 UI 项目正常"。跳过仅在 `no_signal` + 用户确认无界面这一条路径，且须记录 `ui_presence` 值与用户确认原文。
  - 动作：与 `harness-setup` Step 3「蒸馏 UI 设计系统初版」**同一程序**——observe → condense，从 `materials/design/` + 既有代码已有设计语言（CSS 变量 / token 文件 / theme / 组件库）提炼**初版**。**蒸馏前先确认既有设计资产 + 取目录**：先问用户项目是否已有现成设计系统 / 组件库 + 主题定制（Element / antd / MUI + 自定义主题或团队自有库），有则请用户指明组件库（及载体：npm 包 / 仓库内 vendored）、主题 / 变量定制文件、自研 / 业务组件目录，蒸馏优先吸纳这些指定位置；无则机械扫描。目的是把既有标准**吸纳进 Harness 格式**供下游消费，**组件本体仍直接用既有库、不重画**。**细粒度提取按分层并行派子 agent**（设计规范/token、基础组件、整体交互框架、业务组件各一层，设计原则由主 agent 起草 + 问用户），不靠主 agent 一遍范范扫；业务组件无复现单元则留给后续 UI mission。**基础组件层按「来源归属」分流**：npm 包库组件只登记进 `base-components.md` 的「既有组件库 / 设计系统底座登记段」、不重画副本；仓库内 vendored 组件 + 项目自研 + 二次封装才进 `BC-*`，token 真值取项目对库的主题定制层。**规模决定打法**：先跑 `partition_plan.py`（见 harness-setup Step 3）算 `mode`——`simple` 按层派；`partitioned`（超大型）按模块 map → 分层 reduce + 采样 + staging 草案落盘，不在单上下文一把合。token 真值写 `prototype/tokens.css`、组件实现写 `prototype/components/`，并装配可视化对账面 `prototype/component-library.html`（按组件 × 全状态矩阵渲染，打 `data-basecomp` / `data-bizcomp` / `data-shell` 锚点；它是参考展示页、非 SUC 原型，不受 gallery 约束）；**每条挂 source + status，禁止无来源造值**（没抽到标「待补」）。
  - 权限：写 `project-knowledge/product/design-system/**`（受保护，**只新增 / 填空，不覆盖**已有内容）+ 写 `prototype/{tokens.css,components/**,component-library.html}` → `approve-project-knowledge` 门；这是一次实质动作（观察产品 + 提炼），必须经用户 Approved id 才执行，不静默自动跑。

### Phase 6 — 验证 + 回滚

必跑：
```bash
harness-runtime/bin/harness --root . control status --json
harness-runtime/bin/harness --root . knowledge check --json
harness-runtime/bin/harness --root . knowledge index --json
harness-runtime/bin/harness --root . graphify status --json
```
- stdout 落 `traces/<date>-harness-upgrade/verify.log`。
- 任一非零退出 → 停在这里写 `## Verification Failure`，等用户决定修复还是回滚。
- 回滚：按 `backup/<op-id>/` 逆序还原（含 `harness.yaml` 从 Phase 0 备份或 `.bak`），checklist 末尾写 `## Rollback`。

---

## Decision Gate（执行前）

在 checklist 末尾追加，**等用户填回 Approved ids 再开始任何写入**：

```markdown
## Explicit User Approval
- Approved operation ids:
- Rejected operation ids:
- Accepted risks:
- Phase 3 config decisions reviewed: yes/no
- Phase 4 entry-policy: keep | overwrite
```

## 输出契约

- `harness-runtime/harness/traces/<YYYYMMDD>-harness-upgrade/checklist.md`（带逐项打勾时间戳）
- `traces/<date>-harness-upgrade/config-decisions.yaml`
- `traces/<date>-harness-upgrade/backup/**`
- `traces/<date>-harness-upgrade/verify.log`
- 终端摘要：版本 current→target、approved / skipped / failed、保留的项目值、采用的框架变更、丢弃的键

## 拒绝执行的情形

- 上游路径校验失败（无 `install.py` 或 `package/common/rules/core.md`）
- 目标项目没装过 Harness（`.harness/common/rules/core.md` 不存在）
- 工作树有 uncommitted 改动且用户未接受风险
- 用户未给出 Approved operation ids
- Phase 3 存在 requires_decision 项但用户未决策、又拒绝 `--accept-defaults`
- 任一 approve 类权限被 hooks 配置否决
