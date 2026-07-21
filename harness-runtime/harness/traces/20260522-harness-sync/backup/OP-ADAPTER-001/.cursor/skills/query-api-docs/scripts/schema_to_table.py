#!/usr/bin/env python3
"""将 JSON Schema 转为可读的 Markdown 参数表，支持嵌套对象。支持从 YAPI 备注中解析字段说明。"""
import json
import sys
import re

def safe(s: str) -> str:
    if not s:
        return ""
    return str(s).replace("|", "\\|").replace("\n", " ").strip()[:200]

def is_trivial_desc(s: str) -> bool:
    """仅类型无实质说明时视为空，如 String, Long, Void, Boolean, 等"""
    if not s or not s.strip():
        return True
    t = re.sub(r"^\s*(String|Long|Integer|Int|Boolean|Bool|Void|Object|Number|Array|List<[^>]+>)\s*,?\s*", "", s, flags=re.I).strip()
    return len(t) < 2  # 去掉类型前缀后几乎为空

def parse_field_remarks_from_markdown(markdown: str) -> dict:
    """从 YAPI 备注中解析 字段名 -> 说明 映射。支持格式：
    - * `fieldName`：说明
    - * fieldName ：说明
    - | 字段名 | 说明 |
    """
    remarks = {}
    if not markdown or not isinstance(markdown, str):
        return remarks
    # 匹配 * `xxx`：说明 或 * xxx ：说明
    for m in re.finditer(r'[*\-]\s*`?([a-zA-Z_][a-zA-Z0-9_]*)`?\s*[：:]\s*(.+?)(?=\n|$)', markdown):
        name, desc = m.group(1).strip(), m.group(2).strip()
        if name and len(desc) < 300:
            remarks[name] = desc
    # 匹配 markdown 表格 | 字段 | 说明 |
    for m in re.finditer(r'\|\s*`?([a-zA-Z_][a-zA-Z0-9_]*)`?\s*\|\s*([^|]+?)\s*\|', markdown):
        name, desc = m.group(1).strip(), m.group(2).strip()
        if name and not name.startswith("-") and len(desc) < 300:
            remarks[name] = desc
    return remarks

def get_type(prop: dict) -> str:
    t = prop.get("type", "")
    if prop.get("items"):
        inner = prop["items"]
        if isinstance(inner, dict) and inner.get("$ref"):
            return "array<object>"
        return f"array<{inner.get('type', 'any')}>"
    return t or "any"

def render_table(props: dict, required: list, indent: str = "", field_remarks: dict = None) -> list[str]:
    field_remarks = field_remarks or {}
    required_set = set(required or [])
    lines = []
    for k, v in props.items():
        if not isinstance(v, dict):
            continue
        t = get_type(v)
        req = "是" if k in required_set else "否"
        # 口径：备注 = description 字段；说明优先 title
        desc = safe(v.get("title") or "")
        remark = safe(v.get("description") or v.get("remark") or "")
        # 兜底：若 description 空，再尝试从 markdown 备注映射
        if not remark and k in field_remarks:
            remark = safe(field_remarks[k])
        if not remark and k == "code" and "status" in field_remarks:
            remark = safe(field_remarks["status"])
        if not remark and k == "enumName" and "name" in field_remarks:
            remark = safe(field_remarks["name"])
        lines.append(f"| {indent}{k} | {t} | {req} | {desc} | {remark} |")
    return lines

def schema_to_md(schema: dict, root_title: str, field_remarks: dict = None) -> str:
    """递归将 schema 转为 markdown。"""
    out = []
    props = schema.get("properties") or {}
    required = schema.get("required") or []

    if not props:
        return ""

    # 根级参数表
    out.append(f"### {root_title}")
    out.append("")
    out.append("| 参数名 | 类型 | 必填 | 说明 | 备注 |")
    out.append("|--------|------|------|------|------|")
    out.extend(render_table(props, required, "", field_remarks))

    # 嵌套 object 单独成表
    for k, v in props.items():
        if not isinstance(v, dict):
            continue
        nested = v.get("properties") or {}
        # array 的 items 也可能是 object，需单独展示
        if v.get("type") == "array" and v.get("items"):
            items = v["items"]
            if isinstance(items, dict) and items.get("properties"):
                nested = items.get("properties") or {}
                nreq = items.get("required") or []
                out.append("")
                out.append(f"#### {k}（数组元素）")
                out.append("")
                out.append("| 参数名 | 类型 | 必填 | 说明 | 备注 |")
                out.append("|--------|------|------|------|------|")
                out.extend(render_table(nested, nreq, "", field_remarks))
        elif v.get("type") == "object" and nested:
            nreq = v.get("required") or []
            out.append("")
            out.append(f"#### {k} 子字段")
            out.append("")
            out.append("| 参数名 | 类型 | 必填 | 说明 | 备注 |")
            out.append("|--------|------|------|------|------|")
            out.extend(render_table(nested, nreq, "", field_remarks))

    return "\n".join(out) + "\n"

def render_params_table(params: list, fmt: str, field_remarks: dict = None) -> str:
    """渲染 req_query 或 req_body_form 为表格，合并备注中的字段说明。"""
    field_remarks = field_remarks or {}
    if not params:
        return ""
    lines = []
    if fmt == "query":
        lines = ["| 参数名 | 类型 | 必填 | 说明 | 备注 | 示例 |", "|--------|------|------|------|------|------|"]
        for p in params:
            name = p.get("name", "")
            t = p.get("type", "string")
            req = "是" if str(p.get("required", "")) == "1" else "否"
            # 口径：备注 = desc/remark；说明留空（req_query 通常无 title）
            desc = ""
            remark = safe((p.get("desc") or p.get("remark") or "").strip())
            if not remark:
                remark = safe(field_remarks.get(name, ""))
            ex = safe(str(p.get("example", "")))
            lines.append(f"| {name} | {t} | {req} | {desc} | {remark} | {ex} |")
    else:  # form
        lines = ["| 参数名 | 类型 | 必填 | 说明 | 备注 |", "|--------|------|------|------|------|"]
        for p in params:
            name = p.get("name", "")
            t = p.get("type", "text")
            req = "是" if str(p.get("required", "")) == "1" else "否"
            desc = ""
            remark = safe((p.get("desc") or p.get("remark") or "").strip())
            if not remark:
                remark = safe(field_remarks.get(name, ""))
            lines.append(f"| {name} | {t} | {req} | {desc} | {remark} |")
    return "\n".join(lines) + "\n"

def main():
    if len(sys.argv) < 2:
        print("Usage: schema_to_table.py <title> [markdown_file]  # schema from stdin")
        print("   or: schema_to_table.py --params-query <markdown_file>  # req_query from stdin")
        print("   or: schema_to_table.py --params-form <markdown_file>   # req_body_form from stdin")
        return
    mode = sys.argv[1]
    markdown_file = sys.argv[2] if len(sys.argv) > 2 else None
    field_remarks = {}
    if markdown_file:
        try:
            with open(markdown_file, "r", encoding="utf-8") as f:
                field_remarks = parse_field_remarks_from_markdown(f.read())
        except Exception:
            pass
    data = sys.stdin.read().strip()
    if mode == "--params-query":
        try:
            params = json.loads(data)
            print(render_params_table(params if isinstance(params, list) else [], "query", field_remarks))
        except json.JSONDecodeError:
            print("| 参数名 | 类型 | 必填 | 说明 | 备注 | 示例 |\n|--------|------|------|------|------|------|")
        return
    if mode == "--params-form":
        try:
            params = json.loads(data)
            print(render_params_table(params if isinstance(params, list) else [], "form", field_remarks))
        except json.JSONDecodeError:
            print("| 参数名 | 类型 | 必填 | 说明 | 备注 |\n|--------|------|------|------|------|")
        return
    title = mode
    # 去除未转义控制字符（YAPI enumDesc 等含换行会导致 JSON 无效）
    schema_data = re.sub(r"[\x00-\x1f]", " ", data)
    try:
        schema = json.loads(schema_data)
    except json.JSONDecodeError:
        try:
            schema = json.loads(schema_data.replace("\n", " ").replace("\r", " "))
        except json.JSONDecodeError:
            print(f"```json\n{data[:2000]}...\n```")
            return
    if isinstance(schema, str):
        try:
            schema = json.loads(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", schema))
        except json.JSONDecodeError:
            print(f"```json\n{data[:2000]}...\n```")
            return
    if isinstance(schema, dict) and "properties" in schema:
        print(schema_to_md(schema, title, field_remarks))
    else:
        out = json.dumps(schema, ensure_ascii=False, indent=2) if isinstance(schema, dict) else data
        print(f"```json\n{out}\n```")

if __name__ == "__main__":
    main()
