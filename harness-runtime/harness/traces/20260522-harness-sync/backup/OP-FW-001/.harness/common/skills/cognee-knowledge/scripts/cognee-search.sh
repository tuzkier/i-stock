#!/bin/bash
# Cognee Knowledge Graph Query Script
# Usage:
#   bash cognee-search.sh health                              - 检查服务状态
#   bash cognee-search.sh datasets                            - 列出所有数据集
#   bash cognee-search.sh search "query" [--dataset NAME]     - 自然语言问答 (GRAPH_COMPLETION)
#   bash cognee-search.sh chunks "query" [--dataset NAME]     - 原始文档片段 (CHUNKS)
#   bash cognee-search.sh rag "query" [--dataset NAME]        - RAG 检索增强 (RAG_COMPLETION)
#   bash cognee-search.sh add "file_or_text" "dataset_name"   - 入库数据
#   bash cognee-search.sh status                              - 查看处理状态

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config.json"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: 配置文件不存在: ${CONFIG_FILE}"
  echo "请先创建 config.json，参考 SKILL.md 中的配置说明"
  exit 1
fi

eval "$(python3 -c "
import json, sys
try:
    c = json.load(open(sys.argv[1]))
except Exception as e:
    print(f'echo \"ERROR: 配置文件解析失败: {e}\"; exit 1')
    sys.exit(0)
if not c.get('api_url'):
    print('echo \"ERROR: config.json 缺少 api_url\"; exit 1')
    sys.exit(0)
print(f'COGNEE_API={chr(34)}{c[\"api_url\"]}{chr(34)}')
print(f'DEFAULT_DATASET={chr(34)}{c.get(\"default_dataset\", \"\")}{chr(34)}')
print(f'DEFAULT_TOP_K={c.get(\"default_top_k\", 10)}')
" "$CONFIG_FILE")"

COGNEE_TOKEN=""

_auth_header() {
  if [ -n "$COGNEE_TOKEN" ]; then
    echo "-H" "Authorization: Bearer $COGNEE_TOKEN"
  fi
}

_curl() {
  local auth
  auth=$(_auth_header)
  if [ -n "$auth" ]; then
    curl -s -f "$@" -H "Authorization: Bearer $COGNEE_TOKEN"
  else
    curl -s -f "$@"
  fi
}

# 需要鉴权的 API：按 HTTP 状态判断成功；失败时在 stderr 打印状态码与响应体（便于区分 401 / 404）
_curl_api() {
  local tmp code
  tmp=$(mktemp)
  if [ -n "${COGNEE_TOKEN:-}" ]; then
    code=$(curl -sS -o "$tmp" -w "%{http_code}" -H "Authorization: Bearer $COGNEE_TOKEN" "$@") || {
      rm -f "$tmp"
      return 1
    }
  else
    code=$(curl -sS -o "$tmp" -w "%{http_code}" "$@") || {
      rm -f "$tmp"
      return 1
    }
  fi
  if [[ "$code" =~ ^2[0-9][0-9]$ ]]; then
    cat "$tmp"
    rm -f "$tmp"
    return 0
  fi
  echo "ERROR: HTTP ${code}" >&2
  cat "$tmp" >&2
  echo >&2
  rm -f "$tmp"
  return 1
}

# 仅在需要认证的子命令前调用（见下方 case）。优先级：COGNEE_API_TOKEN > api_token > auth 登录；登录结果写入 .cognee_token_cache.json，有效期内复用。
_ensure_token() {
  eval "$(python3 "${SCRIPT_DIR}/cognee_resolve_token.py" "${CONFIG_FILE}")" || exit 1
  if [ -n "${COGNEE_API_TOKEN:-}" ]; then
    COGNEE_TOKEN="$COGNEE_API_TOKEN"
  fi
}

cmd_health() {
  local resp
  resp=$(_curl "${COGNEE_API}/health" 2>/dev/null) || {
    echo "ERROR: Cognee 服务不可用 (${COGNEE_API})"
    exit 1
  }
  echo "$resp" | python3 -c '
import sys, json
d = json.load(sys.stdin)
s = d.get("status", "unknown")
v = d.get("version", "unknown")
print(f"OK: status={s} version={v}")
' 2>/dev/null || echo "OK: $resp"
}

cmd_datasets() {
  local resp
  resp=$(_curl_api "${COGNEE_API}/api/v1/datasets") || {
    echo "ERROR: 无法获取数据集列表"
    exit 1
  }
  echo "$resp" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if not data:
    print('(无数据集)')
    sys.exit(0)
for i, ds in enumerate(data, 1):
    name = ds.get('name', 'Unnamed')
    ds_id = ds.get('id', '?')
    created = ds.get('createdAt', 'N/A')
    print(f'{i}. {name}  (id: {ds_id}, created: {created})')
" 2>/dev/null || echo "$resp"
}

cmd_search() {
  local query="$1"
  local search_type="${2:-GRAPH_COMPLETION}"
  local dataset_name="${3:-$DEFAULT_DATASET}"
  local top_k="${4:-$DEFAULT_TOP_K}"

  local body
  # OpenAPI SearchPayloadDTO 使用 camelCase：searchType、topK（与 /openapi.json 一致）
  body=$(python3 -c "
import json, sys
q = sys.argv[1]
st = sys.argv[2]
ds = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
tk = int(sys.argv[4]) if len(sys.argv) > 4 else 10
d = {'query': q, 'searchType': st, 'topK': tk}
if ds:
    d['datasets'] = [ds]
print(json.dumps(d, ensure_ascii=False))
" "$query" "$search_type" "${dataset_name:-}" "$top_k")

  local resp
  resp=$(_curl_api -X POST "${COGNEE_API}/api/v1/search" \
    -H "Content-Type: application/json" \
    -d "$body") || {
    echo "ERROR: 搜索失败"
    exit 1
  }

  echo "$resp" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    for item in data:
        if isinstance(item, str):
            print(item)
        else:
            print(json.dumps(item, ensure_ascii=False, indent=2))
elif isinstance(data, dict):
    print(json.dumps(data, ensure_ascii=False, indent=2))
else:
    print(data)
" 2>/dev/null || echo "$resp"
}

cmd_add() {
  local data="$1"
  local dataset_name="${2:-main_dataset}"

  if [ -f "$data" ]; then
    local resp
    resp=$(_curl -X POST "${COGNEE_API}/api/v1/add" \
      -F "data=@${data}" \
      -F "datasetName=${dataset_name}" 2>/dev/null) || {
      echo "ERROR: 入库失败"
      exit 1
    }
    echo "已提交入库: ${data} → 数据集: ${dataset_name}"
    echo "运行 cognify 构建知识图谱..."
    _curl -X POST "${COGNEE_API}/api/v1/cognify" \
      -H "Content-Type: application/json" \
      -d "{\"datasets\": [\"${dataset_name}\"]}" 2>/dev/null || echo "WARN: cognify 触发失败，可能需要手动触发"
    echo "已触发知识图谱构建，使用 'status' 命令查看进度"
  else
    local resp
    resp=$(_curl -X POST "${COGNEE_API}/api/v1/add" \
      -F "data=${data}" \
      -F "datasetName=${dataset_name}" 2>/dev/null) || {
      echo "ERROR: 入库失败"
      exit 1
    }
    echo "已提交文本入库 → 数据集: ${dataset_name}"
  fi
}

cmd_status() {
  local resp
  resp=$(_curl "${COGNEE_API}/api/v1/datasets/status" 2>/dev/null) || {
    echo "WARN: 无法获取处理状态（可能无正在处理的任务）"
    exit 0
  }
  echo "$resp" | python3 -m json.tool 2>/dev/null || echo "$resp"
}

# --- Main ---

ACTION="${1:-help}"
shift || true

case "$ACTION" in
  health)
    cmd_health
    ;;
  datasets)
    _ensure_token
    cmd_datasets
    ;;
  search)
    _ensure_token
    QUERY="${1:?'缺少查询内容'}"
    shift
    DATASET=""
    if [ "${1:-}" = "--dataset" ]; then
      shift
      DATASET="${1:?'缺少数据集名称'}"
      shift || true
    fi
    cmd_search "$QUERY" "GRAPH_COMPLETION" "$DATASET"
    ;;
  chunks)
    _ensure_token
    QUERY="${1:?'缺少查询内容'}"
    shift
    DATASET=""
    if [ "${1:-}" = "--dataset" ]; then
      shift
      DATASET="${1:?'缺少数据集名称'}"
      shift || true
    fi
    cmd_search "$QUERY" "CHUNKS" "$DATASET"
    ;;
  rag)
    _ensure_token
    QUERY="${1:?'缺少查询内容'}"
    shift
    DATASET=""
    if [ "${1:-}" = "--dataset" ]; then
      shift
      DATASET="${1:?'缺少数据集名称'}"
      shift || true
    fi
    cmd_search "$QUERY" "RAG_COMPLETION" "$DATASET"
    ;;
  add)
    _ensure_token
    DATA="${1:?'缺少数据（文件路径或文本）'}"
    DATASET_NAME="${2:-main_dataset}"
    cmd_add "$DATA" "$DATASET_NAME"
    ;;
  status)
    _ensure_token
    cmd_status
    ;;
  help|*)
    cat <<USAGE
Cognee Knowledge Graph Query Tool

Usage:
  bash cognee-search.sh health                              检查服务状态
  bash cognee-search.sh datasets                            列出所有数据集
  bash cognee-search.sh search "query" [--dataset NAME]     自然语言问答
  bash cognee-search.sh chunks "query" [--dataset NAME]     原始文档片段
  bash cognee-search.sh rag    "query" [--dataset NAME]     RAG 检索增强
  bash cognee-search.sh add    "file_or_text" [dataset]     入库数据
  bash cognee-search.sh status                              查看处理状态

Config: ${CONFIG_FILE}
  api_url:          ${COGNEE_API}
  default_dataset:  ${DEFAULT_DATASET:-(none)}
USAGE
    ;;
esac
