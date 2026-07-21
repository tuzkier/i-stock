"""澄清沉淀域（改造②）：把 Decision Gate 里人回答的澄清落成可追溯的文档集材料。

设计意图见 docs/harness-correctness-closure-upgrade-plan.md 改造②。

- 每条澄清 = 项目根 `materials/clarifications/CLAR-<NNN>.md`（人可读 + frontmatter）。
- `_index.json` 作为机器 SSOT（可靠枚举），`_index.md` 作为人可读索引（Capio 的 IDX）。
- 澄清在 frontmatter 带 `mission_id`；完备性审查据此把"mission_id 匹配当前 mission"的
  澄清自动计入该 mission 的"人提供资料"文档集（见 stage-doc-standard），
  不依赖脆弱的 source_materials 手工编辑——信息链因此连续。

为什么不进 approvals.json：approvals 是审批 SSOT（决定本身），不在完备性文档集三类内；
澄清的**内容**必须落进 materials/（文档集），下游重导才看得见、信息链才不断。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness_cli_core.infra.time import now_iso


def clarifications_dir(root: Path) -> Path:
    return root / "materials" / "clarifications"


def index_json_path(root: Path) -> Path:
    return clarifications_dir(root) / "_index.json"


def index_md_path(root: Path) -> Path:
    return clarifications_dir(root) / "_index.md"


def clarification_path(root: Path, clar_id: str) -> Path:
    return clarifications_dir(root) / f"{clar_id}.md"


def load_clarifications(root: Path) -> list[dict[str, Any]]:
    """从机器 SSOT `_index.json` 读全部澄清记录；不存在或损坏时返回空列表（非破坏）。"""
    path = index_json_path(root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        records = data.get("clarifications")
    else:
        records = data
    return [item for item in records if isinstance(item, dict)] if isinstance(records, list) else []


def next_clarification_id(records: list[dict[str, Any]]) -> str:
    """项目级全局递增（对齐 Capio A-PS-CLAR-NNN，自 001 起），跨 mission 长期累积。"""
    return f"CLAR-{len(records) + 1:03d}"


def clarification_matches(record: dict[str, Any], *, mission: str | None = None) -> bool:
    if mission and str(record.get("mission_id") or "") != mission:
        return False
    return True


def _render_index_md(records: list[dict[str, Any]]) -> str:
    lines = [
        "# 澄清补充索引（CLAR Index）",
        "",
        "> 本文件由 `harness clarification record` 自动维护，请勿手工编辑。",
        "> 每条澄清是人对 Decision Gate 的回答，已沉淀为文档集"
        "（人提供资料类）的一部分；完备性审查按 `mission_id` 圈定本 mission 纳入的澄清。",
        "",
        "| CLAR | mission | stage | gap | 问题 | 决定时间 |",
        "|---|---|---|---|---|---|",
    ]
    for r in records:
        q = str(r.get("question") or "").replace("|", "\\|").replace("\n", " ")
        if len(q) > 60:
            q = q[:57] + "…"
        lines.append(
            f"| [{r.get('id')}]({r.get('id')}.md) | {r.get('mission_id') or ''} | "
            f"{r.get('stage') or ''} | {r.get('gap_id') or ''} | {q} | {r.get('decided_at') or ''} |"
        )
    return "\n".join(lines) + "\n"


def _render_clarification_md(record: dict[str, Any]) -> str:
    fm = {
        "id": record.get("id"),
        "mission_id": record.get("mission_id"),
        "stage": record.get("stage"),
        "gap_id": record.get("gap_id"),
        "source_role": record.get("source_role"),
        "approval_id": record.get("approval_id"),
        "decided_at": record.get("decided_at"),
    }
    fm_lines = "\n".join(f"{k}: {v if v is not None else ''}" for k, v in fm.items())
    return (
        f"---\n{fm_lines}\n---\n\n"
        f"# {record.get('id')} 澄清补充\n\n"
        f"## 问题（reviewer 标记的信息缺口）\n\n{record.get('question') or ''}\n\n"
        f"## 用户答复（已确认，纳入文档集作为推导前提）\n\n{record.get('answer') or ''}\n"
    )


def write_clarification(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    """落盘单条澄清：写 CLAR-NNN.md + 追加 _index.json + 重渲染 _index.md。

    返回 {clarification, clarification_path, index_json_path, index_md_path}（相对项目根的路径）。
    """
    records = load_clarifications(root)
    if not record.get("id"):
        record = {**record, "id": next_clarification_id(records)}
    record.setdefault("decided_at", now_iso())

    d = clarifications_dir(root)
    d.mkdir(parents=True, exist_ok=True)

    clar_path = clarification_path(root, str(record["id"]))
    clar_path.write_text(_render_clarification_md(record), encoding="utf-8")

    records.append(record)
    index_json_path(root).write_text(
        json.dumps({"schema_version": 1, "clarifications": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    index_md_path(root).write_text(_render_index_md(records), encoding="utf-8")

    return {
        "clarification": record,
        "clarification_path": str(clar_path.relative_to(root)),
        "index_json_path": str(index_json_path(root).relative_to(root)),
        "index_md_path": str(index_md_path(root).relative_to(root)),
    }
