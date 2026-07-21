#!/usr/bin/env bash
# yapi.sh — YAPI 接口文档查询工具
#
# 用法: yapi.sh <action> [project-alias] [args...]
# 详细用法: yapi.sh help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$SKILL_DIR/config.json"

# ─── 依赖检查 ───────────────────────────────────────────────────────────────

for cmd in curl jq; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: '$cmd' is required." >&2
    echo "  Install: brew install $cmd" >&2
    exit 1
  fi
done

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Error: config.json not found at: $CONFIG_FILE" >&2
  echo "  Copy config.example.json to config.json and fill in your values." >&2
  exit 1
fi

# ─── 辅助函数 ───────────────────────────────────────────────────────────────

# URL 编码（用于关键词搜索），优先用 python3，降级到 sed 简单处理
url_encode() {
  local str="$1"
  if command -v python3 &>/dev/null; then
    python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" "$str"
  else
    # 简单处理：仅编码空格，其余字符直接传递（对于纯中文关键词 curl 会自动处理）
    echo "${str// /%20}"
  fi
}

# 发送 GET 请求到 YAPI，返回 .data 字段；遇到 errcode != 0 报错退出
yapi_get() {
  local base_url="$1"
  local endpoint="$2"
  local query_string="$3"

  local url="${base_url}${endpoint}?${query_string}"
  local response
  response=$(curl -s --max-time 30 "$url")

  local errcode
  errcode=$(echo "$response" | jq -r '.errcode // 0')

  if [ "$errcode" != "0" ]; then
    local errmsg
    errmsg=$(echo "$response" | jq -r '.errmsg // "Unknown error"')
    echo "YAPI Error (code $errcode): $errmsg" >&2
    echo "  URL: $url" >&2
    exit 1
  fi

  echo "$response" | jq '.data'
}

# 根据 alias 从 config.json 中查找项目配置，返回 JSON 对象
get_project_config() {
  local alias="$1"

  local config
  config=$(jq -c --arg alias "$alias" '
    .providers[] as $provider |
    $provider.projects[] |
    select(.alias == $alias) |
    {
      base_url: $provider.base_url,
      provider_name: $provider.name,
      provider_type: $provider.type,
      token: .token,
      name: .name,
      alias: .alias
    }
  ' "$CONFIG_FILE" | head -1)  # 取第一个匹配

  if [ -z "$config" ]; then
    echo "Error: Project alias '$alias' not found in config.json" >&2
    echo "" >&2
    echo "Available projects:" >&2
    jq -r '.providers[] as $p | .providers[].projects[] | "  \(.alias)  (\(.name))  — \($p.base_url)"' "$CONFIG_FILE" 2>/dev/null || \
      jq -r '.providers[].projects[] | "  \(.alias)  (\(.name))"' "$CONFIG_FILE"
    exit 1
  fi

  echo "$config"
}

# 通过 token 获取项目 ID（_id）
get_project_id() {
  local base_url="$1"
  local token="$2"
  yapi_get "$base_url" "/api/project/get" "token=$token" | jq -r '._id'
}

# ─── 各 Action 实现 ──────────────────────────────────────────────────────────

action_list_projects() {
  echo "=== 已配置项目 ==="
  jq -r '
    .providers[] as $provider |
    "▸ Provider: \($provider.name) [\($provider.type)]",
    "  Base URL: \($provider.base_url)",
    ($provider.projects[] | "  · \(.name)  alias: \(.alias)"),
    ""
  ' "$CONFIG_FILE"
}

action_project_info() {
  local alias="$1"
  local cfg
  cfg=$(get_project_config "$alias")

  local base_url token
  base_url=$(echo "$cfg" | jq -r '.base_url')
  token=$(echo "$cfg" | jq -r '.token')

  echo "=== 项目信息: $alias ==="
  yapi_get "$base_url" "/api/project/get" "token=$token" | jq '{
    id: ._id,
    name: .name,
    desc: (.desc // "(无描述)"),
    basepath: (.basepath // "/"),
    group_name: (.group_name // ""),
    env: [.env[]? | {name: .name, domain: .domain}]
  }'
}

action_list_categories() {
  local alias="$1"
  local cfg
  cfg=$(get_project_config "$alias")

  local base_url token
  base_url=$(echo "$cfg" | jq -r '.base_url')
  token=$(echo "$cfg" | jq -r '.token')

  local project_id
  project_id=$(get_project_id "$base_url" "$token")

  echo "=== 接口分类树: $alias (project_id=$project_id) ==="
  yapi_get "$base_url" "/api/interface/list_menu" \
    "project_id=${project_id}&token=${token}" | \
    jq -r '.[] |
      "【\(.name)】 (cat_id: \(._id))",
      (
        if (.list | length) > 0 then
          .list[] | "  [\(.method | ascii_upcase)] \(.path)  — \(.title)  (id: \(._id))"
        else
          "  (此分类暂无接口)"
        end
      ),
      ""
    '
}

action_list_apis() {
  local alias="$1"
  local cfg
  cfg=$(get_project_config "$alias")

  local base_url token
  base_url=$(echo "$cfg" | jq -r '.base_url')
  token=$(echo "$cfg" | jq -r '.token')

  local project_id
  project_id=$(get_project_id "$base_url" "$token")

  echo "=== 接口列表: $alias (project_id=$project_id) ==="

  local data
  data=$(yapi_get "$base_url" "/api/interface/list" \
    "project_id=${project_id}&token=${token}&page=1&limit=200")

  local total
  total=$(echo "$data" | jq -r '.count // (.list | length)')
  echo "共 $total 个接口（最多显示 200 条）"
  echo ""

  echo "$data" | jq -r '
    .list[] |
    "[\(.method | ascii_upcase)] \(.path)",
    "  标题: \(.title)",
    "  ID:   \(._id)  状态: \(.status // "undone")",
    ""
  '
}

action_get_api() {
  local alias="$1"
  local api_id="$2"
  local cfg
  cfg=$(get_project_config "$alias")

  local base_url token
  base_url=$(echo "$cfg" | jq -r '.base_url')
  token=$(echo "$cfg" | jq -r '.token')

  echo "=== 接口详情: ID=$api_id ==="
  local data
  data=$(yapi_get "$base_url" "/api/interface/get" "id=${api_id}&token=${token}")

  # 基本信息
  echo "$data" | jq -r '"
接口名称: \(.title)
请求方式: \(.method | ascii_upcase)
接口路径: \(.path)
状    态: \(.status // "undone")
创 建 者: \(.username // "")
更新时间: \(.up_time | todate? // (.up_time | tostring))
"'

  # 请求 Query 参数
  local req_query
  req_query=$(echo "$data" | jq -r '.req_query // []')
  if [ "$(echo "$req_query" | jq 'length')" -gt "0" ]; then
    echo "── Query 参数 ──"
    echo "$req_query" | jq -r '.[] | "  \(if .required == "1" then "* " else "  " end)\(.name)  [\(.type // "string")]  \(.desc // "")  \(if .example != "" and .example != null then "(示例: \(.example))" else "" end)"'
    echo ""
  fi

  # 请求 Headers
  local req_headers
  req_headers=$(echo "$data" | jq -r '[.req_headers[]? | select(.name != "Content-Type")]')
  if [ "$(echo "$req_headers" | jq 'length')" -gt "0" ]; then
    echo "── 请求 Headers ──"
    echo "$req_headers" | jq -r '.[] | "  \(.name): \(.value // "")  \(.desc // "")"'
    echo ""
  fi

  # 请求 Body（form 类型）
  local req_body_form
  req_body_form=$(echo "$data" | jq -r '.req_body_form // []')
  if [ "$(echo "$req_body_form" | jq 'length')" -gt "0" ]; then
    echo "── Body 参数 (form) ──"
    echo "$req_body_form" | jq -r '.[] | "  \(if .required == "1" then "* " else "  " end)\(.name)  [\(.type // "text")]  \(.desc // "")"'
    echo ""
  fi

  # 请求 Body（JSON 类型）
  local req_body_type req_body_other
  req_body_type=$(echo "$data" | jq -r '.req_body_type // "none"')
  req_body_other=$(echo "$data" | jq -r '.req_body_other // ""')
  if [ "$req_body_type" = "json" ] && [ -n "$req_body_other" ]; then
    echo "── Body (JSON Schema) ──"
    echo "$req_body_other" | jq . 2>/dev/null || echo "$req_body_other"
    echo ""
  fi

  # 返回体
  local res_body_type res_body
  res_body_type=$(echo "$data" | jq -r '.res_body_type // "json"')
  res_body=$(echo "$data" | jq -r '.res_body // ""')
  if [ -n "$res_body" ]; then
    echo "── 返回体 ($res_body_type) ──"
    echo "$res_body" | jq . 2>/dev/null || echo "$res_body"
    echo ""
  fi

  # Markdown 备注
  local markdown
  markdown=$(echo "$data" | jq -r '.markdown // ""')
  if [ -n "$markdown" ]; then
    echo "── 备注 ──"
    echo "$markdown"
    echo ""
  fi
}

action_search() {
  local alias="$1"
  local keyword="$2"
  local cfg
  cfg=$(get_project_config "$alias")

  local base_url token
  base_url=$(echo "$cfg" | jq -r '.base_url')
  token=$(echo "$cfg" | jq -r '.token')

  local project_id
  project_id=$(get_project_id "$base_url" "$token")

  local encoded_keyword
  encoded_keyword=$(url_encode "$keyword")

  echo "=== 搜索结果: \"$keyword\" in $alias ==="
  local data
  data=$(yapi_get "$base_url" "/api/interface/search" \
    "q=${encoded_keyword}&project_id=${project_id}&token=${token}")

  local count
  count=$(echo "$data" | jq -r '.count // (.list | length) // 0')
  echo "共找到 $count 个接口"
  echo ""

  echo "$data" | jq -r '
    .list[]? |
    "[\(.method | ascii_upcase)] \(.path)",
    "  标题: \(.title)",
    "  ID:   \(._id)",
    ""
  '
}

# ─── 帮助信息 ────────────────────────────────────────────────────────────────

show_help() {
  cat <<'EOF'
yapi.sh — YAPI 接口文档查询工具

用法:
  yapi.sh <action> [project-alias] [args...]

Actions:
  list-projects                    列出 config.json 中所有已配置项目
  project-info   <alias>           查看项目基本信息（名称、basepath、环境）
  list-categories <alias>          列出接口分类树（含每类接口列表）
  list-apis      <alias>           列出项目所有接口（方法 + 路径 + ID）
  get-api        <alias> <api-id>  获取接口完整文档（参数 + 返回值 + 备注）
  search         <alias> <keyword> 按关键词搜索接口

示例:
  yapi.sh list-projects
  yapi.sh project-info   star-gate
  yapi.sh list-categories star-gate
  yapi.sh list-apis      star-gate
  yapi.sh get-api        star-gate 1234
  yapi.sh search         star-gate "用户登录"

配置:
  config.json 位于脚本上层目录。参考 config.example.json 添加新项目。
EOF
}

# ─── 主入口 ──────────────────────────────────────────────────────────────────

ACTION="${1:-help}"

case "$ACTION" in
  list-projects)
    action_list_projects
    ;;
  project-info)
    [[ "${2:-}" ]] || { echo "Usage: yapi.sh project-info <alias>" >&2; exit 1; }
    action_project_info "$2"
    ;;
  list-categories)
    [[ "${2:-}" ]] || { echo "Usage: yapi.sh list-categories <alias>" >&2; exit 1; }
    action_list_categories "$2"
    ;;
  list-apis)
    [[ "${2:-}" ]] || { echo "Usage: yapi.sh list-apis <alias>" >&2; exit 1; }
    action_list_apis "$2"
    ;;
  get-api)
    [[ "${2:-}" && "${3:-}" ]] || { echo "Usage: yapi.sh get-api <alias> <api-id>" >&2; exit 1; }
    action_get_api "$2" "$3"
    ;;
  search)
    [[ "${2:-}" && "${3:-}" ]] || { echo "Usage: yapi.sh search <alias> <keyword>" >&2; exit 1; }
    action_search "$2" "$3"
    ;;
  help|--help|-h)
    show_help
    ;;
  *)
    echo "Error: Unknown action '$ACTION'" >&2
    echo ""
    show_help >&2
    exit 1
    ;;
esac
