"""Behavior graph (SSOT) model for the interaction stage.

The behavior graph is the single source of truth produced by the interaction
stage. It has **four normalized tables**:

- ``page_states`` — nodes: a surface × state renderable atom (deduped).
- ``steps``       — beats: a (flow-step × outcome), each bound to one page_state.
- ``edges``       — transitions: ``from`` → ``to`` carrying a trigger.
- ``flows``       — paths: an ordered list of step ids (the walkthrough story).

This module is pure (no argparse / no IO side effects beyond reading files):

- load the graph yaml and the surface catalog from ``surface-model.md``;
- extract prototype trace anchors (``data-step`` / ``data-pagestate`` / ``data-via``);
- compute graph reachability (rooted at ``ENTRY`` edges);
- ``reconcile_findings`` — the single pass behind ``harness interaction
  prototype-check`` producing category-tagged findings.

Finding levels follow the repo convention: ``FAIL`` / ``WARN`` / ``PASS``.
Every finding carries a ``category`` in
``{graph, reachability, anchor, coverage, locator, upstream, composition}``.

The ``composition`` category is the **layout / composition axis** (region tree):
behavior tables answer "which states exist and how they flow"; the region tree in
``surface-model.md``'s 「布局骨架（机器段）」 answers "how the page is laid out".
Without it, a prototype's spatial arrangement is unconstrained = a pile of controls.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from harness_cli_core.domain.findings import finding, is_placeholder_text
from harness_cli_core.infra.runtime_paths import (
    mission_artifact_dir,
    mission_stage_dir,
    read_text_if_exists,
    relpath,
)

ENTRY = "ENTRY"

# 图可达性门级白名单（PAGESTATE_UNREACHABLE 的 finding level 由它决定）。
# 默认 fail：除非显式声明 warn，孤儿态一律 FAIL（防脏值悄悄降级）。
REACHABILITY_GATE_LEVELS = ("fail", "warn")
DEFAULT_REACHABILITY_GATE_LEVEL = "fail"


def resolve_reachability_level(config: dict[str, Any]) -> str:
    """从 runtime config 读取 ``interaction.reachability_gate_level``，归一化
    (strip + lower)；非白名单值一律回退 ``DEFAULT_REACHABILITY_GATE_LEVEL``
    （绝不静默降级成 warn）。集中归一化逻辑，供调用处复用。"""
    interaction = config.get("interaction") if isinstance(config, dict) else None
    raw = (interaction or {}).get("reachability_gate_level") if isinstance(interaction, dict) else None
    lvl = str(raw or "").strip().lower()
    return lvl if lvl in REACHABILITY_GATE_LEVELS else DEFAULT_REACHABILITY_GATE_LEVEL


# 组成轴（layout / composition）门级。新增门按 warn 滚动（提示不阻断），项目采用区域树
# 后由 config 升到 fail；off 完全跳过组成校验（迁移期）。
COMPOSITION_GATE_LEVELS = ("fail", "warn", "off")
DEFAULT_COMPOSITION_GATE_LEVEL = "warn"


def resolve_composition_level(config: dict[str, Any]) -> str:
    """从 runtime config 读取 ``interaction.composition_gate_level``，归一化
    (strip + lower)；非白名单值回退 ``DEFAULT_COMPOSITION_GATE_LEVEL``。"""
    interaction = config.get("interaction") if isinstance(config, dict) else None
    raw = (interaction or {}).get("composition_gate_level") if isinstance(interaction, dict) else None
    lvl = str(raw or "").strip().lower()
    return lvl if lvl in COMPOSITION_GATE_LEVELS else DEFAULT_COMPOSITION_GATE_LEVEL


# 设计系统（design system）门级——从组件库装配（R9）。同 composition：warn 滚动，采用后升 fail。
DESIGN_SYSTEM_GATE_LEVELS = ("fail", "warn", "off")
DEFAULT_DESIGN_SYSTEM_GATE_LEVEL = "warn"


def resolve_design_system_level(config: dict[str, Any]) -> str:
    """从 runtime config 读取 ``interaction.design_system_gate_level``，归一化；
    非白名单值回退 ``DEFAULT_DESIGN_SYSTEM_GATE_LEVEL``。"""
    interaction = config.get("interaction") if isinstance(config, dict) else None
    raw = (interaction or {}).get("design_system_gate_level") if isinstance(interaction, dict) else None
    lvl = str(raw or "").strip().lower()
    return lvl if lvl in DESIGN_SYSTEM_GATE_LEVELS else DEFAULT_DESIGN_SYSTEM_GATE_LEVEL


# ---------------------------------------------------------------------------
# Locating + loading
# ---------------------------------------------------------------------------


def interaction_dir(root: Path, mission: str) -> Path:
    """Interaction artifact dir, preferring the artifact store with legacy
    stage-dir fallback (mirrors interaction.py resolution)."""
    artifact_dir = mission_artifact_dir(root, mission) / "interaction"
    legacy_dir = mission_stage_dir(root, mission)
    if legacy_dir.exists() and not artifact_dir.exists():
        return legacy_dir
    return artifact_dir


def behavior_graph_path(root: Path, mission: str) -> Path:
    return interaction_dir(root, mission) / "interaction-spec" / "behavior-graph.yaml"


def surface_model_path(root: Path, mission: str) -> Path:
    return interaction_dir(root, mission) / "interaction-spec" / "surface-model.md"


def load_behavior_graph(root: Path, mission: str) -> tuple[Path, dict[str, Any] | None]:
    """Return ``(path, graph_or_None)``. ``None`` means absent; an empty/invalid
    yaml is reported as ``{}`` so callers can distinguish "no file" from "empty"."""
    path = behavior_graph_path(root, mission)
    if not path.exists():
        return path, None
    try:
        import yaml

        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — malformed yaml surfaces as {} for a graph finding
        return path, {}
    return path, doc if isinstance(doc, dict) else {}


def project_behavior_graph_path(root: Path) -> Path:
    """Project-level accumulated behavior graph — the SSOT for what the long-lived
    prototype must contain across all sedimented missions. Sits next to the SUC
    registry."""
    return root / "project-knowledge" / "product" / "system-use-cases" / "behavior-graph.yaml"


def load_project_behavior_graph(root: Path) -> dict[str, Any]:
    """Load the project-level accumulated graph; {} if absent (greenfield / not yet
    promoted)."""
    path = project_behavior_graph_path(root)
    if not path.exists():
        return {}
    try:
        import yaml

        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return doc if isinstance(doc, dict) else {}


def parse_supersede(mission: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize the mission-local ``superseded:`` declarations — the *iteration*
    primitive that lets a new mission evolve a sedimented surface/anchor into a
    renamed successor without either freezing both side by side (coexistence) or
    deleting the predecessor (``retired``). Each entry maps a predecessor sediment
    id to its successor (a mission increment that carries the coverage forward):

        superseded:
          - predecessor: SURF-BOARD          # surface | suc | page_state | step
            successor:   SURF-CP-BOARD
            kind: surface
            anchor_map: {PS-SURF-BOARD-readable: PS-CP-BOARD-ready, ...}  # optional
            dropped: []                       # coverage intentionally NOT carried
            rationale: "lane×node 看板进化为 mission×stage 看板（同一 WorkGraphBoard.tsx 扩展）"

    The predecessor's anchors drop out of the merged graph (so the regression gate
    no longer requires them physically anchored — one surface, not two); the
    successor must really exist + be covered (validated by ``supersede_findings``)."""
    raw = mission.get("superseded")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        pred = str(row.get("predecessor") or "").strip()
        if not pred:
            continue
        out.append({
            "predecessor": pred,
            "successor": str(row.get("successor") or "").strip(),
            "kind": (str(row.get("kind") or "surface").strip() or "surface"),
            "anchor_map": row.get("anchor_map") if isinstance(row.get("anchor_map"), dict) else {},
            "dropped": [str(x) for x in row.get("dropped")] if isinstance(row.get("dropped"), list) else [],
            "rationale": str(row.get("rationale") or "").strip(),
        })
    return out


def _expand_supersede(
    entries: list[dict[str, Any]],
    ps_rows: dict[str, dict[str, Any]],
    step_rows: dict[str, dict[str, Any]],
) -> tuple[set[str], set[str]]:
    """Expand each superseded predecessor to the concrete page_state/step ids
    (``drop_anchor``) and surface ids (``drop_surf``) that must leave the merged
    graph. ``ps_rows`` / ``step_rows`` are the unioned (project ∪ mission) rows."""
    drop_anchor: set[str] = set()
    drop_surf: set[str] = set()
    for e in entries:
        pred, kind = e["predecessor"], e["kind"]
        if kind == "surface":
            drop_surf.add(pred)
            pred_ps = {pid for pid, p in ps_rows.items() if str(p.get("surf")) == pred}
            drop_anchor |= pred_ps
            for sid, s in step_rows.items():
                if str(s.get("page_state")) in pred_ps:
                    drop_anchor.add(sid)
        elif kind == "page_state":
            drop_anchor.add(pred)
            for sid, s in step_rows.items():
                if str(s.get("page_state")) == pred:
                    drop_anchor.add(sid)
        elif kind == "step":
            drop_anchor.add(pred)
        elif kind == "suc":
            for sid in step_rows:
                if _suc_of(sid) == pred:
                    drop_anchor.add(sid)
    return drop_anchor, drop_surf


def merge_graphs(project: dict[str, Any], mission: dict[str, Any]) -> dict[str, Any]:
    """Merge project-level (sedimented) + mission-local (increment) into one union
    graph for whole-prototype reconcile. Union each table by `id` (mission overrides
    project on id collision = modify); then drop ids the mission deliberately removes:
    the top-level ``retired: [ids]`` (deletion) and the predecessors of ``superseded:``
    (iteration — the successor carries the coverage, so the predecessor's anchors are
    discharged, not kept side by side). ``surfaces`` (inline catalog) and ``flows``
    (keyed by id) merge the same way. A ``superseded_log`` provenance trail accumulates
    so future missions can trace ``predecessor → successor`` lineage."""
    retired = set(mission.get("retired") or []) if isinstance(mission.get("retired"), list) else set()
    supersede_entries = parse_supersede(mission)

    # First union every table (no drops yet) so supersede expansion sees all rows.
    unioned: dict[str, Any] = {}
    edge_rows: list[Any] = []
    for table, key in (("page_states", "id"), ("steps", "id"), ("edges", None),
                       ("flows", "id"), ("surfaces", "surf"), ("regions", "region")):
        merged: dict[str, Any] = {}
        for src in (project, mission):
            rows = src.get(table)
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                if key is None:  # edges: dedup by (from,to)
                    edge_rows.append(row)
                else:
                    kid = str(row.get(key) or "")
                    if kid:
                        merged[kid] = row
        if key is not None:
            unioned[table] = merged

    drop_anchor, drop_surf = _expand_supersede(
        supersede_entries, unioned.get("page_states", {}), unioned.get("steps", {}))
    # ``retired`` stays a universal id set (may name a page_state/step/flow/surface/
    # region id — preserved behavior); supersede expansions add to the anchor + surface
    # namespaces.
    drop_ps_step = retired | drop_anchor          # page_states + steps id namespace
    drop_surf_all = retired | drop_surf           # surfaces (retired may name a surf)

    out: dict[str, Any] = {}
    out["page_states"] = [v for k, v in unioned["page_states"].items() if k not in drop_ps_step]
    out["steps"] = [v for k, v in unioned["steps"].items() if k not in drop_ps_step]
    out["flows"] = [v for k, v in unioned["flows"].items()
                    if k not in retired and not (set(v.get("path") or []) & drop_ps_step)]
    out["surfaces"] = [v for k, v in unioned["surfaces"].items() if k not in drop_surf_all]
    out["regions"] = [v for k, v in unioned["regions"].items()
                      if k not in retired and str(v.get("surf") or "") not in drop_surf]
    # edges: dedup by (from,to), then drop those touching a dropped step
    seen: set[Any] = set()
    deduped: list[Any] = []
    for e in edge_rows:
        sig = (str(e.get("from")), str(e.get("to")))
        if sig in seen:
            continue
        seen.add(sig)
        if str(e.get("from")) in drop_ps_step or str(e.get("to")) in drop_ps_step:
            continue
        deduped.append(e)
    out["edges"] = deduped

    # provenance: accumulate predecessor → successor lineage across missions
    log = [r for r in (project.get("superseded_log") or []) if isinstance(r, dict)]
    for e in supersede_entries:
        log.append({
            "predecessor": e["predecessor"], "successor": e["successor"],
            "kind": e["kind"], "rationale": e["rationale"],
            "mission": mission.get("mission_id") or "",
        })
    if log:
        out["superseded_log"] = log

    out["mission_id"] = mission.get("mission_id") or project.get("mission_id")
    return out


def supersede_findings(
    *,
    tables: dict[str, list[dict[str, Any]]],
    surfaces: dict[str, dict[str, Any]],
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Guard the ``supersede`` primitive against being a silent-degradation backdoor:
    every superseded predecessor must point at a successor that *really exists and is
    covered* in the merged graph (the mission increment). Otherwise it is just a
    disguised deletion and must use ``retired`` instead. ``dropped`` / missing
    ``rationale`` raise WARNs the interaction-reviewer must bless."""
    findings: list[dict[str, Any]] = []
    ps_ids = {str(p.get("id")) for p in tables.get("page_states", []) if p.get("id")}
    step_ids = {str(s.get("id")) for s in tables.get("steps", []) if s.get("id")}
    suc_ids = {_suc_of(sid) for sid in step_ids}
    surf_ids = set(surfaces or {})
    for e in entries:
        pred, succ, kind = e["predecessor"], e["successor"], e["kind"]
        if not succ:
            findings.append(finding(
                "FAIL", "SUPERSEDE_SUCCESSOR_MISSING",
                f"supersede 前驱「{pred}」未声明后继（successor）：取代必须指向承接者，"
                f"纯删除请用 retired。",
                category="supersede", predecessor=pred,
            ))
            continue
        exists = (
            (kind == "surface" and succ in surf_ids)
            or (kind == "page_state" and succ in ps_ids)
            or (kind == "step" and succ in step_ids)
            or (kind == "suc" and succ in suc_ids)
        )
        if not exists:
            findings.append(finding(
                "FAIL", "SUPERSEDE_SUCCESSOR_MISSING",
                f"supersede 后继「{succ}」（kind={kind}）未在合并图（本 mission 增量）中存在并被覆盖："
                f"前驱「{pred}」的回归义务无承接者，等同悄悄退化。补齐后继或改用 retired。",
                category="supersede", predecessor=pred, successor=succ,
            ))
        if e["dropped"]:
            findings.append(finding(
                "WARN", "SUPERSEDE_COVERAGE_DROPPED",
                f"supersede「{pred}→{succ}」显式丢弃覆盖 {e['dropped']}：interaction-reviewer "
                f"须确认这不是退化。",
                category="supersede", predecessor=pred, successor=succ,
            ))
        if not e["rationale"]:
            findings.append(finding(
                "WARN", "SUPERSEDE_RATIONALE_MISSING",
                f"supersede「{pred}→{succ}」缺 rationale：须说明覆盖如何被后继承接。",
                category="supersede", predecessor=pred, successor=succ,
            ))
    return findings


def surfaces_from_graph(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Surface catalog embedded inline in a behavior graph's ``surfaces`` table
    (used by the project-level graph which has no surface-model.md of its own).
    Row: ``{surf, name, type, baseline, page_entry, via_controls: [...]}``."""
    out: dict[str, dict[str, Any]] = {}
    rows = graph.get("surfaces")
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict) or not row.get("surf"):
            continue
        vc = row.get("via_controls")
        controls = set(vc) if isinstance(vc, list) else (
            {c.strip() for c in re.split(r"[,、\s]+", str(vc)) if c.strip()} if vc else set()
        )
        out[str(row["surf"])] = {
            "name": row.get("name", ""), "type": row.get("type", ""),
            "baseline": row.get("baseline", ""), "page_entry": row.get("page_entry", ""),
            "via_controls": controls,
        }
    return out


def regions_from_graph(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Region tree (composition axis) embedded inline in a behavior graph's
    ``regions`` table (used by the project-level accumulated graph which has no
    surface-model.md of its own, and to merge sedimented region trees). Row:
    ``{region, surf, parent, layout, priority, role, carries, scan_order}``."""
    out: dict[str, dict[str, Any]] = {}
    rows = graph.get("regions")
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict) or not row.get("region"):
            continue
        scan = row.get("scan_order")
        out[str(row["region"])] = {
            "surf": str(row.get("surf") or ""),
            "parent": str(row.get("parent") or "root"),
            "layout": str(row.get("layout") or "").lower(),
            "priority": str(row.get("priority") or "").lower(),
            "role": str(row.get("role") or "").lower(),
            "carries": row.get("carries", ""),
            "scan_order": scan if isinstance(scan, int) else None,
        }
    return out


def graph_tables(graph: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Normalize the four tables, tolerating missing/typo'd top keys."""
    def _rows(key: str) -> list[dict[str, Any]]:
        value = graph.get(key)
        return [r for r in value if isinstance(r, dict)] if isinstance(value, list) else []

    return {
        "page_states": _rows("page_states"),
        "steps": _rows("steps"),
        "edges": _rows("edges"),
        "flows": _rows("flows"),
    }


# ---------------------------------------------------------------------------
# surface-model.md machine table (surface catalog)
# ---------------------------------------------------------------------------

_SURF_ID_RE = re.compile(r"^(?:SURF|SUR)-[A-Z0-9][A-Z0-9_-]*$")

# 组成轴：区域树机器段的 id 形态 + 枚举白名单。
_REGION_ID_RE = re.compile(r"^R-[A-Z0-9][A-Za-z0-9_-]*$")
_REGION_LAYOUTS = {"row", "column", "grid", "stack", "flow"}
_REGION_PRIORITIES = {"primary", "secondary", "tertiary"}
_REGION_ROLES = {
    "navigation", "content", "detail", "toolbar",
    "actions", "filters", "status", "header", "footer",
}

# N/A 豁免机器段（structured）：粒度枚举 + PRD 节点 id 形态校验。
_NA_GRANULARITY = {"suc", "flowstep", "beat"}
_NA_NODE_RE = re.compile(r"^(SUC-(?:TF-[A-Z]+-)?[0-9]+)(?:-FLOW-[0-9]+)?(?:\.[A-Za-z0-9_-]+)?$")


def parse_surface_catalog(text: str) -> dict[str, dict[str, Any]]:
    """Parse the fixed-column surface table embedded in ``surface-model.md``:

    ``| surface id | 名称 | 类型 | baseline 关系 | page_entry | via 控件清单 |``

    Returns ``{surf_id: {name, type, baseline, page_entry, via_controls:set}}``.
    Header / separator / non-id rows are skipped. ``via 控件清单`` splits on
    ``,`` / ``、`` / whitespace.
    """
    out: dict[str, dict[str, Any]] = {}
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or not _SURF_ID_RE.match(cells[0]):
            continue
        surf = cells[0]
        via_controls: set[str] = set()
        if len(cells) >= 6:
            via_controls = {
                c.strip()
                for c in re.split(r"[,、\s]+", cells[5])
                if c.strip() and not is_placeholder_text(c)
            }
        out[surf] = {
            "name": cells[1] if len(cells) >= 2 else "",
            "type": cells[2] if len(cells) >= 3 else "",
            "baseline": cells[3] if len(cells) >= 4 else "",
            "page_entry": cells[4] if len(cells) >= 5 else "",
            "via_controls": via_controls,
        }
    return out


def parse_region_catalog(text: str) -> dict[str, dict[str, Any]]:
    """Parse the fixed-column region tree embedded in ``surface-model.md``'s
    「布局骨架（机器段）」 (composition axis):

    ``| 区域 id | 所属 surface | 父区域 | 排布 | 优先级 | 角色 | 默认承载 | 扫描序 |``

    Returns ``{region_id: {surf, parent, layout, priority, role, carries,
    scan_order}}``. Header / separator / placeholder / 散文行 are skipped (first
    cell must match ``_REGION_ID_RE``). ``scan_order`` parses to int or ``None``.
    Mirrors ``parse_surface_catalog``: the two parsers scan the same file but key
    off disjoint id regexes (``SURF-`` vs ``R-``), so neither sees the other's rows.
    """
    out: dict[str, dict[str, Any]] = {}
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or not _REGION_ID_RE.match(cells[0]):
            continue

        def cell(i: int) -> str:
            return cells[i] if len(cells) > i else ""

        scan_raw = cell(7)
        try:
            scan: int | None = int(scan_raw)
        except (TypeError, ValueError):
            scan = None
        out[cells[0]] = {
            "surf": cell(1),
            "parent": cell(2) or "root",
            "layout": cell(3).lower(),
            "priority": cell(4).lower(),
            "role": cell(5).lower(),
            "carries": cell(6),
            "scan_order": scan,
        }
    return out


# ---------------------------------------------------------------------------
# surface-model.md machine table (N/A 豁免) — 结构化界面承载豁免
# ---------------------------------------------------------------------------


def parse_na_exemptions(text: str) -> list[dict[str, Any]]:
    """解析 surface-model.md 的「N/A 豁免（机器段）」固定列表：

    ``| PRD 节点 id | 豁免粒度 | 理由 | 责任归属 |``

    复用 ``parse_surface_catalog`` 的逐行 ``|`` split 模式；命中条件：首列匹配
    ``_NA_NODE_RE`` 且 ≥4 列。Header / 分隔行 / 模板 ``{{...}}`` 占位 / 散文行
    （首列不匹配正则）一律跳过。每条产出
    ``{"node", "granularity"(lower), "reason", "owner"}``，保留出现顺序。
    """
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or not _NA_NODE_RE.match(cells[0]) or len(cells) < 4:
            continue
        out.append({
            "node": cells[0],
            "granularity": cells[1].lower(),
            "reason": cells[2],
            "owner": cells[3],
        })
    return out


def _suc_of(token: str) -> str:
    m = re.match(r"(SUC-(?:TF-[A-Z]+-)?[0-9]+)", token)
    return m.group(1) if m else token


def na_exemption_findings(
    *,
    exemptions: list[dict[str, Any]],
    graph: dict[str, Any],
    prd_sucs: set[str],
    prd_flowsteps: set[str],
    prd_beats: set[str],
) -> tuple[set[str], list[dict[str, Any]]]:
    """结构化 N/A 豁免的单一校验入口。返回 ``(exempt_sucs, findings)``：

    - exempt_sucs：所有「合法且非 stale」豁免行的 ``suc_of(node)``（SUC 级集合，
      喂给 ``upstream_completeness_findings`` 的 ``na_sucs``，保持现有 SUC 级豁免语义）。
    - findings：粒度 / 完整性 / 形态自洽 / stale / orphan 校验。
    """
    findings: list[dict[str, Any]] = []
    exempt_sucs: set[str] = set()

    g_suc = graph_suc_ids(graph)
    g_flowsteps = graph_flowstep_ids(graph)
    g_steps = {str(s.get("id")) for s in graph_tables(graph)["steps"] if s.get("id")}

    for ex in exemptions:
        node = str(ex.get("node") or "")
        gran = str(ex.get("granularity") or "")
        reason = str(ex.get("reason") or "")
        owner = str(ex.get("owner") or "")
        suc = _suc_of(node)

        # a. 粒度枚举
        if gran not in _NA_GRANULARITY:
            findings.append(finding(
                "FAIL", "NA_EXEMPTION_BAD_GRANULARITY",
                f"N/A 豁免 {node} 的粒度「{gran}」非法（应为 suc / flowstep / beat）。",
                category="upstream", node=node, granularity=gran,
            ))
            continue
        # b. 理由 / 责任必填
        if not reason or is_placeholder_text(reason) or not owner or is_placeholder_text(owner):
            findings.append(finding(
                "FAIL", "NA_EXEMPTION_INCOMPLETE",
                f"N/A 豁免 {node} 的理由 / 责任归属为空或占位（两列必填）。",
                category="upstream", node=node,
            ))
            continue
        # c. 节点形态与粒度自洽
        has_flow = "-FLOW-" in node
        has_state = "." in node
        mismatch = (
            (gran == "suc" and (has_flow or has_state))
            or (gran == "flowstep" and (not has_flow or has_state))
            or (gran == "beat" and (not has_flow or not has_state))
        )
        if mismatch:
            findings.append(finding(
                "FAIL", "NA_EXEMPTION_NODE_GRANULARITY_MISMATCH",
                f"N/A 豁免节点 {node} 的形态与粒度「{gran}」不符。",
                category="upstream", node=node, granularity=gran,
            ))
            continue
        # d. stale：声明豁免但节点其实已在合并图里
        in_graph = (
            (gran == "suc" and suc in g_suc)
            or (gran == "flowstep" and node in g_flowsteps)
            or (gran == "beat" and node in g_steps)
        )
        if in_graph:
            findings.append(finding(
                "FAIL", "NA_EXEMPTION_STALE",
                f"声明 N/A 豁免但 {node} 实际已落入行为图，移除豁免或下沉为真实节点。",
                category="upstream", node=node, granularity=gran,
            ))
            continue
        # e. orphan：豁免一个 PRD 根本没有的节点
        in_prd = (
            (gran == "suc" and suc in {_suc_of(s) for s in prd_sucs} | prd_sucs)
            or (gran == "flowstep" and node in prd_flowsteps)
            or (gran == "beat" and node in prd_beats)
        )
        if not in_prd:
            findings.append(finding(
                "WARN", "NA_EXEMPTION_UNKNOWN_NODE",
                f"N/A 豁免节点 {node} 不在对应 PRD 集合（拼写 / 陈旧引用）。",
                category="upstream", node=node, granularity=gran,
            ))
        # 合法且非 stale → 贡献其 SUC 到 SUC 级豁免集合
        exempt_sucs.add(suc)

    return exempt_sucs, findings


def prd_fanout_token_findings(
    *,
    ucm_text: str,
    prd_flowsteps: set[str],
    prd_beats: set[str],
) -> list[dict[str, Any]]:
    """PRD 边界 token 完整性门（#2c）：声明「流步骤扇出多结局」的 flow-step 必须有
    ≥1 个 ``SUC-xx-FLOW-xx.state`` 子节点 token，否则散文未 token 化的扇出结局会
    静默漏进对账分母外。仅在 ucm_text 中出现「扇出」关键词且与该 fs 同一行时触发；
    单结局流步骤（无「扇出」字样）不在此列。"""
    findings: list[dict[str, Any]] = []
    # 跳过约定 / 解释段（含「不在此列」「单结局」「凡一个流步骤」等元描述，或引文 `>` 行），
    # 它们解释扇出规约本身、并非对某条 fs 的扇出声明，否则会误命中。
    _NEG_MARKERS = ("不在此列", "单结局", "凡一个", "凡是", "如 `SUC")
    lines = [
        line for line in ucm_text.splitlines()
        if not (line.lstrip().startswith(">") or any(m in line for m in _NEG_MARKERS))
    ]
    for fs in sorted(prd_flowsteps):
        n = len({b for b in prd_beats if b.startswith(fs + ".")})
        declares_fanout = any(("扇出" in line and fs in line) for line in lines)
        if declares_fanout and n == 0:
            findings.append(finding(
                "FAIL", "PRD_FANOUT_BEATS_MISSING",
                f"流步骤 {fs} 声明扇出多结局，但 use-case-model 无任何 {fs}.state 节拍 token，"
                "扇出结局会漏出对账分母。",
                category="upstream", flow_step=fs,
            ))
    return findings


# ---------------------------------------------------------------------------
# Prototype anchor extraction (data-step / data-pagestate / data-via)
# ---------------------------------------------------------------------------

_DATA_ATTR_RE = re.compile(
    r"""data-(step|pagestate|via|testid|region|shell|bizcomp|basecomp)\s*=\s*["']([^"']+)["']""", re.IGNORECASE
)
_SETATTR_RE = re.compile(
    r"""setAttribute\(\s*["']data-(step|pagestate|via|testid|region|shell|bizcomp|basecomp)["']\s*,\s*["']([^"']+)["']""",
    re.IGNORECASE,
)


def extract_prototype_anchors(html: str) -> dict[str, set[str]]:
    """Element-level trace anchors from prototype HTML (literal attrs + setAttribute).
    Returns ``{steps, page_states, vias, testids, regions, shells, bizcomps,
    basecomps}`` (sets). Comma/space separated multi-values are split."""
    out: dict[str, set[str]] = {
        "steps": set(), "page_states": set(), "vias": set(),
        "testids": set(), "regions": set(),
        "shells": set(), "bizcomps": set(), "basecomps": set(),
    }
    key_map = {
        "step": "steps", "pagestate": "page_states", "via": "vias",
        "testid": "testids", "region": "regions",
        "shell": "shells", "bizcomp": "bizcomps", "basecomp": "basecomps",
    }
    for kind, raw in _DATA_ATTR_RE.findall(html) + _SETATTR_RE.findall(html):
        bucket = key_map[kind.lower()]
        for item in re.split(r"[,\s]+", raw):
            item = item.strip()
            if item:
                out[bucket].add(item)
    return out


# ---------------------------------------------------------------------------
# Graph reachability (rooted at ENTRY edges)
# ---------------------------------------------------------------------------


def reachable_step_ids(steps: list[dict[str, Any]], edges: list[dict[str, Any]]) -> set[str]:
    """Step ids reachable from any ``ENTRY`` edge by following edges forward."""
    step_ids = {str(s.get("id")) for s in steps if s.get("id")}
    adj: dict[str, list[str]] = {}
    roots: set[str] = set()
    for e in edges:
        src, dst = str(e.get("from") or ""), str(e.get("to") or "")
        if not dst:
            continue
        if src == ENTRY:
            roots.add(dst)
        else:
            adj.setdefault(src, []).append(dst)
    reachable: set[str] = set()
    frontier = list(roots & step_ids)
    reachable.update(frontier)
    while frontier:
        nxt: list[str] = []
        for node in frontier:
            for child in adj.get(node, []):
                if child in step_ids and child not in reachable:
                    reachable.add(child)
                    nxt.append(child)
        frontier = nxt
    return reachable


# ---------------------------------------------------------------------------
# The single reconcile (behind `harness interaction prototype-check`)
# ---------------------------------------------------------------------------

def _via_surf_control(via: str) -> tuple[str, str]:
    """Split ``edge.via`` ``<surf>/<control>`` → (surf, control). Tolerates missing slash."""
    via = str(via or "").strip()
    if "/" in via:
        surf, _, control = via.partition("/")
        return surf.strip(), control.strip()
    return "", via


def composition_findings(
    *,
    tables: dict[str, list[dict[str, Any]]],
    regions: dict[str, dict[str, Any]],
    surfaces: dict[str, dict[str, Any]],
    proto_anchors: dict[str, set[str]] | None,
    level: str = DEFAULT_COMPOSITION_GATE_LEVEL,
) -> list[dict[str, Any]]:
    """**组成轴门（composition）——区域树 ⊗ 对象落区 ⊗ 原型渲染保真。**

    行为轴管"有哪些态、怎么流转"，本门管"页面怎么排"。它把"控件乱堆"从主观抱怨
    变成程序化 finding：每个可见对象必须落到声明区域、原型必须忠实渲染区域树。

    ``level`` ∈ {fail, warn, off}：``off`` 整门跳过（迁移期）；``fail``/``warn`` 决定
    FAIL 级 code 的实际级别（advisory 的 SCAN_ORDER_MISSING / REGION_DEAD 恒为 WARN）。

    **增量采用边界**：只对**已声明区域树的 surface** 强制对象落区——某 surface 完全没有
    区域 → 只报一条 ``LAYOUT_REGION_MISSING``，不对其对象级联 ``OBJECT_UNPLACED``（避免
    迁移噪声；采用即闭合）。``proto_anchors=None`` → 原型缺席，跳过渲染保真类。
    """
    lvl = str(level or "").strip().lower()
    if lvl == "off":
        return []
    gate = "FAIL" if lvl == "fail" else "WARN"
    findings: list[dict[str, Any]] = []
    page_states = tables["page_states"]
    region_ids = set(regions)

    # ---- 区域树自身合法性 ----
    for rid, r in regions.items():
        surf = str(r.get("surf") or "")
        if surf and surf not in surfaces:
            findings.append(finding(
                gate, "REGION_SURF_UNKNOWN",
                f"区域 {rid} 的 surf「{surf}」不在 surface 目录。",
                category="composition", region=rid, surf=surf,
            ))
        parent = str(r.get("parent") or "root")
        if parent != "root" and parent not in region_ids:
            findings.append(finding(
                gate, "REGION_PARENT_UNRESOLVED",
                f"区域 {rid} 的父区域「{parent}」未声明。",
                category="composition", region=rid, parent=parent,
            ))
        for field, allowed in (("layout", _REGION_LAYOUTS), ("priority", _REGION_PRIORITIES), ("role", _REGION_ROLES)):
            val = str(r.get(field) or "")
            if val and val not in allowed:
                findings.append(finding(
                    gate, "REGION_BAD_ENUM",
                    f"区域 {rid} 的 {field}「{val}」非法。",
                    category="composition", region=rid, field=field, value=val,
                ))

    # ---- surface 有 page_state 必须有区域树（未采用的 surface 只报这一条，不级联） ----
    regions_by_surf: dict[str, set[str]] = {}
    for rid, r in regions.items():
        regions_by_surf.setdefault(str(r.get("surf") or ""), set()).add(rid)
    adopted_surfs = set(regions_by_surf)
    surfs_with_ps = {str(p.get("surf") or "") for p in page_states if p.get("surf")}
    for surf in sorted(surfs_with_ps - adopted_surfs):
        findings.append(finding(
            gate, "LAYOUT_REGION_MISSING",
            f"surface {surf} 有 page_state 却无布局骨架（区域树）：写 HTML 会变成控件乱堆。",
            category="composition", surf=surf,
        ))

    # ---- 对象 / placement 落区（仅对已采用区域树的 surface 强制） ----
    referenced: set[str] = set()

    def _place(pid: str, surf: str, region: str, label: str) -> None:
        region = str(region or "").strip()
        if not region or is_placeholder_text(region):
            findings.append(finding(
                gate, "OBJECT_UNPLACED",
                f"页面态 {pid} 的 {label} 未落到任何区域（region 缺失）= 控件无家可归。",
                category="composition", page_state=pid, item=label,
            ))
            return
        referenced.add(region)
        if region not in region_ids:
            findings.append(finding(
                gate, "OBJECT_REGION_UNKNOWN",
                f"页面态 {pid} 的 {label} 的 region「{region}」未在区域树声明。",
                category="composition", page_state=pid, region=region,
            ))
        elif regions[region].get("surf") and str(regions[region]["surf"]) != surf:
            findings.append(finding(
                gate, "REGION_SURF_MISMATCH",
                f"页面态 {pid}（surf={surf}）的 {label} 落到了别的 surface 的区域「{region}」。",
                category="composition", page_state=pid, region=region, surf=surf,
            ))

    for p in page_states:
        surf = str(p.get("surf") or "")
        pid = str(p.get("id") or "?")
        if surf not in adopted_surfs:
            continue  # 未采用 surface 已由 LAYOUT_REGION_MISSING 覆盖，不级联噪声
        for o in (p.get("objects") or []):
            if not isinstance(o, dict):
                continue
            region = str(o.get("region") or "").strip()
            if not (o.get("fields") or []):  # 缺位态对象（fields 空）可不落区
                if region:
                    referenced.add(region)
                continue
            _place(pid, surf, region, f"对象 {o.get('obj') or '?'}")
        for pl in (p.get("placements") or []):
            if not isinstance(pl, dict):
                continue
            _place(pid, surf, str(pl.get("region") or ""), f"placement「{pl.get('ref') or pl.get('kind') or '?'}」")

    # ---- 扫描序（同父唯一）+ 死区域：恒 WARN ----
    siblings: dict[tuple[str, str], list[tuple[str, Any]]] = {}
    for rid, r in regions.items():
        siblings.setdefault((str(r.get("surf") or ""), str(r.get("parent") or "root")), []).append(
            (rid, r.get("scan_order"))
        )
    for members in siblings.values():
        by_order: dict[int, list[str]] = {}
        for rid, o in members:
            if o is None:
                findings.append(finding(
                    "WARN", "SCAN_ORDER_MISSING",
                    f"区域 {rid} 缺扫描序（同父区域需唯一扫描序，编码主扫描动线）。",
                    category="composition", region=rid,
                ))
            else:
                by_order.setdefault(int(o), []).append(rid)
        for order, rids in by_order.items():
            if len(rids) > 1:
                for rid in rids:
                    findings.append(finding(
                        "WARN", "SCAN_ORDER_MISSING",
                        f"区域 {rid} 与同父区域扫描序重复（{order}）。",
                        category="composition", region=rid,
                    ))
    for rid in sorted(region_ids - referenced):
        findings.append(finding(
            "WARN", "REGION_DEAD",
            f"区域 {rid} 全程不承载任何对象 / placement（死区域）。",
            category="composition", region=rid,
        ))

    # ---- 原型渲染保真（与四方锚点同构） ----
    if proto_anchors is not None:
        proto_regions = proto_anchors.get("regions", set())
        for rid in sorted(referenced & region_ids):
            if rid not in proto_regions:
                findings.append(finding(
                    gate, "REGION_NOT_RENDERED",
                    f"区域 {rid} 承载内容但原型无 data-region 元素。",
                    category="composition", region=rid,
                ))
        for rid in sorted(proto_regions - region_ids):
            findings.append(finding(
                gate, "REGION_ANCHOR_DANGLING",
                f"原型 data-region「{rid}」未在区域树声明：dangling / ID 漂移。",
                category="composition", region=rid,
            ))

    return findings


# ---------------------------------------------------------------------------
# Design system catalogs (project-knowledge/product/design-system/*.md) + gate
# ---------------------------------------------------------------------------

_BC_ID_RE = re.compile(r"^BC-[a-z0-9][a-z0-9-]*$")
_UC_ID_RE = re.compile(r"^UC-[a-z0-9][a-z0-9-]*$")
_SHELL_ID_RE = re.compile(r"^SHELL-[A-Za-z0-9][A-Za-z0-9_-]*$")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def design_system_dir(root: Path) -> Path:
    return root / "project-knowledge" / "product" / "design-system"


def _parse_id_table(text: str, id_re: re.Pattern[str]) -> list[list[str]]:
    """Generic machine-section row parser: strip HTML comments first (so commented
    example rows never parse), then yield ``|``-split cell lists whose first cell
    matches ``id_re``. ``{{…}}`` placeholder rows don't match the id regex → skipped.
    Mirrors the surface-model machine-section convention."""
    rows: list[list[str]] = []
    for line in _HTML_COMMENT_RE.sub("", text).splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and id_re.match(cells[0]):
            rows.append(cells)
    return rows


def parse_base_components(text: str) -> dict[str, dict[str, Any]]:
    """Parse base-components.md machine section:
    ``| BC-id | 名称 | 构成 | 变体 | 状态矩阵 | token | 实现路径 | source | status |``."""
    out: dict[str, dict[str, Any]] = {}
    for c in _parse_id_table(text, _BC_ID_RE):
        out[c[0]] = {"name": c[1] if len(c) > 1 else "", "states": c[4] if len(c) > 4 else ""}
    return out


def parse_business_components(text: str) -> dict[str, dict[str, Any]]:
    """Parse business-components.md machine section:
    ``| UC-id | 名称 | SUC | OBJ | 组成(BC) | 状态矩阵 | 数据 | 实现路径 | source | status |``.
    ``composed_of`` = the BC-* ids in the 组成 column (split on +/,/whitespace)."""
    out: dict[str, dict[str, Any]] = {}
    for c in _parse_id_table(text, _UC_ID_RE):
        def col(i: int) -> str:
            return c[i] if len(c) > i else ""
        composed = {t for t in re.split(r"[+,、\s]+", col(4)) if _BC_ID_RE.match(t)}
        out[c[0]] = {
            "suc": col(2), "obj": col(3), "composed_of": composed, "states": col(5),
        }
    return out


def parse_shell_catalog(text: str) -> dict[str, dict[str, Any]]:
    """Parse interaction-framework.md「应用外壳（机器段）」: ``| SHELL-id | 角色 | 承载 | … |``."""
    out: dict[str, dict[str, Any]] = {}
    for c in _parse_id_table(text, _SHELL_ID_RE):
        out[c[0]] = {"role": c[1] if len(c) > 1 else ""}
    return out


def load_design_system_catalogs(root: Path) -> dict[str, dict[str, Any]]:
    """Load the three gated design-system catalogs from project-knowledge. Empty
    dicts when files / sections are absent (→ project hasn't adopted → gate skips)."""
    ds = design_system_dir(root)
    return {
        "base": parse_base_components(read_text_if_exists(ds / "base-components.md")),
        "business": parse_business_components(read_text_if_exists(ds / "business-components.md")),
        "shell": parse_shell_catalog(read_text_if_exists(ds / "interaction-framework.md")),
    }


def design_system_findings(
    *,
    tables: dict[str, list[dict[str, Any]]],
    catalogs: dict[str, dict[str, Any]],
    proto_anchors: dict[str, set[str]] | None,
    prd_sucs: set[str] | None = None,
    prd_objs: set[str] | None = None,
    level: str = DEFAULT_DESIGN_SYSTEM_GATE_LEVEL,
) -> list[dict[str, Any]]:
    """**设计系统门（design_system）—— 从组件库装配（R9）。**

    保证原型从设计系统组件库装配、业务组件可追溯，而非另堆裸控件。``level`` ∈
    {fail, warn, off}：``off`` 跳过；``fail``/``warn`` 决定 FAIL 级 code 实际级别
    （advisory 的 OBJECT_NO_BIZCOMP / BIZCOMP_STATE_MISSING 恒 WARN）。

    **非破坏边界 + 增量采用**：组件库目录为空（未采用）→ 该类检查跳过；只对**已声明**
    的目录强制（业务组件目录非空才查业务组件、有 data-bizcomp 锚点才查 dangling）。
    """
    lvl = str(level or "").strip().lower()
    if lvl == "off":
        return []
    gate = "FAIL" if lvl == "fail" else "WARN"
    findings: list[dict[str, Any]] = []
    base = catalogs.get("base") or {}
    business = catalogs.get("business") or {}
    shell = catalogs.get("shell") or {}
    proto = proto_anchors or {}
    prd_sucs = prd_sucs or set()
    prd_objs = prd_objs or set()

    page_states = tables["page_states"]
    obj_bizcomps = {
        str(o.get("bizcomp")).strip()
        for p in page_states for o in (p.get("objects") or [])
        if isinstance(o, dict) and o.get("bizcomp")
    }
    adopted = bool(business or shell or proto.get("bizcomps") or proto.get("shells") or obj_bizcomps)
    if not adopted:
        return []  # 未采用设计系统组件库 → 门不触发

    # ---- 业务组件目录完整性（纯目录） ----
    for uc, meta in business.items():
        for bc in sorted(meta.get("composed_of") or set()):
            if bc not in base:
                findings.append(finding(
                    gate, "BIZCOMP_BASE_UNRESOLVED",
                    f"业务组件 {uc} 的组成基础组件 {bc} 不在 base-components 目录。",
                    category="design_system", bizcomp=uc, base_component=bc,
                ))
        suc = str(meta.get("suc") or "").strip()
        if suc and not is_placeholder_text(suc) and prd_sucs and suc not in prd_sucs:
            findings.append(finding(
                gate, "BIZCOMP_BINDING_DANGLING",
                f"业务组件 {uc} 绑定的 {suc} 不在上游用例（traces_to 悬空）。",
                category="design_system", bizcomp=uc, suc=suc,
            ))
        obj = str(meta.get("obj") or "").strip()
        if obj and not is_placeholder_text(obj) and prd_objs and obj not in prd_objs:
            findings.append(finding(
                gate, "BIZCOMP_BINDING_DANGLING",
                f"业务组件 {uc} 绑定的 {obj} 不在上游业务对象（traces_to 悬空）。",
                category="design_system", bizcomp=uc, obj=obj,
            ))
        if not str(meta.get("states") or "").strip() or is_placeholder_text(meta.get("states")):
            findings.append(finding(
                "WARN", "BIZCOMP_STATE_MISSING",
                f"业务组件 {uc} 未声明状态矩阵（应列全 default/loading/empty/error… 不只 happy path）。",
                category="design_system", bizcomp=uc,
            ))

    # ---- 对象 → 业务组件绑定（behavior-graph objects[].bizcomp） ----
    for p in page_states:
        pid = str(p.get("id") or "?")
        for o in (p.get("objects") or []):
            if not isinstance(o, dict):
                continue
            bc = str(o.get("bizcomp") or "").strip()
            if bc:
                if business and bc not in business:
                    findings.append(finding(
                        gate, "OBJECT_BIZCOMP_UNKNOWN",
                        f"页面态 {pid} 的对象 {o.get('obj') or '?'} 引用业务组件 {bc}，但其不在 business-components 目录。",
                        category="design_system", page_state=pid, bizcomp=bc,
                    ))
            elif business and (o.get("fields") or []):
                findings.append(finding(
                    "WARN", "OBJECT_NO_BIZCOMP",
                    f"页面态 {pid} 的可见对象 {o.get('obj') or '?'} 未经业务组件承载（项目已采用业务组件库，建议用 objects[].bizcomp 标明）。",
                    category="design_system", page_state=pid, obj=str(o.get("obj") or ""),
                ))

    # ---- 原型锚点 dangling（仅对已声明目录强制） ----
    if proto_anchors is not None:
        if business:
            for bc in sorted(proto.get("bizcomps", set()) - set(business)):
                findings.append(finding(
                    gate, "BIZCOMP_ANCHOR_DANGLING",
                    f"原型 data-bizcomp「{bc}」未在 business-components 目录声明。",
                    category="design_system", bizcomp=bc,
                ))
        if shell:
            for sh in sorted(proto.get("shells", set()) - set(shell)):
                findings.append(finding(
                    gate, "SHELL_ANCHOR_DANGLING",
                    f"原型 data-shell「{sh}」未在 interaction-framework 应用外壳目录声明。",
                    category="design_system", shell=sh,
                ))

    return findings


def reconcile_findings(
    *,
    tables: dict[str, list[dict[str, Any]]],
    surfaces: dict[str, dict[str, Any]],
    proto_anchors: dict[str, set[str]] | None,
    manifest_covers: dict[str, set[str]] | None = None,
    manifest_viewports: set[str] | None = None,
    prd_abstract_steps: set[str] | None = None,
    valid_step_universe: set[str] | None = None,
    valid_pagestate_universe: set[str] | None = None,
    reachability_level: str = DEFAULT_REACHABILITY_GATE_LEVEL,
    regions: dict[str, dict[str, Any]] | None = None,
    composition_level: str = DEFAULT_COMPOSITION_GATE_LEVEL,
) -> list[dict[str, Any]]:
    """One pass over the behavior graph + prototype + surface catalog producing
    category-tagged findings. ``proto_anchors=None`` → prototype absent: anchor /
    coverage / locator checks are skipped (the caller marks prototype_absent).
    """
    findings: list[dict[str, Any]] = []
    page_states = tables["page_states"]
    steps = tables["steps"]
    edges = tables["edges"]
    flows = tables["flows"]

    ps_ids = {str(p.get("id")) for p in page_states if p.get("id")}
    step_ids = {str(s.get("id")) for s in steps if s.get("id")}
    manifest_covers = manifest_covers or {}
    manifest_viewports = manifest_viewports or set()

    # ---- graph (纯图) ----
    for s in steps:
        sid = str(s.get("id") or "?")
        ps = str(s.get("page_state") or "")
        if not ps or ps not in ps_ids:
            findings.append(finding(
                "FAIL", "GRAPH_STEP_PAGESTATE_UNRESOLVED",
                f"拍 {sid} 的 page_state「{ps}」未在 page_states 声明。",
                category="graph", step=sid, page_state=ps,
            ))
    for p in page_states:
        pid = str(p.get("id") or "?")
        surf = str(p.get("surf") or "")
        if surf not in surfaces:
            findings.append(finding(
                "FAIL", "GRAPH_PAGESTATE_SURF_UNKNOWN",
                f"页面态 {pid} 的 surf「{surf}」不在 surface-model 的 surface 目录里。",
                category="graph", page_state=pid, surf=surf,
            ))
    for i, e in enumerate(edges):
        src, dst = str(e.get("from") or ""), str(e.get("to") or "")
        ref = f"{src or '∅'}→{dst or '∅'}"
        if (src != ENTRY and src not in step_ids) or dst not in step_ids:
            findings.append(finding(
                "FAIL", "GRAPH_EDGE_ENDPOINT_UNRESOLVED",
                f"边 {ref} 的端点未解析到 step（或 ENTRY）。",
                category="graph", edge=ref,
            ))
        kind = str(e.get("kind") or "")
        if kind not in {"action", "system_event"}:
            findings.append(finding(
                "FAIL", "GRAPH_EDGE_MALFORMED",
                f"边 {ref} 的 kind「{kind}」非法（应为 action / system_event）。",
                category="graph", edge=ref,
            ))
        if kind == "system_event":
            via = str(e.get("via") or "")
            if is_placeholder_text(via):
                findings.append(finding(
                    "FAIL", "GRAPH_SYSTEM_EVENT_MISSING_VIA",
                    f"系统事件边 {ref} 缺 via（必须声明诱发它的产品输入控件）。",
                    category="graph", edge=ref,
                ))
            else:
                surf, control = _via_surf_control(via)
                cat = surfaces.get(surf, {})
                if surf not in surfaces or control not in cat.get("via_controls", set()):
                    findings.append(finding(
                        "FAIL", "EDGE_VIA_UNDECLARED",
                        f"边 {ref} 的 via「{via}」未在 surface「{surf}」的 via 控件清单声明。",
                        category="graph", edge=ref, via=via,
                    ))
    for f in flows:
        fid = str(f.get("id") or "?")
        path = f.get("path") if isinstance(f.get("path"), list) else []
        for node in path:
            if str(node) not in step_ids:
                findings.append(finding(
                    "FAIL", "GRAPH_FLOW_PATH_UNRESOLVED",
                    f"flow {fid} 的 path 含未声明 step「{node}」。",
                    category="graph", flow=fid, step=str(node),
                ))

    # ---- reachability (纯图) ----
    reachable = reachable_step_ids(steps, edges)
    ps_to_steps: dict[str, list[str]] = {}
    for s in steps:
        ps_to_steps.setdefault(str(s.get("page_state") or ""), []).append(str(s.get("id") or "?"))
    for p in page_states:
        pid = str(p.get("id") or "?")
        owners = ps_to_steps.get(pid, [])
        if not owners or not any(o in reachable for o in owners):
            _lvl = str(reachability_level or "").strip().lower()
            level = "FAIL" if _lvl != "warn" else "WARN"
            findings.append(finding(
                level, "PAGESTATE_UNREACHABLE",
                f"页面态 {pid} 无可从 ENTRY 到达的拍引用它（孤儿态 / 仅 teleport 可达）。",
                category="reachability", page_state=pid,
            ))
    edge_index = {(str(e.get("from")), str(e.get("to"))): e for e in edges}
    for f in flows:
        fid = str(f.get("id") or "?")
        path = [str(n) for n in (f.get("path") if isinstance(f.get("path"), list) else [])]
        for a, b in zip(path, path[1:]):
            e = edge_index.get((a, b))
            if e is None:
                findings.append(finding(
                    "FAIL", "FLOW_SEQUENCE_BROKEN",
                    f"flow {fid} 的相邻拍 {a}→{b} 没有对应 edge。",
                    category="reachability", flow=fid, edge=f"{a}→{b}",
                ))
            elif str(e.get("kind")) not in {"action", "system_event"}:
                findings.append(finding(
                    "FAIL", "FLOW_EDGE_NOT_OPERABLE",
                    f"flow {fid} 的边 {a}→{b} 非可操作触发。",
                    category="reachability", flow=fid, edge=f"{a}→{b}",
                ))

    # ---- upstream (纯图：PRD 抽象 step 对账，与原型无关) ----
    for pid in sorted((prd_abstract_steps or set()) - step_ids):
        findings.append(finding(
            "WARN", "UPSTREAM_PRD_STEP_UNBOUND",
            f"PRD 结局节点 {pid} 未落入 behavior-graph；若非界面承载请在 surface-model 写明。",
            category="upstream", step=pid,
        ))

    # ---- composition (组成轴：区域树 ⊗ 对象落区 ⊗ 渲染保真) ----
    # regions=None → 调用方未提供区域目录（向后兼容：旧调用不触发组成门）。
    # 组成门自身处理 proto_anchors=None（仅跳过渲染保真，纯图部分照常）。
    if regions is not None:
        findings.extend(composition_findings(
            tables=tables, regions=regions, surfaces=surfaces,
            proto_anchors=proto_anchors, level=composition_level,
        ))

    # ---- prototype-dependent (anchor / coverage / locator) ----
    if proto_anchors is None:
        findings.append(finding(
            "WARN", "PROTOTYPE_ABSENT",
            "原型未建：anchor / coverage / locator 类检查跳过（pending）。",
            category="anchor",
        ))
        return findings

    proto_steps = proto_anchors.get("steps", set())
    proto_ps = proto_anchors.get("page_states", set())
    proto_vias = proto_anchors.get("vias", set())
    proto_testids = proto_anchors.get("testids", set())
    valid_step_universe = (valid_step_universe or set()) | step_ids
    valid_pagestate_universe = (valid_pagestate_universe or set()) | ps_ids

    # anchor: 四方对账
    for sid in sorted(step_ids - proto_steps):
        findings.append(finding(
            "FAIL", "TRACE_STEP_NOT_ANCHORED",
            f"拍 {sid} 在 graph 声明，但原型无 data-step 锚点。",
            category="anchor", step=sid,
        ))
    for sid in sorted(proto_steps - valid_step_universe):
        findings.append(finding(
            "FAIL", "TRACE_ANCHOR_STEP_DANGLING",
            f"原型 data-step「{sid}」未在 graph 声明：dangling / ID 漂移。",
            category="anchor", step=sid,
        ))
    for pid in sorted(ps_ids - proto_ps):
        findings.append(finding(
            "FAIL", "TRACE_PAGESTATE_NOT_ANCHORED",
            f"页面态 {pid} 在 graph 声明，但原型无 data-pagestate 锚点。",
            category="anchor", page_state=pid,
        ))
    for pid in sorted(proto_ps - valid_pagestate_universe):
        findings.append(finding(
            "FAIL", "TRACE_ANCHOR_PAGESTATE_DANGLING",
            f"原型 data-pagestate「{pid}」未在 graph 声明。",
            category="anchor", page_state=pid,
        ))
    declared_vias = {str(e.get("via")).strip() for e in edges
                     if str(e.get("kind")) == "system_event" and not is_placeholder_text(e.get("via"))}
    for via in sorted(declared_vias - proto_vias):
        findings.append(finding(
            "FAIL", "EDGE_VIA_NOT_ANCHORED",
            f"via「{via}」在 graph 声明，但原型无 data-via 控件元素。",
            category="anchor", via=via,
        ))

    # coverage: 派生分母
    covered_steps = proto_steps | manifest_covers.get("steps", set())
    covered_ps = proto_ps | manifest_covers.get("page_states", set())
    for sid in sorted(step_ids - covered_steps):
        findings.append(finding(
            "FAIL", "VISUAL_STEP_COVERAGE_MISSING",
            f"必覆盖拍 {sid} 无锚点覆盖。",
            category="coverage", step=sid,
        ))
    for pid in sorted(ps_ids - covered_ps):
        findings.append(finding(
            "FAIL", "VISUAL_PAGESTATE_COVERAGE_MISSING",
            f"必覆盖页面态 {pid} 无锚点覆盖。",
            category="coverage", page_state=pid,
        ))
    lowered_viewports = {v.lower() for v in manifest_viewports}
    for viewport in ("desktop", "mobile"):
        if viewport not in lowered_viewports:
            findings.append(finding(
                "FAIL", "VISUAL_VIEWPORT_COVERAGE_MISSING",
                f"manifest 未覆盖 {viewport} 视口。",
                category="coverage", viewport=viewport,
            ))

    # locator: e2e_obligation 边须有 data-testid
    for e in edges:
        if not e.get("e2e_obligation"):
            continue
        src, dst = str(e.get("from") or ""), str(e.get("to") or "")
        ref = f"{src or '∅'}→{dst or '∅'}"
        testid = str(e.get("testid") or "")
        if is_placeholder_text(testid):
            findings.append(finding(
                "WARN", "LOCATOR_MISSING_FOR_E2E_EDGE",
                f"E2E 种子边 {ref} 未声明 testid（建议在 edge.testid 标定位器）。",
                category="locator", edge=ref,
            ))
        elif testid not in proto_testids:
            findings.append(finding(
                "FAIL", "LOCATOR_MISSING_FOR_E2E_EDGE",
                f"E2E 种子边 {ref} 的 testid「{testid}」在原型中无对应 data-testid。",
                category="locator", edge=ref, testid=testid,
            ))

    return findings


# ---------------------------------------------------------------------------
# Walkthrough projection (drives the cockpit shell via generated walkthrough.js)
# ---------------------------------------------------------------------------


def walkthrough_index(
    graph: dict[str, Any],
    focus_sucs: set[str] | None = None,
    suc_titles: dict[str, str] | None = None,
) -> dict[str, Any]:
    """SUC → flow → step walkthrough index for the cockpit. Three-level only
    (SUC / flow / step). When ``focus_sucs`` is given, each SUC is tagged
    ``focus=True`` (本任务) if its id is in the set, else ``focus=False`` (项目已有),
    so the demo player groups 本任务 / 项目已有. ``suc_titles`` attaches a human
    ``title`` per SUC (shown in the player), keyed by suc id."""
    suc_titles = suc_titles or {}
    t = graph_tables(graph)
    ps_by_id = {str(p.get("id")): p for p in t["page_states"] if p.get("id")}
    step_by_id = {str(s.get("id")): s for s in t["steps"] if s.get("id")}
    edge_to = {(str(e.get("from")), str(e.get("to"))): e for e in t["edges"]}

    by_suc: dict[str, list[dict[str, Any]]] = {}
    for f in t["flows"]:
        suc = str(f.get("suc") or "")
        fid = str(f.get("id") or "")
        path = [str(n) for n in (f.get("path") if isinstance(f.get("path"), list) else [])]
        nodes: list[dict[str, Any]] = []
        prev = ENTRY
        for sid in path:
            step = step_by_id.get(sid, {})
            ps = ps_by_id.get(str(step.get("page_state") or ""), {})
            edge = edge_to.get((prev, sid), {})
            nodes.append({
                "step": sid,
                "page_state": str(step.get("page_state") or ""),
                "page_entry": ps.get("page_entry"),
                "anchor_root": ps.get("anchor_root"),
                "state": ps.get("state"),
                "trigger": {"kind": edge.get("kind"), "desc": edge.get("desc"), "via": edge.get("via")},
                "acceptance_refs": step.get("acceptance_refs", []),
            })
            prev = sid
        by_suc.setdefault(suc, []).append({"flow": fid, "rationale": f.get("rationale"), "nodes": nodes})
    return {"by_suc": [
        {"suc": s, "title": suc_titles.get(s, ""),
         "focus": (focus_sucs is None or s in focus_sucs), "flows": by_suc[s]}
        for s in sorted(by_suc)
    ]}


# ---------------------------------------------------------------------------
# Three generated views (markdown). All derived from the graph; never hand-edited.
# ---------------------------------------------------------------------------

_GENERATED_HEADER = (
    "<!-- GENERATED by `harness interaction project` — do not edit. "
    "真相源 = interaction-spec/behavior-graph.yaml -->\n"
)


def _trigger_label(edge: dict[str, Any]) -> str:
    if not edge:
        return "（入口）"
    kind = str(edge.get("kind") or "")
    desc = str(edge.get("desc") or "")
    via = str(edge.get("via") or "")
    label = f"{desc or kind}"
    if kind == "system_event" and via and via.lower() not in {"none", "null"}:
        label += f"（via {via}）"
    return label


def render_by_suc_view(graph: dict[str, Any]) -> str:
    """走查视图：SUC → flow → step 序列。供人走查 / 驾驶舱导航对照。"""
    wt = walkthrough_index(graph)
    lines = [_GENERATED_HEADER, "# 走查视图（by SUC）\n"]
    if not wt["by_suc"]:
        lines.append("_行为图为空。_\n")
    for suc_block in wt["by_suc"]:
        lines.append(f"\n## {suc_block['suc']}\n")
        for flow in suc_block["flows"]:
            lines.append(f"\n### flow：{flow['flow']}")
            if flow.get("rationale"):
                lines.append(f"> {flow['rationale']}")
            lines.append("\n| 序 | 拍 | 页面态 | 到达触发 | 验收追溯 |")
            lines.append("|----|----|--------|----------|----------|")
            for i, node in enumerate(flow["nodes"], start=1):
                refs = ", ".join(str(r) for r in (node.get("acceptance_refs") or [])) or "—"
                pe = node.get("page_entry") or "—"
                lines.append(
                    f"| {i} | `{node['step']}` | `{node['page_state']}`（{pe}） | "
                    f"{_trigger_label(node.get('trigger') or {})} | {refs} |"
                )
    return "\n".join(lines) + "\n"


def render_by_surface_view(graph: dict[str, Any]) -> str:
    """建页视图：每个 surface 要做哪些 page-state（态块）。供 coding agent 建页。"""
    t = graph_tables(graph)
    steps_by_ps: dict[str, list[str]] = {}
    for s in t["steps"]:
        steps_by_ps.setdefault(str(s.get("page_state") or ""), []).append(str(s.get("id") or "?"))
    by_surf: dict[str, list[dict[str, Any]]] = {}
    for p in t["page_states"]:
        by_surf.setdefault(str(p.get("surf") or "?"), []).append(p)

    lines = [_GENERATED_HEADER, "# 建页视图（by surface）\n"]
    if not by_surf:
        lines.append("_行为图为空。_\n")
    for surf in sorted(by_surf):
        lines.append(f"\n## {surf}\n")
        lines.append("| 页面态 | 载体 | 状态 | 业务对象 + 字段 + 状态 | 锚点容器 | 关联拍 |")
        lines.append("|--------|------|------|------------------------|----------|--------|")
        for p in by_surf[surf]:
            objs = "; ".join(
                f"{o.get('obj')}:{','.join(o.get('fields') or []) or '—'}/{o.get('state') or '—'}"
                for o in (p.get("objects") or [])
                if isinstance(o, dict)
            ) or "—"
            owners = ", ".join(f"`{x}`" for x in steps_by_ps.get(str(p.get("id")), [])) or "—"
            lines.append(
                f"| `{p.get('id')}` | {p.get('carrier') or '—'}（{p.get('page_entry') or '—'}） | "
                f"{p.get('state') or '—'} | {objs} | `{p.get('anchor_root') or '—'}` | {owners} |"
            )
    return "\n".join(lines) + "\n"


def render_by_object_view(graph: dict[str, Any]) -> str:
    """BO 状态视图：每个业务对象在哪些 page-state 以什么状态出现。供数据/状态建模。"""
    t = graph_tables(graph)
    by_obj: dict[str, list[dict[str, Any]]] = {}
    for p in t["page_states"]:
        for o in (p.get("objects") or []):
            if isinstance(o, dict) and o.get("obj"):
                by_obj.setdefault(str(o["obj"]), []).append({
                    "page_state": str(p.get("id")),
                    "surf": p.get("surf"),
                    "state": o.get("state"),
                    "fields": o.get("fields") or [],
                    "state_owner": p.get("state_owner"),
                })
    lines = [_GENERATED_HEADER, "# 业务对象状态视图（by object）\n"]
    if not by_obj:
        lines.append("_行为图未声明业务对象。_\n")
    for obj in sorted(by_obj):
        lines.append(f"\n## {obj}\n")
        lines.append("| 出现的页面态 | surface | 状态 | 字段 | 状态机 |")
        lines.append("|--------------|---------|------|------|--------|")
        for row in by_obj[obj]:
            flds = ",".join(row["fields"]) or "—"
            lines.append(
                f"| `{row['page_state']}` | {row['surf'] or '—'} | {row['state'] or '—'} | "
                f"{flds} | {row['state_owner'] or '—'} |"
            )
    return "\n".join(lines) + "\n"


def resolve_feedback_from_graph(
    graph: dict[str, Any],
    *,
    surface: str = "",
    suc: str = "",
    obj: str = "",
    step: str = "",
) -> dict[str, Any]:
    """Forward-navigation from a prototype anchor (SURF / SUC / OBJ / step) to the
    page-state(s) that carry it, with page_entry / anchor_root for deep-linking.
    Replaces the old surface_bindings-based resolver."""
    t = graph_tables(graph)
    ps_by_id = {str(p.get("id")): p for p in t["page_states"] if p.get("id")}
    matched_ps: dict[str, dict[str, Any]] = {}

    def add(pid: str) -> None:
        p = ps_by_id.get(pid)
        if p:
            matched_ps[pid] = p

    for s in t["steps"]:
        sid = str(s.get("id") or "")
        ps = str(s.get("page_state") or "")
        if step and sid == step:
            add(ps)
        if suc and str(s.get("suc") or "") == suc:
            add(ps)
    for pid, p in ps_by_id.items():
        if surface and str(p.get("surf") or "") == surface:
            add(pid)
        if obj and any(str(o.get("obj")) == obj for o in (p.get("objects") or []) if isinstance(o, dict)):
            add(pid)

    forward_nav = [
        {
            "page_state": pid,
            "surf": p.get("surf"),
            "page_entry": p.get("page_entry"),
            "anchor_root": p.get("anchor_root"),
        }
        for pid, p in sorted(matched_ps.items())
    ]
    return {"forward_nav": forward_nav}


def walkthrough_js(
    graph: dict[str, Any],
    focus_sucs: set[str] | None = None,
    suc_titles: dict[str, str] | None = None,
) -> str:
    """演示导览播放器数据：window.__HARNESS_WALKTHROUGH__ = {...}（shell 以 <script> 加载）。
    ``focus_sucs`` 给出本任务的 SUC id 用于分组；``suc_titles`` 给出每个 SUC 的描述。"""
    import json

    payload = walkthrough_index(graph, focus_sucs=focus_sucs, suc_titles=suc_titles)
    return (
        "window.__HARNESS_WALKTHROUGH__ = "
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + ";\n"
    )


def flow_suc_ids(graph: dict[str, Any]) -> set[str]:
    """SUC ids that appear in a graph's flows (used to tag 本任务 focus)."""
    return {str(f.get("suc")) for f in graph_tables(graph)["flows"] if f.get("suc")}


def graph_suc_ids(graph: dict[str, Any]) -> set[str]:
    """All SUC ids the graph realizes (from flows.suc + steps.suc)."""
    t = graph_tables(graph)
    out = {str(f.get("suc")) for f in t["flows"] if f.get("suc")}
    out |= {str(s.get("suc")) for s in t["steps"] if s.get("suc")}
    return out


_FLOWSTEP_PREFIX_RE = re.compile(r"^(SUC-(?:TF-[A-Z]+-)?[0-9]+-FLOW-[0-9]+)\.")


def graph_flowstep_ids(graph: dict[str, Any]) -> set[str]:
    """Flow-step ids the graph covers — from explicit ``steps.from_flow_step`` AND
    derived from each step id's prefix (a step ``SUC-01-FLOW-01.empty`` inherently
    covers flow-step ``SUC-01-FLOW-01``, so ``from_flow_step`` is optional)."""
    out: set[str] = set()
    for s in graph_tables(graph)["steps"]:
        if s.get("from_flow_step"):
            out.add(str(s["from_flow_step"]))
        m = _FLOWSTEP_PREFIX_RE.match(str(s.get("id") or ""))
        if m:
            out.add(m.group(1))
    return out


def upstream_completeness_findings(
    *,
    graph: dict[str, Any],
    prd_sucs: set[str],
    prd_flowsteps: set[str],
    prd_beats: set[str],
    registry_sucs: set[str],
    na_sucs: set[str] | None = None,
) -> list[dict[str, Any]]:
    """**Comprehensive upstream→graph completeness gate (FAIL).** Ensures the graph
    (the lint denominator) is itself complete vs the upstream inventory, so a PASS
    genuinely means "every SUC / flow-step / 节拍 the project requires is in the graph
    (and therefore checked against the prototype)". Without this, a SUC/flow dropped
    from the graph would silently PASS.

    N/A escape: a SUC listed in ``na_sucs`` (justified non-UI in surface-model) is
    exempt from the SUC / its-flowsteps / its-beats requirements.
    """
    g_suc = graph_suc_ids(graph)
    g_steps = {str(s.get("id")) for s in graph_tables(graph)["steps"] if s.get("id")}
    g_flowsteps = graph_flowstep_ids(graph)
    na = na_sucs or set()

    def suc_of(token: str) -> str:
        m = re.match(r"(SUC-(?:TF-[A-Z]+-)?[0-9]+)", token)
        return m.group(1) if m else token

    findings: list[dict[str, Any]] = []
    for sid in sorted(prd_sucs - g_suc - na):
        findings.append(finding(
            "FAIL", "UPSTREAM_SUC_NOT_IN_GRAPH",
            f"PRD 系统用例 {sid} 未落入 behavior-graph：原型不会体现它。若非界面承载，在 surface-model 写明 N/A 豁免。",
            category="upstream", suc=sid,
        ))
    for fs in sorted(prd_flowsteps - g_flowsteps):
        if suc_of(fs) in na:
            continue
        findings.append(finding(
            "FAIL", "UPSTREAM_FLOWSTEP_NOT_IN_GRAPH",
            f"PRD 流步骤 {fs} 未被任何 graph step 承载（缺 from_flow_step）。",
            category="upstream", flow_step=fs,
        ))
    for b in sorted(prd_beats - g_steps):
        if suc_of(b) in na:
            continue
        findings.append(finding(
            "FAIL", "UPSTREAM_BEAT_NOT_IN_GRAPH",
            f"PRD 结局节点（节拍）{b} 未落入 behavior-graph：该结局状态原型不会体现。",
            category="upstream", step=b,
        ))
    for sid in sorted(registry_sucs - g_suc):
        findings.append(finding(
            "FAIL", "UPSTREAM_REGISTRY_SUC_NOT_IN_GRAPH",
            f"项目级 SUC 注册表的 {sid} 在项目级累积图里没有任何 flow：沉淀能力丢失。",
            category="upstream", suc=sid,
        ))
    return findings


# ---------------------------------------------------------------------------
# 下游原型覆盖率门（graph→下游契约）—— upstream_completeness_findings 的对称镜像
# ---------------------------------------------------------------------------

# 分母按 stage 分层：solution / tech 只卡 SURF 级（界面边界），breakdown 卡 PS 级
# （具体页面态）。两类共享同一差集模式与豁免语义。
_SURF_LEVEL_STAGES = {"solution", "technical_analysis"}
_PAGESTATE_LEVEL_STAGES = {"breakdown"}


def _coverage_denominator(
    *, merged_graph: dict[str, Any], surface_catalog: dict[str, Any], stage: str,
) -> tuple[str, set[str]]:
    """返回 ``(level, denominator_ids)``：

    - ``level`` ∈ {"surface", "pagestate", ""}。空串表示该 stage 不参与覆盖率门。
    - SURF 级分母 = surface_catalog 的 surf id ∪ 合并图 page_states 的 ``surf`` 去重。
    - PS 级分母 = 合并图 page_states 的 ``id`` 去重。
    """
    tables = graph_tables(merged_graph)
    page_states = tables["page_states"]
    if stage in _SURF_LEVEL_STAGES:
        surfs = {str(s) for s in surface_catalog.keys() if str(s).startswith(("SURF-", "SUR-"))}
        surfs |= {str(p.get("surf")) for p in page_states if p.get("surf")}
        return "surface", surfs
    if stage in _PAGESTATE_LEVEL_STAGES:
        ps_ids = {str(p.get("id")) for p in page_states if p.get("id")}
        return "pagestate", ps_ids
    return "", set()


def downstream_prototype_coverage_findings(
    *,
    merged_graph: dict[str, Any],
    surface_catalog: dict[str, Any],
    carried_refs: set[str],
    stage: str,
    exemptions: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """**下游原型覆盖率门（FAIL）—— graph→下游契约的对称镜像。**

    ``upstream_completeness_findings`` 保证「上游清单都落进图」；本函数保证「图里
    的界面边界 / 页面态都被下游契约承载」，否则下游（solution / tech-design /
    breakdown）可能自由重设计界面、绕过原型已固化的交互合同。

    分母按 stage 分层（见 ``_coverage_denominator``）：

    - ``solution`` / ``technical_analysis``：只卡 SURF 级（界面边界），不卡 PS，避免
      方案 / 技术设计阶段对页面态粒度误报。
    - ``breakdown``：卡 PS 级（具体页面态），确保拆解到任务时每个页面态都有承载。

    分子 = ``carried_refs``（下游契约 traces_to 里出现的 ref 集合）。差集 =
    分母 − carried_refs − 合法豁免。每个未承载项产一条 FAIL。

    ``exemptions``：``{被豁免 id: 理由}``。理由为空 / 占位 → 该豁免无效（仍 FAIL，
    code ``PROTOTYPE_EXEMPTION_NO_REASON``），防止「写个空豁免就放行」。

    **非破坏边界**：合并图为空 / 无 page_states / 无 surface（任务无 UI、未跑
    interaction）→ 该 stage 分母为空 → 返回空 findings，绝不 FAIL。
    """
    exemptions = exemptions or {}
    level, denominator = _coverage_denominator(
        merged_graph=merged_graph, surface_catalog=surface_catalog, stage=stage,
    )
    if not level or not denominator:
        # 该 stage 不参与覆盖率门，或图里根本没有可卡的界面 / 页面态。
        return []

    # 合法豁免：理由非空且非占位。无理由豁免单独报 FAIL（不计入豁免集）。
    valid_exempt: set[str] = set()
    findings: list[dict[str, Any]] = []
    for ex_id, reason in exemptions.items():
        eid = str(ex_id or "")
        if not eid:
            continue
        if not str(reason or "").strip() or is_placeholder_text(reason):
            findings.append(finding(
                "FAIL", "PROTOTYPE_EXEMPTION_NO_REASON",
                f"原型覆盖率豁免 {eid} 缺少理由（豁免必须登记理由，否则视为无效豁免）。",
                category="prototype_coverage", ref=eid, stage=stage,
            ))
            continue
        valid_exempt.add(eid)

    uncovered = sorted(denominator - carried_refs - valid_exempt)
    if level == "surface":
        for sid in uncovered:
            findings.append(finding(
                "FAIL", "SURFACE_NOT_CARRIED",
                f"{stage} 阶段：原型界面边界 {sid} 未被下游契约承载，下游可能自由重设计界面；"
                f"需承载或经决策门显式改写并登记 N/A 豁免 + 理由。",
                category="prototype_coverage", surf=sid, stage=stage,
            ))
    else:  # pagestate
        for pid in uncovered:
            findings.append(finding(
                "FAIL", "PAGESTATE_NOT_COVERED",
                f"{stage} 阶段：原型页面态 {pid} 未被下游契约承载，下游可能自由重设计界面；"
                f"需承载或经决策门显式改写并登记 N/A 豁免 + 理由。",
                category="prototype_coverage", page_state=pid, stage=stage,
            ))
    return findings


def prototype_e2e_alignment_coverage(
    *,
    graph: dict[str, Any],
    covered_testids: set[str],
    exemptions: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """**verify 阶段原型对齐 e2e 机器门（FAIL）—— interaction locator 门的下游镜像。**

    interaction 阶段的 locator 门只保证「``e2e_obligation`` 边声明的 testid 命中原型
    ``data-testid``」（静态锚点存在）。本函数把这条义务推进到 verify 阶段：图里声明为
    E2E 种子边（``edge.e2e_obligation == True``）的转移，其 ``edge.testid`` 必须真的被
    某条**通过的 e2e 断言**绑定（``covered_testids``），否则下游可以「声明义务、画好锚点，
    却从不写断言」而蒙混过关。

    判定（纯函数，无 IO）：

    - **必需集** = 所有 ``e2e_obligation == True`` 的边的 ``testid``（去占位：用
      ``is_placeholder_text`` 过滤）。声明了 ``e2e_obligation`` 但 testid 占位 / 缺失的边，
      单列 WARN ``E2E_OBLIGATION_EDGE_NO_TESTID``（对齐 interaction 门的 WARN 语义，**不
      FAIL**——锚点缺失由 interaction 门负责，verify 门不重复 FAIL，只提示无法对齐）。
    - **合法豁免** = ``exemptions`` 里理由非空且非占位的 testid。无理由 / 占位理由的豁免
      单独报 FAIL ``PROTOTYPE_EXEMPTION_NO_REASON``（复用既有 code / 语义），且该 testid
      仍按未豁免处理（防「空豁免放行」）。
    - **差集** = 必需 testid − ``covered_testids`` − 合法豁免。每个未被覆盖的义务边 testid
      产一条 FAIL ``PROTOTYPE_E2E_EDGE_NOT_ASSERTED``。

    **非破坏边界**：图为空 / 无 edges / 无 ``e2e_obligation`` 边 → 必需集为空 → 返回空
    findings（非 UI 任务 / 未跑 interaction 自动跳过，**绝不 FAIL**）。``covered_testids``
    取不到时由调用方按 ``source_unavailable`` 整门跳过，不在本函数兜底。
    """
    exemptions = exemptions or {}
    edges = graph_tables(graph).get("edges", []) if graph else []

    findings: list[dict[str, Any]] = []

    # 必需集：e2e_obligation 边的 testid（占位 / 缺失 → WARN，不计入必需集）。
    required_testids: set[str] = set()
    for e in edges:
        if not e.get("e2e_obligation"):
            continue
        src, dst = str(e.get("from") or ""), str(e.get("to") or "")
        ref = f"{src or '∅'}→{dst or '∅'}"
        testid = str(e.get("testid") or "")
        if is_placeholder_text(testid):
            findings.append(finding(
                "WARN", "E2E_OBLIGATION_EDGE_NO_TESTID",
                f"E2E 种子边 {ref} 声明 e2e_obligation 但未标定 testid，verify 阶段无法把它"
                "绑定到具体 e2e 断言（请在 edge.testid 标定位器，interaction locator 门也会提示）。",
                category="prototype_alignment", edge=ref,
            ))
            continue
        required_testids.add(testid)

    if not required_testids:
        # 无任何可对齐的义务边（非 UI / 未跑 interaction / 义务边均缺 testid）→ 只保留 WARN。
        return findings

    # 合法豁免：理由非空且非占位。无理由豁免单独报 FAIL（不计入豁免集）。
    valid_exempt: set[str] = set()
    for ex_id, reason in exemptions.items():
        eid = str(ex_id or "")
        if not eid:
            continue
        if not str(reason or "").strip() or is_placeholder_text(reason):
            findings.append(finding(
                "FAIL", "PROTOTYPE_EXEMPTION_NO_REASON",
                f"原型 e2e 对齐豁免 {eid} 缺少理由（豁免必须登记理由，否则视为无效豁免）。",
                category="prototype_alignment", testid=eid,
            ))
            continue
        valid_exempt.add(eid)

    uncovered = sorted(required_testids - set(covered_testids) - valid_exempt)
    for testid in uncovered:
        findings.append(finding(
            "FAIL", "PROTOTYPE_E2E_EDGE_NOT_ASSERTED",
            f"behavior-graph 声明该转移为 E2E 种子边（e2e_obligation=true）但 verify 阶段无通过的 "
            f"e2e 断言绑定其 testid「{testid}」；须补绑定断言或经决策门登记 "
            "prototype_coverage_exemptions+理由。",
            category="prototype_alignment", testid=testid,
        ))
    return findings


def promote_mission_graph_to_project(root: Path, mission: str) -> dict[str, Any]:
    """Merge a closing mission's behavior-graph into the project-level accumulated
    graph (the steady-state sedimentation step). Injects the mission's surface
    catalog (from surface-model.md machine table) into the project graph's inline
    `surfaces` so future missions' prototype-check knows those surfaces. Idempotent:
    re-promoting overwrites the mission's ids with their latest definition; the
    mission's top-level ``retired: [ids]`` removes sedimented ids."""
    import yaml

    _mp, mg = load_behavior_graph(root, mission)
    if not mg:
        return {"merged": False, "reason": "mission behavior-graph absent"}

    # inject mission surfaces + regions (from surface-model.md) into the mission graph
    # before merge — so the project graph carries both the surface catalog and the
    # region tree (composition baseline) for future missions' prototype-check.
    surface_text = read_text_if_exists(surface_model_path(root, mission))
    if not mg.get("surfaces"):
        catalog = parse_surface_catalog(surface_text)
        mg = dict(mg)
        mg["surfaces"] = [
            {"surf": sid, "name": c.get("name", ""), "type": c.get("type", ""),
             "baseline": c.get("baseline", ""), "page_entry": c.get("page_entry", ""),
             "via_controls": sorted(c.get("via_controls", set()))}
            for sid, c in catalog.items()
        ]
    if not mg.get("regions"):
        rcat = parse_region_catalog(surface_text)
        mg = dict(mg)
        mg["regions"] = [
            {"region": rid, "surf": r.get("surf", ""), "parent": r.get("parent", "root"),
             "layout": r.get("layout", ""), "priority": r.get("priority", ""),
             "role": r.get("role", ""), "carries": r.get("carries", ""),
             "scan_order": r.get("scan_order")}
            for rid, r in rcat.items()
        ]

    proj = load_project_behavior_graph(root)
    counts = lambda g: {k: len(graph_tables(g)[k]) for k in ("page_states", "steps", "edges", "flows")}  # noqa: E731
    before = counts(proj)
    merged = merge_graphs(proj, mg)
    merged.pop("mission_id", None)  # 项目级累积图无单一 mission_id

    path = project_behavior_graph_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# 项目级累积行为图（SSOT）：所有已关闭 mission 图的并集，由 `harness knowledge promote --apply` 自动维护。\n"
        + "# 勿手改；新增/修改/retire 通过各 mission 的 interaction-spec/behavior-graph.yaml 关闭时并入。\n"
        + yaml.safe_dump(merged, allow_unicode=True, sort_keys=False, width=4096),
        encoding="utf-8",
    )
    return {
        "merged": True, "project_graph_path": relpath(root, path),
        "before": before, "after": counts(merged),
        "retired": list(mg.get("retired") or []),
    }
