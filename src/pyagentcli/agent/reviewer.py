from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyagentcli.agent.contracts import ReviewerGateDecision, ReviewerInputContract
from pyagentcli.agent.planner import PlanRun


@dataclass(frozen=True)
class ReviewReport:
    summary: str
    risks: list[str]
    suggested_tests: list[str]
    tools: list[str]
    paths: list[str]
    gate: ReviewerGateDecision

    def format_text(self) -> str:
        lines = [f"Review: {self.summary}", ""]
        lines.append(self.gate.format_text())
        lines.append("")
        lines.append("Risks:")
        lines.extend(f"- {risk}" for risk in (self.risks or ["No obvious risks found."]))
        lines.append("")
        lines.append("Suggested tests:")
        lines.extend(f"- {test}" for test in (self.suggested_tests or ["No specific tests suggested."]))
        lines.append("")
        lines.append("Observed tools:")
        lines.extend(f"- {tool}" for tool in (self.tools or ["<none>"]))
        lines.append("")
        lines.append("Observed paths:")
        lines.extend(f"- {path}" for path in (self.paths or ["<none>"]))
        return "\n".join(lines)


class Reviewer:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self.reviews_dir = self.workspace_root / ".pyagent" / "reviews"

    def review_plan(self, run: PlanRun) -> ReviewReport:
        reviewer_input = ReviewerInputContract(run=run)
        tools, paths = self._audit_summary(run)
        risks = _risk_notes(run)
        suggested_tests = _suggest_tests(run, paths)
        summary = _summary(run, paths)
        gate = _gate_decision(reviewer_input)
        report = ReviewReport(
            summary=summary,
            risks=risks,
            suggested_tests=suggested_tests,
            tools=tools,
            paths=paths,
            gate=gate,
        )
        self.save(run, report)
        return report

    def save(self, run: PlanRun, report: ReviewReport) -> Path:
        self.reviews_dir.mkdir(parents=True, exist_ok=True)
        plan_id = run.plan_id or "unknown_plan"
        path = self.reviews_dir / f"{plan_id}.md"
        path.write_text(report.format_text() + "\n", encoding="utf-8")
        return path

    def _audit_summary(self, run: PlanRun) -> tuple[list[str], list[str]]:
        audit_path = self.workspace_root / ".pyagent" / "audit.log.jsonl"
        if not audit_path.exists():
            return [], []
        tools: list[str] = []
        paths: list[str] = []
        try:
            lines = audit_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return [], []

        goal = run.goal or ""
        for line in reversed(lines[-500:]):
            try:
                event: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_goal = str(event.get("goal") or "")
            if goal and goal not in event_goal:
                continue
            tool_name = str(event.get("tool_name") or "")
            if tool_name and tool_name not in tools:
                tools.append(tool_name)
            args = event.get("tool_args") if isinstance(event.get("tool_args"), dict) else {}
            raw_path = args.get("path")
            if isinstance(raw_path, str) and raw_path not in paths:
                paths.append(raw_path)
        return tools, paths


def _summary(run: PlanRun, paths: list[str]) -> str:
    status = str(run.status)
    if paths:
        return f"Plan finished with status {status}; observed workspace paths: {', '.join(paths[:5])}."
    return f"Plan finished with status {status}; no file paths were observed in audit logs."


def _risk_notes(run: PlanRun) -> list[str]:
    notes: list[str] = []
    risks = {str(step.risk).upper() for step in run.plan.steps}
    statuses = {step.status for step in run.plan.steps}
    if "WRITE" in risks:
        notes.append("WRITE step present: inspect file diffs before considering the task complete.")
    if "EXECUTE" in risks:
        notes.append("EXECUTE step present: review command output for failures or side effects.")
    if "NETWORK" in risks:
        notes.append("NETWORK step present: verify external calls were intended and safe.")
    if "CRITICAL" in risks:
        notes.append("CRITICAL step present: require careful manual review.")
    if "failed" in statuses:
        notes.append("At least one step failed; do not treat the plan as fully complete.")
    if "skipped" in statuses:
        notes.append("At least one step was skipped; confirm the skipped work was optional.")
    return notes


def _suggest_tests(run: PlanRun, paths: list[str]) -> list[str]:
    suggestions: list[str] = []
    lower_paths = [path.lower() for path in paths]
    risks = {str(step.risk).upper() for step in run.plan.steps}
    tools = {tool for step in run.plan.steps for tool in step.suggested_tools}

    if any(path.endswith(".py") for path in lower_paths) or "run_shell" in tools:
        suggestions.append("Run the focused Python test suite for touched modules.")
    if any("readme" in path or path.endswith(".md") for path in lower_paths):
        suggestions.append("Review rendered Markdown or documentation text for clarity.")
    if "WRITE" in risks and not suggestions:
        suggestions.append("Run the smallest relevant verification command for the changed files.")
    if "EXECUTE" in risks:
        suggestions.append("Re-run approved shell verification if the output was inconclusive.")
    return suggestions


def _gate_decision(reviewer_input: ReviewerInputContract) -> ReviewerGateDecision:
    blocking_statuses = {"failed", "skipped", "cancelled"}
    observed = sorted(status for status in set(reviewer_input.step_statuses) if status in blocking_statuses)
    reasons = tuple(f"step status present: {status}" for status in observed)
    return ReviewerGateDecision(passed=not reasons, reasons=reasons)
