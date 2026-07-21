# Project Context

> **来源**：`generate-context` 技能或 retrospective 更新
> **目的**：记录所有 AI 执行者必须长期遵守的项目级约束。只写项目特有、容易被忽视、会影响执行正确性的事实。

**Author:** {{user_name}}
**Date:** {{date}}
**Project:** {{project_name}}
**Status:** `draft` <!-- draft / active / needs-review -->

---

## 项目概览

| 字段 | 值 |
|------|----|
| 项目类型 | greenfield / brownfield |
| 主要语言 | {{primary_language}} |
| 主要框架 | {{primary_framework}} |
| 包管理器 | {{package_manager}} |
| 运行入口 | {{run_entrypoint}} |
| 测试入口 | {{test_entrypoint}} |

{{project_summary}}

---

## 架构约束

> 只记录本项目强制遵守或禁止使用的架构规则。通用最佳实践不写。

| 约束 ID | 规则 | 适用范围 | 证据 / 来源 |
|---------|------|----------|-------------|
| ARCH-001 | {{architecture_rule}} | {{scope}} | {{source}} |

---

## 编码规范

| 约束 ID | 规则 | 示例 / 说明 | 违反风险 |
|---------|------|-------------|----------|
| CODE-001 | {{coding_rule}} | {{example}} | {{risk}} |

---

## 技术选择

| 场景 | 默认选择 | 禁止 / 避免 | 理由 |
|------|----------|-------------|------|
| {{scenario}} | {{preferred_choice}} | {{forbidden_choice}} | {{rationale}} |

---

## 测试约定

| 层级 | 命令 | 测试路径 | 说明 |
|------|------|----------|------|
| unit / integration | `{{test_command}}` | {{test_path}} | {{test_note}} |
| lint / typecheck | `{{quality_command}}` | {{quality_scope}} | {{quality_note}} |
| e2e | `{{e2e_command}}` | {{e2e_path}} | {{e2e_note}} |

---

## 运行时环境

| 检测项 | 当前值 | 获取方式 | 备注 |
|--------|--------|----------|------|
| OS / Arch | {{os_arch}} | `uname -a` | {{os_note}} |
| Node | {{node_version}} | `node -v` | {{node_note}} |
| Python | {{python_version}} | `python3 --version` | {{python_note}} |
| Git | {{git_version}} | `git --version` | {{git_note}} |
| Docker | {{docker_version}} | `docker --version` | {{docker_note}} |

---

## Git 约定

| 项 | 约定 |
|----|------|
| 默认分支 | {{default_branch}} |
| mission 分支格式 | {{mission_branch_pattern}} |
| stage worktree 根目录 | {{stage_worktree_root}} |
| 提交信息格式 | {{commit_message_format}} |
| 推送 / PR 约定 | {{push_pr_policy}} |

---

## 已知风险与坑

| ID | 场景 | 风险 | 正确处理 |
|----|------|------|----------|
| PIT-001 | {{pitfall_context}} | {{pitfall_risk}} | {{correct_handling}} |

---

## 历史教训

> retrospective、bug-fix、quality-control 可以追加本节。每条教训必须能改变未来执行行为。

| 日期 | 来源 mission | 教训 | 后续规则 / 影响 |
|------|--------------|------|-----------------|
| {{date}} | {{mission_id}} | {{lesson}} | {{future_rule}} |
