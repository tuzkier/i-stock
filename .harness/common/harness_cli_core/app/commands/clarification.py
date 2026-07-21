from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ClarificationCommandHandlers:
    record: Callable[[argparse.Namespace], int]
    list: Callable[[argparse.Namespace], int]


def register_clarification_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: ClarificationCommandHandlers,
) -> argparse.ArgumentParser:
    clarification = subparsers.add_parser("clarification")
    clar_sub = clarification.add_subparsers(dest="clarification_command", required=True)

    # record：把人对澄清 Decision Gate 的答复沉淀进 materials/clarifications/（文档集）。
    p = add_leaf(clar_sub, "record", handlers.record)
    p.add_argument("--mission", required=True)
    p.add_argument("--question", required=True, help="reviewer 标记的信息缺口 / 待澄清问题")
    p.add_argument("--answer", required=True, help="用户已确认的答复（作为推导前提纳入文档集）")
    p.add_argument("--stage", help="触发该澄清的阶段")
    p.add_argument("--gap-id", dest="gap_id", help="对应 blocking_gap 的 id")
    p.add_argument("--source-role", dest="source_role", help="提出该澄清的 reviewer 角色")
    p.add_argument("--approval-id", dest="approval_id", help="关联的 approval 记录 id")
    p.add_argument("--clar-id", dest="clar_id", help="显式指定 CLAR id（默认自动递增）")
    p.add_argument("--decided-at", dest="decided_at")

    # list：枚举澄清记录（reviewer / 控制面据此把本 mission 的澄清纳入完备性文档集）。
    p = add_leaf(clar_sub, "list", handlers.list)
    p.add_argument("--mission", help="只列指定 mission 的澄清")

    return clarification
