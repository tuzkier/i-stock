from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class InteractionCommandHandlers:
    check_ui_trigger: Callable[[argparse.Namespace], int]
    spec_check: Callable[[argparse.Namespace], int]
    ux_quality_check: Callable[[argparse.Namespace], int]
    visual_coverage_check: Callable[[argparse.Namespace], int]
    trace_coverage_check: Callable[[argparse.Namespace], int]
    prototype_check: Callable[[argparse.Namespace], int]
    project: Callable[[argparse.Namespace], int]
    resolve_feedback: Callable[[argparse.Namespace], int]
    locator_check: Callable[[argparse.Namespace], int]
    feedback_sync_check: Callable[[argparse.Namespace], int]
    gate_run: Callable[[argparse.Namespace], int]


def register_interaction_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: InteractionCommandHandlers,
) -> argparse.ArgumentParser:
    interaction = subparsers.add_parser("interaction")
    interaction_sub = interaction.add_subparsers(dest="interaction_command", required=True)
    for name, handler in (
        ("check-ui-trigger", handlers.check_ui_trigger),
        ("spec-check", handlers.spec_check),
        ("ux-quality-check", handlers.ux_quality_check),
        ("visual-coverage-check", handlers.visual_coverage_check),
        ("locator-check", handlers.locator_check),
        ("feedback-sync-check", handlers.feedback_sync_check),
    ):
        p = add_leaf(interaction_sub, name, handler)
        p.add_argument("--mission", required=True)

    trace = add_leaf(interaction_sub, "trace-coverage-check", handlers.trace_coverage_check)
    trace.add_argument("--mission", required=True)
    trace.add_argument(
        "--prototype-root",
        default="",
        help="独立原型工程目录（prototype.interactive_prototype.prototype_project_root，默认建议 prototype/）；提供后写入 trace-index.json",
    )

    # 单一 lint：behavior-graph ↔ surface-model ↔ 原型 一次对账（取代 trace/visual/locator 三命令）
    proto_check = add_leaf(interaction_sub, "prototype-check", handlers.prototype_check)
    proto_check.add_argument("--mission", required=True)
    proto_check.add_argument(
        "--prototype-root",
        default="",
        help="独立原型工程目录；提供后扫描其中 *.html 收集 data-step/data-pagestate/data-via/data-testid 锚点",
    )

    # 从 behavior-graph 派生三视图 + 驾驶舱数据 walkthrough.js
    project = add_leaf(interaction_sub, "project", handlers.project)
    project.add_argument("--mission", required=True)
    project.add_argument(
        "--prototype-root",
        default="",
        help="独立原型工程目录；提供后把 walkthrough.js 写入其中供走查驾驶舱加载",
    )

    resolve = add_leaf(interaction_sub, "resolve-feedback", handlers.resolve_feedback)
    resolve.add_argument("--mission", required=True)
    resolve.add_argument("--surface", default="", help="界面边界 ID，如 SURF-002")
    resolve.add_argument("--suc", default="", help="系统用例 ID，如 SUC-03")
    resolve.add_argument("--obj", default="", help="业务对象 ID，如 OBJ-01")
    resolve.add_argument("--step", default="", help="节拍 ID，如 SUC-01-FLOW-01.empty")

    interaction_gate = interaction_sub.add_parser("gate")
    interaction_gate_sub = interaction_gate.add_subparsers(
        dest="interaction_gate_command", required=True
    )
    p = add_leaf(interaction_gate_sub, "run", handlers.gate_run)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--prototype-root",
        default="",
        help="独立原型工程目录；默认从 prototype.interactive_prototype.prototype_project_root 解析",
    )
    return interaction
