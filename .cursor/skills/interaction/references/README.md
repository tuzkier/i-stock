# interaction / references

本目录存放 **interaction skill 产出固定交互标准包时引用的框架级 pattern、schema 与 checklist**。

已有：
- [`region-tree-schema.md`](region-tree-schema.md)：组成轴「布局骨架机器段」区域树的字段定义、写法、基线继承与对账规则。
- [`layout-patterns/`](layout-patterns/README.md)：通用页面布局 pattern 库（列表-详情 / 三栏主从 / 仪表盘 / 向导 / 表单 / 画布+inspector / 信息流 / 设置…），每个含 paste-ready 的区域树行 + 主次/扫描默认 + 典型坑。**新建 surface 从这里选基底骨架，不从白纸排控件。**

> 区别于**项目专属**设计语言：`layout-patterns/` 是与项目无关的通用骨架词汇；项目自己的设计 token / 组件原语 / 布局与交互约定属于长期基线 `project-knowledge/product/ui-design-system.md`，不放本目录。

## 装什么

面向 `interaction.md`、三份固定 `interaction-spec` 文档和 `contracts/interaction.contract.yaml` 产出过程的**可复用骨架**，例如：

- **state matrix 五态范式**：loading / empty / error / permission / keyboard+focus 的最小列表与判定问题
- **交互标准包 schema**：`use-case-realization.md`、`surface-model.md`、`interaction-contract.md` 的字段定义与最小示例
- **user flow pattern**：登录、注册、支付、onboarding、多步表单、长列表/分页、权限分支、撤销/重做等通用流程的合同骨架
- **domain → UI 映射 pattern**：领域实体 / 聚合 / 状态机 / 命令到 screen / state / action 的映射范式
- **E2E obligation pattern**：每条用户路径必须落到 locator / `data-testid` 的命名约定与最小覆盖清单
- **a11y / 键盘焦点 / 权限分支 checklist**：与 `craft/` 横切规则的引用关系
- **consistency report 范式**：怎么证明本次原型与既有 surface / baseline 一致

## 不装什么

- **HTML / SVG / CSS / preview 资产**——那是 [visual-interaction-design/references/](../../visual-interaction-design/references/README.md) 与 `harness-runtime/harness/artifacts/<id>/interaction/visual-interaction/` 的工作面。
- **项目自身的具体 capability spec**——走 `project-knowledge/specs/<capability>/spec.md`，本目录只装与项目无关的 pattern。
- **本次 mission 的 delta spec**——走 `harness-runtime/harness/artifacts/<id>/product/specs/<capability>/spec.md`。
- **HTML seed / 设计 token 套件**——Harness 的终态交付不是 HTML artifact（详见下节 "与 Open Design 的区别"）。注意：`layout-patterns/` 装的是**区域树骨架（结构化文本，线框颗粒）**，不是可粘贴的 HTML 模板，不与本条冲突——它定义"页面分哪些区、怎么排"，不定义像素与具体控件样式。

## 与 Open Design (`nexu-io/open-design`) `design-templates/` 的区别

| | OD `design-templates/` | 本目录 |
|---|---|---|
| 终态产物 | 单文件 HTML artifact，给最终用户 | 固定交互标准包，给下游 solution / technical_analysis / execute / E2E 消费 |
| 资产形态 | `template.html` seed + `layouts.md` paste-ready section + `checklist.md` + design-system tokens | 用例实现 / 界面模型 / 交互合同 schema、flow pattern、state matrix、E2E obligation、a11y checklist（纯文本/markdown/yaml） |
| 角色 | LLM 拼装 HTML 的物料库 | interaction-designer agent 起草合同的骨架库 |
| HTML / preview 地位 | 终态交付 | 仅作设计证据，受 manifest / Gate 约束（见 visual-interaction-design） |

OD 那一套不能照搬——它的"四件套"在 Harness 里对应的是 `visual-interaction-design/` 下的设计证据规范，而不是 interaction 合同骨架。

## 三层资产关系

```
框架级 pattern（本目录）
   │   被 interaction skill workflow 引用
   ▼
项目级 spec（project-knowledge/specs/<capability>/）
   │   建立长期能力契约
   ▼
本次 mission delta（harness-runtime/harness/artifacts/<id>/product/specs/<capability>/）
   │   本次任务的差量
   ▼
本次 mission 产物（interaction.md / interaction-spec/use-case-realization.md / interaction-spec/surface-model.md / interaction-spec/interaction-contract.md / contracts/）
```

## 维护提示

- 新增 pattern 命名 kebab-case，每个 pattern 一个 `.md`，开头一句话写"何时引用"。
- pattern 若与 `craft/` 横切规则重叠，本目录只引用、不复制。
- 若同一 pattern 被 solution / test-planning 等其他 skill 也引用，提案抽到与 `craft/` 同层的横切目录，再回到本目录引用。
