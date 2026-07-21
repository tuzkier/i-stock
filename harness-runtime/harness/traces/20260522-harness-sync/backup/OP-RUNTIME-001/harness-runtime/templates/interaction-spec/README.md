# Interaction Spec: {{mission_id}}

> **来源**：interaction skill → `harness-runtime/harness/stages/{{mission_id}}/interaction-spec/`
> **用途**：本次 mission 对长期 prototype project 的 patch，也是下游 AI 的 canonical 原型实现合同。目录内部按真实系统 surface / bounded context / navigation node 组织，不按任务或版本堆页面。`visual-interaction/prototype/index.html` 给人确认可操作原型，不作为实现合同。

## Authority

| Source | Role |
|--------|------|
| `../interaction.md` | 阶段入口和人类总览 |
| `../contracts/interaction.contract.yaml` | 程序化权威契约 |
| `interaction-spec/**` | AI handoff canonical contract |
| `../visual-interaction/prototype/index.html` | 人类确认的主可操作原型 |

## Reading Order

1. `source-trace.md`
2. `surface-index.md`
3. `surface-baseline.md`
4. `surface-changeset.md`
5. `information-architecture.md`
6. `domain-ui-mapping.md`
7. `surfaces/<bounded-context>/<surface-id>.md`
8. `flows.md`
9. `states.md`
10. `interactions.md`
11. `scenarios.md`
12. `validation-rules.md`
13. `view-models.ts`
14. `consistency-report.md`

## Update Rule

评审反馈必须先更新本目录和 `../interaction.md`，再重建 `../visual-interaction/prototype/index.html`。不得直接手改 prototype 作为最终结果。

## Surface Rule

- 本目录是本次 mission 的变更证据，不是长期按任务堆积的系统原型库。
- 可以把原型视为一个长期 prototype project；本目录只描述本次 mission 对它的 patch。
- 每个受影响界面必须有 stable `Surface ID`。
- 修改既有界面时，先写 baseline ref，再写 changeset。
- 新建界面时，说明为什么不能复用或扩展既有 surface。
- 任务收尾 / retrospective 后，稳定 prototype project 结构应提炼到 `project-knowledge/product/prototype/`，稳定 surface 细节同步到 `project-knowledge/product/ui-surfaces/`。
