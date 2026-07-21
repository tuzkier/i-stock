"""Domain constants + pure helpers for the interaction stage CLIs.

Covers signal keyword tables, regex patterns, and trace-reference collectors
used by ``harness interaction *`` and ``harness alignment check``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from harness_cli_core.domain.contracts import load_control_contract_or_empty
from harness_cli_core.infra.runtime_paths import (
    mission_artifact_dir,
    mission_stage_dir,
    read_text_if_exists,
)


# 原型必要性判定模型（2026-06 重设计）：
# 「要不要原型」不再在 PRD 用 `UIC-xx` 前置门控——那条链路绕远、把决策塞错了阶段。
# 新模型：**每个 mission 默认进入 interaction 阶段**，由 interaction-designer 在阶段内做
# 一次原型必要性判断（能明确判的自动判，灰色地带才问用户），结论写进确定记录
# `interaction/prototype-necessity.json`（needed / reason / decided_by）。
# `interaction_required_decision` 现在只是**读这份确定记录**：有记录 → 按 needed；无记录 →
# decided=None（待阶段内判定，调用方按"默认进入"处理）。不再扫描 use-case-model 的 UIC。
UIC_ID_RE = re.compile(r"\bUIC-[A-Z0-9][A-Z0-9_-]*\b")


DOMAIN_REF_RE = re.compile(
    r"\b(?:BO|BC|CAP|ACT|AGG|ENT|VO|CMD|EVT|INV|POL|DS|STM|EXC|AUD)-[A-Z0-9][A-Z0-9_-]*\b"
)
# page_state id（PS-<surf>-<state>）的状态后缀是小写（如 -empty / -loading），
# 所以 PS- 单列一个允许大小写尾段的分支；其余前缀保持大写-only（不放宽全局尾段，
# 避免把 FLOW-onboarding 这类小写散文误判为 ref）。PS- 分支放在主分支前面，确保
# PS-SURF-BOARD-empty 整体命中而不是在 PS-SURF-BOARD- 处提前 \b 截断。
TRACE_REF_RE = re.compile(
    r"\bPS-[A-Za-z0-9][A-Za-z0-9_-]*\b"
    r"|\b(?:SCN|RULE|DEC|MOD|IF|DATA|VS|FLOW|STATE|INT|VAL|E2E|SUC|UIC|SURF|BASE|CHG|CONS|"
    r"BO|CMD|ENT|INV|STM|POL|AGG|BC|CAP|ACT|EVT|EXC|AUD|TASK|T|AT)-[A-Z0-9][A-Z0-9_-]*\b"
)

INTERACTION_REQUIRED_FILES: tuple[str, ...] = (
    "surface-model.md",
    "behavior-graph.yaml",
)
INTERACTION_REQUIRED_STATES: tuple[str, ...] = (
    "STATE-LOADING",
    "STATE-EMPTY",
    "STATE-SUCCESS",
    "STATE-ERROR",
    "STATE-PERMISSION",
    "STATE-DISABLED",
)

OPERABLE_PROTOTYPE_ROLES = {"operable_prototype", "primary_prototype"}
OPERABLE_PROTOTYPE_PATHS = {
    "prototype/index.html",
}
OPERABLE_PROTOTYPE_FORBIDDEN_TEXT: tuple[str, ...] = (
    "阅读顺序",
    "评审入口",
    "评审说明",
    "Flow 串走",
    "状态陈列",
    "组件目录",
    "缩略图墙",
    "coverage",
    "manifest",
    "visual-interaction-manifest",
    "interaction-spec",
    "contracts/interaction",
    "traces_to",
    "reviewer",
)
OPERABLE_PROTOTYPE_FORBIDDEN_RE = re.compile(
    r"\b(?:REQ|SCN|US|UC|FLOW|STATE|E2E)-[A-Za-z0-9._-]+\b"
)
OPERABLE_PROTOTYPE_INTERACTIVE_RE = re.compile(
    r"<\s*(?:button|input|select|textarea)\b|<\s*a\b[^>]*\bhref\s*=|"
    r"\bdata-testid\s*=|\brole\s*=\s*['\"](?:button|tab|checkbox|menuitem|switch|combobox)['\"]",
    re.IGNORECASE,
)


# Keywords in mission-contract.md / product definition / solution.md that
# indicate dependency-impact analysis is required for tech-design.
DEP_IMPACT_TRIGGER_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("外部业务系统", "external_system"),
    ("external system", "external_system"),
    ("third-party", "external_system"),
    ("third party", "external_system"),
    ("外部 API", "external_api"),
    ("external api", "external_api"),
    ("数据迁移", "data_migration"),
    ("data migration", "data_migration"),
    ("schema change", "schema_change"),
    ("schema 变更", "schema_change"),
    ("DDL", "schema_change"),
    ("跨服务", "cross_service"),
    ("cross-service", "cross_service"),
    ("微服务", "cross_service"),
    ("microservice", "cross_service"),
    ("integration", "integration"),
    ("webhook", "integration"),
    ("infrastructure", "infrastructure"),
    ("基础设施", "infrastructure"),
)


# ---------------------------------------------------------------------------
# Helpers — pure functions used across interaction handlers.
# ---------------------------------------------------------------------------


def interaction_stage_artifact_dir(root: Path, mission: str) -> Path:
    """Resolve the interaction stage content dir, preferring the artifact store
    ``artifacts/<mission>/interaction`` and falling back to the legacy
    ``stages/<mission>`` layout only when the artifact dir is absent."""
    artifact_dir = mission_artifact_dir(root, mission) / "interaction"
    legacy_dir = mission_stage_dir(root, mission)
    if legacy_dir.exists() and not artifact_dir.exists():
        return legacy_dir
    return artifact_dir


def interaction_product_dir(root: Path, mission: str) -> Path:
    """Resolve the product-definition content dir, preferring the artifact store
    ``artifacts/<mission>/product`` with legacy ``stages/<mission>/product``
    fallback."""
    artifact_dir = mission_artifact_dir(root, mission) / "product"
    legacy_dir = mission_stage_dir(root, mission) / "product"
    if legacy_dir.exists() and not artifact_dir.exists():
        return legacy_dir
    return artifact_dir


def prototype_necessity_path(root: Path, mission: str) -> Path:
    """原型必要性确定记录的落点：``interaction/prototype-necessity.json``。

    由 interaction-designer 在阶段内 Step 0 写入（不是机器扫描产物，也不是 manifest，
    不受 ``design.interaction`` 覆盖层对 manifest 的写禁约束）。"""
    return interaction_stage_artifact_dir(root, mission) / "prototype-necessity.json"


def load_prototype_necessity(root: Path, mission: str) -> dict[str, Any] | None:
    """读取原型必要性确定记录。缺失 / 不可解析 → None（= 尚未判定）。

    期望结构：``{"needed": bool, "reason": str, "decided_by": "agent"|"user"}``。
    """
    import json

    path = prototype_necessity_path(root, mission)
    text = read_text_if_exists(path)
    if not text.strip():
        return None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict) or "needed" not in data:
        return None
    return data


def interaction_required_decision(root: Path, mission: str) -> dict[str, Any]:
    """**原型必要性判定**——读阶段内确定记录 ``prototype-necessity.json``，不扫关键词、
    不再读 use-case-model 的 UIC。

    返回 ``{"decided": bool|None, "uic": [...], "source": str, "reason": str,
    "decided_by": str|None}``：

    - 有确定记录 → ``decided = needed``（True/False），``source="determination"``。
    - 无确定记录 → ``decided=None``：尚未在阶段内判定。**每个 mission 默认进入 interaction**，
      由 interaction-designer 在阶段内判断；调用方对 None 按"默认进入、阶段内判定"处理，
      不猜、不退回关键词。``uic`` 字段保留为空列表仅为向后兼容旧调用方。
    """
    record = load_prototype_necessity(root, mission)
    if record is None:
        return {
            "decided": None,
            "uic": [],
            "source": "determination:absent",
            "reason": "尚未产出原型必要性确定记录：默认进入 interaction 阶段，由 interaction-designer 阶段内判定。",
            "decided_by": None,
        }
    needed = bool(record.get("needed"))
    return {
        "decided": needed,
        "uic": [],
        "source": "determination",
        "reason": str(record.get("reason") or ("判定需要原型设计。" if needed else "判定无需原型设计。")),
        "decided_by": str(record.get("decided_by") or "") or None,
    }


def interaction_spec_dir(root: Path, mission: str) -> Path:
    return interaction_stage_artifact_dir(root, mission) / "interaction-spec"


_PLACEHOLDER_SEGMENT_RE = re.compile(r"^([NXMnxm])\1+$")


def is_placeholder_or_convention_ref(ref: str) -> bool:
    """True for numbering-convention / placeholder / range tokens that appear in
    explanatory prose and must not be treated as concrete trace references.

    Ignored: range notations (``STATE-301..305``) and repeated-marker placeholders
    where a hyphen segment is a single marker letter repeated — ``NN``/``NNN``
    (``SUC-NN``, ``FLOW-NNN``, ``SUC-NN-FLOW-NN``), ``XX``/``xx`` (``FLOW-xx``),
    ``MM``. Concrete ids are kept, including non-numeric ones such as ``FLOW-X``,
    ``SCN-1`` and ``E2E-LOGIN``."""
    if ".." in ref:
        return True
    segments = ref.split("-")[1:]
    return any(_PLACEHOLDER_SEGMENT_RE.match(seg) for seg in segments)


def collect_refs_from_value(value: object, pattern: re.Pattern[str] = TRACE_REF_RE) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for child in value.values():
            refs.update(collect_refs_from_value(child, pattern))
    elif isinstance(value, list):
        for child in value:
            refs.update(collect_refs_from_value(child, pattern))
    elif isinstance(value, str):
        if "{{" not in value:
            refs.update(
                ref for ref in pattern.findall(value)
                if not is_placeholder_or_convention_ref(ref)
            )
    return refs


def known_domain_refs(root: Path, mission: str) -> set[str]:
    product_dir = interaction_product_dir(root, mission)
    candidates = [
        product_dir / "product-domain-model.md",
        product_dir / "use-case-model.md",
        product_dir / "acceptance-scenarios.md",
        mission_stage_dir(root, mission) / "product-domain-model.md",
        root / "project-knowledge" / "product" / "product-domain-model.md",
        root / "project-knowledge" / "product" / "use-case-model.md",
        root / "project-knowledge" / "product" / "acceptance-scenarios.md",
    ]
    refs: set[str] = set()
    for path in candidates:
        refs.update(DOMAIN_REF_RE.findall(read_text_if_exists(path)))
    prd_contract = mission_stage_dir(root, mission) / "contracts" / "prd.contract.yaml"
    refs.update(collect_refs_from_value(load_control_contract_or_empty(prd_contract), DOMAIN_REF_RE))
    return refs


def interaction_prd_feedback_required(root: Path, mission: str) -> bool:
    contract = load_control_contract_or_empty(
        mission_stage_dir(root, mission) / "contracts" / "interaction.contract.yaml"
    )
    feedback = (
        contract.get("prd_feedback")
        if isinstance(contract.get("prd_feedback"), dict)
        else {}
    )
    status = str(feedback.get("status") or feedback.get("state") or "").lower()
    if feedback.get("requires_prd_feedback") is True:
        return True
    return status in {"required", "pending", "needs_prd_feedback", "prd_feedback_required"}


def state_has_na_reason(text: str, state_id: str) -> bool:
    for line in text.splitlines():
        if state_id in line and re.search(r"\bN/A\b|不适用|not applicable|无需|无此状态", line, re.I):
            return True
    return False


# Canonical interaction states mapped to concept keywords (zh + en). A spec that
# covers the concept with a domain-specific state id (e.g. STATE-302 board.loading)
# satisfies the matrix even without the literal canonical token.
CANONICAL_STATE_CONCEPTS: dict[str, tuple[str, ...]] = {
    "STATE-LOADING": ("state-loading", "loading", "加载", "骨架", "skeleton"),
    "STATE-EMPTY": ("state-empty", "empty", "空态", "空状态", "无数据", "无节点"),
    "STATE-SUCCESS": ("state-success", "success", "成功", "readable", "数据态", "正常态"),
    "STATE-ERROR": ("state-error", "error", "错误", "失败", "read_error", "read-error"),
    "STATE-PERMISSION": ("state-permission", "permission", "权限", "只读", "readonly", "read-only"),
    "STATE-DISABLED": ("state-disabled", "disabled", "禁用", "焦点", "focus", "keyboard", "键盘"),
}


def state_concept_covered(text: str, state_id: str) -> bool:
    """True when the canonical interaction state is covered either by its literal
    id or by any concept keyword (so domain-specific state naming still counts)."""
    if state_id in text:
        return True
    lowered = text.lower()
    for keyword in CANONICAL_STATE_CONCEPTS.get(state_id, ()):  # noqa: SIM110
        if keyword.lower() in lowered:
            return True
    return False


def spec_text_blob(root: Path, mission: str) -> str:
    spec_dir = interaction_spec_dir(root, mission)
    chunks: list[str] = []
    if spec_dir.exists():
        for child in sorted(spec_dir.rglob("*")):
            if child.is_file() and child.suffix in {".md", ".ts", ".tsx", ".yaml", ".yml", ".json"}:
                chunks.append(read_text_if_exists(child))
    return "\n".join(chunks)


def contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(token.lower() in lowered for token in tokens)


def contains_ascii_wireframe(text: str) -> bool:
    return bool(
        re.search(r"\bascii\s+wireframe\b|\bwireframe\b|线框图|草图", text, re.I)
        or re.search(r"(?m)^\s*\+[+-]{3,}\+", text)
    )


# ---------------------------------------------------------------------------
# Visual manifest helpers
# ---------------------------------------------------------------------------


def load_visual_manifest(root: Path, mission: str) -> tuple[Path, dict[str, Any] | None]:
    """Return (manifest_path, manifest_dict_or_None). The first candidate path
    is returned even when the file is missing so callers can surface a
    relative path in the finding message.
    """
    import json

    artifact_dir = mission_artifact_dir(root, mission) / "interaction"
    stage_dir = mission_stage_dir(root, mission)
    candidates = [
        artifact_dir / "visual-interaction" / "visual-interaction-manifest.json",
        artifact_dir / "visual-interaction-manifest.json",
        stage_dir / "visual-interaction" / "visual-interaction-manifest.json",
        stage_dir / "visual-interaction-manifest.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return path, None
            return path, data if isinstance(data, dict) else None
    return candidates[0], None


def covered_manifest_values(manifest: dict[str, Any], key: str) -> set[str]:
    from harness_cli_core.domain.findings import is_placeholder_text

    covered: set[str] = set()
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return covered
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        covers = artifact.get("covers") if isinstance(artifact.get("covers"), dict) else {}
        values = covers.get(key)
        if isinstance(values, list):
            covered.update(str(v) for v in values if not is_placeholder_text(v))
    return covered


def artifact_rel_path(artifact: dict[str, Any]) -> str:
    return str(artifact.get("path") or "").replace("\\", "/").lstrip("./")


def artifact_role(artifact: dict[str, Any]) -> str:
    return (
        str(
            artifact.get("artifact_role")
            or artifact.get("role")
            or artifact.get("kind")
            or ""
        )
        .strip()
        .lower()
    )


def is_operable_prototype_artifact(artifact: dict[str, Any]) -> bool:
    rel = artifact_rel_path(artifact)
    if str(artifact.get("type") or "").lower() != "html":
        return False
    return artifact_role(artifact) in OPERABLE_PROTOTYPE_ROLES or rel in OPERABLE_PROTOTYPE_PATHS


def resolve_visual_artifact_path(
    root: Path,
    mission: str,
    manifest_path: Path,
    artifact: dict[str, Any],
) -> Path:
    absolute = artifact.get("absolute_path")
    if isinstance(absolute, str) and absolute:
        candidate = Path(absolute)
        if candidate.exists():
            return candidate
    rel = artifact_rel_path(artifact)
    return manifest_path.parent / rel


def html_without_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Trace 脊柱（SURF ↔ SUC ↔ OBJ ↔ SCN）对账
# ---------------------------------------------------------------------------

TRACE_OBJ_RE = re.compile(r"\bOBJ-[0-9]+\b")
TRACE_SUC_RE = re.compile(r"\bSUC-[0-9]+(?:-(?:OP|FLOW)-[0-9]+)?\b")
TRACE_SURF_RE = re.compile(r"\bSURF-[A-Za-z0-9._-]+\b")
TRACE_DATA_ATTR_RE = re.compile(
    r"""data-(surf|suc|obj)\s*=\s*["']([^"']+)["']""", re.IGNORECASE
)
TRACE_FIELD_ATTR_RE = re.compile(
    r"""data-field\s*=\s*["']([^"']+)["']""", re.IGNORECASE
)
# JS-created elements set anchors via setAttribute('data-obj', '...') instead of a
# literal HTML attribute; recognize those too so prototypes that render via templates
# / DOM APIs aren't blind spots for trace coverage.
TRACE_DATA_SETATTR_RE = re.compile(
    r"""setAttribute\(\s*["']data-(surf|suc|obj)["']\s*,\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
TRACE_FIELD_SETATTR_RE = re.compile(
    r"""setAttribute\(\s*["']data-field["']\s*,\s*["']([^"']+)["']""", re.IGNORECASE
)
# A field anchor token is `OBJ-<n>.<field>` (object-scoped, self-describing).
TRACE_FIELD_TOKEN_RE = re.compile(r"^(OBJ-[0-9]+)\.([A-Za-z0-9_-]+)$")


def _suc_base(suc_id: str) -> str:
    """Reduce SUC-01-OP-03 / SUC-01-FLOW-02 to its base SUC-01.

    DEPRECATED for coverage judgment. The behavior-graph model
    (``domain/behavior_graph.py``) reconciles at step / page-state granularity and
    does NOT collapse to SUC base — collapsing here is what hid SUC-internal
    branch/state coverage. This helper is retained only for legacy
    ``trace_coverage_findings`` (superseded by ``prototype-check``) and for
    "valid id range" widening, never for deciding whether a SUC is covered.
    """
    match = re.match(r"(SUC-[0-9]+)(?:-(?:OP|FLOW)-[0-9]+)?$", suc_id)
    return match.group(1) if match else suc_id


def _suc_bases(ids: set[str]) -> set[str]:
    return {_suc_base(x) for x in ids}


def extract_data_anchor_ids(html: str) -> dict[str, set[str]]:
    """Element-level trace anchors from prototype HTML (data-surf/data-suc/data-obj)."""
    out: dict[str, set[str]] = {"surf": set(), "suc": set(), "obj": set()}
    for kind, raw in TRACE_DATA_ATTR_RE.findall(html) + TRACE_DATA_SETATTR_RE.findall(html):
        for item in re.split(r"[,\s]+", raw):
            item = item.strip()
            if item and not is_placeholder_or_convention_ref(item):
                out[kind.lower()].add(item)
    return out


def extract_field_anchor_ids(html: str) -> dict[str, set[str]]:
    """Element-level field anchors from prototype HTML: `data-field="OBJ-02.status"`
    (object-scoped, self-describing, space/comma-separated for multiple). Returns a
    map OBJ-id -> {field, ...}. Malformed tokens are ignored here and surface as
    dangling findings via the reconcile."""
    out: dict[str, set[str]] = {}
    for raw in TRACE_FIELD_ATTR_RE.findall(html) + TRACE_FIELD_SETATTR_RE.findall(html):
        for item in re.split(r"[,\s]+", raw):
            item = item.strip()
            m = TRACE_FIELD_TOKEN_RE.match(item)
            if m:
                out.setdefault(m.group(1), set()).add(m.group(2))
    return out


def trace_coverage_findings(
    *,
    prd_suc: set[str],
    prd_obj: set[str],
    spec_surf: set[str],
    spec_suc: set[str],
    spec_obj: set[str],
    proto_surf: set[str],
    proto_suc: set[str],
    proto_obj: set[str],
    extra_valid_suc: set[str] | None = None,
    extra_valid_obj: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Three-way reconcile PRD inventory ↔ interaction-spec binding ↔ prototype anchors.

    SUC is compared at the base id level (OP/FLOW children count for their parent)
    to avoid noise; SURF/OBJ are exact.

    `prd_suc`/`prd_obj` are the CURRENT mission's PRD inventory (drives the
    "PRD id never bound" WARN — only this mission is accountable for its own ids).
    `extra_valid_suc`/`extra_valid_obj` are project-level registry ids (other missions'
    objects / use cases) that are *valid to reference* but do NOT make this mission
    responsible for binding them — they widen only the "unknown id" universe so a
    project-level surface anchor isn't flagged TRACE_SPEC_*_UNKNOWN.
    """
    from harness_cli_core.domain.findings import finding

    findings: list[dict[str, Any]] = []

    prd_suc_b = _suc_bases(prd_suc)
    spec_suc_b = _suc_bases(spec_suc)
    proto_suc_b = _suc_bases(proto_suc)
    valid_suc_b = prd_suc_b | _suc_bases(extra_valid_suc or set())
    valid_obj = prd_obj | (extra_valid_obj or set())

    # 1) spec binding references an ID that does not exist upstream (typo / renamed / stale)
    for sid in sorted(spec_suc_b - valid_suc_b):
        findings.append(finding(
            "FAIL", "TRACE_SPEC_SUC_UNKNOWN",
            f"interaction-spec 引用了 PRD / 项目级用例注册表不存在的系统用例 {sid}：疑似 typo / 已改名 / 失效引用。",
            suc=sid,
        ))
    for oid in sorted(spec_obj - valid_obj):
        findings.append(finding(
            "FAIL", "TRACE_SPEC_OBJ_UNKNOWN",
            f"interaction-spec 引用了 PRD / 项目级对象注册表不存在的业务对象 {oid}。",
            obj=oid,
        ))

    # 2) declared in spec binding but not embodied by any prototype anchor (dropped)
    for sid in sorted(spec_surf - proto_surf):
        findings.append(finding(
            "FAIL", "TRACE_SURF_NOT_ANCHORED",
            f"界面边界 {sid} 在 interaction-spec 声明，但原型未植入对应锚点（被改丢或从未体现）。",
            surf=sid,
        ))
    for sid in sorted(spec_suc_b - proto_suc_b):
        findings.append(finding(
            "FAIL", "TRACE_SUC_NOT_ANCHORED",
            f"系统用例 {sid} 在 binding 声明，但原型未植入对应锚点。",
            suc=sid,
        ))
    for oid in sorted(spec_obj - proto_obj):
        findings.append(finding(
            "FAIL", "TRACE_OBJ_NOT_ANCHORED",
            f"业务对象 {oid} 在 binding 声明，但原型未体现对应锚点。",
            obj=oid,
        ))

    # 3) prototype anchors not declared in spec binding (dangling / ID 漂移)
    for sid in sorted(proto_surf - spec_surf):
        findings.append(finding(
            "FAIL", "TRACE_ANCHOR_SURF_DANGLING",
            f"原型锚点 {sid} 未在 interaction-spec 声明：dangling / ID 漂移。",
            surf=sid,
        ))
    for sid in sorted(proto_suc_b - spec_suc_b):
        findings.append(finding(
            "FAIL", "TRACE_ANCHOR_SUC_DANGLING",
            f"原型锚点 {sid} 未在 binding 声明。",
            suc=sid,
        ))
    for oid in sorted(proto_obj - spec_obj):
        findings.append(finding(
            "FAIL", "TRACE_ANCHOR_OBJ_DANGLING",
            f"原型锚点 {oid} 未在 binding 声明。",
            obj=oid,
        ))

    # 4) PRD ID never bound (WARN — may be non-UI; must be justified in surface-model)
    for sid in sorted(prd_suc_b - spec_suc_b):
        findings.append(finding(
            "WARN", "TRACE_PRD_SUC_UNBOUND",
            f"PRD 系统用例 {sid} 未进入任何 interaction binding；若非界面承载请在 surface-model 写明理由。",
            suc=sid,
        ))
    for oid in sorted(prd_obj - spec_obj):
        findings.append(finding(
            "WARN", "TRACE_PRD_OBJ_UNBOUND",
            f"PRD 业务对象 {oid} 未进入任何 interaction binding；若用户不可见请在 surface-model 写明隐藏理由。",
            obj=oid,
        ))

    return findings


def interaction_surface_binding_ids(root: Path, mission: str) -> dict[str, set[str]]:
    """Canonical declared trace binding from `interaction.contract.yaml#surface_bindings`
    (the machine projection of surface-model.md). Empty means the mandatory binding is
    missing and must be reported by the caller."""
    contract = load_control_contract_or_empty(
        mission_stage_dir(root, mission) / "contracts" / "interaction.contract.yaml"
    )
    proto = contract.get("prototype") if isinstance(contract.get("prototype"), dict) else {}
    rows = proto.get("surface_bindings") if isinstance(proto.get("surface_bindings"), list) else []
    surf: set[str] = set()
    suc: set[str] = set()
    obj: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("surf"):
            surf.add(str(row["surf"]).strip())
        for key, target in (("suc", suc), ("obj", obj)):
            value = row.get(key)
            if isinstance(value, list):
                target.update(str(item).strip() for item in value if str(item).strip())
            elif value:
                target.add(str(value).strip())
    return {"surf": surf, "suc": suc, "obj": obj}


def interaction_field_bindings(root: Path, mission: str) -> dict[str, Any]:
    """Declared field-level coverage from `interaction.contract.yaml#surface_bindings`.

    Each binding row may carry `fields: {OBJ-02: [id, title, ...]}` declaring which
    domain fields of an object must be visible on that surface. Returns:
    - `bound_objs`: every OBJ referenced by any binding's `obj`.
    - `declared`: OBJ -> required field set (union across surfaces).
    - `waived`: OBJ ids declared with an explicit empty list (`fields: {OBJ-06: []}`),
      i.e. a deliberate "no field-level coverage" opt-out (justified in surface-model).
    - `objs_with_fields_key`: OBJ ids that appear as a key in some binding's `fields`
      (declared or waived) — used to flag bound objects that never declared fields."""
    contract = load_control_contract_or_empty(
        mission_stage_dir(root, mission) / "contracts" / "interaction.contract.yaml"
    )
    proto = contract.get("prototype") if isinstance(contract.get("prototype"), dict) else {}
    rows = proto.get("surface_bindings") if isinstance(proto.get("surface_bindings"), list) else []
    bound_objs: set[str] = set()
    declared: dict[str, set[str]] = {}
    waived: set[str] = set()
    objs_with_fields_key: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        obj_val = row.get("obj")
        obj_list = obj_val if isinstance(obj_val, list) else ([obj_val] if obj_val else [])
        for o in obj_list:
            o = str(o).strip()
            if o:
                bound_objs.add(o)
        fields = row.get("fields")
        if isinstance(fields, dict):
            for obj_id, flds in fields.items():
                obj_id = str(obj_id).strip()
                if not obj_id:
                    continue
                objs_with_fields_key.add(obj_id)
                items = flds if isinstance(flds, list) else ([flds] if flds else [])
                tokens = {str(f).strip() for f in items if str(f).strip()}
                if tokens:
                    declared.setdefault(obj_id, set()).update(tokens)
                else:
                    waived.add(obj_id)
    return {
        "bound_objs": bound_objs,
        "declared": declared,
        "waived": waived,
        "objs_with_fields_key": objs_with_fields_key,
    }


def field_coverage_findings(
    *,
    bound_objs: set[str],
    declared: dict[str, set[str]],
    waived: set[str],
    objs_with_fields_key: set[str],
    proto_fields: dict[str, set[str]],
) -> list[dict[str, Any]]:
    """Reconcile declared field-level coverage with prototype field anchors.

    Enforcement = 全覆盖强制: every bound OBJ must declare its fields (or explicitly
    waive with `fields: []`); every declared field must be anchored; every prototype
    field anchor must trace to a declared field."""
    from harness_cli_core.domain.findings import finding

    findings: list[dict[str, Any]] = []

    # 1) bound object never declared (or waived) its fields
    for oid in sorted(bound_objs - objs_with_fields_key):
        findings.append(finding(
            "FAIL", "TRACE_OBJ_FIELDS_UNDECLARED",
            f"业务对象 {oid} 已绑定 surface，但未在任何 binding 的 fields 声明可见字段；"
            f"全覆盖强制：请声明 fields[{oid}]=[...]，或确无字段时显式写 fields[{oid}]=[] 并在 surface-model 说明理由。",
            obj=oid,
        ))

    # 2) declared field not embodied by any prototype field anchor
    for oid in sorted(declared):
        missing = declared[oid] - proto_fields.get(oid, set())
        for fld in sorted(missing):
            findings.append(finding(
                "FAIL", "TRACE_OBJ_FIELD_NOT_ANCHORED",
                f"字段 {oid}.{fld} 在 binding 声明为必需可见，但原型未植入 data-field=\"{oid}.{fld}\" 锚点。",
                obj=oid, field=fld,
            ))

    # 3) prototype field anchor not declared (dangling / 未声明字段)
    for oid in sorted(proto_fields):
        allowed = declared.get(oid, set())
        for fld in sorted(proto_fields[oid] - allowed):
            if oid in waived:
                findings.append(finding(
                    "FAIL", "TRACE_FIELD_ANCHOR_ON_WAIVED_OBJ",
                    f"原型为 {oid} 植入了字段锚点 {oid}.{fld}，但 binding 将 {oid} 声明为无字段（fields=[]）；声明与原型矛盾。",
                    obj=oid, field=fld,
                ))
            else:
                findings.append(finding(
                    "FAIL", "TRACE_FIELD_ANCHOR_DANGLING",
                    f"原型字段锚点 {oid}.{fld} 未在 binding 的 fields 声明：dangling / 未声明字段。",
                    obj=oid, field=fld,
                ))
    return findings


def trace_nav_entries(root: Path, mission: str) -> list[dict[str, Any]]:
    """SUC-centric forward-navigation index for the prototype frame shell:
    each entry is a system use case (SUC) and the surfaces that carry it, with the
    surface `page_entry` / `anchor_root` to deep-link the embedded prototype.

    Built from `interaction.contract.yaml#surface_bindings` — the same canonical
    binding source as trace coverage — so the SUC directory never drifts from the
    declared trace spine. The shell consumes this (via the generated `trace-nav.js`
    global); it never re-derives ids from prototype text."""
    contract = load_control_contract_or_empty(
        mission_stage_dir(root, mission) / "contracts" / "interaction.contract.yaml"
    )
    proto = contract.get("prototype") if isinstance(contract.get("prototype"), dict) else {}
    rows = proto.get("surface_bindings") if isinstance(proto, dict) else None
    by_suc: dict[str, list[dict[str, Any]]] = {}
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            entry = {
                "surf": str(row.get("surf") or ""),
                "page_entry": row.get("page_entry"),
                "anchor_root": row.get("anchor_root"),
            }
            raw_suc = row.get("suc")
            suc_list = raw_suc if isinstance(raw_suc, list) else ([raw_suc] if raw_suc else [])
            for s in suc_list:
                s = str(s).strip()
                if s:
                    by_suc.setdefault(s, []).append(entry)
    return [{"suc": s, "surfaces": by_suc[s]} for s in sorted(by_suc)]


_USE_CASE_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$")
_SURFACE_TOKEN_RE = re.compile(r"^[A-Z][A-Z0-9-]+$")
_SUC_TITLE_RE = re.compile(r"^#{2,4}\s*(SUC-[0-9]+)\s*[:：]\s*(.+?)\s*$")


def parse_project_use_cases(root: Path) -> list[dict[str, Any]]:
    """Project-level use-case catalog parsed from
    `project-knowledge/product/workflows/*.md`. Each markdown table row
    `| <id> | <title> | <surfaces> | <priority> |` becomes a use case. The id is
    prefix-agnostic (e.g. BUC-TF-*); header / separator rows are skipped. Surfaces
    are split on `+` / `,` / whitespace into stable surface tokens (e.g. SUR-*)."""
    wf_dir = root / "project-knowledge" / "product" / "workflows"
    out: list[dict[str, Any]] = []
    if not wf_dir.exists():
        return out
    seen: set[str] = set()
    for md in sorted(wf_dir.glob("*.md")):
        for line in read_text_if_exists(md).splitlines():
            if "|" not in line:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2 or not _USE_CASE_ID_RE.match(cells[0]):
                continue
            uc_id = cells[0]
            if uc_id in seen:
                continue
            seen.add(uc_id)
            surfaces = []
            if len(cells) >= 3:
                surfaces = [s for s in re.split(r"[+,\s]+", cells[2]) if _SURFACE_TOKEN_RE.match(s)]
            out.append({
                "id": uc_id,
                "title": cells[1],
                "surfaces": surfaces,
                "priority": cells[3] if len(cells) >= 4 else "",
            })
    return out


def parse_project_surfaces(root: Path) -> list[dict[str, Any]]:
    """Project-level stable UI surface registry parsed from
    `project-knowledge/product/ui-surfaces/*.md`. Each markdown table row
    `| <id> | <name> | <type> | <responsibility> |` becomes a surface. The id is
    prefix-agnostic (e.g. SUR-*); header / separator rows are skipped."""
    surf_dir = root / "project-knowledge" / "product" / "ui-surfaces"
    out: list[dict[str, Any]] = []
    if not surf_dir.exists():
        return out
    seen: set[str] = set()
    for md in sorted(surf_dir.glob("*.md")):
        for line in read_text_if_exists(md).splitlines():
            if "|" not in line:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2 or not _USE_CASE_ID_RE.match(cells[0]):
                continue
            sid = cells[0]
            if sid in seen:
                continue
            seen.add(sid)
            out.append({
                "id": sid,
                "name": cells[1] if len(cells) >= 2 else "",
                "type": cells[2] if len(cells) >= 3 else "",
                "desc": cells[3] if len(cells) >= 4 else "",
            })
    return out


def parse_project_system_use_cases(root: Path) -> list[dict[str, Any]]:
    """Project-level **system use case (SUC)** registry parsed from
    `project-knowledge/product/system-use-cases/*.md` — the sediment of system use
    cases already realized by the long-lived prototype across past missions.

    Table row:
    `| <SUC id> | <名称> | <实现 BUC> | <承载 surface> | <入口页 page_entry> | <锚点 anchor_root> | <来源> |`.
    Header / separator rows are skipped. Surfaces split on `+` / `,` / whitespace.
    Returns `{id, title, surfaces, page_entry, anchor_root}` per SUC."""
    suc_dir = root / "project-knowledge" / "product" / "system-use-cases"
    out: list[dict[str, Any]] = []
    if not suc_dir.exists():
        return out
    seen: set[str] = set()
    for md in sorted(suc_dir.glob("*.md")):
        for line in read_text_if_exists(md).splitlines():
            if "|" not in line:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2 or not _USE_CASE_ID_RE.match(cells[0]):
                continue
            sid = cells[0]
            if sid in seen:
                continue
            seen.add(sid)
            surfaces = []
            if len(cells) >= 4:
                surfaces = [s for s in re.split(r"[+,\s]+", cells[3]) if _SURFACE_TOKEN_RE.match(s)]
            out.append({
                "id": sid,
                "title": cells[1] if len(cells) >= 2 else "",
                "surfaces": surfaces,
                "page_entry": cells[4] if len(cells) >= 5 else "",
                "anchor_root": cells[5] if len(cells) >= 6 else "",
            })
    return out


def project_object_registry_ids(root: Path) -> set[str]:
    """Project-level stable business-object ids (OBJ-xx) from the aggregated registry
    `project-knowledge/product/business-objects.md`. Used to widen the valid object
    universe of trace-coverage so prototypes can carry trace anchors for objects that
    were defined by earlier missions' PRD outputs (not only the current mission's
    business-object-analysis)."""
    text = read_text_if_exists(root / "project-knowledge" / "product" / "business-objects.md")
    return set(TRACE_OBJ_RE.findall(text))


def project_use_case_ids(root: Path) -> set[str]:
    """Project-level use-case ids (e.g. BUC-*) from the workflows catalog, to widen the
    valid system-use-case universe of trace-coverage for project-level surfaces."""
    return {uc["id"] for uc in parse_project_use_cases(root)}


def suc_titles(root: Path, mission: str) -> dict[str, str]:
    """SUC id -> human title from the mission `use-case-model.md` headings
    (`### SUC-01：展示 Work Graph Board`)."""
    text = read_text_if_exists(interaction_product_dir(root, mission) / "use-case-model.md")
    titles: dict[str, str] = {}
    for line in text.splitlines():
        m = _SUC_TITLE_RE.match(line.strip())
        if m:
            titles.setdefault(m.group(1), m.group(2))
    return titles


def _mission_surface_context(root: Path, mission: str) -> dict[str, Any]:
    """From the mission contract derive: baseline SUR set the mission touches, and a
    SUR -> {page_entry, anchor_root} deep-link map (via surface_baseline.baseline_ref
    joined with surface_bindings.page_entry/anchor_root)."""
    contract = load_control_contract_or_empty(
        mission_stage_dir(root, mission) / "contracts" / "interaction.contract.yaml"
    )
    proto = contract.get("prototype") if isinstance(contract.get("prototype"), dict) else {}
    bindings = proto.get("surface_bindings") if isinstance(proto, dict) else []
    binding_by_surf: dict[str, dict[str, Any]] = {}
    if isinstance(bindings, list):
        for row in bindings:
            if isinstance(row, dict) and row.get("surf"):
                binding_by_surf[str(row["surf"])] = row
    baseline = contract.get("surface_baseline") if isinstance(contract.get("surface_baseline"), dict) else {}
    baseline_rows = baseline.get("surfaces") if isinstance(baseline, dict) else []
    touched_sur: set[str] = set()
    sur_entry: dict[str, dict[str, Any]] = {}
    # (a) baseline-mapped: a stable SUR touched via a SURF-* this mission works on.
    if isinstance(baseline_rows, list):
        for row in baseline_rows:
            if not isinstance(row, dict):
                continue
            ref = str(row.get("baseline_ref") or "").strip()
            if not ref or ref.lower() in {"none", "无", "-"}:
                continue
            touched_sur.add(ref)
            binding = binding_by_surf.get(str(row.get("id") or ""))
            if binding and binding.get("page_entry"):
                sur_entry[ref] = {
                    "page_entry": binding.get("page_entry"),
                    "anchor_root": binding.get("anchor_root"),
                }
    # (b) direct: a stable SUR-* that has its own backfilled binding row carries its
    #     own page_entry / anchor_root (project-level surfaces, not "touched" by this
    #     mission but still navigable in the frame).
    for surf_id, binding in binding_by_surf.items():
        if surf_id.startswith("SUR-") and binding.get("page_entry") and surf_id not in sur_entry:
            sur_entry[surf_id] = {
                "page_entry": binding.get("page_entry"),
                "anchor_root": binding.get("anchor_root"),
            }
    return {"touched_sur": touched_sur, "sur_entry": sur_entry}


_FRAME_PAGE_ENTRY_RE = re.compile(r"^(?:#.+|[\w./-]+\.html(?:#.*)?)$")


def prototype_frame_nav(root: Path, mission: str) -> dict[str, Any]:
    """System-use-case navigation index for the prototype frame shell.

    左侧导航项是**遍历系统用例(SUC)生成的——一个 SUC 一条**,不是按页面 / surface 去重。
    一个 SUC 已经包含「涉及哪些页面、怎么操作、哪些状态、哪些 BO」;frame 左侧是 SUC 清单,
    点一条 → 右侧用原型页面 + 交互把该 SUC 表现出来。

    每个 SUC 条目:
    - `page_entry` / `anchor_root`: 该 SUC 的入口页(它第一个可路由 surface 所在页;
      界面边界 SURF-* 优先于共享组件)。
    - `surfaces`: 该 SUC 涉及的界面边界(作为信息,不单独成导航项)。

    业务用例(BUC-*)和组件级界面(timeline / sidebar / composer / drawer / toast)不作为
    左侧导航项——BUC 是更高层的业务意图,组件在所属 SUC 的页面里被操作。

    `focus` = 本任务在制的系统用例(来自本 Mission contract);`project` = 项目级已沉淀
    的系统用例(来自 `project-knowledge/product/system-use-cases/`,即之前 Mission 已实现
    并走查过的能力)。两组同形状:`{id, title, page_entry, anchor_root, surfaces, focus}`。
    """
    suc_title_map = suc_titles(root, mission)

    def routable_surfaces(entry: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            surf
            for surf in (entry.get("surfaces", []) or [])
            if _FRAME_PAGE_ENTRY_RE.match(str(surf.get("page_entry") or "").strip())
        ]

    focus: list[dict[str, Any]] = []
    focus_ids: set[str] = set()
    for entry in trace_nav_entries(root, mission):
        uc = str(entry.get("suc", "")).strip()
        if not uc.startswith("SUC-"):  # 左侧只列系统用例
            continue
        rs = routable_surfaces(entry)
        if not rs:
            continue
        primary = rs[0]  # 入口页:第一个可路由 surface(SURF 界面边界优先)
        focus_ids.add(uc)
        focus.append({
            "id": uc,
            "title": suc_title_map.get(uc, ""),
            "page_entry": str(primary.get("page_entry")).strip(),
            "anchor_root": primary.get("anchor_root"),
            "surfaces": [
                str(s.get("surf")).strip()
                for s in (entry.get("surfaces", []) or [])
                if str(s.get("surf") or "").strip()
            ],
            "focus": True,
        })

    # 项目级已沉淀系统用例(之前 Mission 已实现的能力)
    project: list[dict[str, Any]] = []
    for suc in parse_project_system_use_cases(root):
        pe = str(suc.get("page_entry") or "").strip()
        if suc["id"] in focus_ids or not _FRAME_PAGE_ENTRY_RE.match(pe):
            continue
        project.append({
            "id": suc["id"],
            "title": suc.get("title", ""),
            "page_entry": pe,
            "anchor_root": suc.get("anchor_root") or None,
            "surfaces": suc.get("surfaces", []),
            "focus": False,
        })
    return {"mission_id": mission, "focus": focus, "project": project}


def resolve_feedback_routing(
    root: Path,
    mission: str,
    *,
    surface: str = "",
    suc: str = "",
    obj: str = "",
) -> dict[str, Any]:
    """Given a prototype anchor (SURF / SUC / OBJ), route human feedback back to the
    interaction-spec sections, the surface binding and the upstream PRD docs that own
    the ID — so feedback on a page maps to the docs to edit."""
    from harness_cli_core.infra.runtime_paths import relpath

    query = {"surface": surface, "suc": suc, "obj": obj}
    ids = [v for v in (surface, suc, obj) if v]

    # 1) where the id is referenced in the interaction-spec / interaction.md
    search_paths: list[Path] = []
    spec_dir = interaction_spec_dir(root, mission)
    if spec_dir.exists():
        search_paths.extend(p for p in sorted(spec_dir.rglob("*.md")) if p.is_file())
    interaction_md = interaction_stage_artifact_dir(root, mission) / "interaction.md"
    if interaction_md.exists():
        search_paths.append(interaction_md)

    references: list[dict[str, Any]] = []
    for path in search_paths:
        for line_no, line in enumerate(read_text_if_exists(path).splitlines(), start=1):
            if any(token and token in line for token in ids):
                references.append({
                    "path": relpath(root, path),
                    "line": line_no,
                    "text": line.strip()[:200],
                })

    # 2) the surface binding(s) from the contract — bidirectional & forward-navigable:
    #    SURF / SUC / OBJ -> surface(s) + page_entry + anchor_root. Querying by SUC or
    #    OBJ scans every binding (one SUC/OBJ can be carried by multiple surfaces);
    #    querying by SURF returns its single row. `binding` (singular) is kept for
    #    backward compatibility; `bindings` (list) carries the full forward-navigation
    #    result.
    contract = load_control_contract_or_empty(
        mission_stage_dir(root, mission) / "contracts" / "interaction.contract.yaml"
    )
    proto = contract.get("prototype") if isinstance(contract.get("prototype"), dict) else {}
    rows = proto.get("surface_bindings") if isinstance(proto, dict) else None
    bindings: list[dict[str, Any]] = []
    if isinstance(rows, list):
        suc_base = _suc_base(suc) if suc else ""
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_suc = row.get("suc")
            row_suc_set = {str(x).strip() for x in row_suc if str(x).strip()} if isinstance(row_suc, list) else ({str(row_suc).strip()} if row_suc else set())
            row_obj = row.get("obj")
            row_obj_set = {str(x).strip() for x in row_obj if str(x).strip()} if isinstance(row_obj, list) else ({str(row_obj).strip()} if row_obj else set())
            matched = (
                (bool(surface) and str(row.get("surf") or "") == surface)
                or (bool(suc) and suc_base in _suc_bases(row_suc_set))
                or (bool(obj) and obj in row_obj_set)
            )
            if matched:
                bindings.append(row)
    if surface:
        binding = next((r for r in bindings if str(r.get("surf") or "") == surface), None)
    else:
        binding = bindings[0] if bindings else None

    # 3) upstream owners of the ID (回流 PRD candidates)
    upstream: list[str] = []
    if suc:
        upstream.append("product/use-case-model.md（SUC 定义；若要改的是系统用例本身，回流 PRD）")
    if obj:
        upstream.append("product/business-object-analysis.md（OBJ 定义；若要改的是业务对象本身，回流 PRD）")

    forward_nav = [
        {
            "surf": str(r.get("surf") or ""),
            "page_entry": r.get("page_entry"),
            "anchor_root": r.get("anchor_root"),
        }
        for r in bindings
    ]

    return {
        "mission_id": mission,
        "query": query,
        "spec_references": references,
        "binding": binding,
        "bindings": bindings,
        "forward_nav": forward_nav,
        "upstream_candidates": upstream,
        "hint": "界面/交互层面的反馈改 interaction-spec 对应段落并回写原型；若涉及 SUC/OBJ 语义本身，停下回流 PRD。正向定位：forward_nav 给出承载该 SURF/SUC/OBJ 的 surface 及 page_entry / anchor_root，打开主原型对应入口即可。",
    }


def build_trace_index(
    *,
    mission: str,
    prd_suc: set[str],
    prd_obj: set[str],
    spec_surf: set[str],
    spec_suc: set[str],
    spec_obj: set[str],
    proto_surf: set[str],
    proto_suc: set[str],
    proto_obj: set[str],
    status: str,
) -> dict[str, Any]:
    """Low-noise audit artifact committed to prototype_project_root for 回溯."""
    return {
        "type": "trace_index",
        "version": 1,
        "mission_id": mission,
        "status": status,
        "object_axis": "OBJ",
        "prd_inventory": {"suc": sorted(prd_suc), "obj": sorted(prd_obj)},
        "spec_binding": {
            "surf": sorted(spec_surf),
            "suc": sorted(spec_suc),
            "obj": sorted(spec_obj),
        },
        "prototype_anchors": {
            "surf": sorted(proto_surf),
            "suc": sorted(proto_suc),
            "obj": sorted(proto_obj),
        },
    }


def html_visible_product_copy(text: str) -> str:
    """Return the static, user-visible product markup: HTML comments, ``<script>``
    and ``<style>`` blocks removed. Trace ids carried in JS fixture data / code
    comments and CSS are not visible product copy and must not be scanned as
    review/spec annotations leaking into the UI."""
    without_comments = html_without_comments(text)
    return re.sub(
        r"(?is)<(script|style)\b[^>]*>.*?</\1>",
        " ",
        without_comments,
    )


_FIELD_ANCHORED_EL_RE = re.compile(
    r"""<([a-zA-Z][\w-]*)\b[^>]*\bdata-field\s*=\s*["'][^"']*["'][^>]*>(.*?)</\1>""",
    re.IGNORECASE | re.DOTALL,
)


def strip_field_anchored_text(html: str) -> str:
    """Blank the inner text of elements that declare a domain field anchor
    (``data-field``). Those values are declared, field-level trace-covered domain
    data deliberately shown in the UI (e.g. a Work Graph board node id ``REQ-…``,
    a scenario-like domain id) — not review/spec annotation. The operable-prototype
    forbidden-copy scan runs on the result so genuine spec/review leakage in normal
    prose is still caught, while declared domain field values are not false-flagged."""
    prev = None
    out = html
    # bounded fixpoint so nested data-field elements collapse outer-after-inner
    for _ in range(8):
        if prev == out:
            break
        prev = out
        out = _FIELD_ANCHORED_EL_RE.sub(lambda m: f"<{m.group(1)}></{m.group(1)}>", out)
    return out


def operable_visible_text(html: str) -> str:
    """User-visible product text for the operable-prototype forbidden-copy scan.

    Pipeline: drop ``<script>``/``<style>``/comments, blank declared domain field
    values (``data-field``), then strip all remaining tags so element *attributes*
    (``data-testid``, ``onclick``, ``aria-label``, ``class`` …) are not scanned —
    those are not user-visible copy. The scan then catches only review / spec /
    coverage wording a user would actually read in the UI, not domain ids that a
    real product legitimately renders or wires into testids/handlers."""
    no_fields = strip_field_anchored_text(html_visible_product_copy(html))
    return re.sub(r"<[^>]+>", " ", no_fields)


# ---------------------------------------------------------------------------
# Locator helpers
# ---------------------------------------------------------------------------


def scenario_rows_with_locator_obligation(text: str) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        first_cell = cells[0] if cells else ""
        # A locator obligation belongs to a row that *declares* an E2E/scenario
        # obligation (id in its leading cell) or carries a P0/P1 priority — not
        # to rows that merely reference a scenario id in a trace column.
        if re.search(r"\b(?:E2E|SCN)-[A-Za-z0-9._-]+\b", first_cell) or re.search(r"\bP[01]\b", line):
            rows.append((idx, line))
    return rows


_BACKTICK_TESTID_RE = re.compile(r"`[^`]*[a-z][a-z0-9]*-[a-z0-9][^`]*`")


def row_has_locator_strategy(row: str) -> bool:
    from harness_cli_core.domain.findings import is_placeholder_text

    lowered = row.lower()
    if any(
        token in lowered
        for token in (
            "data-testid",
            "locator",
            "getbyrole",
            "getbylabel",
            "aria",
            "accessibility",
            "role=",
        )
    ):
        return not is_placeholder_text(row)
    # A backtick-quoted kebab-case identifier (e.g. `board-lanes`,
    # `node-card-<nodeId>`) is a declared data-testid locator strategy.
    if _BACKTICK_TESTID_RE.search(row):
        return not is_placeholder_text(row)
    return False


# ---------------------------------------------------------------------------
# Alignment source map
# ---------------------------------------------------------------------------


def alignment_source_paths(root: Path, mission: str) -> dict[str, Path]:
    stage_dir = mission_stage_dir(root, mission)
    contracts = stage_dir / "contracts"
    product_dir = interaction_product_dir(root, mission)
    return {
        "mission_contract": root
        / "harness-runtime"
        / "harness"
        / "missions"
        / mission
        / "mission-contract.md",
        "product_definition": product_dir / "product-definition.md",
        "use_case_model": product_dir / "use-case-model.md",
        "acceptance_scenarios": product_dir / "acceptance-scenarios.md",
        "product_domain_model": product_dir / "product-domain-model.md",
        "product_evidence": product_dir / "product-evidence.md",
        "prd_contract": contracts / "prd.contract.yaml",
        "interaction_spec": interaction_spec_dir(root, mission),
        "interaction_contract": contracts / "interaction.contract.yaml",
        "solution_contract": contracts / "solution.contract.yaml",
        "tech_design_contract": contracts / "tech-design.contract.yaml",
        "execution_brief_contract": contracts / "execution-brief.contract.yaml",
        "verification_report_contract": contracts / "verification-report.contract.yaml",
        # 两层累积：项目级 system-use-cases（SUC 注册表 + 累积 behavior-graph）。
        # interaction project 会把这些项目级累积 SUC 合并进生成视图，故它们也是合法上游来源。
        "project_system_use_cases": root
        / "project-knowledge"
        / "product"
        / "system-use-cases",
    }


def collect_refs_from_path(path: Path) -> set[str]:
    if path.is_dir():
        refs: set[str] = set()
        for child in sorted(path.rglob("*")):
            if child.is_file() and child.suffix in {".md", ".yaml", ".yml", ".ts", ".tsx", ".json"}:
                refs.update(TRACE_REF_RE.findall(read_text_if_exists(child)))
        return refs
    if path.suffix in {".yaml", ".yml", ".json"}:
        return collect_refs_from_value(load_control_contract_or_empty(path), TRACE_REF_RE)
    return set(TRACE_REF_RE.findall(read_text_if_exists(path)))


def collect_known_upstream_refs(root: Path, mission: str, stage: str) -> set[str]:
    paths = alignment_source_paths(root, mission)
    order_by_stage = {
        "interaction": [
            "mission_contract",
            "product_definition",
            "use_case_model",
            "acceptance_scenarios",
            "product_domain_model",
            "product_evidence",
            "prd_contract",
        ],
        "solution": [
            "mission_contract",
            "product_definition",
            "use_case_model",
            "acceptance_scenarios",
            "product_domain_model",
            "product_evidence",
            "prd_contract",
            "interaction_spec",
            "interaction_contract",
        ],
        "technical_analysis": [
            "mission_contract",
            "product_definition",
            "use_case_model",
            "acceptance_scenarios",
            "product_domain_model",
            "product_evidence",
            "prd_contract",
            "interaction_spec",
            "interaction_contract",
            "solution_contract",
        ],
        "breakdown": [
            "mission_contract",
            "product_definition",
            "use_case_model",
            "acceptance_scenarios",
            "product_domain_model",
            "product_evidence",
            "prd_contract",
            "interaction_spec",
            "interaction_contract",
            "solution_contract",
            "tech_design_contract",
        ],
        "verify": [
            "mission_contract",
            "product_definition",
            "use_case_model",
            "acceptance_scenarios",
            "product_domain_model",
            "product_evidence",
            "prd_contract",
            "interaction_spec",
            "interaction_contract",
            "solution_contract",
            "tech_design_contract",
            "execution_brief_contract",
        ],
    }
    refs: set[str] = set()
    for key in order_by_stage.get(stage, []):
        refs.update(collect_refs_from_path(paths[key]))
    # 两层累积：interaction 起，生成视图（interaction_spec/views）会合并项目级累积图的
    # SUC-TF-*，故项目级 system-use-cases（注册表 + 累积 behavior-graph）也是合法上游来源，
    # 否则合并进来的项目级 SUC 会被误判为 BROKEN_UPSTREAM_TRACE。
    if stage in order_by_stage:
        refs.update(collect_refs_from_path(paths["project_system_use_cases"]))
    return refs


def alignment_current_payload(
    root: Path, mission: str, stage: str
) -> tuple[str, object, Path | None]:
    paths = alignment_source_paths(root, mission)
    if stage == "interaction":
        return (
            stage,
            {
                "spec_refs": sorted(collect_refs_from_path(paths["interaction_spec"])),
                "contract_refs": sorted(collect_refs_from_path(paths["interaction_contract"])),
            },
            paths["interaction_spec"],
        )
    if stage == "solution":
        path = paths["solution_contract"]
    elif stage == "technical_analysis":
        path = paths["tech_design_contract"]
    elif stage == "breakdown":
        path = paths["execution_brief_contract"]
    elif stage == "verify":
        path = paths["verification_report_contract"]
    else:
        path = None
    return stage, load_control_contract_or_empty(path) if path else {}, path


# ---------------------------------------------------------------------------
# Feedback-sync helpers (shared by interaction + prototype-as-frontend)
# ---------------------------------------------------------------------------


def contract_feedback_sync_findings(
    root: Path, mission: str, contract_name: str
) -> list[dict[str, object]]:
    from harness_cli_core.domain.findings import finding, is_placeholder_text
    from harness_cli_core.infra.runtime_paths import relpath

    contract_path = mission_stage_dir(root, mission) / "contracts" / contract_name
    contract = load_control_contract_or_empty(contract_path)
    findings: list[dict[str, object]] = []
    feedback = (
        contract.get("feedback_sync")
        if isinstance(contract.get("feedback_sync"), dict)
        else {}
    )
    unsynced = feedback.get("unsynced_feedback_count")
    if is_placeholder_text(unsynced):
        return findings
    try:
        unsynced_count = int(str(unsynced))
    except ValueError:
        unsynced_count = 1
    if unsynced_count > 0:
        findings.append(
            finding(
                "FAIL",
                "FEEDBACK_NOT_SYNCED",
                f"{contract_name} records unsynced user/reviewer feedback.",
                path=relpath(root, contract_path),
                unsynced_feedback_count=unsynced_count,
            )
        )
    return findings
