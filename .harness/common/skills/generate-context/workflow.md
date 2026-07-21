# Generate 上下文工作流

**Goal:** 为项目创建或更新 project-context.md，这是给所有 AI 执行者的项目级常量注入文件。

**Your Role:** 你是一个项目特征提取器。你从代码库结构、已有文档、配置文件中提炼出 AI 在这个项目中容易踩坑的、不显眼但必须遵守的规则。

**关键原则：**
- 只写 AI 需要被提醒的内容，显而易见的事情不写
- 宁缺毋滥：不确定的约束不写入，等后续执行中验证后再补充
- 保持精简：这个文件会被每次执行都读取，不能太长

---

## 初始化

1. 调用 `harness-cli` 执行 `harness config snapshot --json`，确认项目类型（全新项目 / 既有项目）；不得直接读取 `harness-runtime/config/harness.yaml`
2. 检查 `project-context.md` 是否已存在

---

## 执行

<workflow skill="generate-context" version="2">

<step n="1" goal="收集项目信息">
  - 条件：既有项目（既有项目: true）
    - 扫描项目结构，识别：
    - 主语言和框架
    - 目录组织规范
    - 已有的依赖管理配置（package.json / requirements.txt / go.mod 等）
    - 已有的 lint/格式化配置
    - 已有的测试框架和测试目录
    - 已有的 CI/CD 配置
    - 可转成 project-lint profile 的项目边界、受保护路径和本地检查命令

    - 扫描代码，识别：
    - 分层架构模式（如果有）
    - 错误处理模式
    - 日志模式
    - 关键的抽象/接口

    - **界面存在性检测（三态，供下游蒸馏判定）**：按多栈信号扫描项目是否含界面，得出 `ui_presence`，连同命中证据交给下游（harness-setup Step 3 / harness-upgrade OP-DS-001）。
      - 信号集**不限于现代 JS 前端**，任一命中即算"有界面信号"：
        - Web 前端：React/Vue/Svelte/Angular 组件文件 + `package.json` 里的 UI 依赖；
        - 服务端模板：`.cshtml`（ASP.NET MVC/Razor Pages）、`.razor`（Blazor）、`.jsp`、Thymeleaf、Jinja、ERB、PHP 视图、Go template；
        - 桌面 / 原生 UI 标记：XAML（WPF / WinForms / MAUI / Avalonia）、Qt `.ui`、Android layout XML、SwiftUI / Storyboard；
        - 样式层：任意 CSS / SCSS / LESS、`wwwroot/css`、Tailwind / styled-components；
        - 既有 `prototype/`。
      - `confirmed_ui`：命中任一信号；`no_signal`：零信号命中。**`no_signal` 不等于"非 UI 项目"——下游必须按"默认有 UI"向用户确认，绝不静默判成非 UI 而跳过蒸馏。**
      - **必须输出机械结果 + 命中证据清单**（哪些信号命中、命中文件 / 路径），作为给下游的显式交接，不只给一个结论词。下游（harness-setup Step 3 / harness-upgrade OP-DS-001）**只认这个机械结果，不得用"这看着是后端项目 / 主要是 .NET / 主要是 API"之类主观二分覆盖**。
      - **`confirmed_ui` 即 UI 项目，下游必须蒸馏、无跳过路径**：哪怕前端是 jQuery + 服务端模板、哪怕零设计 token，也是有界面。「无设计系统 / 无 token」≠「非 UI」≠「可跳过」——缺 token 标「待补」，不是跳过理由。
    - 当 `ui_presence=confirmed_ui` 时，额外采集 **UI 设计语言信号**供 harness-setup 的「蒸馏 UI 设计系统初版」子步使用：CSS 变量 / 设计 token（间距 / 字阶 / 色彩角色）、theme 文件、组件库 / 组件原语、`materials/design/` 下团队提供的设计系统资料。这些信号不进 `project-context.md`，由 harness-setup 蒸馏进 `project-knowledge/product/design-system/`。
      - **既有组件库 / 设计系统底座识别（供 setup/upgrade 精准吸纳）**：从依赖清单（`package.json` / `*.csproj` / `pom.xml`）+ import 频度 + 源码目录，判定项目是否已搭在一套成熟组件库 / 设计系统上，并区分两类载体（下游按此分流）：①**npm 包库**（element-plus/element-ui、antd、@mui、chakra…，组件住 `node_modules`、项目只 import + 主题定制）；②**仓库内 vendored 组件**（shadcn 风格、组件源码住项目 `components/ui/` 等、由项目持有）。同时采集项目对其的**主题 / 变量定制**（SCSS 变量 override 如 `$--color-primary`、`theme.token` / ConfigProvider、`element-variables.scss`、全局 CSS 变量）与**二次封装 / 业务组件目录**。这些信号交下游（harness-setup Step 3 / harness-upgrade OP-DS-001），不进 `project-context.md`。

    - 如果有已有的 README 或文档，读取其中的规范描述

  - 条件：全新项目（既有项目: false）
    - 读取已有的阶段文档（prd、solution、tech-design）
    - 从中提取：
    - 选定的技术栈和框架
    - 架构决策和约束
    - 编码规范约定
    - 测试策略
</step>

<step n="2" goal="检测运行时环境">
  - 检测并记录以下运行时信息：

  | 检测项 | 命令 |
  |--------|------|
  | OS 和架构 | `uname -a` |
  | 主语言版本 | `node -v` / `python3 --version` / `go version` 等（根据项目） |
  | 包管理器 | `npm -v` / `pip --version` / `pnpm -v` 等 |
  | Git 状态 | `git --version`、`git remote -v`、当前分支 |
  | Docker（如有） | `docker --version` |

  - 如果检测失败（命令不存在），记录为"未安装"而不是报错
  - 将检测结果作为 project-context的"环境状态"部分的输入
</step>

<step n="3" goal="提炼约束">
  - 从收集到的信息中提炼以下类别的约束：

  **架构约束**：哪些模式是强制的，哪些是禁止的
  **编码规范**：命名、错误处理、日志格式（只写项目特有的、AI 容易忽视的）
  **技术选择**：每个场景该用什么、禁止用什么、为什么
  **测试要求**：最低覆盖率、测试文件放在哪、运行命令
  **运行时环境**：语言版本、包管理器、依赖安装命令、本地启动命令
  **Git 约定**：分支命名、提交格式、PR 流程（由 git-workflow 技能发现的约定也写入此处）
  **项目 lint profile**：受保护路径、代码变更匹配规则、必须命令证据、可接入的 dependency-cruiser / semgrep / import-linter / ESLint custom rule 命令

  - 对每条约束问自己：
  - 如果不写这条，AI 会不会自己做对？→ 会，则不写
  - 这条是项目特有的还是通用的？→ 通用的不写
  - 这条是有争议的还是确定的？→ 有争议的先不写
</step>

<step n="4" goal="写入 project-context.md">
  - 使用 `harness-runtime/templates/project-context.md` 模板结构
  - 填充所有相关章节
  - 写入项目根目录的 `project-context.md`
</step>

<step n="5" goal="生成或更新 project-lint profile">
  - 读取 `project-knowledge/engineering/policies/project-lint.yaml`；若不存在，从模板创建
  - 根据 Step 1/2 的发现保守补齐：
  - `commands.required_for_code_change`：项目至少应有 test；有 lint/typecheck 时加入
  - `code_change.patterns` / `ignore_patterns`：按项目源码、测试、文档目录设置
  - `changed_files.protected_paths`：保留 `.harness/common/**` 等框架资产保护
  - `external_commands.items`：仅加入已存在且无破坏性的本地命令，例如 dependency-cruiser、semgrep、import-linter、ESLint custom rules
  - 不确定的架构边界只写入 `project-context.md` 作为候选，不写成 blocking lint 规则
</step>

<step n="6" goal="与用户确认">
  - 向用户展示 project-context.md 的摘要
  - 询问：
  - 有没有遗漏的重要约束？
  - 有没有写错的地方？
  - 有没有需要补充的已知坑？

  - 根据用户反馈更新
</step>

</workflow>
