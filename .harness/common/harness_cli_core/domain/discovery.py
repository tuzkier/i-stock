"""Pure domain constants for discovery stage commands."""

from __future__ import annotations


GRAPHIFY_INDEX_FRESH_HOURS: int = 24


# Keywords in mission-contract.md that trigger discovery's dependency-impact
# skill. Order matters only for the first-match wins log; multiple keywords
# mapping to the same signal id collapse to one reason in the output.
DEPENDENCY_TRIGGER_KEYWORDS: tuple[tuple[str, str], ...] = (
    # Data model / schema / migration signals
    ("数据模型", "data_model"),
    ("data model", "data_model"),
    ("schema", "schema_change"),
    ("数据迁移", "data_migration"),
    ("migration", "data_migration"),
    ("DDL", "ddl_change"),
    # External system / API / integration signals
    ("外部业务系统", "external_system"),
    ("external system", "external_system"),
    ("third-party", "external_system"),
    ("third party", "external_system"),
    ("外部 API", "external_api"),
    ("external api", "external_api"),
    ("integration", "integration"),
    ("webhook", "integration"),
    # Infrastructure / deployment signals
    ("基础设施", "infrastructure"),
    ("infrastructure", "infrastructure"),
    ("deployment", "infrastructure"),
    ("CI/CD", "infrastructure"),
)
