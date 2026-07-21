# Operating Model

本文件是 HarnessV2 模板的顶层设计文档。它回答三个问题：

1. 这个模板让 AI 怎么工作
2. 人和 AI 各自负责什么
3. 什么时候走轻路径，什么时候走重路径

## 一句话定位

HarnessV2 是一个给 Cursor 使用的模板。AI 接到任务后默认持续推进，只在命中 Decision Gate 或确认门时暂停并等待人类输入。

## 人和 AI 的分工

### 人负责什么

人不是每一步都亲自写代码，而是负责五类高杠杆控制：

1. **定义目标**：这次到底要解决什么问题
2. **定义边界**：哪些事情这轮做，哪些不做
3. **定义验收**：结果怎样才算完成
4. **决定取舍**：多方案冲突时拍板选哪个
5. **兜住风险**：高风险改动是否允许执行

### AI 负责什么

AI 负责受约束的执行，不是方向性决策：

- 读取当前上下文和任务边界
- 规划下一步最小动作
- 执行并验证
- 产出结构化的阶段文档
- 准确识别需要人类介入的时刻

AI 不应该默认拥有：重定义需求的权力、越过 Stage Gate 的权力、擅自扩范围的权力、用降级方案假装完成的权力。

## 三种工作模式

HarnessV2 把所有输入分成三种模式，模式决定 AI 的行为边界。

### conversation

适用于讨论、解释、澄清、审查反馈、方案比较。

- 不创建任务契约
- 不进入自治循环
- 不产出阶段文档

### 默认执行模式（`autonomous_execution`）

适用于绝大多数正常任务。这是默认模式。

- 创建任务契约
- 进入自治循环，默认持续推进
- 命中 Checkpoint（阶段文档需要人确认）时暂停
- 命中 Decision Gate（需要人拍板）时暂停
- 其余时间 AI 自主执行

### 高治理执行模式（`governed_execution`）

适用于高风险任务、高复杂度任务、多方案冲突的任务。

- 创建任务契约，且执行治理级别（`autonomy_level`）设为“受控推进”
- 进入自治循环；哪些关键阶段产物需要人确认由 `execution_governance.levels.受控推进.human_checkpoints` 配置
- 可以触发设计评审（Council 机制）
- 审批链更长，但保障更强

### 如何判断用哪种模式

```
收到输入
├── 是讨论/解释/澄清？ → conversation
├── 是明确的、低风险的、边界清晰的任务？ → 默认执行模式（autonomous_execution）
└── 是高风险的、跨模块的、方案不确定的？ → 高治理执行模式（governed_execution）
```

当默认执行模式过程中发现任务比预期复杂时，AI 应主动升级为高治理执行模式。升级条件定义在 `harness-runtime/config/harness.yaml` 的 `escalation` 字段中。

## 模板内部的核心对象

### 任务契约

每轮任务的入口契约。它定义了目标、范围、验收标准、执行治理级别和升级规则。

没有任务契约，AI 就不知道自己这次被授权做什么、推进到哪里、什么时候必须停下来。它是整个执行的锚点。

详见 `mission-contract.md`。

### 自治循环

AI 的主循环。结构是：

```
恢复 Work Graph / Mission Slice → 选择当前 lane action → 执行 → Stage Gate → 写回 graph operation → 判断（继续 / checkpoint / 升级 / 收口）
```

阶段文档的产出都发生在当前 Mission Slice action 内部。循环本身不扫描固定阶段队列；它只关心当前 Work Graph node、lane action、任务契约目标和 graph operation 是否可以推进。

详见 `autonomy-loop.md`。

### 决策系统

定义"什么时候 AI 必须停下来找人"。四类决策：

1. **boundary_decision**：需求边界变了或不清楚
2. **artifact_confirmation**：阶段文档需要人确认
3. **risk_acceptance**：高风险改动需要人拍板
4. **tradeoff_decision**：多方案取舍需要人决定

详见 `decision-and-checkpoint.md`。

### Artifact Gate

判断阶段文档是否合格。它只回答两个问题：

1. 当前阶段文档是否存在且结构完整
2. 当前阶段文档是否需要人工审核

Gate 不决定下一步做什么，不编排执行，不推断模式。

### Execution Driver

负责触发下一轮执行。可以是：

- Cursor 的 stop hook（当前主要方式）
- 手动触发
- 未来的外部控制面

Driver 只负责"谁来触发"，不负责"该做什么"。

## 阶段文档在执行中的位置

阶段文档不是治理负担，而是执行的自然产出。AI 在推进任务的过程中，每到一个阶段会产出对应的文档。这些文档同时服务两个目的：

1. **给人审阅**：正式、可读、能在 5 分钟内抓到主线
2. **给下游消费**：结构稳定，下一个阶段的 AI 能直接从中提取上下文

详见 `stage-docs-spec.md`。

## 与旧 Harness 的主要区别

| 维度 | 旧 Harness | HarnessV2 |
|------|-----------|-----------|
| 主角 | 治理、留痕、Gate | AI 持续执行 |
| 入口对象 | stage / 任务项文件 | 任务契约 |
| Council | 默认前置入口 | 升级机制 |
| 模式 | conversation / fast_track / full_flow | conversation / autonomous_execution / governed_execution |
| Gate | 一个 Stage Gate 混合体 | Artifact Gate + 决策系统 + Driver 分拆 |
| 阶段文档 | 偏内部状态 dump | 正式可读文档 |
| 人工参与 | 频繁的命令切换 | 只在 Checkpoint 和 Decision Gate 介入 |

## 阅读顺序

读完本文件后，推荐按以下顺序继续：

1. `mission-contract.md`
2. `autonomy-loop.md`
3. `decision-and-checkpoint.md`
4. `stage-docs-spec.md`
5. `cursor-conventions.md`
