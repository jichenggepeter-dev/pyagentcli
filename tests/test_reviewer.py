from pathlib import Path

from pyagentcli.agent.planner import PlanPreview, PlanRun, PlanRunStatus, PlanStep
from pyagentcli.agent.reviewer import Reviewer


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
    assert "Gate: pass" in report.format_text()
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
    assert "Gate: block" in report.format_text()
    assert "step status present: failed" in report.format_text()
    assert "step status present: skipped" in report.format_text()
    assert "At least one step failed" in report.format_text()
    assert "At least one step was skipped" in report.format_text()
