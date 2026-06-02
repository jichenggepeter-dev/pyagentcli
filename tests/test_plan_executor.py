from pathlib import Path

from pyagentcli.agent.plan_executor import PlanExecutor
from pyagentcli.agent.plan_store import PlanStore
from pyagentcli.agent.planner import PlanPreview, PlanRun, PlanRunStatus, PlanStep
from pyagentcli.safety.approval import ApprovalResult
from pyagentcli.safety.policy import SafetyAction


class FakeAgent:
    def __init__(self, outputs: list[str], calls: list[str]) -> None:
        self.outputs = outputs
        self.calls = calls

    def run(self, goal: str) -> str:
        self.calls.append(goal)
        if not self.outputs:
            raise RuntimeError("no output configured")
        output = self.outputs.pop(0)
        if output == "__raise__":
            raise RuntimeError("boom")
        return output


class FakeApproval:
    def __init__(self, approved: bool = True) -> None:
        self.approved = approved
        self.requests: list[str] = []

    def request(self, *, tool_name, risk_level, args, decision, preview=None) -> ApprovalResult:
        self.requests.append(f"{tool_name}:{risk_level}")
        if decision.action == SafetyAction.ALLOW:
            return ApprovalResult(True, decision.reason)
        if self.approved:
            return ApprovalResult(True, "approved in test")
        return ApprovalResult(False, "denied in test")


def make_run() -> PlanRun:
    return PlanRun(
        plan_id=None,
        goal="update demo",
        status=PlanRunStatus.PLANNED,
        plan=PlanPreview(
            summary="Update demo",
            steps=[
                PlanStep(id="S1", title="Read", description="Read README.", suggested_tools=["read_file"], risk="READ"),
                PlanStep(id="S2", title="Edit", description="Edit README.", suggested_tools=["edit_file"], risk="WRITE"),
            ],
        ),
    )


def test_plan_executor_runs_steps_serially(tmp_path: Path) -> None:
    store = PlanStore(tmp_path)
    saved = store.save(make_run())
    calls: list[str] = []
    outputs = ["read complete", "edit complete"]

    approval = FakeApproval()
    executor = PlanExecutor(store=store, agent_factory=lambda: FakeAgent(outputs, calls), approval_handler=approval)
    completed = executor.execute(saved)

    assert completed.status == PlanRunStatus.SUCCESS
    assert [step.status for step in completed.plan.steps] == ["success", "success"]
    assert "S1: read complete" in (completed.execution_result or "")
    assert "S2: edit complete" in (completed.execution_result or "")
    assert [handoff.role for handoff in completed.handoffs] == ["executor", "executor", "executor", "executor"]
    assert completed.handoffs[-1].next_action == "run reviewer gate"
    assert len(calls) == 2
    assert "Step S1: Read" in calls[0]
    assert "Role: Executor Agent" in calls[0]
    assert "Step S2: Edit" in calls[1]
    assert len(approval.requests) == 2


def test_plan_executor_stops_on_step_failure(tmp_path: Path) -> None:
    store = PlanStore(tmp_path)
    saved = store.save(make_run())
    calls: list[str] = []
    outputs = ["read complete", "__raise__"]

    executor = PlanExecutor(store=store, agent_factory=lambda: FakeAgent(outputs, calls), approval_handler=FakeApproval())
    failed = executor.execute(saved)

    assert failed.status == PlanRunStatus.FAILED
    assert [step.status for step in failed.plan.steps] == ["success", "failed"]
    assert "boom" in (failed.execution_result or "")
    assert failed.handoffs[-1].status == "failed"
    assert failed.handoffs[-1].step_id == "S2"
    assert "retry this step" in (failed.handoffs[-1].next_action or "")
    assert len(calls) == 2


def test_plan_executor_resume_skips_successful_steps(tmp_path: Path) -> None:
    store = PlanStore(tmp_path)
    run = PlanRun(
        plan_id=None,
        goal="update demo",
        status=PlanRunStatus.FAILED,
        plan=PlanPreview(
            summary="Update demo",
            steps=[
                PlanStep(
                    id="S1",
                    title="Read",
                    description="Read README.",
                    suggested_tools=["read_file"],
                    risk="READ",
                    status="success",
                    result_summary="read complete",
                ),
                PlanStep(
                    id="S2",
                    title="Edit",
                    description="Edit README.",
                    suggested_tools=["edit_file"],
                    risk="WRITE",
                    status="failed",
                    result_summary="previous failure",
                ),
            ],
        ),
    )
    saved = store.save(run)
    calls: list[str] = []
    outputs = ["edit complete"]

    executor = PlanExecutor(store=store, agent_factory=lambda: FakeAgent(outputs, calls), approval_handler=FakeApproval())
    completed = executor.execute(saved)

    assert completed.status == PlanRunStatus.SUCCESS
    assert [step.status for step in completed.plan.steps] == ["success", "success"]
    assert len(calls) == 1
    assert "Step S2: Edit" in calls[0]
    assert "S1: skipped already-successful step: read complete" in (completed.execution_result or "")
    assert "S2: edit complete" in (completed.execution_result or "")


def test_plan_executor_skips_denied_risky_step(tmp_path: Path) -> None:
    store = PlanStore(tmp_path)
    saved = store.save(make_run())
    calls: list[str] = []
    outputs = ["read complete"]
    approval = FakeApproval(approved=False)

    executor = PlanExecutor(store=store, agent_factory=lambda: FakeAgent(outputs, calls), approval_handler=approval)
    completed = executor.execute(saved)

    assert completed.status == PlanRunStatus.SUCCESS
    assert [step.status for step in completed.plan.steps] == ["success", "skipped"]
    assert len(calls) == 1
    assert "Step S1: Read" in calls[0]
    assert "S2: skipped by approval: denied in test" in (completed.execution_result or "")
    assert any(handoff.status == "skipped" and handoff.step_id == "S2" for handoff in completed.handoffs)
