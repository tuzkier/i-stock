"""Pure path / contract helpers for the ``prototype-as-frontend`` lane."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from harness_cli_core.domain.contracts import load_control_contract_or_empty
from harness_cli_core.domain.findings import finding, is_placeholder_text
from harness_cli_core.infra.runtime_paths import mission_stage_dir, read_text_if_exists

# 门A：frontend-changeset.md 结构化 surfaces 机器表（首列 SURF-<digits> 为锚点）。
_SURFACE_ROW_RE = re.compile(r"^SURF-[0-9]+$")
# trace_to / domain_refs token 形态（与 behavior_graph 同源）。
_FLOWSTEP_FULL_RE = re.compile(r"^SUC-(?:TF-[A-Z]+-)?[0-9]+-FLOW-[0-9]+(?:\.[A-Za-z0-9_-]+)?$")
_FLOWSTEP_PREFIX_RE = re.compile(r"^(SUC-(?:TF-[A-Z]+-)?[0-9]+-FLOW-[0-9]+)\.")
# 门A 结构化 N/A 豁免段（标题 `## 界面承载豁免（N/A）` 下的固定列表）。
_NA_NODE_RE = re.compile(r"^(SUC-(?:TF-[A-Z]+-)?[0-9]+)(-FLOW-[0-9]+)?(\.[A-Za-z0-9_-]+)?$")
_NA_GRANULARITY = {"suc", "flowstep", "beat"}


def parse_frontend_changeset_surfaces(text: str) -> list[dict[str, Any]]:
    """解析 frontend-changeset.md 的固定列 surfaces 机器表：

    ``| surface_id | kind | operation | file_path | baseline_ref | traces_to | domain_refs |``

    首列匹配 ``^SURF-\\d+`` 为锚点；表头 / 分隔 / 散文行跳过。``traces_to`` /
    ``domain_refs`` 按 ``[,、\\s]`` split 并丢弃 placeholder。baseline_ref 为
    ``null`` / ``-`` / placeholder 时归 None。"""
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or not _SURFACE_ROW_RE.match(cells[0]):
            continue

        def _split(idx: int) -> set[str]:
            if len(cells) <= idx:
                return set()
            return {
                tok.strip()
                for tok in re.split(r"[,、\s]+", cells[idx])
                if tok.strip() and not is_placeholder_text(tok.strip())
            }

        baseline = cells[4] if len(cells) >= 5 else ""
        baseline_ref = None if (not baseline or baseline.lower() in {"null", "-"} or is_placeholder_text(baseline)) else baseline
        out.append({
            "surface_id": cells[0],
            "kind": cells[1] if len(cells) >= 2 else "",
            "operation": cells[2] if len(cells) >= 3 else "",
            "file_path": cells[3] if len(cells) >= 4 else "",
            "baseline_ref": baseline_ref,
            "traces_to": _split(5),
            "domain_refs": _split(6),
        })
    return out


def changeset_traces_union(surfaces: list[dict[str, Any]]) -> set[str]:
    """把所有行 ``traces_to`` 求并，并对每个 ``SUC-xx-FLOW-xx[.state]`` 用前缀正则
    抽出 flow-step 前缀加入并集（changeset 写 beat token 也算覆盖其 flow-step，
    对齐 graph_flowstep_ids 语义）。原始 token 同样保留。"""
    union: set[str] = set()
    for surf in surfaces:
        for tok in surf.get("traces_to") or set():
            tok = str(tok)
            union.add(tok)
            m = _FLOWSTEP_PREFIX_RE.match(tok)
            if m:
                union.add(m.group(1))
    return union


def frontend_upstream_completeness_findings(
    *,
    changeset_surfaces: list[dict[str, Any]],
    prd_flowsteps: set[str],
    na_flowsteps: set[str] | None = None,
) -> list[dict[str, Any]]:
    """门A 主体（FAIL）：PRD flow-step 全集 ⊆ 所有 changeset.traces_to 并集
    （∪ N/A 豁免）。漏一个报 ``FRONTEND_FLOWSTEP_NOT_IN_CHANGESET``。"""
    union = changeset_traces_union(changeset_surfaces)
    na = na_flowsteps or set()
    findings: list[dict[str, Any]] = []
    for fs in sorted(prd_flowsteps - union - na):
        findings.append(finding(
            "FAIL", "FRONTEND_FLOWSTEP_NOT_IN_CHANGESET",
            f"PRD 流步骤 {fs} 未被任何 frontend-changeset surface 的 traces_to 承载：前端不会体现它。"
            "若非界面承载，在 changeset 结构化豁免段写明 N/A。",
            category="upstream", flow_step=fs,
        ))
    return findings


def parse_frontend_na_flowsteps(text: str, prd_flowsteps: set[str]) -> tuple[set[str], list[dict[str, Any]]]:
    """解析 frontend-changeset.md 的结构化 N/A 豁免段
    ``| prd_node_id | 豁免粒度 | 理由 | 责任归属 |``。

    返回 ``(na_flowsteps, exemptions)``。粒度=flowstep 直接取 id；粒度=suc 时
    把该 SUC 下全部 PRD flow-step（前缀匹配）纳入豁免。beat 粒度归一到其 flow-step。"""
    exemptions: list[dict[str, Any]] = []
    na_flowsteps: set[str] = set()
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or not _NA_NODE_RE.match(cells[0]) or len(cells) < 4:
            continue
        node, gran = cells[0], cells[1].lower()
        exemptions.append({"node": node, "granularity": gran, "reason": cells[2], "owner": cells[3]})
        if gran == "flowstep":
            na_flowsteps.add(node)
        elif gran == "beat":
            m = _FLOWSTEP_PREFIX_RE.match(node)
            if m:
                na_flowsteps.add(m.group(1))
        elif gran == "suc":
            m = re.match(r"(SUC-(?:TF-[A-Z]+-)?[0-9]+)", node)
            suc = m.group(1) if m else node
            na_flowsteps |= {fs for fs in prd_flowsteps if fs.startswith(suc + "-FLOW-")}
    return na_flowsteps, exemptions


def frontend_na_stale_findings(
    *, na_flowsteps: set[str], changeset_surfaces: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """声明豁免但该 flow-step 其实在 traces_union 里 → WARN（豁免 + 实现共存只是冗余）。"""
    union = changeset_traces_union(changeset_surfaces)
    findings: list[dict[str, Any]] = []
    for fs in sorted(na_flowsteps & union):
        findings.append(finding(
            "WARN", "FRONTEND_NA_EXEMPTION_STALE",
            f"flow-step {fs} 声明界面承载 N/A 豁免，但 changeset traces_to 实际已承载它（冗余豁免）。",
            category="upstream", flow_step=fs,
        ))
    return findings


def frontend_flowstep_obligation_coverage(
    prd_flowsteps: set[str], e2e_obligations: list[dict[str, Any]]
) -> dict[str, Any]:
    """门B 覆盖判定（纯函数）：flow-step 被覆盖 ⟺ 在某条 e2e_obligation 且
    (status==required 视为有 E2E 义务 / status==accepted_alternative 且 accepted_reason 非空)。
    返回 ``{flowstep_coverage, covered_flowsteps, uncovered_flowsteps}``。"""
    coverage: dict[str, dict[str, Any]] = {}
    for ob in e2e_obligations or []:
        if not isinstance(ob, dict):
            continue
        fs = str(ob.get("flow_step") or "").strip()
        if not fs:
            continue
        status = str(ob.get("status") or "required").strip().lower()
        reason = str(ob.get("accepted_reason") or "").strip()
        if status == "accepted_alternative":
            covered = bool(reason) and not is_placeholder_text(reason)
            accepted = covered
            has_e2e = False
        else:  # required
            covered = True
            accepted = False
            has_e2e = True
        prev = coverage.get(fs)
        if prev is None or (covered and not prev["covered"]):
            coverage[fs] = {"has_e2e": has_e2e, "accepted": accepted, "reason": reason, "covered": covered}
    covered_flowsteps = {fs for fs, c in coverage.items() if c["covered"]}
    uncovered = sorted(prd_flowsteps - covered_flowsteps)
    return {
        "flowstep_coverage": coverage,
        "covered_flowsteps": sorted(covered_flowsteps),
        "uncovered_flowsteps": uncovered,
    }


def prd_flowsteps_for_mission(root: Path, mission: str) -> set[str]:
    """PRD flow-step 全集，来源与 interactive 路线一致：读 product 目录的
    use-case-model.md 跑 ``\\bSUC-[0-9]+-FLOW-[0-9]+\\b``。"""
    from harness_cli_core.domain.interaction import interaction_product_dir

    ucm = read_text_if_exists(interaction_product_dir(root, mission) / "use-case-model.md")
    return set(re.findall(r"\bSUC-[0-9]+-FLOW-[0-9]+\b", ucm))


def contract_e2e_obligations(contract: dict[str, Any]) -> list[dict[str, Any]]:
    """从 prototype-as-frontend contract 读 ``e2e_obligation[]``（新 key），
    兼容旧 key ``e2e_locator_obligations[]``（避免历史 contract 解析炸裂）。"""
    for key in ("e2e_obligation", "e2e_locator_obligations"):
        val = contract.get(key)
        if isinstance(val, list):
            return [v for v in val if isinstance(v, dict)]
    return []


def prototype_as_frontend_contract_path(root: Path, mission: str) -> Path:
    return (
        mission_stage_dir(root, mission)
        / "contracts"
        / "prototype-as-frontend.contract.yaml"
    )


def prototype_as_frontend_contract(root: Path, mission: str) -> dict[str, Any]:
    return load_control_contract_or_empty(
        prototype_as_frontend_contract_path(root, mission)
    )


def frontend_changeset_path(root: Path, mission: str) -> Path:
    return mission_stage_dir(root, mission) / "frontend-changeset.md"


def frontend_project_root_from_contract(root: Path, mission: str) -> Path | None:
    contract = prototype_as_frontend_contract(root, mission)
    frontend_project = (
        contract.get("frontend_project")
        if isinstance(contract.get("frontend_project"), dict)
        else {}
    )
    value = frontend_project.get("root")
    if not isinstance(value, str) or is_placeholder_text(value):
        return None
    path = Path(value)
    return path if path.is_absolute() else root / path
