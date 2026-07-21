---
name: query-api-docs
description: '当任务涉及系统对接、需要查询 YAPI 等接口文档平台、了解 API 规范、接口列表/详情、请求参数、返回值或请求示例时使用。触发词：查接口文档、查 API、看接口、接口对接、yapi、查一下 XX 接口、XX 接口怎么定义的。'
---

# Query API Docs — 接口文档查询

查询 YAPI 等接口文档平台，支持多项目、多 token 配置。

## 何时使用

- 涉及系统对接，需要了解 API 接口规范
- 需要查看接口路径、方法、请求参数、返回值
- 用户说"查一下 XX 接口"、"看看 YAPI 上的接口定义"、"帮我查 XX 项目的接口"

## 何时不使用

- 用户只是问接口设计建议（无需实际查文档）
- 讨论的是当前项目自身的代码接口（非外部系统对接）

## 配置

项目与 token 配置在 `scripts/../config.json`。

当前已配置项目（config.json）：

| 别名 | 项目名 | 平台 |
|------|-------|------|
| `star-gate` | 星门(star-gate) | YAPI @ yapi.800best.com |

> 新增项目：参考 `config.example.json`，向 `providers[].projects` 添加条目。

## 查询工作流

```
用户描述接口需求
      ↓
1. 如不知道接口 ID，先搜索或列出接口
      ↓
2. 拿到接口 ID 后，获取完整接口文档
      ↓
3. 将接口信息整理后呈现给用户
```

## 脚本用法

所有命令在项目根目录执行：

**列出所有已配置项目：**
```bash
bash .harness/common/skills/query-api-docs/scripts/yapi.sh list-projects
```

**查看项目基本信息：**
```bash
bash .harness/common/skills/query-api-docs/scripts/yapi.sh project-info star-gate
```

**列出接口分类树（含每类接口）：**
```bash
bash .harness/common/skills/query-api-docs/scripts/yapi.sh list-categories star-gate
```

**列出所有接口（方法 + 路径 + ID）：**
```bash
bash .harness/common/skills/query-api-docs/scripts/yapi.sh list-apis star-gate
```

**获取接口完整文档（参数 + 返回值 + 描述）：**
```bash
bash .harness/common/skills/query-api-docs/scripts/yapi.sh get-api star-gate <接口ID>
```

**按关键词搜索接口：**
```bash
bash .harness/common/skills/query-api-docs/scripts/yapi.sh search star-gate "登录"
```

## 标准输出格式

对于 `get-api`，将接口信息按以下格式整理给用户：

```
接口名称：xxx
请求方式：GET/POST/...
接口路径：/api/xxx/yyy
状态：已发布 / 开发中

请求参数：
  Query: name(必填) — 说明
  Body:  field(类型, 必填) — 说明

返回示例：
  {JSON 示例}

备注：...
```

## 依赖

- `curl`（macOS 内置）
- `jq`（若未安装：`brew install jq`）
- `python3`（macOS 内置，用于 URL 编码）
