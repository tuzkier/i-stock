---
name: harness-update
description: 用新版本 HarnessV2 模板刷新已安装项目的框架正文（A 类资产），按权限化变更协议拆 operation 并等待用户批准。
argument-hint: "[upstream-source-path]"
scope: post-install
requires:
  - .harness/docs/install-guide.md
  - .harness/common/rules/core.md
asset_class: A
permission: approve-framework
---

# /harness-update

用新版本的 HarnessV2 模板刷新当前已安装项目的**框架正文**。不动 runtime 数据、不动 project-knowledge、不动 adapter 入口。

## 触发条件

- 项目已经安装 Harness（存在 `.harness/common/rules/core.md`）
- 用户拿到新版本的 HarnessV2 源码仓库（或对应 tag），想把框架升级到新版本
- 用户**没有**要求迁移历史结果或调整 adapter 集合（那是 `/harness-migrate` 或 `/harness-add-adapter` 的事）

## 严格不做

- 不运行 `install.py --force` 整目录覆盖
- 不动 `harness-runtime/harness/**`（mission / stages / traces / state / work-graph / deliveries / memory）
- 不动 `project-knowledge/**`
- 不动根 `AGENTS.md` / `CLAUDE.md` 等 adapter 入口（除非 operation 表格里被显式列出且用户批准）

## 执行 procedure

### 1. 前置检查

- 读 `.harness/docs/install-guide.md`（即原 `INSTALL.md` 的运行现场副本）确认当前权限化协议没有变
- 读 `.harness/common/rules/core.md` 与 `.harness/common/rules/decision-system.md` 确认本次动作满足 Decision Gate 要求
- 询问用户上游 HarnessV2 模板的本地路径（参数 `$1` 或交互获取）。下文用 `<upstream>` 指代它
- 如果用户没给出，停在这里要求提供，不要自己猜

### 2. 版本比对

- 读 `<upstream>/VERSION` 与目标项目 `harness-runtime/config/harness.yaml` 里的 `harness_template.version`
- 列出版本差异（current → target）
- 如果两边一致，停下并报告"已经是同一版本，无需更新"，不进入 operation 阶段

### 3. 生成 operation 表

按下表生成 **Permissioned Change Plan**，写入 `harness-runtime/harness/traces/<YYYYMMDD>-harness-update/plan.md`：

| ID | Path | Operation | Source | Why Needed | Verification |
|---|---|---|---|---|---|
| OP-FW-001 | `.harness/common/**` | replace | `<upstream>/package/common/**` | 框架正文升级 | `harness control status --json` |
| OP-DOC-001 | `.harness/docs/**` | replace | `<upstream>/package/docs/**` | 安装后文档刷新 | 抽样 diff |
| OP-DOC-002 | `.harness/workflow-map.html` | replace | `<upstream>/package/workflow-map.html` | 工作流地图刷新 | 打开核验 |
| OP-VER-001 | `harness-runtime/config/harness.yaml` 中的 `harness_template` block | patch | `<upstream>/VERSION` + git short SHA | 元数据同步 | yaml 解析 |

> 不要把 `harness-runtime/templates/**`、`harness-runtime/scripts/**`、`harness-runtime/bin/**`、`harness-runtime/config/**` 写入这张表。它们是 C 类 runtime structure，需要 `approve-runtime-structure`，请用户走 `/harness-migrate` 而不是 `/harness-update`。

### 4. Decision Gate

在 plan 末尾追加 explicit user approval 区块：

```markdown
## Explicit User Approval
- Approved operation ids:
- Rejected operation ids:
- Accepted risks:
```

把 plan 路径展示给用户，**停下等待 approval**。用户填回 approved ids 之前不要执行任何写入。

### 5. 执行已批准 operation

- 对每个 approved id：
  - 先把目标路径备份到 `harness-runtime/harness/traces/<YYYYMMDD>-harness-update/backup/<op-id>/`
  - 再做替换 / patch
  - 在 plan 文件里把该行打上 `[done]` 标记和时间戳
- 拒绝 / 未批准的 operation 留 `[skipped]` 标记，不动磁盘

### 6. 验证

执行（必跑）：

```bash
harness-runtime/bin/harness --root . control status --json
harness-runtime/bin/harness --root . knowledge check --json
```

将 stdout 写入 `harness-runtime/harness/traces/<YYYYMMDD>-harness-update/verify.log`。

### 7. 回滚条件

如果任一验证命令非零退出，或用户在交付前判定回滚，按 backup/<op-id>/ 逆序还原，并在 plan 末尾记录 `## Rollback` 区块。

## 输出契约

- `harness-runtime/harness/traces/<YYYYMMDD>-harness-update/plan.md`
- `harness-runtime/harness/traces/<YYYYMMDD>-harness-update/backup/**`
- `harness-runtime/harness/traces/<YYYYMMDD>-harness-update/verify.log`
- 终端摘要：approved ids、skipped ids、verification 结果

## 拒绝执行的情形

- 上游路径不存在或不是 HarnessV2 源码仓库（不含 `install.py` 与 `package/common/rules/core.md`）
- 目标项目没装过 Harness（`.harness/common/rules/core.md` 不存在）
- 用户未给出 Approved operation ids
- 当前分支有 uncommitted 改动且用户未明确接受风险
