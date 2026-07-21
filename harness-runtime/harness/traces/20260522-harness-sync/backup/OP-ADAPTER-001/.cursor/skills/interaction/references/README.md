# interaction / references

本目录存放 **interaction skill 产出"结构化原型合同"时引用的框架级 pattern、schema 与 checklist**。当前为空——按需补，不必铺满。

## 装什么

面向 `interaction.md` / `interaction-spec/` / `contracts/interaction.contract.yaml` 产出过程的**可复用骨架**，例如：

- **state matrix 五态范式**：loading / empty / error / permission / keyboard+focus 的最小列表与判定问题
- **prototype interface map / interaction-spec schema**：surface → screen → state → action → view-model 的字段定义与最小示例
- **user flow pattern**：登录、注册、支付、onboarding、多步表单、长列表/分页、权限分支、撤销/重做等通用流程的合同骨架
- **domain → UI 映射 pattern**：领域实体 / 聚合 / 状态机 / 命令到 screen / state / action 的映射范式
- **E2E obligation pattern**：每条用户路径必须落到 locator / `data-testid` 的命名约定与最小覆盖清单
- **a11y / 键盘焦点 / 权限分支 checklist**：与 `craft/` 横切规则的引用关系
- **consistency report 范式**：怎么证明本次原型与既有 surface / baseline 一致

## 不装什么

- **HTML / SVG / CSS / preview 资产**——那是 [visual-interaction-design/references/](../../visual-interaction-design/references/README.md) 与 `harness-runtime/harness/stages/<id>/visual-interaction/` 的工作面。
- **项目自身的具体 capability spec**——走 `project-knowledge/specs/<capability>/spec.md`，本目录只装与项目无关的 pattern。
- **本次 mission 的 delta spec**——走 `harness-runtime/harness/stages/<id>/specs/<capability>/spec.md`。
- **HTML seed / layout 物料库 / 设计 token 套件**——Harness 的终态交付不是 HTML artifact（详见下节 "与 Open Design 的区别"）。

## 与 Open Design (`nexu-io/open-design`) `design-templates/` 的区别

| | OD `design-templates/` | 本目录 |
|---|---|---|
| 终态产物 | 单文件 HTML artifact，给最终用户 | 结构化原型合同，给下游 solution / technical_analysis / execute / E2E 消费 |
| 资产形态 | `template.html` seed + `layouts.md` paste-ready section + `checklist.md` + design-system tokens | 合同 schema / flow pattern / state matrix / E2E obligation / a11y checklist（纯文本/markdown/yaml） |
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
本次 mission delta（harness-runtime/harness/stages/<id>/specs/<capability>/）
   │   本次任务的差量
   ▼
本次 mission 产物（interaction.md / interaction-spec/ / contracts/）
```

## 维护提示

- 新增 pattern 命名 kebab-case，每个 pattern 一个 `.md`，开头一句话写"何时引用"。
- pattern 若与 `craft/` 横切规则重叠，本目录只引用、不复制。
- 若同一 pattern 被 solution / test-planning 等其他 skill 也引用，提案抽到与 `craft/` 同层的横切目录，再回到本目录引用。
