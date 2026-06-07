from pathlib import Path

from pyagentcli.agent.planner import PlanPreview, PlanRun, PlanRunStatus, PlanStep
from pyagentcli.agent.reviewer import Reviewer
from pyagentcli.llm.base import LLMResponse, Message


class FakeReviewerLLM:
    def __init__(self, content: str) -> None:
        self.content = content
        self.messages: list[Message] = []

    def chat(self, messages: list[Message], tools: list[dict]) -> LLMResponse:
        self.messages = messages
        assert tools == []
        return LLMResponse(content=self.content)


def test_reviewer_reports_risks_and_suggested_tests(tmp_path: Path) -> None:
    run = PlanRun(
        plan_id="plan_review",
        goal="update docs",
        status=PlanRunStatus.SUCCESS,
        execution_result="S1: edited README",
        plan=PlanPreview(
            summary="Update docs",
            steps=[
                PlanStep(
                    id="S1",
                    title="Edit README",
                    description="Edit README.",
                    suggested_tools=["edit_file"],
                    risk="WRITE",
                    status="success",
                ),
                PlanStep(
                    id="S2",
                    title="Verify",
                    description="Run check.",
                    suggested_tools=["run_shell"],
                    risk="EXECUTE",
                    status="success",
                ),
            ],
        ),
    )

    report = Reviewer(tmp_path).review_plan(run)

    assert report.gate.passed is True
    assert report.retry_proposal is None
    assert report.model_suggestion is None
    assert "Gate: pass" in report.format_text()
    assert "Handoff recommendation: accept after running the suggested verification commands" in report.format_text()
    assert "WRITE step present" in report.format_text()
    assert "EXECUTE step present" in report.format_text()
    assert "Run the focused Python test suite" in report.format_text()
    assert (tmp_path / ".pyagent" / "reviews" / "plan_review.md").exists()


def test_reviewer_notes_failed_and_skipped_steps(tmp_path: Path) -> None:
    run = PlanRun(
        plan_id="plan_review",
        goal="update docs",
        status=PlanRunStatus.FAILED,
        plan=PlanPreview(
            summary="Update docs",
            steps=[
                PlanStep(id="S1", title="Read", description="Read.", risk="READ", status="failed"),
                PlanStep(id="S2", title="Edit", description="Edit.", risk="WRITE", status="skipped"),
            ],
        ),
    )

    report = Reviewer(tmp_path).review_plan(run)

    assert report.gate.passed is False
    assert report.retry_proposal is not None
    assert report.retry_proposal.recommended_action == "retry_step"
    assert report.retry_proposal.target_step_id == "S1"
    assert report.retry_proposal.suggested_command == "pyagent --retry-step plan_review S1"
    assert "Gate: block" in report.format_text()
    assert "Handoff recommendation: retry the failed step" in report.format_text()
    assert "Retry proposal:" in report.format_text()
    assert "Recommended action: retry_step" in report.format_text()
    assert "Requires approval: yes" in report.format_text()
    assert "step status present: failed" in report.format_text()
    assert "step status present: skipped" in report.format_text()
    assert "At least one step failed" in report.format_text()
    assert "At least one step was skipped" in report.format_text()


def test_reviewer_proposes_user_decision_for_skipped_step(tmp_path: Path) -> None:
    run = PlanRun(
        plan_id="plan_skipped",
        goal="update docs",
        status=PlanRunStatus.FAILED,
        plan=PlanPreview(
            summary="Update docs",
            steps=[
                PlanStep(
                    id="S2",
                    title="Edit",
                    description="Edit.",
                    risk="WRITE",
                    status="skipped",
                    result_summary="denied by user",
                ),
            ],
        ),
    )

    report = Reviewer(tmp_path).review_plan(run)

    assert report.retry_proposal is not None
    assert report.retry_proposal.recommended_action == "user_decision"
    assert report.retry_proposal.target_step_id == "S2"
    assert report.retry_proposal.suggested_command == "pyagent --retry-step plan_skipped S2"
    assert "denied by user" in report.retry_proposal.reason


def test_reviewer_proposes_resume_for_cancelled_step(tmp_path: Path) -> None:
    run = PlanRun(
        plan_id="plan_cancelled",
        goal="update docs",
        status=PlanRunStatus.CANCELLED,
        plan=PlanPreview(
            summary="Update docs",
            steps=[
                PlanStep(id="S1", title="Read", description="Read.", risk="READ", status="cancelled"),
            ],
        ),
    )

    report = Reviewer(tmp_path).review_plan(run)

    assert report.retry_proposal is not None
    assert report.retry_proposal.recommended_action == "resume_plan"
    assert report.retry_proposal.target_step_id == "S1"
    assert report.retry_proposal.suggested_command == "pyagent --resume-plan plan_cancelled"


def test_reviewer_includes_model_suggestion_when_llm_is_configured(tmp_path: Path) -> None:
    run = PlanRun(
        plan_id="plan_model_review",
        goal="update docs",
        status=PlanRunStatus.FAILED,
        execution_result="pytest failed",
        plan=PlanPreview(
            summary="Update docs",
            steps=[
                PlanStep(
                    id="S1",
                    title="Run tests",
                    description="Run tests.",
                    suggested_tools=["run_shell"],
                    risk="EXECUTE",
                    status="failed",
                    result_summary="pytest failed",
                ),
            ],
        ),
    )
    fake_llm = FakeReviewerLLM(
        """
{
  "summary": "Retry the failed test step after checking the failure output.",
  "risk_notes": ["Failed verification means the task is not complete."],
  "suggested_tests": ["Re-run the focused pytest command."],
  "recommended_action": "retry_step",
  "confidence": "high"
}
""".strip()
    )

    report = Reviewer(tmp_path, llm=fake_llm).review_plan(run)

    assert report.gate.passed is False
    assert report.retry_proposal is not None
    assert report.retry_proposal.recommended_action == "retry_step"
    assert report.model_suggestion is not None
    assert report.model_suggestion.recommended_action == "retry_step"
    assert report.model_suggestion.confidence == "high"
    assert "Model-backed reviewer suggestion:" in report.format_text()
    assert "Retry the failed test step" in report.format_text()
    assert "deterministic_review" in (fake_llm.messages[-1].content or "")


def test_reviewer_sanitizes_invalid_model_suggestion(tmp_path: Path) -> None:
    run = PlanRun(
        plan_id="plan_invalid_model_review",
        goal="update docs",
        status=PlanRunStatus.SUCCESS,
        plan=PlanPreview(
            summary="Update docs",
            steps=[PlanStep(id="S1", title="Read", description="Read.", risk="READ", status="success")],
        ),
    )

    report = Reviewer(tmp_path, llm=FakeReviewerLLM("not json")).review_plan(run)

    assert report.gate.passed is True
    assert report.model_suggestion is not None
    assert report.model_suggestion.recommended_action == "inspect"
    assert report.model_suggestion.confidence == "low"
