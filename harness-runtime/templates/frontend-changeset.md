# 前端变更清单（frontend-changeset）：{{mission_id}}

> **来源**：`prototype-as-frontend` 技能 → `harness-runtime/harness/artifacts/{{mission_id}}/interaction/frontend-changeset.md`
> **用途**：`prototype.delivery_mode=frontend_engineering` 路线下，本次任务对长期前端工程 `{{frontend_project_root}}` 的界面边界增量变更清单。它是 `frontend-reviewer` 审查与 `harness prototype-as-frontend changeset-check` 对账的权威产物，对齐 `contracts/prototype-as-frontend.contract.yaml`。
> **不适用**：`interactive_prototype` 路线（见 `surface-model.md` + `interaction.contract.yaml`）。

## 主要用户任务（primary_user_tasks）

> 本次变更服务哪些用户任务；每个任务一句话，对应一个或多个验收场景 / 条件。不得从路由 / 组件清单倒推。

- {{primary_user_task}}

## 信息架构（information_architecture）

> 路由 / 页面 / 区块 / 面板 / 弹窗 / 列表 / 详情的层级如何服务用户任务和决策顺序；禁止按领域实体机械拆页面。

| 维度 | 内容 |
|------|------|
| navigation_model | {{navigation_model}} |
| route_hierarchy | {{route_hierarchy}} |
| page_sections | {{page_sections}} |
| decision_order | {{decision_order}} |

## 领域可见性决策（domain_visibility_decisions）

> 每个关键领域概念分类为主对象 / 支撑上下文 / 状态指示 / 动作入口 / 隐藏内部概念，并说明展示 / 折叠 / 合并 / 隐藏原因。

| 领域引用（domain_ref） | 可见性分类 | 承载界面边界 | 理由 |
|------------------------|-----------|--------------|------|
| Entity:{{entity}} | primary_object / supporting_context / state_indicator / action_affordance / hidden_internal | SURF-001 | {{visibility_reason}} |

## 界面边界改动清单（surfaces，机器段）

> **本表是 CLI 读取本次界面边界变更的唯一权威机器段**，列顺序固定，被 `harness prototype-as-frontend changeset-check` 解析（`parse_frontend_changeset_surfaces`，锚点 = 首列匹配 `^SURF-\d+`）：
> - 表头 / 分隔行 / `{{...}}` 占位 / 散文行一律跳过；
> - **门 A（上游覆盖）**：PRD 流步骤全集（`use-case-model.md` 的 `SUC-xx-FLOW-xx`）必须 ⊆ 所有 surface 行 `traces_to` 的并集（写 `SUC-xx-FLOW-xx.<state>` beat token 也算覆盖其流步骤前缀）；漏一个流步骤报 `FRONTEND_FLOWSTEP_NOT_IN_CHANGESET`(FAIL)。若该流步骤非界面承载，在下方「界面承载豁免（N/A）」段声明；
> - changeset 存在但本表解析不出任何 SURF 行 → `FRONTEND_CHANGESET_SURFACES_UNPARSEABLE`(FAIL，防止散文糊弄)。
>
> 列定义（顺序不可变）：
> - **surface_id**：`SURF-xxx`，引上游真源（界面边界注册表），不在本阶段新造编号。
> - **kind**：`route | page | component | type`。
> - **operation**：`create_surface | modify_surface | extend_surface | retire_surface`。
> - **file_path**：`{{frontend_project_root}}/...` 真实工程路径。
> - **baseline_ref**：`create_surface` 时填 `null` / `-`；其它操作必填基线路径。
> - **traces_to**：以 `,` / `、` / 空白分隔的 token；token 形态 `SCN-\d+` / `SUC-\d+-FLOW-\d+` / `SUC-\d+-FLOW-\d+\.[A-Za-z0-9_-]+`。
> - **domain_refs**：以 `,` / `、` / 空白分隔的 `Entity:X` / `State:Y` / `Action:Z`。

| surface_id | kind | operation | file_path | baseline_ref | traces_to | domain_refs |
|------------|------|-----------|-----------|--------------|-----------|-------------|
| SURF-001 | route | create_surface | {{frontend_project_root}}/app/<route>/page.tsx | null | SCN-01 SUC-01-FLOW-01 | Entity:Workspace, State:active, Action:create_workspace |

## 界面承载豁免（N/A）

> **本段取代旧的关键词 grep**，列顺序固定，被 changeset-check 解析（锚点 = 本标题下的固定列表）：
> - 凡某个 PRD 节点（SUC / 流步骤 / 节拍）不需要任何界面承载（纯后台 / 纯外部集成 / 纯定时任务），在此声明一行把它从门 A 覆盖分母里豁免；
> - 粒度 `flowstep` 直接豁免该流步骤；粒度 `suc` 豁免该 SUC 下全部 PRD 流步骤（前缀匹配）；粒度 `beat` 豁免该节拍。
> - 声明豁免但该流步骤其实已被某 surface 的 `traces_to` 承载 → `FRONTEND_NA_EXEMPTION_STALE`(WARN，豁免与实现冗余共存)。
>
> 列定义（顺序不可变；列名 / 粒度枚举与 `surface-model.md` 的「N/A 豁免（机器段）」严格一致）：
> - **prd_node_id**：匹配 `SUC-(?:TF-[A-Z]+-)?\d+(-FLOW-\d+)?(\.[A-Za-z0-9_-]+)?`。
> - **豁免粒度**：`suc | flowstep | beat`。
> - **理由**：非空非占位。
> - **责任归属**：非空非占位。

| prd_node_id | 豁免粒度 | 理由 | 责任归属 |
|-------------|----------|------|----------|
| {{na_prd_node_id}} | suc / flowstep / beat | {{na_reason}} | {{na_owner}} |

<!-- 示例（实际豁免时复制并填真值，删除占位行）：
| SUC-07-FLOW-02 | flowstep | 纯后台对账步骤，无任何用户可观察界面承载 | product-owner |
-->

## 端到端义务（e2e_obligation，机器段，门 B 下游键）

> 以 **PRD 流步骤为键**的端到端义务清单，透传到 verify 阶段：每条 PRD 流步骤必须有一条 E2E 义务（`status: required`）或显式接受替代（`status: accepted_alternative` + 非空 `accepted_reason`），否则 verify 阶段 `e2e_resolver` 报 `frontend_flowstep_e2e_uncovered`（FAIL）。本阶段只列点，不写 / 不跑 e2e spec。
> 字段：`flow_step`（键，必填 `SUC-xx-FLOW-xx`）、`surface_id`、`traces_to`（验收场景锚点）、`status`（`required | accepted_alternative`）、`accepted_reason`（status=accepted_alternative 时必填非空）、`locator`、`assertable_states`。

```yaml
e2e_obligation:
  - flow_step: SUC-01-FLOW-01        # 必填，作为键
    surface_id: SURF-001
    traces_to: [SCN-01]              # 验收场景锚点
    status: required                 # required | accepted_alternative
    accepted_reason: ""              # status=accepted_alternative 时必填非空
    locator: '[data-testid="submit-workspace"]'
    assertable_states: ['出现"创建成功"', 'URL 跳转 /workspaces/:id']
```

## 产品定义回流检查

> 实施过程中若需要改产品定义 / 领域模型 / 验收场景 / 范围，停止推进，把差异写在此处并发起决策门或路由回产品定义阶段。

| 发现 | 影响的产品定义内容 | 建议处理 | 是否阻断 |
|------|--------------------|----------|----------|
| {{prd_feedback_finding}} | {{affected_prd}} | 回流产品定义 / 决策门 / 不采纳：{{reason}} | 是 / 否 |

## 沉淀候选（knowledge_promotion_candidates）

| 候选 | 类型 | 来源路径 | 理由 |
|------|------|----------|------|
| {{kpc}} | frontend_pattern / shared_type / locator_convention | {{source_ref}} | {{promotion_reason}} |
