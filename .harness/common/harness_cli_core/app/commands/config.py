from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigCommandHandlers:
    snapshot: Callable[[argparse.Namespace], int]
    diff: Callable[[argparse.Namespace], int]
    migrate: Callable[[argparse.Namespace], int]


def register_config_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: ConfigCommandHandlers,
) -> argparse.ArgumentParser:
    config = subparsers.add_parser("config")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    add_leaf(config_sub, "snapshot", handlers.snapshot)

    # config diff：升级时对 harness.yaml 做三方分类（旧装/新模板/归属清单），输出 todolist。
    p = add_leaf(config_sub, "diff", handlers.diff)
    p.add_argument("--upstream", required=True, help="新版本 HarnessV2 源码根（或新模板 harness.yaml）路径")
    p.add_argument("--current", help="当前已装 harness.yaml 路径（缺省取 <root>/harness-runtime/config/harness.yaml）")
    p.add_argument("--ownership", help="config-ownership.yaml 路径（缺省取 upstream 内）")

    # config migrate：按 plan + decisions 合并出新 harness.yaml（以新模板为基底，保留项目值）。
    p = add_leaf(config_sub, "migrate", handlers.migrate)
    p.add_argument("--upstream", required=True, help="新版本 HarnessV2 源码根（或新模板 harness.yaml）路径")
    p.add_argument("--current", help="当前已装 harness.yaml 路径（缺省取 <root>/harness-runtime/config/harness.yaml）")
    p.add_argument("--ownership", help="config-ownership.yaml 路径（缺省取 upstream 内）")
    p.add_argument("--decisions", help="决策文件（yaml/json，path→verb）路径")
    p.add_argument("--accept-defaults", action="store_true", dest="accept_defaults", help="对需决策项采用默认决策")
    p.add_argument("--output", help="合并结果写入路径（缺省原地写并生成 .bak）")
    p.add_argument("--dry-run", action="store_true", dest="dry_run", help="只输出合并结果，不写盘")
    return config
