from __future__ import annotations

import argparse
import json
from typing import Any


def fail_payload(control: str, code: str, message: str) -> dict[str, Any]:
    return {"status": "FAIL", "control": control, "findings": [{"level": "FAIL", "code": code, "message": message}]}


def emit_payload(args: argparse.Namespace, payload: dict[str, Any]) -> int:
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{payload.get('control', 'harness')}: {payload.get('status')}")
        for item in payload.get("findings") or []:
            print(f"[{item.get('level')}] {item.get('code')}: {item.get('message')}")
    return 0 if payload.get("status") in {"PASS", "WARN"} else 1


def finding(level: str, code: str, message: str, *, source: str = "", blocking: bool = False, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"level": level, "code": code, "message": message, "blocking": blocking}
    if source:
        item["source"] = source
    item.update(extra)
    return item


def status_from_findings(findings: list[dict[str, Any]]) -> str:
    levels = {str(item.get("level") or "").upper() for item in findings}
    if "FAIL" in levels:
        return "FAIL"
    if "BLOCKED" in levels or any(bool(item.get("blocking")) for item in findings):
        return "BLOCKED"
    if "WARN" in levels:
        return "WARN"
    return "PASS"
