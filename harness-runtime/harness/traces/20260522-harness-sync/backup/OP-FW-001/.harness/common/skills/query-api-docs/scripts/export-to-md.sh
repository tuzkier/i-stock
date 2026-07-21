#!/usr/bin/env bash
# export-to-md.sh — 将 YAPI 项目接口导出为 Markdown（同一分类的接口合并到同一个 md 文件）
#
# 用法: export-to-md.sh <project-alias> [output-dir]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$SKILL_DIR/config.json"

ALIAS="${1:?Usage: export-to-md.sh <project-alias> [output-dir]}"
OUTPUT_DIR="${2:-$(cd "$SCRIPT_DIR/../../../../.." && pwd)/star-gate-api}"

for cmd in curl jq python3; do
  command -v "$cmd" &>/dev/null || { echo "Error: '$cmd' required." >&2; exit 1; }
done

[ -f "$CONFIG_FILE" ] || { echo "Error: config.json not found." >&2; exit 1; }

cfg=$(jq -c --arg alias "$ALIAS" '
  .providers[] as $provider |
  $provider.projects[] |
  select(.alias == $alias) |
  { base_url: $provider.base_url, token: .token }
' "$CONFIG_FILE" | head -1)

[ -n "$cfg" ] || { echo "Error: Project '$ALIAS' not found." >&2; exit 1; }

base_url=$(echo "$cfg" | jq -r '.base_url')
token=$(echo "$cfg" | jq -r '.token')

yapi_get() {
  local endpoint="$1" query="$2"
  local resp
  resp=$(curl -s --max-time 30 "${base_url}${endpoint}?${query}")
  [ "$(echo "$resp" | jq -r '.errcode // 0')" = "0" ] || { echo "YAPI Error" >&2; exit 1; }
  echo "$resp" | jq '.data'
}

project_id=$(yapi_get "/api/project/get" "token=$token" | jq -r '._id')
menu=$(yapi_get "/api/interface/list_menu" "project_id=${project_id}&token=${token}")

# 生成 分类<TAB>api_id 映射（按分类分组）
MAP_FILE=$(mktemp)
trap "rm -f $MAP_FILE" EXIT
echo "$menu" | jq -r '.[] | .name as $cat | .list[]? | "\($cat)\t\(._id)"' 2>/dev/null > "$MAP_FILE"

# 分类名 → 安全文件名
safe_fname() {
  echo "$1" | sed 's/[/\\:*?"<>|]/_/g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | head -c 80
}

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# 获取某分类下的所有 api_id
get_api_ids() {
  local cat="$1"
  awk -F'\t' -v c="$cat" '$1==c {print $2}' "$MAP_FILE"
}

# 输出单个接口的内容（不包含 # 标题，由调用方加）
render_interface() {
  local data="$1"
  local cat_name="$2"

  local title method path status desc markdown
  title=$(echo "$data" | jq -r '.title // .path // "未命名"')
  method=$(echo "$data" | jq -r '.method | ascii_upcase')
  path=$(echo "$data" | jq -r '.path // ""')
  status=$(echo "$data" | jq -r '.status // "undone"')
  desc=$(echo "$data" | jq -r '.desc // ""')
  markdown=$(echo "$data" | jq -r '.markdown // ""')

  echo "## $title"
  echo ""
  desc_plain=$(echo "$desc" | sed -E 's/<[^>]+>//g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  if [ -n "$desc_plain" ] && [ "$desc_plain" != "$markdown" ]; then
    echo "> $desc_plain"
    echo ""
  fi
  echo "### 基本信息"
  echo ""
  echo "| 属性 | 值 |"
  echo "|------|-----|"
  echo "| 接口路径 | \`$path\` |"
  echo "| 请求方式 | $method |"
  echo "| 状态 | $status |"
  echo "| 分类 | $cat_name |"
  echo ""

  if [ -n "$markdown" ]; then
    echo "### 备注"
    echo ""
    echo "$markdown"
    echo ""
  fi

  markdown_file=""
  if [ -n "$markdown" ]; then
    markdown_file=$(mktemp)
    echo "$markdown" > "$markdown_file"
  fi

  req_query=$(echo "$data" | jq -c '.req_query // []' 2>/dev/null)
  if [ "$(echo "$req_query" | jq 'length')" -gt 0 ]; then
    echo "### Query 参数"
    echo ""
    if [ -n "$markdown_file" ]; then
      echo "$req_query" | python3 "$SCRIPT_DIR/schema_to_table.py" --params-query "$markdown_file"
    else
      echo "$req_query" | python3 "$SCRIPT_DIR/schema_to_table.py" --params-query
    fi
    echo ""
  fi

  req_body_form=$(echo "$data" | jq -c '.req_body_form // []' 2>/dev/null)
  if [ "$(echo "$req_body_form" | jq 'length')" -gt 0 ]; then
    echo "### Body 参数 (form)"
    echo ""
    if [ -n "$markdown_file" ]; then
      echo "$req_body_form" | python3 "$SCRIPT_DIR/schema_to_table.py" --params-form "$markdown_file"
    else
      echo "$req_body_form" | python3 "$SCRIPT_DIR/schema_to_table.py" --params-form
    fi
    echo ""
  fi

  req_body_type=$(echo "$data" | jq -r '.req_body_type // "none"')
  req_body_other=$(echo "$data" | jq -c '.req_body_other // empty' 2>/dev/null)
  if [ "$req_body_type" = "json" ] && [ -n "$req_body_other" ]; then
    echo "### 请求体参数"
    echo ""
    if [ -n "$markdown_file" ]; then
      echo "$req_body_other" | python3 "$SCRIPT_DIR/schema_to_table.py" "请求体字段" "$markdown_file"
    else
      echo "$req_body_other" | python3 "$SCRIPT_DIR/schema_to_table.py" "请求体字段"
    fi
    echo ""
  fi

  res_body=$(echo "$data" | jq -c '.res_body // empty' 2>/dev/null)
  if [ -n "$res_body" ]; then
    echo "### 返回字段"
    echo ""
    if [ -n "$markdown_file" ]; then
      echo "$res_body" | python3 "$SCRIPT_DIR/schema_to_table.py" "返回结构" "$markdown_file"
    else
      echo "$res_body" | python3 "$SCRIPT_DIR/schema_to_table.py" "返回结构"
    fi
    echo ""
  fi

  [ -n "$markdown_file" ] && [ -f "$markdown_file" ] && rm -f "$markdown_file"
}

# 获取所有不重复的分类（每行一个，保留名称中的空格）
categories=$(awk -F'\t' '{print $1}' "$MAP_FILE" | sort -u)
total_cats=$(echo "$categories" | wc -l | tr -d ' ')
cat_idx=0

while IFS= read -r cat_name; do
  [ -z "$cat_name" ] && continue
  cat_idx=$((cat_idx + 1))
  dir_name=$(safe_fname "$cat_name")
  out="$OUTPUT_DIR/${dir_name}.md"

  {
    echo "# $cat_name"
    echo ""
    echo "本分类包含以下接口："
    echo ""

    # 生成目录
    for api_id in $(get_api_ids "$cat_name"); do
      data=$(yapi_get "/api/interface/get" "id=${api_id}&token=${token}")
      title=$(echo "$data" | jq -r '.title // .path // "未命名"')
      method=$(echo "$data" | jq -r '.method | ascii_upcase')
      path=$(echo "$data" | jq -r '.path // ""')
      anchor=$(echo "$title" | tr ' ' '-' | sed 's/[][#*`<>()]//g' | sed -E 's/-+/-/g' | sed 's/^-//;s/-$//')
      [ -z "$anchor" ] && anchor="接口"
      echo "- [$title](#${anchor})  \`$method $path\`"
    done
    echo ""
    echo "---"
    echo ""

    # 输出每个接口详情（单接口失败不中断，继续处理其余）
    set +e
    for api_id in $(get_api_ids "$cat_name"); do
      data=$(yapi_get "/api/interface/get" "id=${api_id}&token=${token}" 2>/dev/null)
      if [ $? -eq 0 ] && [ -n "$data" ]; then
        render_interface "$data" "$cat_name" 2>/dev/null || true
      fi
    done
    set -e
  } > "$out"

  api_count=$(get_api_ids "$cat_name" | wc -l)
  echo "  [$cat_idx/$total_cats] ${dir_name}.md ($api_count 个接口)"
done <<< "$categories"

# 生成 README 索引
{
  echo "# Star Gate API 接口文档"
  echo ""
  echo "按分类导出，每个分类一个文档。"
  echo ""
  while IFS= read -r cat_name; do
    [ -z "$cat_name" ] && continue
    dir_name=$(safe_fname "$cat_name")
    api_count=$(get_api_ids "$cat_name" | wc -l)
    echo "- [$cat_name](${dir_name}.md) ($api_count 个接口)"
  done <<< "$categories"
  echo ""
} > "$OUTPUT_DIR/README.md"

total=$(wc -l < "$MAP_FILE")
echo "Done. $total 个接口 → $total_cats 个文档 + README in $OUTPUT_DIR"
