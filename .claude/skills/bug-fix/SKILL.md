---
name: bug-fix
description: '当存在 expected vs actual 偏差并需要缺陷闭环时使用：用户报告结果不对、输出丢失内容/样式、行为回归、线上异常、crash、测试失败指向产品行为缺陷、验证发现验收场景 / 条件未通过，或审查员指出 correctness defect。'
---

# 缺陷修复

## 铁律

```
没有复现证据或 blocked 复现记录，不写修复代码。
```

## 何时使用

- 用户描述了 expected vs actual 偏差：结果不对、内容缺失、样式丢失、状态错误、输出与模板 / 规格 / 验收场景或条件不符
- 用户说有缺陷、线上异常、回归、crash
- 测试失败表现为产品行为缺陷，或验证中的验收场景 / 条件失败
- correctness 审查员发现 High defect

## 典型表达

| 用户表达 | 路由原因 |
|----------|----------|
| "某个输出产物缺失了预期内容或样式" | 输出产物与预期不符，需要复现、根因、修复、回归闭环 |
| "这个接口返回结果不对" | 存在 expected vs actual 偏差 |
| "昨天还好的功能今天回归了" | 回归缺陷，需要缺陷闭环 |

## 边界

本技能不替代 `execute` 的代码修改，也不替代 `systematic-debugging` 的根因分析能力。它读取 `.harness/common/protocols/bug-fix/PROTOCOL.md`，保证复现、根因、修复、回归、验证和记忆决策闭环。

路由优先级：只要输入包含具体不符合预期的行为或产物，就先进入 `bug-fix`；只有在根因定位阶段才把 `systematic-debugging` 作为 carrier 调用。

按 `./workflow.md` 执行。
# 缺陷修复工作流

## CLI-first control-plane preflight

适用场景：`bug_report`、`continue`、`status`。进入缺陷闭环前先调用 `harness-cli` 执行 `harness control status --json`、`harness control candidates --intent continue --json`；若缺陷疑似属于现有任务，显式确定 mission 后再执行 `harness control frame --mission <mission-id> --json`、`harness control guidance --mission <mission-id> --json`、`harness control context-index --mission <mission-id> --json`。若不属于当前 Mission 或需要扩大范围，按 Decision Gate 处理；不得把 candidates 当作最终选择。若必须临时读取旧 runtime 文件，记录 `fallback_used`、`fallback_reason`、`legacy_source`、`follow_up`。

## 初始化

1. 读取 `.harness/common/protocols/README.md`
2. 读取 `.harness/common/protocols/bug-fix/PROTOCOL.md`
3. 读取当前任务契约、execution-brief、验证报告 / failing command 输出（如存在）
4. 调用 `harness-cli` 执行 `harness context check --json`；PASS 则读取 `project-context.md`，FAIL 时按 `project-context` 规则记录 `inputs_missing.project_context=true` 不得静默继续。同时按 `spec.enabled` 决定是否读取 `project-knowledge/specs/`

## 执行

<workflow skill="bug-fix" version="2">

<step n="1" goal="缺陷接入">
 - 结构化记录 symptom、impact、reproduction steps / trigger、actual result、expected result、suspected area、severity、范围
 - 条件：关键信息无法从日志、测试、代码或用户描述补全
 - 提出澄清问题或记录阻塞，不得猜测式修复
</step>

<step n="2" goal="范围与意图检查">
 - 判断缺陷是否属于当前任务、当前改动回归、阻塞验收场景 / 条件，或无关后续事项
 - 条件：修复需要扩大范围
 - 触发 Decision Gate
</step>

<step n="3" goal="先复现">
 - 优先写或运行失败测试，其次使用可重复命令、E2E/browser/screenshot、最小手动步骤
 - 保存 reproduction evidence ID，并记录命令、cwd、exit code、输出摘要
 - 条件：无法复现
 - 记录 attempted commands / inputs / environment 和阻塞 reason；不得进入 patch
</step>

<step n="4" goal="根因分析">
 - 调度 `trace-log` 记录 carrier 切换：

 ```yaml
 carrier_invocation:
 from_skill: bug-fix
 to_skill: systematic-debugging
 protocol: bug-fix
 reason: root_cause_analysis
 ```

 - 使用 `systematic-debugging` 定位 direct cause、deep cause、Harness 缺口、blast radius
 - 根因必须引用代码、测试、日志、规格或阶段文档证据
 - systematic-debugging 返回后，调度 `trace-log` 记录 `bug-fix:root_cause` 事件，包含 direct cause、deep cause、Harness 缺口和 blast radius 摘要
</step>

<step n="5" goal="约束下修复">
 - 进入 `execute` 或当前修复 carrier，只针对根因做最小修复
 - 禁止删除、跳过、弱化复现测试；公共行为变化必须回到行为契约 / 差量规格
</step>

<step n="6" goal="回归与验证">
 - 运行复现测试确认 red -> green，运行相关回归包，调用 `verify/scripts/collect_command_evidence.py` 收集 fresh evidence
 - 有逻辑变更时触发相关审查员重新确认
</step>

<step n="7" goal="Harness 缺口决策">
 - 决定是否更新 project-knowledge/specs、project-context、回归测试、审查检查清单、模板 / 工作流 candidate
 - 为每个记忆决策分配 `MEM-NNN` 候选 ID；retrospective 阶段负责合并去重并写入 Memory Update Contract（记忆更新契约）
 - 每项写 applied / proposed / 延后和理由
</step>

</workflow>
