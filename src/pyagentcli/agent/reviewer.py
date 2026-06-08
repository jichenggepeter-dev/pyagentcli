from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyagentcli.agent.contracts import ReviewerGateDecision, ReviewerInputContract
from pyagentcli.agent.planner import PlanRun, PlanStep
from pyagentcli.llm.base import LLMClient, Message


MODEL_REVIEWER_PROMPT = """You are PyAgentCLI Reviewer Advisor.

You provide optional review advice after the deterministic Reviewer has already produced a gate decision.
You must not claim to execute tools, retry steps, or override the deterministic gate.

Return only JSON with this shape:

{
  "summary": "one concise sentence",
  "risk_notes": ["risk note"],
  "suggested_tests": ["test suggestion"],
  "recommended_action": "accept|retry_step|resume_plan|user_decision|inspect",
  "confidence": "low|medium|high"
}
"""


@dataclass(frozen=True)
class RetryProposal:
    recommended_action: str
    reason: str
    target_step_id: str | None = None
    suggested_command: str | None = None
    requires_approval: bool = True

    def format_text(self) -> str:
        lines = ["Retry proposal:"]
        lines.append(f"- Recommended action: {self.recommended_action}")
        if self.target_step_id:
            lines.append(f"- Target step: {self.target_step_id}")
        lines.append(f"- Reason: {self.reason}")
        if self.suggested_command:
            lines.append(f"- Suggested command: `{self.suggested_command}`")
        approval = "yes" if self.requires_approval else "no"
        lines.append(f"- Requires approval: {approval}")
        return "\n".join(lines)


@dataclass(frozen=True)
class ModelReviewSuggestion:
    summary: str
    risk_notes: list[str]
    suggested_tests: list[str]
    recommended_action: str
    confidence: str
    raw_response: str

    def format_text(self) -> str:
        lines = ["Model-backed reviewer suggestion:"]
        lines.append(f"- Summary: {self.summary}")
        lines.append(f"- Recommended action: {self.recommended_action}")
        lines.append(f"- Confidence: {self.confidence}")
        lines.append("- Risk notes:")
        lines.extend(f"  - {note}" for note in (self.risk_notes or ["<none>"]))
        lines.append("- Suggested tests:")
        lines.extend(f"  - {test}" for test in (self.suggested_tests or ["<none>"]))
        return "\n".join(lines)


@dataclass(frozen=True)
class GitChangedFile:
    path: str
    added_lines: int
    removed_lines: int

    @property
    def changed_lines(self) -> int:
        return self.added_lines + self.removed_lines


@dataclass(frozen=True)
class ChangedFileRisk:
    path: str
    level: str
    score: int
    reasons: list[str]
    suggested_tests: list[str]

    def format_text(self) -> str:
        reasons = "; ".join(self.reasons) if self.reasons else "No special risk signals."
        tests = "; ".join(self.suggested_tests) if self.suggested_tests else "No specific test suggestion."
        return f"{self.level.upper()} {self.path} (score={self.score}): {reasons} Suggested: {tests}"


@dataclass(frozen=True)
class GitDiffSummary:
    available: bool
    has_diff: bool
    message: str
    changed_files: list[GitChangedFile]
    hunks: list[str]
    file_risks: list[ChangedFileRisk]

    def format_text(self) -> str:
        lines = ["Git diff summary:"]
        lines.append(f"- Status: {self.message}")
        lines.append("- Changed files:")
        if self.changed_files:
            lines.extend(
                f"  - {file.path} (+{file.added_lines}/-{file.removed_lines})"
                for file in self.changed_files
            )
        else:
            lines.append("  - <none>")
        lines.append("- Key hunks:")
        lines.extend(f"  - {hunk}" for hunk in (self.hunks or ["<none>"]))
        lines.append("- Changed-file risk scoring:")
        if self.file_risks:
            lines.extend(f"  - {risk.format_text()}" for risk in self.file_risks)
        else:
            lines.append("  - <none>")
        return "\n".join(lines)


@dataclass(frozen=True)
class ReviewReport:
    summary: str
    risks: list[str]
    suggested_tests: list[str]
    tools: list[str]
    paths: list[str]
    gate: ReviewerGateDecision
    handoff_recommendation: str
    git_diff: GitDiffSummary
    retry_proposal: RetryProposal | None = None
    model_suggestion: ModelReviewSuggestion | None = None

    def format_text(self) -> str:
        lines = [f"Review: {self.summary}", ""]
        lines.append(self.gate.format_text())
        lines.append(f"Handoff recommendation: {self.handoff_recommendation}")
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
        lines.extend(["", self.git_diff.format_text()])
        if self.retry_proposal is not None:
            lines.extend(["", self.retry_proposal.format_text()])
        if self.model_suggestion is not None:
            lines.extend(["", self.model_suggestion.format_text()])
        return "\n".join(lines)


class Reviewer:
    def __init__(
        self,
        workspace_root: Path,
        *,
        llm: LLMClient | None = None,
        model_system_prompt: str | None = None,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.reviews_dir = self.workspace_root / ".pyagent" / "reviews"
        self.llm = llm
        self.model_system_prompt = model_system_prompt or MODEL_REVIEWER_PROMPT

    def review_plan(self, run: PlanRun) -> ReviewReport:
        reviewer_input = ReviewerInputContract(run=run)
        tools, paths = self._audit_summary(run)
        git_diff = _git_diff_summary(self.workspace_root)
        risks = _risk_notes(run, git_diff)
        suggested_tests = _suggest_tests(run, paths, git_diff)
        summary = _summary(run, paths, git_diff)
        gate = _gate_decision(reviewer_input)
        handoff_recommendation = _handoff_recommendation(reviewer_input, gate)
        retry_proposal = _retry_proposal(run)
        model_suggestion = self._model_suggestion(
            run=run,
            summary=summary,
            risks=risks,
            suggested_tests=suggested_tests,
            gate=gate,
            retry_proposal=retry_proposal,
            git_diff=git_diff,
        )
        report = ReviewReport(
            summary=summary,
            risks=risks,
            suggested_tests=suggested_tests,
            tools=tools,
            paths=paths,
            gate=gate,
            handoff_recommendation=handoff_recommendation,
            git_diff=git_diff,
            retry_proposal=retry_proposal,
            model_suggestion=model_suggestion,
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

    def _model_suggestion(
        self,
        *,
        run: PlanRun,
        summary: str,
        risks: list[str],
        suggested_tests: list[str],
        gate: ReviewerGateDecision,
        retry_proposal: RetryProposal | None,
        git_diff: GitDiffSummary,
    ) -> ModelReviewSuggestion | None:
        if self.llm is None:
            return None

        prompt = _model_review_prompt(
            run=run,
            summary=summary,
            risks=risks,
            suggested_tests=suggested_tests,
            gate=gate,
            retry_proposal=retry_proposal,
            git_diff=git_diff,
        )
        response = self.llm.chat(
            [Message.system(self.model_system_prompt), Message.user(prompt)],
            tools=[],
        )
        return _parse_model_suggestion(response.content or "")


def _summary(run: PlanRun, paths: list[str], git_diff: GitDiffSummary) -> str:
    status = str(run.status)
    if git_diff.has_diff:
        changed = ", ".join(file.path for file in git_diff.changed_files[:5])
        return f"Plan finished with status {status}; git diff changed: {changed}."
    if paths:
        return f"Plan finished with status {status}; observed workspace paths: {', '.join(paths[:5])}."
    return f"Plan finished with status {status}; no file paths were observed in audit logs."


def _model_review_prompt(
    *,
    run: PlanRun,
    summary: str,
    risks: list[str],
    suggested_tests: list[str],
    gate: ReviewerGateDecision,
    retry_proposal: RetryProposal | None,
    git_diff: GitDiffSummary,
) -> str:
    steps = [
        {
            "id": step.id,
            "title": step.title,
            "risk": step.risk,
            "status": step.status,
            "result_summary": step.result_summary,
            "suggested_tools": step.suggested_tools,
        }
        for step in run.plan.steps
    ]
    payload = {
        "goal": run.goal,
        "plan_status": str(run.status),
        "execution_result": run.execution_result,
        "deterministic_review": {
            "summary": summary,
            "risks": risks,
            "suggested_tests": suggested_tests,
            "gate_passed": gate.passed,
            "gate_reasons": list(gate.reasons),
            "retry_proposal": {
                "recommended_action": retry_proposal.recommended_action,
                "target_step_id": retry_proposal.target_step_id,
                "reason": retry_proposal.reason,
                "requires_approval": retry_proposal.requires_approval,
            }
            if retry_proposal is not None
            else None,
            "git_diff": {
                "available": git_diff.available,
                "has_diff": git_diff.has_diff,
                "message": git_diff.message,
                "changed_files": [
                    {
                        "path": file.path,
                        "added_lines": file.added_lines,
                        "removed_lines": file.removed_lines,
                    }
                    for file in git_diff.changed_files
                ],
                "file_risks": [
                    {
                        "path": risk.path,
                        "level": risk.level,
                        "score": risk.score,
                        "reasons": risk.reasons,
                        "suggested_tests": risk.suggested_tests,
                    }
                    for risk in git_diff.file_risks
                ],
            },
        },
        "steps": steps,
        "constraints": [
            "Do not override the deterministic gate.",
            "Do not suggest executing tools automatically.",
            "Recommended action must be one of accept, retry_step, resume_plan, user_decision, inspect.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _parse_model_suggestion(content: str) -> ModelReviewSuggestion:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return ModelReviewSuggestion(
            summary="Model reviewer returned non-JSON advice.",
            risk_notes=[],
            suggested_tests=[],
            recommended_action="inspect",
            confidence="low",
            raw_response=content,
        )

    if not isinstance(payload, dict):
        payload = {}
    recommended_action = _allowed_action(str(payload.get("recommended_action") or "inspect"))
    confidence = str(payload.get("confidence") or "low").lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "low"
    return ModelReviewSuggestion(
        summary=str(payload.get("summary") or "No model reviewer summary provided."),
        risk_notes=_string_list(payload.get("risk_notes")),
        suggested_tests=_string_list(payload.get("suggested_tests")),
        recommended_action=recommended_action,
        confidence=confidence,
        raw_response=content,
    )


def _allowed_action(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"accept", "retry_step", "resume_plan", "user_decision", "inspect"}:
        return normalized
    return "inspect"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _git_diff_summary(workspace_root: Path) -> GitDiffSummary:
    inside = _run_git(workspace_root, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return GitDiffSummary(
            available=False,
            has_diff=False,
            message="workspace is not a git repository",
            changed_files=[],
            hunks=[],
            file_risks=[],
        )

    numstat = _run_git(workspace_root, "diff", "HEAD", "--numstat", "--")
    diff_text = _run_git(workspace_root, "diff", "HEAD", "--unified=1", "--no-ext-diff", "--")
    if numstat.returncode != 0 or diff_text.returncode != 0:
        numstat = _run_git(workspace_root, "diff", "--numstat", "--")
        diff_text = _run_git(workspace_root, "diff", "--unified=1", "--no-ext-diff", "--")

    changed_files = _parse_numstat(numstat.stdout if numstat.returncode == 0 else "")
    hunks = _extract_hunks(diff_text.stdout if diff_text.returncode == 0 else "")
    untracked_files = _untracked_files(workspace_root)
    known_paths = {file.path for file in changed_files}
    for path in untracked_files:
        if path not in known_paths:
            changed_files.append(GitChangedFile(path=path, added_lines=0, removed_lines=0))
            hunks.append(f"{path}: untracked file")
    if not changed_files and not hunks:
        return GitDiffSummary(
            available=True,
            has_diff=False,
            message="no uncommitted git diff found",
            changed_files=[],
            hunks=[],
            file_risks=[],
        )
    file_risks = [_score_changed_file(file) for file in changed_files]
    return GitDiffSummary(
        available=True,
        has_diff=True,
        message=f"{len(changed_files)} changed file(s) in git diff",
        changed_files=changed_files,
        hunks=hunks,
        file_risks=file_risks,
    )


def _run_git(workspace_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(workspace_root), *args],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(
            args=["git", "-C", str(workspace_root), *args],
            returncode=1,
            stdout="",
            stderr=str(exc),
        )


def _parse_numstat(output: str) -> list[GitChangedFile]:
    changed: list[GitChangedFile] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added = _parse_git_line_count(parts[0])
        removed = _parse_git_line_count(parts[1])
        path = parts[2]
        if path:
            changed.append(GitChangedFile(path=path, added_lines=added, removed_lines=removed))
    return changed


def _parse_git_line_count(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def _extract_hunks(diff_text: str, *, max_hunks: int = 8, max_chars: int = 280) -> list[str]:
    hunks: list[str] = []
    current_file = ""
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line.removeprefix("+++ b/")
            continue
        if not line.startswith("@@"):
            continue
        hunk = line
        if current_file:
            hunk = f"{current_file}: {line}"
        if len(hunk) > max_chars:
            hunk = hunk[: max_chars - 3] + "..."
        hunks.append(hunk)
        if len(hunks) >= max_hunks:
            break
    return hunks


def _untracked_files(workspace_root: Path) -> list[str]:
    status = _run_git(workspace_root, "status", "--porcelain", "--untracked-files=normal")
    if status.returncode != 0:
        return []
    paths: list[str] = []
    for line in status.stdout.splitlines():
        if not line.startswith("?? "):
            continue
        path = line[3:].strip()
        if path and not path.startswith(".pyagent/"):
            paths.append(path)
    return paths


def _score_changed_file(file: GitChangedFile) -> ChangedFileRisk:
    path = file.path
    lower = path.lower()
    score = 1
    reasons: list[str] = []
    suggested_tests: list[str] = []

    if lower.startswith("src/pyagentcli/safety/"):
        score += 7
        reasons.append("safety boundary path changed")
        suggested_tests.append("run tests/test_safety_policy.py")
    elif lower.startswith("src/pyagentcli/tools/"):
        score += 4
        reasons.append("tool execution path changed")
        suggested_tests.append("run tests/test_tools.py")
    elif lower.startswith("src/pyagentcli/llm/"):
        score += 4
        reasons.append("LLM adapter or tool-calling path changed")
        suggested_tests.append("run tests/test_llm_model_config.py and model smoke checks")
    elif lower.startswith("src/pyagentcli/agent/"):
        score += 3
        reasons.append("agent orchestration path changed")
        suggested_tests.append("run planner, executor, and reviewer tests")
    elif lower.startswith("src/pyagentcli/rag/"):
        score += 3
        reasons.append("retrieval/indexing path changed")
        suggested_tests.append("run RAG indexer and retriever tests")
    elif lower.startswith("src/"):
        score += 2
        reasons.append("runtime source file changed")
        suggested_tests.append("run focused Python tests for touched module")

    if lower.startswith("tests/"):
        score += 1
        reasons.append("test coverage changed")
        suggested_tests.append("run the changed test file")
    if lower.startswith("docs/") or lower.endswith((".md", ".rst")):
        reasons.append("documentation changed")
        suggested_tests.append("review rendered documentation text")
    if lower in {"pyproject.toml", "requirements.txt"} or lower.endswith((".lock", "lockfile")):
        score += 3
        reasons.append("packaging or dependency metadata changed")
        suggested_tests.append("run packaging and install smoke tests")
    if lower.endswith((".yml", ".yaml", ".toml", ".json")) and not lower.startswith("docs/"):
        score += 2
        reasons.append("configuration file changed")
        suggested_tests.append("run config and packaging tests")

    if file.changed_lines >= 200:
        score += 3
        reasons.append(f"large diff size ({file.changed_lines} changed lines)")
    elif file.changed_lines >= 50:
        score += 2
        reasons.append(f"medium diff size ({file.changed_lines} changed lines)")
    elif file.changed_lines > 0:
        reasons.append(f"small diff size ({file.changed_lines} changed lines)")

    if file.removed_lines >= 50:
        score += 2
        reasons.append(f"many removed lines ({file.removed_lines})")
    elif file.removed_lines > file.added_lines and file.removed_lines >= 10:
        score += 1
        reasons.append("deletion-heavy diff")

    level = _risk_level_from_score(score)
    return ChangedFileRisk(
        path=path,
        level=level,
        score=score,
        reasons=_dedupe_text(reasons),
        suggested_tests=_dedupe_text(suggested_tests),
    )


def _risk_level_from_score(score: int) -> str:
    if score >= 7:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def _dedupe_text(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def _risk_notes(run: PlanRun, git_diff: GitDiffSummary) -> list[str]:
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
    if git_diff.has_diff:
        changed_paths = [file.path.lower() for file in git_diff.changed_files]
        notes.append("Git diff present: review changed files before accepting the plan.")
        high_risk = [risk for risk in git_diff.file_risks if risk.level == "high"]
        medium_risk = [risk for risk in git_diff.file_risks if risk.level == "medium"]
        if high_risk:
            paths = ", ".join(risk.path for risk in high_risk[:5])
            notes.append(f"High-risk changed files: {paths}.")
        if medium_risk:
            paths = ", ".join(risk.path for risk in medium_risk[:5])
            notes.append(f"Medium-risk changed files: {paths}.")
        if any(path.endswith(".py") for path in changed_paths):
            notes.append("Python files changed in git diff: run focused pytest coverage.")
        if any(path.endswith((".md", ".rst")) for path in changed_paths):
            notes.append("Documentation changed in git diff: check rendered wording and examples.")
    elif git_diff.available:
        notes.append("No uncommitted git diff found for Reviewer to inspect.")
    return notes


def _suggest_tests(run: PlanRun, paths: list[str], git_diff: GitDiffSummary) -> list[str]:
    suggestions: list[str] = []
    lower_paths = [path.lower() for path in paths]
    lower_paths.extend(file.path.lower() for file in git_diff.changed_files)
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
    for risk in git_diff.file_risks:
        suggestions.extend(risk.suggested_tests)
    return _dedupe_text(suggestions)


def _gate_decision(reviewer_input: ReviewerInputContract) -> ReviewerGateDecision:
    blocking_statuses = {"failed", "skipped", "cancelled"}
    observed = sorted(status for status in set(reviewer_input.step_statuses) if status in blocking_statuses)
    reasons = tuple(f"step status present: {status}" for status in observed)
    return ReviewerGateDecision(passed=not reasons, reasons=reasons)


def _handoff_recommendation(reviewer_input: ReviewerInputContract, gate: ReviewerGateDecision) -> str:
    statuses = set(reviewer_input.step_statuses)
    if gate.passed:
        return "accept after running the suggested verification commands"
    if "failed" in statuses:
        return "retry the failed step after inspecting the execution result"
    if "skipped" in statuses:
        return "ask the user to retry, explicitly skip, or accept the skipped work as out of scope"
    if "cancelled" in statuses:
        return "resume the plan only after renewed user approval"
    return "inspect the plan state before continuing"


def _retry_proposal(run: PlanRun) -> RetryProposal | None:
    failed = _first_step_with_status(run, "failed")
    if failed is not None:
        return RetryProposal(
            recommended_action="retry_step",
            target_step_id=failed.id,
            reason=_step_reason(failed, "The step failed during execution."),
            suggested_command=_retry_command(run, failed),
            requires_approval=True,
        )

    skipped = _first_step_with_status(run, "skipped")
    if skipped is not None:
        return RetryProposal(
            recommended_action="user_decision",
            target_step_id=skipped.id,
            reason=_step_reason(skipped, "The step was skipped and may still be required."),
            suggested_command=_retry_command(run, skipped),
            requires_approval=True,
        )

    cancelled = _first_step_with_status(run, "cancelled")
    if cancelled is not None:
        return RetryProposal(
            recommended_action="resume_plan",
            target_step_id=cancelled.id,
            reason=_step_reason(cancelled, "The plan has a cancelled step and needs renewed user approval."),
            suggested_command=_resume_command(run),
            requires_approval=True,
        )

    return None


def _first_step_with_status(run: PlanRun, status: str) -> PlanStep | None:
    return next((step for step in run.plan.steps if step.status == status), None)


def _step_reason(step: PlanStep, fallback: str) -> str:
    if step.result_summary:
        return f"{fallback} Result summary: {step.result_summary}"
    return fallback


def _retry_command(run: PlanRun, step: PlanStep) -> str | None:
    if not run.plan_id:
        return None
    return f"pyagent --retry-step {run.plan_id} {step.id}"


def _resume_command(run: PlanRun) -> str | None:
    if not run.plan_id:
        return None
    return f"pyagent --resume-plan {run.plan_id}"
