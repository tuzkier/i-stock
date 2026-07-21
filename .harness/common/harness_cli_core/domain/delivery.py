"""Pure path helpers for delivery stage commands.

Loading helpers live in :mod:`harness_cli_core.domain.contracts`
(``load_control_contract``) and :mod:`harness_cli_core.domain.verification`
(``verify_report_path``).
"""

from __future__ import annotations

from pathlib import Path


def delivery_contract_path(root: Path, mission: str) -> Path:
    return (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission
        / "contracts"
        / "delivery.contract.yaml"
    )


def tech_design_contract_path(root: Path, mission: str) -> Path:
    return (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission
        / "contracts"
        / "tech-design.contract.yaml"
    )
from harness_cli_core.domain.graph_operations import (
    graph_operation_input_nodes,
    graph_operation_output_nodes,
    operation_type_tree,
    validate_graph_operation_structure,
)

__all__ = [
    "graph_operation_input_nodes",
    "graph_operation_output_nodes",
    "operation_type_tree",
    "validate_graph_operation_structure",
]
