#!/usr/bin/env python3
"""partition_plan —— 大规模语料的 map-reduce 执行计划生成器（确定性、stdlib-only）。

谁用 / 为什么
  harness-setup 在 install 编排里调用本脚本，把"超大型项目怎么扇出"从"AI 凭感觉
  spawn N 个子 agent"变成"按计算出来的计划执行"：
    - Step 2（建图 graphify）：对未缓存的非代码文件做语义提取扇出。
    - Step 3（设计系统蒸馏）：对 UI 源做分层蒸馏扇出。

它解决三件 workflow 散文做不到的事：
    1. partition（分区）：按模块 / bounded-context（路径前 N 段）把文件分组，
       每个 map 子 agent 只看一个模块 —— 局部性更好、语义边更准、上下文不爆。
    2. priority（优先级）：分区按文件数降序排，先扫高价值模块；可设采样上限
       （蒸馏是 observe→condense，不是穷举）。
    3. wave + hierarchical reduce：按并发上限切波次；分区多于并发时给出
       两阶段 reduce（分组合并 → 全局合并），避免单上下文塞不下。

输出：一份 JSON 计划，consumer（workflow）照着 dispatch，不再自行决定扇出形状。

用法
  # 从文件清单（graphify：未缓存非代码文件）
  partition_plan.py --files-from /tmp/uncached.txt --chunk 22 --concurrency 10 --json

  # 从项目扫描（蒸馏：UI 源根）
  partition_plan.py --root . --include 'components/**' 'src/**/components/**' \
      'app/**' 'areas/**' 'wwwroot/**' --chunk 30 --threshold 150 --json
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import math
import os
import sys
from pathlib import PurePosixPath

DEFAULT_EXCLUDES = [
    "**/node_modules/**", "**/.git/**", "**/dist/**", "**/build/**",
    "**/__pycache__/**", "**/.next/**", "**/vendor/**", "**/.venv/**",
    "**/coverage/**", "**/out/**", "**/.turbo/**",
]


def _norm(p: str) -> str:
    return str(PurePosixPath(p.replace(os.sep, "/")))


def _matches_any(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat.rstrip("/*") + "/*")
              or fnmatch.fnmatch(rel, "**/" + pat) for pat in patterns)


def collect_files(root: str, files_from: str | None, includes: list[str],
                  excludes: list[str]) -> list[str]:
    """收集相对路径清单。files_from 优先；否则按 includes glob 扫描 root。"""
    excl = list(excludes) + DEFAULT_EXCLUDES
    if files_from:
        with open(files_from, encoding="utf-8") as fh:
            raw = [line.strip() for line in fh if line.strip()]
        files = []
        for r in raw:
            rel = _norm(os.path.relpath(r, root)) if os.path.isabs(r) else _norm(r)
            if _matches_any(rel, excl):
                continue
            files.append(rel)
        return sorted(set(files))

    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # 原地裁剪明显应忽略的目录，避免下潜 node_modules 等
        dirnames[:] = [d for d in dirnames
                       if not _matches_any(_norm(os.path.relpath(os.path.join(dirpath, d), root)), excl)
                       and d not in {"node_modules", ".git", "dist", "build", "__pycache__",
                                     ".next", "vendor", ".venv", "coverage", "out", ".turbo"}]
        for fn in filenames:
            rel = _norm(os.path.relpath(os.path.join(dirpath, fn), root))
            if _matches_any(rel, excl):
                continue
            if includes and not _matches_any(rel, includes):
                continue
            files.append(rel)
    return sorted(set(files))


def partition_key(rel: str, depth: int) -> str:
    """取相对路径前 depth 段作为模块 / bounded-context 分区键。"""
    parts = PurePosixPath(rel).parts
    if len(parts) <= 1:
        return "(root)"
    key_parts = parts[: min(depth, len(parts) - 1)]
    return "/".join(key_parts)


def chunk(seq: list, size: int) -> list[list]:
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def build_plan(files: list[str], *, depth: int, chunk_size: int, concurrency: int,
               threshold: int, sample_cap: int | None) -> dict:
    total = len(files)
    mode = "partitioned" if total >= threshold else "simple"

    groups: dict[str, list[str]] = {}
    for rel in files:
        groups.setdefault(partition_key(rel, depth), []).append(rel)

    # 优先级：文件数降序，模块名升序 tie-break
    ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    partitions = []
    tasks = []  # (partition, batch_index)
    for rank, (mod, mod_files) in enumerate(ranked):
        batches = chunk(sorted(mod_files), chunk_size)
        partitions.append({
            "module": mod,
            "file_count": len(mod_files),
            "priority_rank": rank,
            "batch_count": len(batches),
            "batches": batches,
        })
        for bi in range(len(batches)):
            tasks.append({"module": mod, "batch_index": bi})

    # 波次：按并发上限切
    waves = chunk(tasks, max(1, concurrency))

    num_partitions = len(partitions)
    # 分层 reduce：分区多于并发时两阶段合并，否则单次
    if num_partitions <= concurrency:
        reduce_plan = {
            "strategy": "single",
            "phase1_map": "每个 (module,batch) 子 agent 产出 module-local 草案，写入 staging",
            "phase2_reduce": "单个 reduce 步骤把全部 module 草案合并 → 去重 → canonical",
        }
    else:
        group_count = math.ceil(num_partitions / concurrency)
        reduce_plan = {
            "strategy": "hierarchical",
            "phase1_map": "每个 (module,batch) 子 agent 产出 module-local 草案，写入 staging",
            "phase2_group_reduce": f"把 {num_partitions} 个 module 草案分成 {group_count} 组，"
                                   f"每组一个 reduce 子 agent 产出组级小结",
            "phase3_global_reduce": f"主 orchestrator 合并 {group_count} 份组级小结 → canonical",
            "group_count": group_count,
        }

    sampling = None
    if sample_cap is not None and total > sample_cap:
        # 采样：按优先级累计文件数到 cap，标出"主导分区集"
        covered, dominant = 0, []
        for p in partitions:
            if covered >= sample_cap:
                break
            dominant.append(p["module"])
            covered += p["file_count"]
        sampling = {
            "cap": sample_cap,
            "note": "蒸馏是 observe→condense：优先扫主导分区，覆盖到 cap 即可收敛 canonical，"
                    "不穷举每个文件；尾部低价值分区留作增量沉淀。",
            "dominant_partitions": dominant,
            "dominant_file_coverage": covered,
        }

    return {
        "total_files": total,
        "mode": mode,
        "threshold": threshold,
        "chunk_size": chunk_size,
        "concurrency": concurrency,
        "partition_depth": depth,
        "num_partitions": num_partitions,
        "num_map_tasks": len(tasks),
        "num_waves": len(waves),
        "partitions": partitions,
        "waves": waves,
        "reduce_plan": reduce_plan,
        "sampling": sampling,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="大规模语料 map-reduce 执行计划生成器")
    ap.add_argument("--root", default=".")
    ap.add_argument("--files-from", default=None,
                    help="换行分隔的文件清单（优先于 --include 扫描）")
    ap.add_argument("--include", nargs="*", default=[],
                    help="glob（相对 root）；不给则收全部文件")
    ap.add_argument("--exclude", nargs="*", default=[])
    ap.add_argument("--chunk", type=int, default=22, help="每个 map 子 agent 的文件上限")
    ap.add_argument("--concurrency", type=int, default=10, help="并发上限（决定波次）")
    ap.add_argument("--threshold", type=int, default=150,
                    help="总文件数 ≥ 此值 → partitioned 模式")
    ap.add_argument("--partition-depth", type=int, default=1,
                    help="按路径前 N 段分区（模块 / bounded-context 粒度）")
    ap.add_argument("--sample-cap", type=int, default=None,
                    help="蒸馏专用：canonical 覆盖文件数上限，超出则按优先级采样")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    files = collect_files(args.root, args.files_from, args.include, args.exclude)
    plan = build_plan(files, depth=args.partition_depth, chunk_size=args.chunk,
                      concurrency=args.concurrency, threshold=args.threshold,
                      sample_cap=args.sample_cap)

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(f"total={plan['total_files']} mode={plan['mode']} "
              f"partitions={plan['num_partitions']} map_tasks={plan['num_map_tasks']} "
              f"waves={plan['num_waves']} reduce={plan['reduce_plan']['strategy']}")
        for p in plan["partitions"][:20]:
            print(f"  [{p['priority_rank']}] {p['module']}  "
                  f"files={p['file_count']} batches={p['batch_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
