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

## 语言规则

阶段文档默认使用中文。英文只作为专用词、机器标识、字段名、命令、路径、状态码、真实专名、行业通用缩写或引用上游原文时的辅助说明；需要解释英文概念时优先写成“中文（English）”。标题、结论、需求、验收、风险、决策和面向用户的说明一律以中文表达为准，除非模板或脚本要求固定英文标识。

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
3. Contract 不复制长正文；只引用稳定 ID。当前稳定 ID 前缀体系如下（**与代码侧 SSOT `harness_cli_core.domain.closure.KNOWN_ID_PREFIXES` 为同一组；新增 ID 体系（如界面 `SURF-`、页面态 `PS-`、系统用例 `SUC-`）时此处与代码必须同步扩展**，由 `tests/test_id_prefix_doc_sync.py` 守卫防漂移——只改一处会让守卫测试失败）：`REQ-`、`SCN-`、`US-`、`UC-`、`SUC-`、`DEC-`、`MOD-`、`IF-`、`DATA-`、`VS-`、`EV-`、`CMD-`、`OBL-`、`PS-`、`SURF-`、`CLAR-`、`T-`。
4. 下游工作流不得自行发明缺失的上游 ID。缺 ID 时回到上游文档补齐。
5. Action Contract 只要求声明 `required_evidence`；不要求拆解阶段已经产生 evidence。
6. 验证证据契约中 `pass` 的验收场景、系统责任或质量与运行约束必须引用具体 evidence；`blocked` 必须提供 `blocked_reason`、`impact`、`next_step`。
7. `status: blocked` 是 Stage Gate 阻断信号，除非有 Decision Gate / accepted risk 记录，不得推进。
8. Markdown 不复制 `control_contract` 内容；若发现内嵌 fenced YAML contract，视为模板漂移，必须迁移到外部 YAML。
9. Contract 口径必须与模板、工作流、Stage Gate checker 保持一致；修改其中一个时同步检查另外两个。**落点**：这三方一致由 `harness-lint`（框架自检）兜底——改完 checker / contract / 模板任一方后，跑 `harness lint` 比对 contract 必填字段 vs 模板章节 vs checker 断言，确认三者覆盖同一组字段后再提交，不靠人眼记忆。（当前 `harness lint` 若尚未覆盖该三方比对，可后续加一条专门的 cross-asset 一致性 checker。）

## 文档集构成与位置约定（完备性基线）

reviewer 做完备性审查时，判断"是否被充分覆盖"所依据的**文档集**由以下三类共同构成，三类都必须纳入，缺一类即审查基线不完整：

1. **阶段产出**：本 mission 各阶段已产出的阶段文档与产物，固定在 `harness-runtime/harness/artifacts/<mission>/<stage>/` 等运行时目录（已有约定）。
2. **人提供资料**：固定在项目根 `materials/` 目录，不带 mission id、长期迭代累积。用户给的文件拷入该目录；临时给的外部目录 / 链接写进 `materials/_sources.md` 清单以留痕。每个 mission 在 mission-contract 的 `source_materials` 字段记录**本次引用了 `materials/` 下哪些文档**（引用清单，非自由文本），完备性审查据此圈定本 mission 实际纳入的人提供资料范围。
   - **已确认澄清属于本类**：人对 Decision Gate / 澄清批次的回答，由 `harness clarification record` 沉淀为 `materials/clarifications/CLAR-<NNN>.md`（机器 SSOT `_index.json` + 人可读 `_index.md`）。它是文档集的一类输入，**不是只活在 `approvals.json`** 的审批记录——approvals 记"决定本身"，澄清的**内容**必须进文档集，下游回退重导才看得见、推理链才不断。
   - **澄清按 `mission_id` 自动纳入**：CLAR 条目的 frontmatter 带 `mission_id`；完备性审查把 `mission_id` 匹配当前 mission 的澄清**自动计入**本 mission 的人提供资料文档集（不依赖 `source_materials` 手工追加）。reviewer 可用 `harness clarification list --mission <id>` 枚举本 mission 的已确认澄清。任一阶段结论的推理链终点落在某条已确认澄清上时，该澄清必须已 record 落盘，否则视为"链断在审批记录里"= 完备性缺口。
3. **项目 spec**：全量 `project-knowledge/specs/` 加本次任务差量 `harness-runtime/harness/stages/<id>/specs/`，共同构成本 mission 生效的行为契约边界。

三类合并即完备性的文档集边界：reviewer 不得只看阶段产出而漏掉人提供资料或项目 spec，也不得把 `source_materials` 未引用的 `materials/` 文档强行计入本 mission 的覆盖范围。
