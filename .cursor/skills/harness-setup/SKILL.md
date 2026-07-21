---
name: harness-setup
description: '把 HarnessV2 安装 / 初始化 / 更新到一个项目时使用。INSTALL.md 在 clone + install.py scaffold 之后交棒给本技能，由它完成全部复杂编排：环境与模式判定、初始化（context / knowledge / project_name / brownfield）、graphify 建图与 gitignore、项目上下文填充、完整性验证与移交；遇升级 / 迁移 / 加 adapter 时编排到对应命令。用户说"把 harness 装到这个项目""初始化 harness""装好了接下来怎么弄""更新 harness 框架"时也触发。'
---

# Harness Setup — 安装 / 初始化 / 更新编排

## 概述

`install.py` 只做机械 scaffold（拷文件、生成 adapter 入口）。**把一个项目真正变成"可用的 Harness 项目"的复杂流程由本技能编排**：判模式、初始化控制面、设项目配置、建 graphify 图谱、填项目上下文、验证、移交；生命周期的更新 / 迁移 / 加 adapter 编排到已有命令。

本技能随 Harness 一起安装（`.harness/common/skills/harness-setup/`），所以 `install.py` scaffold 之后它立刻可用——这正是 INSTALL.md「scaffold 即交棒」的接棒点。

## 何时触发

- INSTALL.md 跑完 clone + `install.py` scaffold，交棒过来完成初始化
- 已安装但初始化没跑完 / 半途失败，需要续装或修复（re-init）
- 要升级框架 / 迁移模板 / 追加 adapter（编排到对应命令）
- 用户说"把 harness 装到这个项目""初始化一下 harness""装好了接下来怎么弄""更新 harness 框架"

## 何时不触发

- 项目里要做**业务任务**（实现功能 / 修 bug / 写需求）→ 那是 `intake` 与阶段技能，不是本技能
- 只是查 Harness 状态 / 跑某条 CLI → `harness-cli`

## 模式

本技能第一步先判模式，再分支（详见 `workflow.md`）：

| 模式 | 触发条件 | 本技能动作 |
|---|---|---|
| `install` | CLI 就位（`harness-runtime/bin/harness`）、初始化未完成（无 `project-context.md`） | 自己跑完整初始化编排 |
| `re-init` | 已安装、初始化部分完成或失败 | 检测断点、补跑缺失项、不覆盖已有 runtime 数据 |
| `upgrade` | 升级到新版本模板（框架正文 + runtime 结构 + `harness.yaml` 三方迁移） | 编排到 `/harness-upgrade` 命令 |
| `add-adapter` | 追加 AI 工具入口 | 编排到 `/harness-add-adapter` 命令 |

## 红线

<HARD-GATE>
- **不得覆盖或删除 runtime 数据、项目知识与外部资料**：`harness-runtime/harness/**`、`project-knowledge/**`、`materials/**` 默认只读；初始化只新增、不重写已有内容。
- **`harness knowledge init` 不重跑**：scaffold 已铺好 `project-knowledge/`，再 init 会 FAIL。只 `knowledge check`。
- **upgrade / add-adapter 必须走权限化命令**：本技能不直接改框架正文 / runtime 结构 / adapter 入口去"更新"，只把用户导到 `/harness-upgrade`、`/harness-add-adapter`，由它们的权限化 operation + Decision Gate 执行。`harness.yaml` 升级靠 `harness config diff/migrate` 三方迁移，绝不重跑 `install.py --force`（会冲掉 `project_name` / `brownfield` / 各开关）。
- **既有项目建图用 `graphify-build` 技能**（agent 自己提取、免 Key），不要用终端裸跑 `graphify .` 建文档图（那会要 Key）。
- **建图的语义分析不准跳过**：文档 / Markdown / PDF / 图片的语义抽取是建图的一部分，**不允许只做代码 AST 就算建完**。文件多时**必须按 `graphify-build` 的方式派发多个子 agent 并行完成**（每 ~20-25 个待抽取文件一个子 agent，约 `ceil(待抽取文件数 / 22)` 个），不得因为"文件太多""省 token"而跳过或截断语义抽取。
- **`brownfield` 默认 true**，只有确属全新 / 空项目才覆盖为 false。
</HARD-GATE>

## 与其他技能 / 命令的关系

| 对象 | 关系 |
|---|---|
| `install.py` | 上游 scaffold；本技能在其之后接棒 |
| `harness-cli` | 初始化与验证的 CLI 命令（`context init` / `knowledge check` / `config snapshot` / `control status` / `graphify status`）经它调用 |
| `graphify-build` | 既有项目建图（免 Key）由本技能在初始化中调用 |
| `generate-context` | 既有项目的 `project-context.md` 填充交给它 |
| `/harness-upgrade`、`/harness-add-adapter` | 生命周期的升级 / 加 adapter，本技能编排过去、不重写 |

按 `workflow.md` 执行详细步骤。
