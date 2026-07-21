# 阶段文档写作标准

当你产出任何阶段文档时，必须遵守以下标准。

## 结构规范

1. 每份文档开头必须有 TL;DR（一句话总结）
2. 每个一级章节先写 1-3 句结论性判断，再展开细节
3. 正文承载决策和判断，附录承载执行细节
4. 使用表格和列表辅助，但不能用表格替代论述

## 写作纪律

1. 高信息密度：每句话必须承载信息，消除冗余措辞
2. 可验证：所有标准、需求、约束必须可验证，不用"用户友好""高性能"等模糊表述
3. 先结论后展开：读者只读标题和首段就能抓到主线
4. 不重复：同一结论不在多个章节机械重复

## 禁止做法

- 不要把文档写成检查清单或字段填空表
- 不要用代码路径和函数名承载主论证（放附录）
- 不要提前写成下游文档（prd 不是 tech-design）
- 不要用审查语言覆盖文档语言
- 不要在正文中添加大量 emoji 或装饰性标记

## 双受众优化

每份文档都为两类读者服务：

1. **人类读者**：清晰、专业、5 分钟内抓到主线
2. **AI 下游消费者**：结构稳定、关键信息可提取

具体做法：
- 一级标题用于章节划分，便于 AI 按节提取
- 关键约束和验收标准用明确格式标注
- 上下游引用使用相对路径

## 模板使用

产出阶段文档时，读取 `harness-runtime/templates/` 下对应的模板作为结构参考。模板定义了必须包含的章节，但文档的实际内容应该因任务而异，不要机械填空。

## 控制契约规范

阶段文档如果承载下游约束或验证证据，必须在正文前部放置 `## Control Contract`，但该段只引用外部 YAML。正文解释判断和理由；独立 contract YAML 才是 Runtime / Stage Gate 的程序化权威来源。

```md
## Control Contract

- Contract: `contracts/<stage>.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。
```

`contracts/<stage>.contract.yaml` 是相对当前阶段目录的路径；安装后完整位置通常是 `harness-runtime/harness/stages/<mission-id>/contracts/<stage>.contract.yaml`。

写作要求：

1. `type`、`version`、`mission_id`、`stage`、`status`、`upstream`、`consumers` 是 v1 必填字段。
2. `status: ready` 只表示 contract 可被下游消费，不表示阶段整体通过；阶段状态仍由 `harness-cli` 提供的当前 Mission 状态和 Stage Gate 判断。
3. Contract 不复制长正文；只引用 `AC-*`、`FR-*`、`NFR-*`、`REQ-*`、`SCN-*`、`T*`、`EV-*`、`CMD-*` 等稳定 ID。
4. 下游工作流不得自行发明缺失的上游 ID。缺 ID 时回到上游文档补齐。
5. Action Contract 只要求声明 `required_evidence`；不要求拆解阶段已经产生 evidence。
6. 验证证据契约中 `pass` 的 AC / NFR 必须引用具体 evidence；`blocked` 必须提供 `blocked_reason`、`impact`、`next_step`。
7. `status: blocked` 是 Stage Gate 阻断信号，除非有 Decision Gate / accepted risk 记录，不得推进。
8. Markdown 不复制 `control_contract` 内容；若发现内嵌 fenced YAML contract，视为模板漂移，必须迁移到外部 YAML。
9. Contract 口径必须与模板、工作流、Stage Gate checker 保持一致；修改其中一个时同步检查另外两个。
