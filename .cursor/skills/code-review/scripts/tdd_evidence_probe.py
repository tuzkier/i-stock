#!/usr/bin/env python3
"""Collect low-cost toolchain signals for Harness code-review.

This is HarnessV2's TDD toolchain control-plane adapter. It detects common
open-source test quality tools, records their configured commands/report paths,
and emits deterministic candidate signals. It does not decide test adequacy;
the tdd-reviewer uses normalized toolchain status and reports as inputs.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TEST_FILE_RE = re.compile(
    r"(^|/)(__tests__/.*|tests?/.*|.*(\.|_)(test|spec)\.(py|ts|tsx|js|jsx|mjs|cjs|go|rs))$"
)
SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"}
FRONTEND_PREFIXES = ("apps/frontend/", "frontend/", "src/app/", "src/components/")
TOOL_REPORT_CANDIDATES = (
    "coverage.xml",
    "coverage.json",
    "htmlcov/index.html",
    "junit.xml",
    "pytest-report.json",
    "test-results.json",
    "playwright-report/index.html",
    "mutation.html",
    "reports/mutation/mutation.html",
    "reports/mutation/mutation.json",
    ".stryker-tmp/reports/mutation/mutation.json",
)


@dataclass
class Signal:
    level: str
    code: str
    message: str
    evidence: list[str]
    reviewer_guidance: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "evidence": self.evidence,
            "reviewer_guidance": self.reviewer_guidance,
        }


@dataclass
class ToolAdapter:
    tool: str
    category: str
    configured: bool
    available: bool
    commands: list[str]
    report_paths: list[str]
    purpose: str
    notes: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "category": self.category,
            "configured": self.configured,
            "available": self.available,
            "commands": self.commands,
            "report_paths": self.report_paths,
            "purpose": self.purpose,
            "notes": self.notes,
        }


def run_git(root: Path, args: list[str]) -> list[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def harness_cli_path() -> Path:
    return Path(__file__).resolve().parents[3] / "cli" / "harness_cli.py"


def load_mission_status(root: Path, mission_id: str | None = None, extra_args: list[str] | None = None) -> dict[str, Any]:
    cli = harness_cli_path()
    if not cli.exists():
        return {}
    cmd = [sys.executable, str(cli), "--root", str(root), "mission", "status"]
    if mission_id:
        cmd.extend(["--mission", mission_id])
    if extra_args:
        cmd.extend(extra_args)
    cmd.append("--json")
    proc = subprocess.run(cmd, cwd=str(root), text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    if proc.returncode != 0:
        return {}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def find_latest_mission(root: Path, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    payload = load_mission_status(root, extra_args=["--open", "--ids-only"])
    mission_ids = payload.get("mission_ids") if isinstance(payload.get("mission_ids"), list) else []
    return str(mission_ids[-1]) if mission_ids else None


def find_baseline_commit(root: Path, mission_id: str | None) -> str | None:
    if not mission_id:
        return None
    payload = load_mission_status(root, mission_id=mission_id)
    entry = payload.get("mission_status") if isinstance(payload.get("mission_status"), dict) else {}
    git = entry.get("git") if isinstance(entry.get("git"), dict) else {}
    baseline = git.get("baseline_commit") or entry.get("baseline_commit")
    return str(baseline) if baseline else None


def changed_files(root: Path, baseline: str | None) -> list[str]:
    files: set[str] = set()
    if baseline:
        files.update(run_git(root, ["diff", "--name-only", f"{baseline}..HEAD"]))
    files.update(run_git(root, ["diff", "--name-only"]))
    files.update(run_git(root, ["diff", "--name-only", "--cached"]))
    files.update(run_git(root, ["ls-files", "--others", "--exclude-standard"]))
    return sorted(files)


def list_repo_tests(root: Path) -> list[str]:
    tracked = run_git(root, ["ls-files"])
    untracked = run_git(root, ["ls-files", "--others", "--exclude-standard"])
    return sorted(path for path in {*tracked, *untracked} if TEST_FILE_RE.search(path))


def package_scripts(root: Path, package_path: str) -> dict[str, str]:
    data = load_json(root / package_path)
    scripts = data.get("scripts")
    return scripts if isinstance(scripts, dict) else {}


def has_test_script(scripts: dict[str, str]) -> bool:
    names = set(scripts)
    return bool(names & {"test", "test:unit", "test:integration", "vitest", "jest", "playwright", "e2e"})


def command_available(command: str) -> bool:
    return shutil.which(command) is not None


def package_dependency_names(root: Path, package_path: str) -> set[str]:
    data = load_json(root / package_path)
    names: set[str] = set()
    for field in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        deps = data.get(field)
        if isinstance(deps, dict):
            names.update(deps)
    return names


def existing_reports(root: Path, base: str = ".") -> list[str]:
    base_path = root / base
    reports: list[str] = []
    for rel in TOOL_REPORT_CANDIDATES:
        path = base_path / rel
        if path.exists():
            reports.append(str(path.relative_to(root)))
    return reports


def file_exists_any(root: Path, patterns: list[str]) -> bool:
    return any(root.glob(pattern) for pattern in patterns)


def detect_toolchain(root: Path) -> list[ToolAdapter]:
    root_scripts = package_scripts(root, "package.json")
    frontend_scripts = package_scripts(root, "apps/frontend/package.json")
    root_deps = package_dependency_names(root, "package.json")
    frontend_deps = package_dependency_names(root, "apps/frontend/package.json")
    pyproject = read_text(root / "pyproject.toml")
    backend_pyproject = read_text(root / "apps/backend/pyproject.toml")
    requirements_text = "\n".join(
        read_text(path)
        for path in [
            root / "requirements.txt",
            root / "requirements-dev.txt",
            root / "apps/backend/requirements.txt",
            root / "apps/backend/requirements-dev.txt",
        ]
    )

    adapters: list[ToolAdapter] = []

    pytest_configured = (
        (root / "pytest.ini").exists()
        or (root / "apps/backend/pytest.ini").exists()
        or (root / "apps/backend/tests").exists()
        or "[tool.pytest" in pyproject
        or "[tool.pytest" in backend_pyproject
    )
    adapters.append(ToolAdapter(
        tool="pytest",
        category="test_result",
        configured=pytest_configured,
        available=command_available("pytest"),
        commands=[
            "python3 -m pytest --junitxml=harness-runtime/harness/traces/<mission-id>/tools/pytest-junit.xml",
            "python3 -m pytest --json-report --json-report-file=harness-runtime/harness/traces/<mission-id>/tools/pytest-report.json",
        ],
        report_paths=[
            *existing_reports(root),
            *existing_reports(root, "apps/backend"),
        ],
        purpose="Collect Python unit/integration pass/fail and test identity evidence.",
        notes=[] if pytest_configured else ["No pytest config/tests detected by Harness probe."],
    ))

    pytest_cov_configured = (
        "pytest-cov" in requirements_text
        or "pytest-cov" in pyproject
        or "pytest-cov" in backend_pyproject
        or "[tool.coverage" in pyproject
        or "[tool.coverage" in backend_pyproject
        or (root / ".coveragerc").exists()
        or (root / "apps/backend/.coveragerc").exists()
    )
    adapters.append(ToolAdapter(
        tool="coverage.py/pytest-cov",
        category="coverage",
        configured=pytest_cov_configured,
        available=command_available("coverage"),
        commands=[
            "python3 -m pytest --cov --cov-report=xml:harness-runtime/harness/traces/<mission-id>/tools/coverage.xml --cov-report=json:harness-runtime/harness/traces/<mission-id>/tools/coverage.json"
        ],
        report_paths=[
            path for path in [*existing_reports(root), *existing_reports(root, "apps/backend")]
            if "coverage" in path or "htmlcov" in path
        ],
        purpose="Measure executed Python lines/branches; feed diff-cover and reviewer adequacy checks.",
        notes=[] if pytest_cov_configured else ["Coverage tool/config not detected."],
    ))

    adapters.append(ToolAdapter(
        tool="diff-cover",
        category="diff_coverage",
        configured=file_exists_any(root, ["coverage.xml", "apps/backend/coverage.xml"]),
        available=command_available("diff-cover"),
        commands=[
            "diff-cover harness-runtime/harness/traces/<mission-id>/tools/coverage.xml --compare-branch=<baseline>"
        ],
        report_paths=[],
        purpose="Map coverage to changed lines so reviewer can focus on mission diff risk.",
        notes=["Requires coverage.xml from coverage.py/pytest-cov."],
    ))

    mutmut_configured = (
        "mutmut" in requirements_text
        or "mutmut" in pyproject
        or "mutmut" in backend_pyproject
        or "[tool.mutmut" in pyproject
        or "[tool.mutmut" in backend_pyproject
        or (root / "mutmut_config.py").exists()
    )
    adapters.append(ToolAdapter(
        tool="mutmut",
        category="mutation",
        configured=mutmut_configured,
        available=command_available("mutmut"),
        commands=[
            "mutmut run --paths-to-mutate <changed-python-source>",
            "mutmut results",
        ],
        report_paths=[],
        purpose="Prove critical Python tests fail when source behavior is mutated.",
        notes=[] if mutmut_configured else ["Mutation testing not configured for Python."],
    ))

    vitest_configured = (
        "vitest" in frontend_deps
        or "vitest" in root_deps
        or any("vitest" in script for script in frontend_scripts.values())
        or file_exists_any(root, ["apps/frontend/vitest.config.*", "vitest.config.*"])
    )
    adapters.append(ToolAdapter(
        tool="vitest/jest",
        category="frontend_unit_component",
        configured=vitest_configured or "jest" in frontend_deps or "jest" in root_deps,
        available=command_available("pnpm") or command_available("npm"),
        commands=[
            "pnpm --filter @theforce/frontend test -- --reporter=json --coverage",
            "npm test -- --json --coverage",
        ],
        report_paths=[path for path in existing_reports(root, "apps/frontend") if "coverage" in path or "test-results" in path],
        purpose="Validate frontend units/components/API clients with structured results and coverage.",
        notes=[] if vitest_configured else ["No Vitest/Jest frontend test harness detected."],
    ))

    playwright_configured = (
        "@playwright/test" in frontend_deps
        or "@playwright/test" in root_deps
        or any("playwright" in script for script in {**root_scripts, **frontend_scripts}.values())
        or file_exists_any(root, ["playwright.config.*", "apps/frontend/playwright.config.*"])
    )
    adapters.append(ToolAdapter(
        tool="playwright",
        category="e2e_ui",
        configured=playwright_configured,
        available=command_available("pnpm") or command_available("npx"),
        commands=[
            "pnpm exec playwright test --reporter=json --reporter=junit",
        ],
        report_paths=[path for path in [*existing_reports(root), *existing_reports(root, "apps/frontend")] if "playwright" in path or "test-results" in path],
        purpose="Validate user-visible UI workflows, browser behavior, traces, and E2E acceptance paths.",
        notes=[] if playwright_configured else ["No Playwright config/dependency detected."],
    ))

    stryker_configured = (
        "@stryker-mutator/core" in frontend_deps
        or "@stryker-mutator/core" in root_deps
        or file_exists_any(root, ["stryker.conf.*", "apps/frontend/stryker.conf.*", "stryker.config.*"])
    )
    adapters.append(ToolAdapter(
        tool="StrykerJS",
        category="mutation",
        configured=stryker_configured,
        available=command_available("pnpm") or command_available("npx"),
        commands=[
            "pnpm exec stryker run --incremental",
        ],
        report_paths=[
            path for path in [*existing_reports(root), *existing_reports(root, "apps/frontend")]
            if "mutation" in path or "stryker" in path
        ],
        purpose="Prove critical JS/TS tests fail when frontend/source behavior is mutated.",
        notes=[] if stryker_configured else ["StrykerJS mutation testing not configured."],
    ))

    return adapters


def parse_required_evidence(execution_brief: str) -> dict[str, list[str]]:
    required: dict[str, list[str]] = {}
    current_task: str | None = None
    for line in execution_brief.splitlines():
        task_match = re.search(r"- id:\s*(T\d+)", line)
        if task_match:
            current_task = task_match.group(1)
            required.setdefault(current_task, [])
        evidence_match = re.search(r"id:\s*(EV-[^,\s}]+).*type:\s*([^,\s}]+)", line)
        if current_task and evidence_match:
            required.setdefault(current_task, []).append(f"{evidence_match.group(1)}:{evidence_match.group(2)}")
    return required


def parse_authorized_paths(execution_brief: str) -> list[str]:
    paths: list[str] = []
    in_authorized = False
    for line in execution_brief.splitlines():
        if "authorized_paths:" in line:
            in_authorized = True
            continue
        if in_authorized and re.match(r"\s+(prohibited_paths|required_evidence|stop_if|dependencies):", line):
            in_authorized = False
        if not in_authorized:
            continue
        match = re.search(r"-\s+[\"']?([^\"'\n]+?)[\"']?\s*$", line)
        if match:
            paths.append(match.group(1).strip())
    return sorted(set(paths))


def matches_any(path: str, patterns: list[str]) -> bool:
    if not patterns:
        return True
    for pattern in patterns:
        normalized = pattern.rstrip("/")
        if pattern.endswith("/*"):
            prefix = pattern[:-1]
            if path.startswith(prefix):
                return True
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            if path == prefix or path.startswith(prefix + "/"):
                return True
        if fnmatch.fnmatch(path, normalized):
            return True
        if "*" not in normalized and (path == normalized or path.startswith(normalized.rstrip("/") + "/")):
            return True
    return False


def collect_trace_names(root: Path, mission_id: str | None) -> list[str]:
    if not mission_id:
        return []
    trace_root = root / "harness-runtime/harness/traces" / mission_id
    if not trace_root.exists():
        return []
    return sorted(str(path.relative_to(root)) for path in trace_root.rglob("*") if path.is_file())


def source_changed_without_tests(changed: list[str]) -> list[str]:
    source_changed = [
        path for path in changed
        if Path(path).suffix in SOURCE_EXTENSIONS and not TEST_FILE_RE.search(path)
    ]
    changed_tests = [path for path in changed if TEST_FILE_RE.search(path)]
    if changed_tests:
        return []
    return source_changed[:50]


def grep_any(root: Path, files: list[str], patterns: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {pattern: [] for pattern in patterns}
    compiled = {pattern: re.compile(pattern, re.IGNORECASE) for pattern in patterns}
    for rel in files:
        text = read_text(root / rel)
        for pattern, regex in compiled.items():
            if regex.search(text):
                result[pattern].append(rel)
    return result


def build_probe(root: Path, mission_id: str | None) -> dict[str, Any]:
    baseline = find_baseline_commit(root, mission_id)
    changed = changed_files(root, baseline)
    tests = list_repo_tests(root)
    stage_root = root / "harness-runtime/harness/stages" / mission_id if mission_id else root / "__missing__"
    execution_brief = read_text(stage_root / "execution-brief.md")
    required_evidence = parse_required_evidence(execution_brief)
    authorized_paths = parse_authorized_paths(execution_brief)
    scoped_changed = [path for path in changed if matches_any(path, authorized_paths)]
    review_changed = scoped_changed or changed

    changed_tests = [path for path in review_changed if TEST_FILE_RE.search(path)]
    changed_sources = [
        path for path in review_changed
        if Path(path).suffix in SOURCE_EXTENSIONS and not TEST_FILE_RE.search(path)
    ]
    frontend_changed = [path for path in review_changed if path.startswith(FRONTEND_PREFIXES) or path.startswith("apps/frontend/")]
    frontend_tests = [path for path in tests if path.startswith("apps/frontend/") or path.startswith("frontend/")]
    frontend_scripts = package_scripts(root, "apps/frontend/package.json")
    root_scripts = package_scripts(root, "package.json")
    toolchain = detect_toolchain(root)
    tool_by_name = {adapter.tool: adapter for adapter in toolchain}

    trace_names = collect_trace_names(root, mission_id)

    signals: list[Signal] = []
    frontend_unit_tool = tool_by_name.get("vitest/jest")
    playwright_tool = tool_by_name.get("playwright")
    frontend_tool_configured = bool(
        (frontend_unit_tool and frontend_unit_tool.configured)
        or (playwright_tool and playwright_tool.configured)
        or has_test_script(frontend_scripts)
    )
    if frontend_changed and not frontend_tests and not frontend_tool_configured:
        signals.append(Signal(
            level="FAIL",
            code="frontend_changed_without_test_toolchain",
            message="Frontend behavior changed, but Harness did not detect a frontend unit/component/E2E toolchain.",
            evidence=[
                "apps/frontend/package.json",
                *frontend_changed[:20],
            ],
            reviewer_guidance=(
                "Candidate TDD High only if the changed frontend behavior maps to scenario evidence and "
                "detected tools cannot make the wrong behavior fail. Prefer Vitest/RTL or Playwright evidence."
            ),
        ))
    elif frontend_changed and not frontend_tests:
        signals.append(Signal(
            level="WARN",
            code="frontend_changed_without_frontend_tests",
            message="Frontend behavior changed, but no frontend test files were detected.",
            evidence=frontend_changed[:20],
            reviewer_guidance="Check whether another browser/component test path covers these UI behaviors.",
        ))

    mutation_tools = [adapter for adapter in toolchain if adapter.category == "mutation" and adapter.configured]
    if changed_sources and not mutation_tools:
        signals.append(Signal(
            level="WARN",
            code="changed_source_without_mutation_toolchain",
            message="Source behavior changed, but no configured mutation testing tool was detected.",
            evidence=changed_sources[:20],
            reviewer_guidance=(
                "Not a finding by itself. For high-risk logic, require mutmut/StrykerJS, targeted fault "
                "injection, or equivalent proof that wrong behavior fails tests."
            ),
        ))

    if required_evidence:
        red_required = [
            evidence for evidence_list in required_evidence.values()
            for evidence in evidence_list
            if ":failing_test" in evidence or "-RED:" in evidence
        ]
        red_traces = [
            name for name in trace_names
            if "red" in name.lower() or "fail" in name.lower()
        ]
        if red_required and not red_traces:
            signals.append(Signal(
                level="WARN",
                code="required_red_evidence_not_found",
                message="Execution brief declares RED/failing-test evidence, but no obvious red/fail trace artifact was found.",
                evidence=red_required[:30],
                reviewer_guidance=(
                    "For historical review, do not auto-HOLD on this alone. Inspect assertion strength "
                    "and fault detection before classifying as TDD Integrity gap."
                ),
            ))

    untested_sources = source_changed_without_tests(review_changed)
    if untested_sources:
        signals.append(Signal(
            level="WARN",
            code="source_changed_without_changed_tests",
            message="Source files changed without changed test files in the same diff.",
            evidence=untested_sources,
            reviewer_guidance=(
                "Not a finding by itself. Use as a routing hint to inspect existing tests or missing "
                "test obligations for changed behavior."
            ),
        ))

    risk_patterns = [
        r"unbound",
        r"revoked",
        r"mismatch",
        r"stale",
        r"idempot",
        r"concurrent",
        r"target exists",
        r"a11y|accessib|keyboard",
        r"websocket|realtime|invalidation",
    ]
    test_pattern_hits = grep_any(root, tests, risk_patterns)
    design_text = read_text(stage_root / "tech-design.md") + "\n" + execution_brief
    design_pattern_mentions = {
        pattern: bool(re.search(pattern, design_text, flags=re.IGNORECASE))
        for pattern in risk_patterns
    }
    missing_pattern_tests = [
        pattern for pattern, mentioned in design_pattern_mentions.items()
        if mentioned and not test_pattern_hits.get(pattern)
    ]
    if missing_pattern_tests:
        signals.append(Signal(
            level="WARN",
            code="risk_keyword_without_matching_test_text",
            message="Some risk keywords appear in design/brief but not in detected tests.",
            evidence=missing_pattern_tests,
            reviewer_guidance=(
                "Heuristic only. Inspect whether equivalent tests exist under different wording before "
                "raising a TDD adequacy finding."
            ),
        ))

    status = "FAIL" if any(signal.level == "FAIL" for signal in signals) else "WARN" if signals else "PASS"
    return {
        "schema_version": 1,
        "status": status,
        "mission_id": mission_id,
        "baseline_commit": baseline,
        "changed_files": {
            "total": len(changed),
            "scoped_total": len(review_changed),
            "authorized_path_patterns": authorized_paths,
            "sources": changed_sources,
            "tests": changed_tests,
            "frontend": frontend_changed,
        },
        "test_inventory": {
            "total": len(tests),
            "frontend_test_files": frontend_tests,
            "backend_test_files": [path for path in tests if path.startswith("apps/backend/")],
            "frontend_has_test_script": has_test_script(frontend_scripts),
            "frontend_scripts": frontend_scripts,
            "root_has_test_script": has_test_script(root_scripts),
            "root_scripts": root_scripts,
        },
        "toolchain": [adapter.as_dict() for adapter in toolchain],
        "normalized_reports": {
            "test_result": [adapter.as_dict() for adapter in toolchain if adapter.category == "test_result"],
            "coverage": [adapter.as_dict() for adapter in toolchain if adapter.category in {"coverage", "diff_coverage"}],
            "mutation": [adapter.as_dict() for adapter in toolchain if adapter.category == "mutation"],
            "ui_e2e": [adapter.as_dict() for adapter in toolchain if adapter.category in {"frontend_unit_component", "e2e_ui"}],
        },
        "required_evidence": required_evidence,
        "trace_artifacts": trace_names,
        "risk_keyword_test_hits": test_pattern_hits,
        "signals": [signal.as_dict() for signal in signals],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--mission-id", help="Mission id; defaults to mission-status current/latest")
    parser.add_argument("--output", help="Optional JSON artifact path")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    mission_id = find_latest_mission(root, args.mission_id)
    result = build_probe(root, mission_id)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
