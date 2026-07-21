# Surface Index

> 按真实系统结构组织受影响界面。Surface ID 应跨任务稳定，不能用 mission id 或版本号命名。

| Surface ID | Name | Bounded Context / Module | Navigation Node | Operation | Spec Path | Baseline Ref | Trace |
|------------|------|--------------------------|-----------------|-----------|-----------|--------------|-------|
| SURF-001 | {{surface_name}} | {{bounded_context}} | {{nav_node}} | create_surface / modify_surface / extend_surface / retire_surface | `surfaces/{{bounded_context}}/SURF-001.md` | {{baseline_ref_or_none}} | AC-{{id}} |

## Naming Rules

- Prefer domain language from `product-domain-model.md`.
- Do not include mission id, date, version, or temporary implementation names in Surface ID.
- If a surface already exists, reuse the stable Surface ID and mark operation as modify / extend / retire.

