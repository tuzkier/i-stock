"""全局闭包域（改造⑤b）：交付终局的跨阶段一次性闭包校验。

各阶段 reviewer 做的是"本阶段 vs 直接上游"的局部完备；本域补一个**全 mission 一次性**
兜底：把所有阶段 contract 收集起来，检查每条 `traces_to` 引用的稳定 ID 是否在
mission 文档集内有定义——引用了一个**集合内不存在的 ID** = 悬空引用 = 推理链断在
文档集外（对齐 Capio"悬空引用"闭包校验）。

设计为**纯函数 + 保守**：只对"长得像稳定 ID"（命中已知前缀）的引用判悬空，避免对
自由文本误报；默认 WARN 灰度，strict 模式才升 FAIL。机器化、确定性，不是 AI 审查。
"""

from __future__ import annotations

import re
from typing import Any

# 稳定 ID 前缀（代码侧 SSOT）。只有命中这些前缀的 traces_to 叶子才参与悬空判定，
# 自由文本不参与。
# 同步约束：本元组与 rules/stage-doc-standard.md 第 3 条列举的稳定 ID 前缀体系**必须一致**——
# 新增 ID 体系（如界面 SURF- / 页面态 PS- / 系统用例 SUC-）时两处一起改，否则
# tests/test_id_prefix_doc_sync.py 守卫会失败。历史教训：曾因界面 SURF- 只进了下游覆盖门
# 却漏进本白名单，导致「覆盖门要求写 SURF、闭包门又判 SURF 悬空」的自相矛盾死锁。
# 注意：框架已废弃 AC / FR / NFR 旧词汇（见 scripts/check_legacy_semantics.py），故不收录。
KNOWN_ID_PREFIXES = (
    "REQ-", "SCN-", "US-", "UC-", "SUC-",
    "DEC-", "MOD-", "IF-", "DATA-", "VS-", "EV-", "CMD-", "OBL-",
    "PS-", "SURF-", "CLAR-", "T-",
)

# 前缀至少 1 个大写字母（支持单字母前缀如 T-）；真正的过滤靠 startswith(prefixes) 白名单。
_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[A-Za-z0-9._-]+$")


def looks_like_id(value: Any, prefixes: tuple[str, ...] = KNOWN_ID_PREFIXES) -> bool:
    s = str(value).strip()
    if not _ID_RE.match(s):
        return False
    return s.startswith(prefixes)


def _walk_traces_to(value: Any, out: set[str]) -> None:
    """traces_to 可能是 list、dict-of-lists（如 {ac:[...], fr:[...]}）或标量。收集所有叶子。"""
    if isinstance(value, dict):
        for v in value.values():
            _walk_traces_to(v, out)
    elif isinstance(value, list):
        for v in value:
            _walk_traces_to(v, out)
    elif value is not None:
        out.add(str(value).strip())


def extract_contract_ids(contract: dict[str, Any]) -> tuple[set[str], set[str]]:
    """从单个 contract 递归提取 (defined_ids, referenced_ids)。

    - defined_ids：任意层级出现的 ``id`` 与 ``node_id`` 字段值（obligations / decisions /
      role_verdicts / matrix 行 / 节点等都带 id）。
    - referenced_ids：任意层级 ``traces_to`` 键下的所有叶子（list / dict-of-lists 都展开）。
    """
    defined: set[str] = set()
    referenced: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                if key in ("id", "node_id") and isinstance(val, (str, int)):
                    defined.add(str(val).strip())
                elif key == "traces_to":
                    _walk_traces_to(val, referenced)
                else:
                    visit(val)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(contract)
    return defined, referenced


def mission_closure_findings(
    contracts: list[dict[str, Any]],
    *,
    strict: bool = False,
    id_prefixes: tuple[str, ...] = KNOWN_ID_PREFIXES,
) -> list[dict[str, str]]:
    """跨全部阶段 contract 的闭包校验：报告悬空引用（referenced 但 nowhere defined）。

    - 把所有 contract 的 defined_ids 并成 mission 级"已定义集合"。
    - 对每个 referenced id：命中已知前缀（looks_like_id）且不在已定义集合中 → 悬空。
    - strict=True 时悬空记 FAIL，否则记 WARN（灰度期默认）。

    返回 finding dict 列表：{level, code, message, id}。无悬空时返回 []（闭包成立）。
    """
    all_defined: set[str] = set()
    all_referenced: set[str] = set()
    for c in contracts:
        if not isinstance(c, dict):
            continue
        d, r = extract_contract_ids(c)
        all_defined |= d
        all_referenced |= r

    dangling = sorted(
        ref for ref in all_referenced
        if looks_like_id(ref, id_prefixes) and ref not in all_defined
    )
    level = "FAIL" if strict else "WARN"
    findings: list[dict[str, str]] = []
    for ref in dangling:
        findings.append(
            {
                "level": level,
                "code": "dangling_traces_to",
                "id": ref,
                "message": (
                    f"traces_to 引用了 {ref}，但它在本 mission 全部阶段 contract 中均无定义"
                    "（悬空引用 = 推理链断在文档集外）"
                ),
            }
        )
    return findings
