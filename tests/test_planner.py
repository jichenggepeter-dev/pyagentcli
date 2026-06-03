from typing import Any

from pyagentcli.agent.planner import PlanRun, PlanRunStatus, Planner
from pyagentcli.llm.base import LLMResponse, Message


class FakePlannerLLM:
    def __init__(self, content: str) -> None:
        self.content = content
        self.last_tools: list[dict[str, Any]] | None = None
        self.last_messages: list[Message] | None = None

    def chat(self, messages: list[Message], tools: list[dict[str, Any]]) -> LLMResponse:
        self.last_messages = messages
        self.last_tools = tools
        return LLMResponse(content=self.content)


def test_planner_parses_json_plan() -> None:
    llm = FakePlannerLLM(
        """
        {
          "summary": "Update the demo safely.",
          "steps": [
            {
              "id": "S1",
              "title": "Read README",
              "description": "Inspect the existing status line.",
              "suggested_tools": ["read_file"],
              "risk": "READ"
            },
            {
              "id": "S2",
              "title": "Edit status",
              "description": "Replace TODO with READY.",
              "suggested_tools": ["edit_file"],
              "risk": "WRITE"
            }
          ]
        }
        """
    )

    plan = Planner(llm).preview("change status")

    assert llm.last_tools == []
    assert plan.summary == "Update the demo safely."
    assert len(plan.steps) == 2
    assert plan.steps[1].suggested_tools == ["edit_file"]
    assert plan.steps[0].status == "pending"


def test_planner_uses_custom_system_prompt() -> None:
    llm = FakePlannerLLM("not json")

    Planner(llm, system_prompt="Custom planner role prompt.").preview("change status")

    assert llm.last_messages is not None
    assert llm.last_messages[0].role == "system"
    assert llm.last_messages[0].content == "Custom planner role prompt."


def test_planner_falls_back_on_non_json() -> None:
    plan = Planner(FakePlannerLLM("I would inspect, edit, and test.")).preview("fix tests")

    assert plan.summary == "Plan for: fix tests"
    assert [step.id for step in plan.steps] == ["S1", "S2", "S3"]
    assert plan.steps[2].risk == "EXECUTE"


def test_plan_formats_executor_goal() -> None:
    plan = Planner(FakePlannerLLM("not json")).preview("update README")

    executor_goal = plan.format_executor_goal("update README")

    assert "Original task:" in executor_goal
    assert "Approved plan:" in executor_goal
    assert "update README" in executor_goal
    assert "S1. [pending] Inspect workspace" in executor_goal


def test_plan_can_update_step_statuses() -> None:
    plan = Planner(FakePlannerLLM("not json")).preview("update README")

    running_plan = plan.with_step_status("running")

    assert all(step.status == "running" for step in running_plan.steps)
    assert all(step.status == "pending" for step in plan.steps)


def test_plan_update_step_raises_for_missing_step() -> None:
    plan = Planner(FakePlannerLLM("not json")).preview("update README")

    try:
        plan.with_updated_step("S99", status="skipped")
    except ValueError as exc:
        assert "Step not found: S99" in str(exc)
    else:
        raise AssertionError("Expected missing step to raise")


def test_plan_run_formats_status_and_result() -> None:
    plan = Planner(FakePlannerLLM("not json")).preview("update README")
    run = PlanRun(plan_id=None, plan=plan, status=PlanRunStatus.SUCCESS, execution_result="done")

    text = run.format_text()

    assert "PlanRun status: success" in text
    assert "Execution result:" in text
    assert "done" in text


def test_plan_retry_from_step_resets_target_and_following_steps() -> None:
    plan = Planner(FakePlannerLLM("not json")).preview("update README").with_step_status(
        "success",
        result_summary="done",
    )

    retry_plan = plan.with_retry_from_step("S2")

    assert [step.status for step in retry_plan.steps] == ["success", "pending", "pending"]
    assert retry_plan.steps[0].result_summary == "done"
    assert retry_plan.steps[1].result_summary is None
    assert retry_plan.steps[2].result_summary is None
