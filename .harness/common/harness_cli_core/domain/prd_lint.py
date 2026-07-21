"""Pure helpers for PRD-stage anti-pattern + domain-model lint commands.

Used by ``harness prd anti-pattern-scan`` / ``prd domain-model-lint`` and
``harness spec delta-lint``. All scanning is text-only and deterministic so
hooks / lint pipelines can call them as a single domain function and get the
same findings back.
"""

from __future__ import annotations

import re
from typing import Any


# Anti-pattern rule definitions (prd.workflow.md Step 4)
PRD_VAGUE_TERMS: frozenset[str] = frozenset(
    {
        "好用",
        "快速",
        "直观",
        "简单",
        "高效",
        "流畅",
        "友好",
        "方便",
        "robust",
        "fast",
        "intuitive",
        "simple",
        "efficient",
        "user-friendly",
        "easy",
        "smooth",
        "good",
        "nice",
        "better",
        "improved",
    }
)

PRD_IMPL_LEAK_PATTERNS: list[str] = [
    r"\b(React|Vue|Angular|Django|Flask|Express|Spring|Hibernate|ORM|SDK|API|REST|GraphQL|"
    r"PostgreSQL|MongoDB|Redis|Elasticsearch|Kubernetes|Docker|Terraform)\b",
]

DOMAIN_MODEL_REQUIRED_SECTIONS: tuple[str, ...] = (
    "Domain Intent",
    "Strategic DDD",
    "Tactical DDD",
    "Rules & Constraints",
    "Traceability",
    "Downstream Guidance",
)

DOMAIN_MODEL_REQUIRED_SUBSECTIONS: tuple[str, ...] = (
    "Bounded Contexts",
    "Context Map",
    "Ubiquitous Language",
    "Aggregates",
    "Domain Commands",
    "Domain Events",
    "Invariants",
    "State Machines",
    "Permission Matrix",
)

DOMAIN_MODEL_TECH_LEAK_PATTERNS: list[str] = [
    *PRD_IMPL_LEAK_PATTERNS,
    r"(?i)\b(database|db table|table|column|schema migration|endpoint|route|controller|repository|"
    r"cache|message queue|Kafka|RabbitMQ|HTTP API|/api/|SQL|MySQL|PostgreSQL|Redis)\b",
]


def compute_ignore_lines(text: str, marker_prefix: str) -> set[int]:
    """Return 1-based line numbers inside ``<!-- {prefix}-start -->`` ...
    ``<!-- {prefix}-end -->`` blocks so authors can fence narrow regions
    (e.g. glossary tables that intentionally cite SDK / API) without
    dropping the regex on the rest of the document.
    """
    start_tag = f"<!-- {marker_prefix}-start -->"
    end_tag = f"<!-- {marker_prefix}-end -->"
    ignored: set[int] = set()
    inside = False
    for line_no, line in enumerate(text.splitlines(), 1):
        if start_tag in line:
            inside = True
            ignored.add(line_no)
            continue
        if end_tag in line:
            ignored.add(line_no)
            inside = False
            continue
        if inside:
            ignored.add(line_no)
    return ignored


def markdown_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections[title] = text[start:end].strip()
    return sections


def has_heading(text: str, heading: str) -> bool:
    return bool(re.search(rf"^#+\s+{re.escape(heading)}\s*$", text, flags=re.MULTILINE))


def section_has_content(body: str) -> bool:
    meaningful = []
    for raw in body.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("|---") or stripped.startswith("---"):
            continue
        if stripped.startswith("### "):
            continue
        meaningful.append(stripped)
    return bool(meaningful)


def is_na_with_reason(line: str) -> bool:
    """Return True when the line is **not** an unjustified N/A entry.

    The legacy behavior (preserved here) returns True both when the line
    isn't an N/A entry at all AND when it does carry a reason — callers
    that walk every line append a finding only when this returns ``False``.
    """
    lowered = line.lower()
    if "n/a" not in lowered and "不适用" not in line:
        return True
    return any(marker in lowered for marker in ("because", "reason", "not applicable because")) or any(
        marker in line for marker in ("因为", "由于", "原因", "理由")
    )


def scan_anti_patterns(text: str) -> list[dict[str, Any]]:
    """Scan PRD text for 5 anti-pattern categories and return typed findings."""
    findings: list[dict[str, Any]] = []
    ignored_lines = compute_ignore_lines(text, "prd-anti-pattern-ignore")

    # 1. Vague adjectives
    for line_no, line in enumerate(text.splitlines(), 1):
        if line_no in ignored_lines:
            continue
        words = set(w.lower().rstrip(".,;:!") for w in line.split())
        hits = words & PRD_VAGUE_TERMS
        if hits:
            findings.append(
                {
                    "rule": "vague_adjective",
                    "location": f"line {line_no}",
                    "evidence": ", ".join(sorted(hits)),
                    "message": f"Vague adjective(s) found: {', '.join(sorted(hits))}. Replace with measurable criteria.",
                }
            )

    # 2. Implementation leaks
    for pattern in PRD_IMPL_LEAK_PATTERNS:
        for m in re.finditer(pattern, text):
            line_no = text[: m.start()].count(chr(10)) + 1
            if line_no in ignored_lines:
                continue
            findings.append(
                {
                    "rule": "implementation_leak",
                    "location": f"line {line_no}",
                    "evidence": m.group(0),
                    "message": (
                        f"Implementation detail '{m.group(0)}' leaked into requirement text. "
                        "Replace with capability description."
                    ),
                }
            )

    # 3. Unmeasurable indicators (heuristic on trace anchor lines)
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(("REQ-", "SCN-", "RULE-")):
            rest = stripped.split(":", 1)[-1] if ":" in stripped else stripped
            has_digit = any(c.isdigit() for c in rest)
            has_gwt = any(
                kw in rest for kw in ("GIVEN", "WHEN", "THEN", " GIVEN ", " WHEN ", " THEN ")
            )
            if not has_digit and not has_gwt and len(rest) > 10:
                findings.append(
                    {
                        "rule": "unmeasurable",
                        "location": f"line {line_no}",
                        "evidence": rest[:80],
                        "message": (
                            "Trace anchor line lacks quantitative criteria or Given/When/Then "
                            "structure. Add measurable acceptance criteria."
                        ),
                    }
                )

    return findings


def scan_domain_model(
    text: str,
    *,
    product_definition_text: str | None = None,
    contract: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    sections = markdown_sections(text)

    def add(code: str, rule: str, location: str, evidence: str, message: str) -> None:
        findings.append(
            {
                "code": code,
                "rule": rule,
                "location": location,
                "evidence": evidence,
                "message": message,
            }
        )

    for section in DOMAIN_MODEL_REQUIRED_SECTIONS:
        body = sections.get(section)
        if body is None:
            add(
                "missing_domain_model_section",
                "missing_required_section",
                section,
                section,
                f"product-domain-model.md must include section '## {section}'.",
            )
        elif not section_has_content(body):
            add(
                "empty_domain_model_section",
                "empty_required_section",
                section,
                section,
                f"section '## {section}' must contain concrete modeling content or an N/A reason.",
            )

    for heading in DOMAIN_MODEL_REQUIRED_SUBSECTIONS:
        if not has_heading(text, heading):
            code = {
                "Bounded Contexts": "missing_bounded_context",
                "Aggregates": "missing_aggregate_root",
                "Domain Commands": "missing_domain_command",
                "Domain Events": "missing_domain_event",
                "Invariants": "missing_invariant_trace",
                "State Machines": "missing_state_transition",
                "Permission Matrix": "missing_permission_matrix",
            }.get(heading, "missing_domain_model_subsection")
            add(
                code,
                "missing_required_subsection",
                heading,
                heading,
                f"DDD domain model must include subsection '{heading}' or mark it N/A with a reason.",
            )

    domain_ignored_lines = compute_ignore_lines(text, "domain-model-lint-ignore")

    for line_no, line in enumerate(text.splitlines(), 1):
        if line_no in domain_ignored_lines:
            continue
        if not is_na_with_reason(line):
            add(
                "na_without_reason",
                "unjustified_not_applicable",
                f"line {line_no}",
                line.strip()[:120],
                "N/A / 不适用 entries must include a reason.",
            )

    for pattern in DOMAIN_MODEL_TECH_LEAK_PATTERNS:
        for match in re.finditer(pattern, text):
            line_no = text[: match.start()].count(chr(10)) + 1
            if line_no in domain_ignored_lines:
                continue
            add(
                "technical_leakage_in_domain_model",
                "technical_leakage",
                f"line {line_no}",
                match.group(0),
                "Product domain model must describe business semantics, not implementation choices.",
            )

    if has_heading(text, "State Machines"):
        state_body = ""
        for title, body in sections.items():
            if "State Machines" in body or title == "Tactical DDD":
                state_body = body
                break
        state_text = state_body or text
        if "From State" in state_text or "To State" in state_text:
            required = (
                "From State",
                "To State",
                "Trigger",
                "Actor",
                "Preconditions",
                "Invalid Transitions",
            )
            missing = [item for item in required if item not in state_text]
            if missing:
                add(
                    "invalid_state_machine_shape",
                    "state_machine_missing_columns",
                    "State Machines",
                    ", ".join(missing),
                    "State machine must cover from/to state, trigger, actor, preconditions, and invalid transitions.",
                )

    if has_heading(text, "Permission Matrix"):
        required = ("Actor", "Command", "State", "Allowed", "Reason")
        missing = [item for item in required if item not in text]
        if missing:
            add(
                "invalid_permission_matrix_shape",
                "permission_matrix_missing_columns",
                "Permission Matrix",
                ", ".join(missing),
                "Permission matrix must cover actor, command, state, allowed decision, and reason.",
            )

    if product_definition_text:
        requirement_ids = sorted(
            set(re.findall(r"\b(?:REQ|SCN|US|UC|RULE)-[A-Za-z0-9-]+\b", product_definition_text))
        )
        traceability = sections.get("Traceability", "")
        for req_id in requirement_ids:
            if req_id not in traceability:
                add(
                    "untraced_requirement",
                    "missing_requirement_trace",
                    "Traceability",
                    req_id,
                    f"{req_id} appears in product-definition.md but is not traced to a domain element.",
                )

    if contract:
        domain_model = contract.get("domain_model")
        if not isinstance(domain_model, dict):
            add(
                "missing_domain_model_contract",
                "missing_contract_domain_model",
                "contracts/prd.contract.yaml",
                "domain_model",
                "prd.contract.yaml must include structured domain_model fields aligned with product-domain-model.md.",
            )
        else:
            required_keys = (
                "bounded_contexts",
                "aggregates",
                "commands",
                "events",
                "invariants",
                "state_machines",
                "permission_rules",
                "modeling_risks",
            )
            for key in required_keys:
                if key not in domain_model:
                    add(
                        "missing_domain_model_contract_field",
                        "missing_contract_domain_model_field",
                        f"domain_model.{key}",
                        key,
                        f"prd.contract.yaml domain_model must include '{key}'.",
                    )

    return findings
