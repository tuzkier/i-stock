---
name: graphify-cli
description: "当用户需要执行 Graphify CLI 操作如索引/重建项目图、检查状态、清理索引、生成 wiki、列出已索引仓库时使用。示例：\"索引这个仓库\"\"重新分析代码库\"\"生成 wiki\""
---

# Graphify CLI 命令

本技能讲的是 `graphify` **CLI 子命令**（status / query / 清理 / hook / PR 等），命令假设当前 working directory 是项目根（含 `.git/` 与源码）；无全局安装时可用 `python -m graphify`。

> **建图（索引）请用 `graphify-build` 技能**（Harness 收编的 graphify 官方构建技能，随 Harness 一起安装）：它让 **agent 自己派发子 agent 提取文档**、宿主会话就是模型，**免 Key**。
> 本技能下面列的 `graphify .` 是**裸 CLI 索引**（独立子进程）：代码 AST 免 Key，但文档 / Markdown 的语义提取要 backend + Key——只适合纯代码增量（`--update`，仅 AST）或已配好 backend 的场景。**不要把裸 `graphify .` 当作免 Key 建文档图的方式**——那是另一种执行模式；免 Key 建文档图走 `graphify-build` 技能。

## 命令

### 索引 / 重建

```bash
graphify .                          # 全量索引当前目录
graphify ./docs --update            # 增量：只重新提取变化文件
graphify . --cluster-only           # 不重抽取，只重跑社区聚类
graphify . --cluster-only --resolution 1.5  # 更细粒度社区
graphify . --no-viz                 # 跳过 HTML 可视化，只产 report + JSON
graphify . --wiki                   # 从图生成 markdown wiki
graphify . --force                  # 强制全量重建（解决 ghost 节点 / 节点变少问题）
```

主要 flag：

| Flag                     | 作用                                                        |
| ------------------------ | ----------------------------------------------------------- |
| `--force`                | 强制全量重建，即使更新后节点变少                            |
| `--update`               | 只重抽取变化文件（AST，无 LLM 调用）                        |
| `--cluster-only`         | 跳过抽取，重跑 Leiden 聚类                                  |
| `--resolution <float>`   | 社区聚类粒度（默认 1.0）                                    |
| `--exclude-hubs <int>`   | 在 god-node 排名里抑制 utility 超级节点                     |
| `--no-viz`               | 不生成 HTML 可视化                                          |
| `--wiki`                 | 同时生成 markdown wiki                                      |
| `--backend <name>`       | 选择 LLM 后端：claude / gemini / openai / deepseek / kimi / bedrock / ollama |
| `--google-workspace`     | 把 `.gdoc / .gsheet / .gslides` 走 `gws` 转换后纳入图       |

### 状态检查

```bash
harness graphify status              # HarnessV2 内置：返回 typed payload，hooks 使用
graphify status                      # graphify 自带：人读输出
```

`harness graphify status` 给出统一格式：

```yaml
status: PASS / WARN
control: graphify.status
available: <bool>           # graphify-out/ 是否存在
indexed: <bool>             # graphify-out/ 非空
fresh: <bool>               # graphify-out/ mtime < 24h
last_index_at: <ISO-8601>
target_repo: <git remote 或目录名>
findings: [...]
```

discovery / dependency-impact / stage-gate 通过这个 payload 决定是否需要在 `degradations[]` 记录 `graphify_unavailable` / `graphify_stale`。

### 清理

```bash
graphify uninstall                   # 从所有 adapter 下线 graphify
graphify uninstall --purge           # 同时删除 graphify-out/
graphify claude uninstall            # 仅从 Claude Code 下线
```

### 查询（在 CLI 触发，免 MCP 也可用）

```bash
graphify query "什么连接了 auth 和 database？"
graphify path "UserService" "DatabasePool"
graphify explain "RateLimiter"
graphify list                        # 列出已索引仓库
graphify add https://arxiv.org/abs/1706.03762   # 把论文加入图
graphify add <youtube-url>            # 把视频转录加入图
```

### 自动重建 hook

```bash
graphify hook install                # git commit / merge 后自动重建（AST only，无 LLM 成本）
```

安装后每次 commit / merge 触发 `graphify --update`；同时设置 git merge driver 让 `graph.json` 在并行提交时自动 union-merge，不留冲突标记。

### 图谱合并（多仓库实验性）

```bash
graphify merge-graphs a.json b.json   # 合并两个 graph.json
```

graphify 按仓库建图、不是中心化服务；跨项目 / 外部系统知识需对各自仓库分别建图后，用 `graphify-exploring` / `graphify-impact-analysis` 查询。

### PR 操作（详见 graphify-pr-review）

```bash
graphify prs                          # 当前仓库 PR 仪表板
graphify prs 42                       # PR #42 深度分析 + 图谱影响
graphify prs --triage                 # AI 排序 review 队列
graphify prs --conflicts              # 命中同一社区的 PR 群组（merge order 风险）
```

## 索引产物入 git

`graphify-out/` 的**图谱本体**（`graph.json` / `GRAPH_REPORT.md` / `graph.html`）建议入 git 团队共享一份基线；**其余是本地 / 派生产物，默认忽略，不入 git**。`.gitignore` 推荐：

```gitignore
graphify-out/manifest.json    # mtime 相关，clone 后会破
graphify-out/cost.json        # 本地 LLM 成本，不要分享
graphify-out/cache/           # 逐文件抽取缓存（本地增量重建用），默认不入 git
```

## 索引控制（`.graphifyignore`）

与 `.gitignore` 同语法，支持 `!` 反向匹配。常用：

```gitignore
node_modules/
dist/
*.generated.py
external/
reference-repos/
```

## 排错

- **"Not inside a git repository"** —— 在含 `.git/` 的目录跑
- **更新后节点变少（疑似重构删除）** —— `graphify . --force`
- **同一实体出现幽灵副本** —— `graphify extract . --force` 全量重抽取
- **Ollama 显存不够** —— 设 `GRAPHIFY_OLLAMA_NUM_CTX` 缩小 KV-cache
- **CLI 找不到** —— 用 `uv tool install graphifyy` / `pipx install graphifyy`（不是 `graphify`，PyPI 名是 `graphifyy` 双 y）

## 与 HarnessV2 的集成

- `harness graphify status` 是 discovery / stage-gate hook 的统一上游
- `graphify status` WARN / 未索引只代表代码索引证据降级，**不**等于 Harness 控制面不可用、Mission 不存在或 CLI 不能用
- brownfield 信号在 HarnessV2 内统一为 "`graphify-out/` 目录存在且非空"
