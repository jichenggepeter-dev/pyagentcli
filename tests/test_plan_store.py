from pathlib import Path

from pyagentcli.agent.plan_store import PlanStore
from pyagentcli.agent.planner import AgentHandoff, PlanPreview, PlanRun, PlanRunStatus, PlanStep


def test_plan_store_saves_and_loads_plan_run(tmp_path: Path) -> None:
    store = PlanStore(tmp_path)
    run = PlanRun(
        plan_id=None,
        goal="update demo",
        status=PlanRunStatus.PLANNED,
        plan=PlanPreview(
            summary="Update safely.",
            steps=[
                PlanStep(
                    id="S1",
                    title="Read file",
                    description="Read README.",
                    suggested_tools=["read_file"],
                    risk="READ",
                )
            ],
        ),
    )

    saved = store.save(run)
    loaded = store.load(saved.plan_id or "")

    assert saved.plan_id is not None
    assert saved.created_at is not None
    assert saved.updated_at is not None
    assert loaded.goal == "update demo"
    assert loaded.status == PlanRunStatus.PLANNED
    assert loaded.plan.steps[0].title == "Read file"


def test_plan_store_preserves_review_result(tmp_path: Path) -> None:
    store = PlanStore(tmp_path)
    saved = store.save(
        PlanRun(
            plan_id="plan_review",
            goal="review task",
            status=PlanRunStatus.SUCCESS,
            plan=PlanPreview(summary="Review", steps=[]),
            review_result="Review: looks good",
        )
    )

    loaded = store.load(saved.plan_id or "")

    assert loaded.review_result == "Review: looks good"
    assert "Review result:" in loaded.format_text()


def test_plan_store_preserves_agent_handoffs(tmp_path: Path) -> None:
    store = PlanStore(tmp_path)
    saved = store.save(
        PlanRun(
            plan_id="plan_handoff",
            goal="handoff task",
            status=PlanRunStatus.PLANNED,
            plan=PlanPreview(summary="Handoff", steps=[]),
            handoffs=[
                AgentHandoff(
                    role="planner",
                    summary="Produced plan.",
                    status="planned",
                    detail="1 step.",
                    next_action="ask approval",
                )
            ],
        )
    )

    loaded = store.load(saved.plan_id or "")

    assert loaded.handoffs[0].role == "planner"
    assert loaded.handoffs[0].next_action == "ask approval"
    assert "Agent handoffs:" in loaded.format_text()
    assert "planner: Produced plan. [planned]" in loaded.format_text()


def test_plan_store_lists_runs_newest_first(tmp_path: Path) -> None:
    store = PlanStore(tmp_path)
    first = store.save(
        PlanRun(
            plan_id="plan_first",
            goal="first",
            status=PlanRunStatus.PLANNED,
            plan=PlanPreview(summary="First", steps=[]),
        )
    )
    second = store.save(
        PlanRun(
            plan_id="plan_second",
            goal="second",
            status=PlanRunStatus.SUCCESS,
            plan=PlanPreview(summary="Second", steps=[]),
        )
    )

    runs = store.list_runs()

    assert {run.plan_id for run in runs} == {first.plan_id, second.plan_id}
    assert runs[0].updated_at >= runs[1].updated_at
