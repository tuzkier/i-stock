from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness_cli_core.infra.runtime_paths import runtime_harness_root


TODO_STATUS_FROM_TRACE = {
    "pass": "completed",
    "fail": "blocked",
    "blocked": "blocked",
}


def trace_log_path(root: Path, mission_id: str) -> Path:
    return runtime_harness_root(root) / "traces" / mission_id / "steps.jsonl"


def append_trace_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def init_trace_log(root: Path, mission_id: str, *, stage: str | None, timestamp: str) -> tuple[Path, bool]:
    path = trace_log_path(root, mission_id)
    is_new = not path.exists()
    if is_new:
        append_trace_record(
            path,
            {
                "event": "log-init",
                "mission_id": mission_id,
                "stage": stage,
                "timestamp": timestamp,
            },
        )
    elif stage:
        append_trace_record(
            path,
            {
                "event": "stage-init",
                "mission_id": mission_id,
                "stage": stage,
                "timestamp": timestamp,
            },
        )
    return path, is_new


def trace_report(root: Path, mission_id: str, *, stage: str | None = None) -> dict[str, Any]:
    path = trace_log_path(root, mission_id)
    event_counts: dict[str, int] = {}
    stage_counts: dict[str, int] = {}
    event_count = 0
    stage_event_count = 0
    warnings: list[str] = []

    if not path.exists():
        warnings.append("trace_log_missing")
    else:
        with path.open(encoding="utf-8") as handle:
            for raw_line in handle:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    record = json.loads(raw_line)
                except json.JSONDecodeError:
                    warnings.append(f"malformed_record:{raw_line[:60]}")
                    continue
                event = str(record.get("event") or "")
                if not event:
                    warnings.append("missing_event")
                    continue
                event_count += 1
                event_counts[event] = event_counts.get(event, 0) + 1
                record_stage = str(record.get("stage") or record.get("phase") or "")
                if record_stage:
                    stage_counts[record_stage] = stage_counts.get(record_stage, 0) + 1
                if stage and record_stage == stage:
                    stage_event_count += 1

    return {
        "trace_path": path,
        "event_count": event_count,
        "event_counts": event_counts,
        "stage": stage,
        "stage_counts": stage_counts,
        "stage_event_count": stage_event_count,
        "warnings": warnings,
    }


def build_step_record(
    *,
    mission_id: str,
    step: str,
    event: str,
    timestamp: str,
    phase: str | None = None,
    rounds: int | None = None,
    note: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "event": f"step-{event}",
        "mission_id": mission_id,
        "step": step,
        "timestamp": timestamp,
    }
    if phase:
        record["phase"] = phase
    if rounds is not None:
        record["rounds"] = rounds
    if note:
        record["note"] = note
    if status is not None:
        record["status"] = status
    return record


def build_round_record(
    *,
    mission_id: str,
    round_number: int,
    event: str,
    timestamp: str,
    status: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "event": f"round-{event}",
        "mission_id": mission_id,
        "round": round_number,
        "timestamp": timestamp,
    }
    if event == "exit":
        record["status"] = status
    if note:
        record["note"] = note
    return record


def derive_todos_from_trace(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    todos: list[dict[str, Any]] = []
    seen_step_order: list[str] = []
    last_event_per_step: dict[str, dict[str, Any]] = {}
    first_note_per_step: dict[str, str] = {}
    warnings: list[str] = []

    if not path.exists():
        return todos, ["trace_log_missing"]

    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError:
                warnings.append(f"malformed_record:{raw_line[:60]}")
                continue
            event = record.get("event")
            step = record.get("step")
            if event in {"step-enter", "step-exit"} and isinstance(step, str):
                if step not in last_event_per_step:
                    seen_step_order.append(step)
                last_event_per_step[step] = record
                note = record.get("note")
                if step not in first_note_per_step and isinstance(note, str) and note:
                    first_note_per_step[step] = note

    for step in seen_step_order:
        record = last_event_per_step[step]
        event = record.get("event")
        if event == "step-enter":
            status = "in_progress"
        elif event == "step-exit":
            exit_status = str(record.get("status", "")).lower()
            status = TODO_STATUS_FROM_TRACE.get(exit_status)
            if status is None:
                warnings.append(f"unknown_exit_status:{step}={exit_status}")
                status = "blocked"
        else:
            continue

        content = first_note_per_step.get(step, step)
        active_form = f"Working on {content}" if status == "in_progress" else content
        todos.append(
            {
                "content": content,
                "activeForm": active_form,
                "status": status,
                "step_id": step,
                "phase": record.get("phase"),
                "rounds": record.get("rounds"),
                "last_event_timestamp": record.get("timestamp"),
            }
        )

    return todos, warnings


def summarize_todos(todos: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(todos),
        "in_progress": sum(1 for todo in todos if todo["status"] == "in_progress"),
        "completed": sum(1 for todo in todos if todo["status"] == "completed"),
        "blocked": sum(1 for todo in todos if todo["status"] == "blocked"),
    }
