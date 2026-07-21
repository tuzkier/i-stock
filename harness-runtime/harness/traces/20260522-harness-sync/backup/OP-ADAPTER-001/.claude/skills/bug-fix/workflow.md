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
 - 判断缺陷是否属于当前任务、当前改动回归、阻塞 AC、或无关后续事项
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
