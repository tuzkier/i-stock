# Agent Eval Report: {{mission_id}}

> **来源**：agent-eval 技能 → `harness-runtime/harness/stages/{{mission_id}}/agent-eval-report.md`
> **上游**：`solution.md ## Agent 架构` | `tech-design.md ## Agent 实现`
> **目的**：验证 Agent 行为分布是否符合设计中的工作权、边界权、责任权和 eval 阈值。

**Author:** {{user_name}}
**Date:** {{date}}
**mission-id:** {{mission_id}}
**Status:** `draft` <!-- draft / pass / blocked / regression -->

---

## 整体结论

| 字段 | 值 |
|------|----|
| Verdict | PASS / FAIL / REGRESSION / BLOCKED |
| 评估 Agent 数 | {{agent_count}} |
| High 失败数 | {{high_failure_count}} |
| 是否存在行为退化 | yes / no |
| 是否需要返回 execute / design | yes / no |

{{eval_summary}}

---

## 评估范围

| Agent 组件 | 设计来源 | 工作权范围 | Eval 阈值 | 本次是否评估 |
|------------|----------|------------|-----------|--------------|
| {{agent_name}} | tech-design.md#{{section}} | {{work_scope}} | {{threshold}} | yes / no |

---

## 输入集设计

| Agent | 场景类型 | 输入 ID | 输入摘要 | 预期行为 | 运行次数 |
|-------|----------|---------|----------|----------|----------|
| {{agent_name}} | normal / boundary / adversarial / ambiguous | EVAL-IN-001 | {{input_summary}} | {{expected_behavior}} | {{run_count}} |

---

## 行为分布

| Agent | 场景类型 | 样本数 | 通过数 | 通过率 | 阈值 | 结论 |
|-------|----------|--------|--------|--------|------|------|
| {{agent_name}} | normal | {{sample_count}} | {{pass_count}} | {{pass_rate}} | {{threshold}} | pass / fail |
| {{agent_name}} | boundary | {{sample_count}} | {{pass_count}} | {{pass_rate}} | {{threshold}} | pass / fail |
| {{agent_name}} | adversarial | {{sample_count}} | {{pass_count}} | {{pass_rate}} | {{threshold}} | pass / fail |
| {{agent_name}} | ambiguous | {{sample_count}} | {{pass_count}} | {{pass_rate}} | {{threshold}} | pass / fail |

---

## 失败案例

| Failure ID | Agent | 场景 | 输入 | 预期输出 | 实际输出 | 失真工作权 | 严重级别 |
|------------|-------|------|------|----------|----------|------------|----------|
| EVAL-FND-001 | {{agent_name}} | {{scenario_type}} | {{input_ref}} | {{expected_output}} | {{actual_output}} | 判断权 / 行动权 / 边界权 / 责任权 | high / medium / low |

### 根因分析

| Failure ID | 根因分类 | 证据 | 修复方向 |
|------------|----------|------|----------|
| EVAL-FND-001 | 知识不足 / 偏好层不足 / 制度层未执行化 / 工具缺口 | {{evidence}} | {{fix_direction}} |

---

## 回归对比

| Agent | 指标 | 历史基线 | 本次结果 | 变化 | 结论 |
|-------|------|----------|----------|------|------|
| {{agent_name}} | boundary adherence | {{baseline}} | {{current}} | {{delta}} | stable / regression |

---

## 阻塞项与后续动作

| 项 | 影响 | 下一步 | Owner |
|----|------|--------|-------|
| {{blocked_item}} | {{impact}} | {{next_step}} | {{owner}} |
