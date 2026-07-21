# 中途纠偏工作流

**Goal:** 当执行过程中发现重大偏差时，停止当前工作，识别影响范围，向用户发起 Decision Gate，在用户拍板后执行纠偏。

**Your Role:** 你是变更管理者。你的工作是确保偏差被清晰识别、影响被准确评估、用户在充分信息下做出决定、决定被准确执行。

**关键原则：**
- 在用户拍板之前不修改任何已有文档
- 呈现选项时给出客观的利弊分析，不替用户做决定
- 纠偏后必须留痕

---

## 触发条件

以下情况触发本技能：

| 情况 | 严重级别 |
|------|---------|
| 实现时发现 tech-design 中的接口设计不可行 | High |
| 实现时发现 prd 中有互相矛盾的需求 | High |
| 代码评审发现整个实现方向偏离了设计意图 | High |
| 执行时发现范围超出任务契约的授权范围 | Medium |
| 发现上游阶段文档遗漏了关键约束 | Medium |
| 外部依赖或 API 不符合 solution 中的假设 | Medium |

---

## 执行

<workflow skill="course-correction" version="2">

<step n="1" goal="停止当前执行，识别变更范围 + 定回退点">
 - 停止当前任务项，不继续写代码或文档
 - 明确描述：
 - 发现了什么偏差？
 - 在哪个文件/代码/文档中发现的？
 - 哪些已完成的工作受影响？
 - 哪些未完成的工作受影响？

 **回退点与影响面判定规程（不得凭感觉填 `reset-stage --stage`）：**

 偏差「在哪个阶段被发现」往往不是「最早被污染」的阶段；`reset-stage` 是不可逆操作，回退点必须从依赖链反查，逐项标证据等级后才能确定，不允许直接拿发现位置当回退点。

 1. **反查上游来源**：从偏差所在产物出发，沿其 contract 的 `traces_to` 链反查这条错误结论的上游来源——错误是哪个上游 stage 的哪条结论引入的。`traces_to` 断在哪个 stage，最早受污染的就可能落在那个 stage 或它的前序。
 2. **取依赖与文件集证据**：用 `harness mission artifacts --mission <id> --json`（经 harness-cli 调用）列出各 stage 已产出的 artifact 与其依赖；对偏差涉及的符号 / 模块 / 接口跑 graphify-impact（blast-radius，依赖影响能力已建立）取代码侧扩散面。两路证据合并，得到「受影响 stage 集合」与「受影响文件集合」。
 3. **逐项判定 + 标证据等级**：对每个候选 stage / 文件，按下表判「受影响 / 可保留」并标证据等级，**CONFIRMED**＝有 `traces_to` 引用、graphify 调用关系或产物内容直接证据；**INFERRED**＝仅靠架构 / 依赖推断、无直接证据。

 | 对象（stage / 产物 / 文件） | 判定 | 依据 | 证据等级 |
 |---|---|---|---|
 | `<stage 或文件>` | 受影响 / 可保留 | `<traces_to 链 / graphify 调用 / 产物证据>` | CONFIRMED / INFERRED |

 4. **确定回退点**：回退点取「受影响 stage 集合」中**最早的前序阶段**——即被污染结论首次引入的那个 stage。INFERRED 项若无法降为 CONFIRMED 又会扩大回退面，写入 step-2 Decision Gate 交用户裁决，不擅自纳入回退集。据此在 step-3 填 `harness mission reset-stage --stage <最早受影响前序阶段>`，不得用发现位置或凭感觉填。
</step>

<step n="2" goal="发起 Decision Gate">
 - 向用户发出结构化的纠偏请求：

 ```
 🔄 Course Correction 请求

 **发现位置**：<在哪个阶段/文件发现的>
 **偏差描述**：<具体发现了什么问题>

 **影响范围**：
 - 需要修改：<列出受影响的阶段文档>
 - 需要回退：<列出需要丢弃的代码或文档内容>
 - 不受影响：<哪些工作可以保留>

 **推荐方案**：
 A. <方案 A> — 影响：<>，代价：<>
 B. <方案 B> — 影响：<>，代价：<>

 **等待你的决定。**
 ```

 - 等待用户选择方案或提供其他方向
</step>

<step n="3" goal="执行纠偏">
 - 按用户的决定执行：

 1. 更新受影响的阶段文档
 2. 在 `harness-runtime/harness/traces/` 留痕：
 - 文件名：`<YYYY-MM-DD>-course-correction-<mission-id>.md`
 - 内容：原始内容摘要 → 变更内容 → 变更原因 → 用户决定
 3. 清理需要丢弃的代码
 4. 通过 `harness-cli` 更新 `harness-runtime/harness/mission-status.yaml`：记录当前 Mission Slice 的纠偏状态、受影响 `control_plane.stage`、需要重新生成或废弃的 stage artifact；回退点必须取自 step-1 判定表得出的「最早受影响前序阶段」，按该结论调 `harness mission reset-stage --stage <最早受影响前序阶段>`，不得通过扫描固定 stage 队列或凭感觉选择回退点
 5. 通过 Board Router / Work Graph operation 重新生成或恢复受影响的 Mission Slice，从最早受影响的 node / lane action 重新开始

 - 条件：纠偏涉及已审批的 Checkpoint 文档
 - 该 Checkpoint 需要重走审批流程
 - 从checkpoints_passed 中移除该 Checkpoint
</step>

<step n="4" goal="记录教训">
 - 如果纠偏揭示了可复用的教训，更新 project-context.md 的历史教训部分
 - 在最终 retrospective 的"计划与实现的偏差"中记录本次纠偏
</step>

</workflow>
