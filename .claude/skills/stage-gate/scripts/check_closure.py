#!/usr/bin/env python3
"""跨阶段全局闭包门（改造⑤b）：交付终局一次性校验 mission 文档集无悬空引用。

各阶段 reviewer 做局部完备（本阶段 vs 直接上游）；本门做全 mission 一次性兜底：
收集本 mission 全部阶段 contract，检查每条 traces_to 引用的稳定 ID 是否在集合内有定义。
悬空引用 = 推理链断在文档集外。纯逻辑在 harness_cli_core.domain.closure（可单测）；
本脚本只做文件层装配。默认 WARN 灰度，--strict 升 FAIL。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to check closure") from exc

# 复用 domain 纯函数（SSOT）。跨包 import 路径：scripts → package/common。
_COMMON_ROOT = Path(__file__).resolve().parents[3]
if str(_COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(_COMMON_ROOT))
from harness_cli_core.domain.closure import mission_closure_findings  # noqa: E402


def load_mission_contracts(root: Path, mission: str) -> list[dict]:
    """glob 本 mission 的全部阶段 contract（control_contract / 裸 dict 都兼容）。"""
    contracts_dir = root / "harness-runtime" / "harness" / "stages" / mission / "contracts"
    out: list[dict] = []
    if not contracts_dir.is_dir():
        return out
    for path in sorted(contracts_dir.glob("*.contract.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(data, dict):
            out.append(data.get("control_contract") if isinstance(data.get("control_contract"), dict) else data)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--mission", required=True)
    parser.add_argument("--strict", action="store_true", help="悬空引用升 FAIL（灰度校准后开启）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    contracts = load_mission_contracts(root, args.mission)
    findings = mission_closure_findings(contracts, strict=args.strict)
    if not findings:
        findings = [{"level": "PASS", "code": "closure_resolved", "message": "全 mission 文档集闭包成立：无悬空引用"}]

    status = "FAIL" if any(f["level"] == "FAIL" for f in findings) else "WARN" if any(f["level"] == "WARN" for f in findings) else "PASS"
    payload = {"status": status, "control": "stage_gate.check_closure", "mission_id": args.mission, "contracts_scanned": len(contracts), "findings": findings}
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
