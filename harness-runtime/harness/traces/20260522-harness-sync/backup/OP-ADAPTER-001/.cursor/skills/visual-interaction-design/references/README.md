# visual-interaction-design / references

本目录存放 **visual-interaction-design skill 产出"可视化设计证据"时引用的框架级规范与模板**。当前为空——按需补，不必铺满。

## 装什么

面向 `visual-interaction/prototype/`、`visual-interaction/variants/`、`visual-interaction/evidence/`、`visual-interaction-manifest.json`、`design-brief.md` 这一组资产的产出过程，例如：

- **variant 命名 / 目录布局规范**：variant id、surface、viewport、device frame、对应 interaction-spec surface 的引用约定
- **prototype 信息架构范式**：`visual-interaction/prototype/index.html` 主可操作原型的目录布局、边界和最小覆盖
- **manifest 语义说明**：解释 `harness evidence visual manifest` 命令生成的字段含义（实际 schema 由 CLI 强制，本目录只做语义注释与最小示例）
- **design-brief 模板**：怎么从 product-definition / interaction-spec 提取交互专家所需的上下文（领域对象、状态、权限、动作、E2E obligation、关键约束）
- **可访问性可视证据规范**：对比度、focus ring、视口覆盖（mobile / tablet / desktop）、暗色模式 / RTL 的截图义务
- **既有风格引用约定**：怎么引用项目现有 CSS / design token，而不是另起一套——区别于 OD 把 design-system 注入 `:root`

## 不装什么

- **HTML seed / paste-ready layout / 通用设计 token 库**——Harness 的可视化资产是**设计证据**，不是终态交付，不需要框架自带 HTML 物料库（详见下节 "与 Open Design 的区别"）。
- **结构化原型合同骨架（state matrix / flow pattern / interaction-spec schema）**——那是 [interaction/references/](../../interaction/references/README.md) 的工作面。
- **项目自身的具体视觉资产 / 实际 variants / preview HTML**——产出于 `harness-runtime/harness/stages/<id>/visual-interaction/`，不进入框架资产库。
- **品牌 / 视觉 token 套件**——项目的视觉 token 走项目仓库自己的源码或 `project-knowledge/`，不在框架层维护"129 套 design-system"这种物料库。

## 与 Open Design (`nexu-io/open-design`) `design-templates/` + `design-systems/` 的区别

| | OD | 本目录 |
|---|---|---|
| HTML / preview 地位 | 终态交付，给最终用户看 | `visual-interaction/prototype/index.html` 是唯一默认人类确认入口；内部证据受 manifest / Gate 约束，AI handoff 仍以 interaction-spec 为准 |
| 物料库形态 | 框架自带 80+ HTML 模板 + 129 套 design-system token | 不维护通用 HTML 模板和 token 库；引用项目自有风格 |
| 资产形态 | `template.html` seed + `layouts.md` + `checklist.md` + design-system tokens | manifest 字段语义 / 命名约定 / 主可操作原型信息架构 / a11y 视觉证据规范（纯文本/markdown） |
| 验证手段 | 五维 critique 自检后直接 emit `<artifact>` | reviewer 循环（interaction-reviewer）+ Artifact Gate + E2E obligation |

OD 把 HTML 当成熟产品；Harness 把 HTML 当成"用来证明合同被正确承载"的证据，所以本目录立的是**证据规范**，不是物料库。

## 三层资产关系

```
框架级规范（本目录）
   │   被 visual-interaction-design workflow 引用
   ▼
项目级视觉约定（项目自有 CSS / token / project-knowledge/）
   │   各项目自己维护
   ▼
本次 mission 设计证据（harness-runtime/harness/stages/<id>/visual-interaction/）
   │   variants / preview / manifest / design-brief
   ▼
被 interaction-reviewer + Artifact Gate 审查
```

## 与 interaction/references/ 的边界

- **interaction/references/**：合同骨架（"原型该怎么写"）
- **本目录**：证据规范（"原型变体与 preview 怎么落地、命名、组织、归档"）
- 同一 pattern 若两边都需要，统一沉到 interaction/references/，本目录只引用。

## 维护提示

- 新增规范命名 kebab-case，每个规范一个 `.md`，开头一句话写"何时引用"。
- 涉及 CLI 字段语义的，注明对应 `harness evidence visual` 子命令版本，CLI 变更时同步更新。
- 不要把项目特有的视觉风格沉到这里——那是项目自己的事。
