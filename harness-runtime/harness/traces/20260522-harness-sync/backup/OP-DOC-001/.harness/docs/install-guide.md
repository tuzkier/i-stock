# HarnessV2 安装指南

本文是安装到目标项目后的唯一安装、更新、迁移入口。HarnessV2 源码仓库中的权威入口是根目录 `INSTALL.md`。

旧文件 `ai-installation-integration.md`、`permissioned-installation.md`、`harness-update-sop.md` 只保留为兼容跳转，不再承载独立方案。

## 核心规则

`install.py` 只用于首次安装 scaffold。

它不是已安装项目的自动更新器、迁移器或修复器。已安装项目的更新和迁移必须按路径级 operation 做人工审查和授权。

## 环境判定

| 环境 | 判定依据 | Harness 正文 | Runtime |
|---|---|---|---|
| HarnessV2 源码仓库 | 存在 `install.py` 和 `.harness/common/rules/core.md` | `.harness/common/` | `harness-runtime/` |
| 已安装目标项目 | 存在 `.harness/common/rules/core.md` | `.harness/common/` | `harness-runtime/` |

不要混用两套路径。源码仓库的 `package/**` 安装后才对应目标项目里的 `.harness/**` 和 `harness-runtime/**`。

## 首次安装

只有目标项目尚未安装 Harness 时，才使用 `install.py`。

```bash
python3 install.py /path/to/project
python3 install.py /path/to/project --adapter codex
python3 install.py /path/to/project --adapter cursor --adapter claude
python3 install.py /path/to/project --entry-policy keep
```

执行前先检查目标项目是否已有这些路径：

- `.harness/`
- `harness-runtime/`
- `project-knowledge/`
- `AGENTS.md`
- `CLAUDE.md`
- `.cursor/`、`.claude/`、`.opencode/`、`.pi/`

如果已经存在 Harness 文件，不要继续安装，改走下面的权限化变更方法。

## 首次安装产物

| 源码仓库路径 | 目标项目路径 | 职责 |
|---|---|---|
| `.harness/common/**` | `.harness/common/**` | Harness 规则、技能、Agent、schema、CLI、协议、runtime overlay |
| `.harness/docs/**` | `.harness/docs/**` | 安装后参考文档 |
| `.harness/workflow-map.html` | `.harness/workflow-map.html` | 工作流地图 |
| `harness-runtime/**` | `harness-runtime/**` | Runtime 骨架、模板、脚本、配置 |
| `project-knowledge/**` | `project-knowledge/**` | 项目长期知识库初始结构 |
| `package/adapters/**` | 根入口文件和工具目录 | Codex、Claude、Cursor、OpenCode、Pi 等入口 |

已有的 `project-knowledge/**` 不能被覆盖。它是团队长期知识资产，不是框架运行状态。

## 已安装项目的更新或迁移

不要运行自动安装模式。先产出权限化变更计划。

```markdown
# Harness Permissioned Change Plan

## Target
- Project root:
- Current Harness evidence:
- Requested change:

## Asset Classification
| Class | Paths | Operation | Permission Required | Risk | Rollback |
|---|---|---|---|---|---|
| A framework | `.harness/common/**`, `.harness/docs/**` | replace/patch | approve-framework | medium | restore backup |
| B adapter entry | `AGENTS.md`, `CLAUDE.md`, `.cursor/**`, `.opencode/**`, `.pi/**` | patch/replace | approve-adapter | medium | restore backup |
| C runtime structure | `harness-runtime/config/**`, `harness-runtime/templates/**`, `harness-runtime/bin/**`, `harness-runtime/scripts/**` | patch/merge | approve-runtime-structure | high | restore backup |
| D runtime data | `harness-runtime/harness/**` | read-only by default | approve-runtime-data | critical | restore backup |
| E project knowledge | `project-knowledge/**` | patch/create | approve-project-knowledge | high | restore backup |

## Proposed Operations
| ID | Path | Operation | Source | Why Needed | Verification |
|---|---|---|---|---|---|
| OP-001 | TBD | TBD | TBD | TBD | TBD |

## Explicit User Approval
- Approved operation ids:
- Rejected operation ids:
- Accepted risks:
```

只执行用户批准的 operation id。不要把一句“更新 Harness”理解成可以覆盖整目录。

## 模板迁移更新

模板迁移更新的目标是：让已安装项目切到新的 HarnessV2 模板，同时保留已有 runtime 数据，并让历史任务结果在新模板下继续可读、可索引、可复用。

这不是 `install.py --update`。它必须拆成权限化 operation 执行。

### 必须保留的 runtime 数据

以下路径默认只读，不得覆盖：

| 路径 | 内容 |
|---|---|
| `harness-runtime/harness/missions/**` | 任务契约实例 |
| `harness-runtime/harness/stages/**` | PRD、方案、设计、拆解、验证、交付、复盘等阶段结果 |
| `harness-runtime/harness/traces/**` | 执行证据、迁移记录、回退记录 |
| `harness-runtime/harness/state/**` | approvals、trace-log、状态缓存 |
| `harness-runtime/harness/work-graph/**` | Work Graph node、board、index、tree |
| `harness-runtime/harness/deliveries/**` | 交付归档 |
| `harness-runtime/harness/memory/**` | 历史沉淀 |
| `project-knowledge/**` | 项目长期知识库 |
| `project-context.md` | 旧项目上下文；若已迁入 `project-knowledge/context/`，仍保留来源记录 |
| `harness-runtime/project-spec/specs/**` | 旧安装中的 legacy 行为规格；迁移到 `project-knowledge/specs/**` 前不得删除 |

### 可以迁移到新模板的资产

这些路径可以作为新模板资产刷新，但必须先列入 operation 并获得对应授权：

| 资产 | 操作 | 权限 |
|---|---|---|
| `.harness/common/**` | 用新模板替换或 patch | `approve-framework` |
| `.harness/docs/**` | 用新模板替换或 patch | `approve-framework` |
| `.harness/workflow-map.html` | 用新模板替换 | `approve-framework` |
| `AGENTS.md`、`CLAUDE.md`、`.cursor/**`、`.opencode/**`、`.pi/**` | 重新渲染或 patch adapter 入口 | `approve-adapter` |
| `harness-runtime/bin/harness` | 刷新 shim | `approve-runtime-structure` |
| `harness-runtime/templates/**`、`harness-runtime/scripts/**` | 合并新增模板和脚本 | `approve-runtime-structure` |
| `harness-runtime/config/**` | 只做 key 级合并；目标项目已有值优先 | `approve-runtime-structure` |

### 结果迁移规则

历史任务结果不要原地改写。迁移时按这个顺序处理：

1. 盘点旧结果：列出 `missions/`、`stages/`、`deliveries/`、`work-graph/`、`memory/`、legacy `project-spec/specs/` 中已有内容。
2. 生成迁移计划：写入 `harness-runtime/harness/traces/<YYYYMMDD>-template-migration/plan.md`，记录来源路径、目标路径、迁移原因、是否需要人工批准。
3. 新模板校验：用新 `.harness/common/**` 运行 control、graph、knowledge、contract 检查，确认旧结果是否还能被新控制面读取。
4. 语义迁移：只有当新模板的产物结构变化时，才创建适配后的新副本；旧结果保留不动，新副本必须带来源链接。
5. 知识沉淀：已完成任务中的稳定结论、规格、设计决策、工程约定、运行手册和教训，迁入 `project-knowledge/**`，然后运行 `harness knowledge index`。
6. 行为规格迁移：旧 `harness-runtime/project-spec/specs/**` 中仍有效的能力规格，迁入 `project-knowledge/specs/**`；迁移前后都保留 source metadata。
7. 收尾记录：在 migration trace 中记录已迁移、保留、跳过和需要后续人工确认的项。

### 推荐 operation 拆分

| ID | 目的 | 路径 | 权限 |
|---|---|---|---|
| OP-FW-001 | 刷新框架正文 | `.harness/common/**` | `approve-framework` |
| OP-DOC-001 | 刷新安装后文档 | `.harness/docs/**`、`.harness/workflow-map.html` | `approve-framework` |
| OP-ADAPTER-001 | 重新生成工具入口 | `AGENTS.md`、adapter 目录 | `approve-adapter` |
| OP-RUNTIME-001 | 合并 runtime 结构资产 | `harness-runtime/bin/**`、`harness-runtime/templates/**`、`scripts/**`、`config/**` | `approve-runtime-structure` |
| OP-RESULT-001 | 生成迁移计划和索引历史结果 | `harness-runtime/harness/traces/<date>-template-migration/**` | `approve-runtime-data` |
| OP-KNOWLEDGE-001 | 将稳定结果沉淀到项目知识库 | `project-knowledge/**` | `approve-project-knowledge` |

只有 OP-RESULT-001 和 OP-KNOWLEDGE-001 可以写入历史结果相关区域；它们也只能新增迁移记录或提炼后的知识，不得删除旧 runtime 数据。

## 禁止的捷径

这些参数已经废弃，`install.py` 会拒绝执行：

```bash
python3 install.py /path/to/project --update
python3 install.py /path/to/project --migrate-legacy
python3 install.py /path/to/project --migrate-harness-dir
```

`--force` 也不是更新方法。只有用户明确批准替换受影响的 scaffold / runtime structure 路径时，才可以把它作为某个已批准 operation 的执行手段。

## 项目知识

`project-knowledge/` 是项目长期知识库，供后续任务在做需求、方案、设计、编码和验证时读取。

用 Harness CLI 管理结构和上下文解析：

```bash
harness-runtime/bin/harness --root /path/to/project knowledge check --json
harness-runtime/bin/harness --root /path/to/project knowledge index --json
harness-runtime/bin/harness --root /path/to/project knowledge resolve --stage <stage> --json
harness-runtime/bin/harness --root /path/to/project knowledge promote --mission <mission-id> --write-plan --json
```

不要把完整阶段产物直接复制进项目知识库。只沉淀稳定的产品知识、规格、设计决策、工程约定、运行手册和复盘教训。

## 验证

首次安装或权限化变更后至少运行：

```bash
harness-runtime/bin/harness --root /path/to/project control status --json
harness-runtime/bin/harness --root /path/to/project knowledge check --json
```

修改 HarnessV2 源码仓库自身时运行：

```bash
python3 -m py_compile install.py .harness/common/cli/harness_cli.py
python3 -m pytest tests
```
