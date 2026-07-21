from __future__ import annotations

from typing import Any

from .collections import unique


def operation_type_tree(operation: dict[str, Any]) -> list[str]:
    operation_type = str(operation.get("type") or "")
    values = [operation_type] if operation_type else []
    if operation_type == "batch" and isinstance(operation.get("operations"), list):
        for child in operation["operations"]:
            if isinstance(child, dict):
                values.extend(operation_type_tree(child))
    return values


def validate_graph_operation_structure(operation: dict[str, Any], path: str = "graph_operation") -> list[str]:
    operation_type = str(operation.get("type") or "")
    if not operation_type:
        return [f"{path}.type is required"]
    if operation_type != "batch":
        return []
    operations = operation.get("operations")
    if not isinstance(operations, list) or not operations:
        return [f"{path}.operations must be a non-empty list"]
    errors: list[str] = []
    for index, child in enumerate(operations, start=1):
        if not isinstance(child, dict):
            errors.append(f"{path}.operations[{index}] must be an object")
            continue
        errors.extend(validate_graph_operation_structure(child, f"{path}.operations[{index}]"))
    return errors


def graph_operation_output_nodes(operation: dict[str, Any]) -> list[str]:
    operation_type = str(operation.get("type") or "")
    outputs: list[str] = []
    if operation_type == "split_node":
        children = operation.get("children")
        if isinstance(children, list):
            outputs.extend(str(item.get("id") or "") for item in children if isinstance(item, dict))
    elif operation_type == "merge_nodes":
        target = operation.get("target")
        if isinstance(target, dict):
            outputs.append(str(target.get("id") or ""))
    elif operation_type == "batch":
        for child in operation.get("operations") or []:
            if isinstance(child, dict):
                outputs.extend(graph_operation_output_nodes(child))
    return unique([item for item in outputs if item])


def graph_operation_input_nodes(operation: dict[str, Any]) -> list[str]:
    operation_type = str(operation.get("type") or "")
    inputs: list[str] = []
    # reset_stage：被回退的节点即 primary（input）；不产生新 output 节点，
    # 下游 output 节点按 output_node_policy 处理（keep 时全部留盘、不进 output 解析）。
    if operation_type in {"advance_lane", "split_node", "block_node", "defer_node", "supersede_node", "reset_stage"}:
        inputs.append(str(operation.get("node_id") or ""))
    # reset_stage 也支持以 primary_nodes 列表表达被回退的多个节点。
    if operation_type == "reset_stage":
        inputs.extend(str(item) for item in operation.get("primary_nodes") or [])
    if operation_type in {"merge_nodes", "supersede_node"}:
        inputs.extend(str(item) for item in operation.get("node_ids") or [])
    if operation_type == "batch":
        for child in operation.get("operations") or []:
            if isinstance(child, dict):
                inputs.extend(graph_operation_input_nodes(child))
    return unique([item for item in inputs if item])
