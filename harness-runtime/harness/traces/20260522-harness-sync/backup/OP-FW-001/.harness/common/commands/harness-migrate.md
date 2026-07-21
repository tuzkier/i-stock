---
name: harness-migrate
description: 完整模板迁移——把已安装项目切到新版本 HarnessV2 模板，保留 runtime 数据，并按权限化 operation 处理框架、文档、adapter 入口、runtime 结构和历史结果迁移。
argument-hint: "[upstream-source-path]"
scope: post-install
requires:
  - .harness/docs/install-guide.md
  - .harness/common/rules/core.md
asset_class: A+B+C+D+E
permission:
  - approve-framework
  - approve-adapter
  - approve-runtime-structure
  - approve-runtime-data
  - approve-project-knowledge
---

# /harness-migrate

模板迁移：把已安装项目从旧版本 HarnessV2 模板**整体切换**到新版本。比 `/harness-update` 范围大——除了框架正文，还包括 adapter 入口、runtime 结构资产（templates / scripts / bin / config）、历史结果索引、项目知识沉淀。

**默认保留 runtime 数据**。本命令不会删除 `harness-runtime/harness/**` 与 `project-knowledge/**` 已有内容，但会生成迁移轨迹、索引和必要的语义副本。

## 触发条件

- 项目已经安装 Harness
- 用户拿到新版本 HarnessV2 源码仓库（VERSION 差异较大、或上游 release notes 标注 breaking schema 变更）
- 用户接受这是一次跨 5 类资产的整体动作，不是单点刷新

## 严格不做

- 不原地改写 `harness-runtime/harness/**` 下任意历史结果
- 不删除 `project-knowledge/**`
- 不绕过用户 approval 直接执行任一 operation
- 不在分支有 uncommitted 改动时启动

## Runtime 数据保留清单

下列路径在迁移期间默认只读，不得 replace 或 delete。它们只能由 OP-RESULT-* 与 OP-KNOWLEDGE-* 类 operation 新增内容：

| 路径 | 内容 |
|---|---|
| `harness-runtime/harness/missions/**` | 任务契约实例 |
| `harness-runtime/harness/stages/**` | PRD / 方案 / 设计 / 拆解 / 验证 / 交付 / 复盘等阶段结果 |
| `harness-runtime/harness/traces/**` | 执行证据、迁移记录、回退记录 |
| `harness-runtime/harness/state/**` | approvals、trace-log、状态缓存 |
| `harness-runtime/harness/work-graph/**` | Work Graph node / board / index / tree |
| `harness-runtime/harness/deliveries/**` | 交付归档 |
| `harness-runtime/harness/memory/**` | 历史沉淀 |
| `project-knowledge/**` | 项目长期知识库 |
| `project-context.md` | 旧项目上下文 |
| `harness-runtime/project-spec/specs/**` | legacy 行为规格 |

## 执行 procedure

### 1. 前置检查

- 工作树干净；存在未提交变更时停下要求用户提交或显式接受风险
- 读 `.harness/docs/install-guide.md` 中"模板迁移更新"小节确认协议没有变
- 上游路径 `<upstream>` 必须存在 `install.py` 与 `package/common/rules/core.md`
- 比对 VERSION：相同则停下，建议改走 `/harness-update`

### 2. 盘点旧 runtime

写入 `harness-runtime/harness/traces/<YYYYMMDD>-template-migration/inventory.md`：

- `missions/**` 列表（含 mission-id、status）
- `stages/**` 列表（含 stage、artifact）
- `work-graph/**` 当前节点与 board 视图
- `deliveries/**` 列表
- `memory/**` 列表
- legacy `project-spec/specs/**`（如有）

### 3. 生成 operation 表

写入 `harness-runtime/harness/traces/<YYYYMMDD>-template-migration/plan.md`，至少包含：

| ID | 目的 | 路径 | 操作 | 权限 |
|---|---|---|---|---|
| OP-FW-001 | 刷新框架正文 | `.harness/common/**` | replace | `approve-framework` |
| OP-DOC-001 | 刷新安装后文档 | `.harness/docs/**`、`.harness/workflow-map.html` | replace | `approve-framework` |
| OP-ADAPTER-001 | 重新生成 adapter 入口 | `AGENTS.md` / `CLAUDE.md` / `.cursor/**` / `.opencode/**` / `.pi/**` 等当前已装 adapter | patch / replace | `approve-adapter` |
| OP-RUNTIME-001 | 合并 runtime 结构资产 | `harness-runtime/bin/**`、`harness-runtime/templates/**`、`harness-runtime/scripts/**`、`harness-runtime/config/**` | patch（config 走 key 级合并，目标值优先） | `approve-runtime-structure` |
| OP-RESULT-001 | 生成迁移计划 + 历史结果适配副本（仅在新模板产物结构变化时） | `harness-runtime/harness/traces/<date>-template-migration/**` | create | `approve-runtime-data` |
| OP-KNOWLEDGE-001 | 沉淀稳定结论到知识库 | `project-knowledge/**` | patch / create | `approve-project-knowledge` |
| OP-SPEC-001 | legacy `project-spec/specs/**` 迁入 `project-knowledge/specs/**` | 同上 | move + 保留 source metadata | `approve-project-knowledge` |
| OP-VER-001 | 同步 `harness_template` 元数据 | `harness-runtime/config/harness.yaml` 中的对应 block | patch | `approve-runtime-structure` |

对每一项标注：source 上游路径、why needed、verification、rollback。

### 4. Decision Gate

plan 末尾追加：

```markdown
## Explicit User Approval
- Approved operation ids:
- Rejected operation ids:
- Accepted risks:
```

**等用户填回，再继续**。

### 5. 执行已批准 operation

- 按 ID 顺序执行
- 每个 op 先备份到 `harness-runtime/harness/traces/<YYYYMMDD>-template-migration/backup/<op-id>/`
- replace 类用上游对应路径整体替换；patch 类做最小差量
- config 合并规则：目标项目已有值优先；新增 key 写入；删除 key 必须列在 plan 中由用户单独 approve
- 历史结果**绝不原地改写**——OP-RESULT-001 只能创建带 `source_link` 的新副本
- 每个 op 完成后在 plan 中打 `[done]` 时间戳；rejected 留 `[skipped]`

### 6. 新模板可读性校验

执行：

```bash
harness-runtime/bin/harness --root . control status --json
harness-runtime/bin/harness --root . knowledge check --json
harness-runtime/bin/harness --root . knowledge index --json
```

任一非零退出 → 停在这里写 `## Verification Failure`，等用户决定继续修复还是回滚。

### 7. 收尾记录

在 plan 末尾追加 `## Migration Summary`：

- 已迁移项
- 保留未动项
- 跳过项及原因
- 仍需人工确认项

### 8. 回滚

完整回滚按 backup/<op-id>/ 逆序还原；部分回滚必须列出回滚 id 并附原因。

## 输出契约

- `harness-runtime/harness/traces/<YYYYMMDD>-template-migration/inventory.md`
- `harness-runtime/harness/traces/<YYYYMMDD>-template-migration/plan.md`
- `harness-runtime/harness/traces/<YYYYMMDD>-template-migration/backup/**`
- 验证 stdout 落 `verify.log`
- 终端摘要：approved / skipped / failed

## 拒绝执行的情形

- 工作树有 uncommitted 改动且用户未接受风险
- 上游路径校验失败
- 用户未提供 Approved operation ids
- 任一 approve 类权限被 hooks 配置否决
