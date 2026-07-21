# materials/clarifications/ — 已确认澄清沉淀（机器写入区）

> 本目录由 `harness clarification record` 写入：当某阶段出现 `gap_root=clarification`（信息缺失需问用户）的缺口，
> 控制面把同批澄清汇总成澄清 Decision Gate 一次性问人，用户答复后经 `harness clarification record` 沉淀到这里，
> 成为后续阶段**文档集**的合法输入（与原始 `materials/` 资料同等地位）。

## 规则

- **机器写入为主**：优先经 `harness clarification record` 落盘，保持 mission / 提问 / 答复 / 时间的结构化记录。
- **是文档集输入**：各阶段产出者与审查员把这里的已确认澄清当作可引用事实，不再当"脑内假设"。
- **不可被 harness 覆盖**：与 `materials/` 整体一样受保护，只增不删。
- `harness clarification list --mission <id>` 列出某 mission 的全部已确认澄清，供审查员核对。
