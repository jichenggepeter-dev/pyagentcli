from __future__ import annotations

from pyagentcli.agent.contracts import ExecutorStepContract
from pyagentcli.agent.plan_store import PlanStore
from pyagentcli.agent.planner import AgentHandoff, PlanRun, PlanRunStatus, PlanStep
from pyagentcli.safety.approval import ApprovalHandler
from pyagentcli.safety.policy import SafetyAction, SafetyDecision
from pyagentcli.tools.base import RiskLevel


class PlanExecutor:
    def __init__(self, *, store: PlanStore, agent_factory, approval_handler: ApprovalHandler | None = None) -> None:
        self.store = store
        self.agent_factory = agent_factory
        self.approval_handler = approval_handler or ApprovalHandler(interactive=False)

    def execute(self, run: PlanRun) -> PlanRun:
        if not run.goal:
            return self.store.save(
                PlanRun(
                    plan_id=run.plan_id,
                    goal=run.goal,
                    plan=run.plan,
                    status=PlanRunStatus.FAILED,
                    execution_result="Plan has no saved goal.",
                    handoffs=[
                        *run.handoffs,
                        AgentHandoff(
                            role="executor",
                            summary="Plan execution failed before starting.",
                            status="failed",
                            detail="Plan has no saved goal.",
                            next_action="create a new plan with a saved goal",
                        ),
                    ],
                    created_at=run.created_at,
                )
            )

        handoffs = [
            *run.handoffs,
            AgentHandoff(
                role="executor",
                summary="Started approved plan execution.",
                status="running",
                detail=f"Executing {len(run.plan.steps)} planned step(s).",
            ),
        ]
        current = self.store.save(
            PlanRun(
                plan_id=run.plan_id,
                goal=run.goal,
                plan=run.plan,
                status=PlanRunStatus.RUNNING,
                handoffs=handoffs,
                created_at=run.created_at,
            )
        )

        execution_outputs: list[str] = []
        for step in current.plan.steps:
            if step.status == "success":
                summary = step.result_summary or "already completed"
                execution_outputs.append(f"{step.id}: skipped already-successful step: {summary}")
                continue
            if step.status not in {"pending", "failed", "running"}:
                execution_outputs.append(f"{step.id}: skipped step with status {step.status}")
                continue

            approval = _approve_step(step, self.approval_handler)
            if not approval.approved:
                skipped_plan = current.plan.with_updated_step(
                    step.id,
                    status="skipped",
                    result_summary=approval.reason,
                )
                execution_outputs.append(f"{step.id}: skipped by approval: {approval.reason}")
                current = self.store.save(
                    PlanRun(
                        plan_id=current.plan_id,
                        goal=current.goal,
                        plan=skipped_plan,
                        status=PlanRunStatus.RUNNING,
                        execution_result=_join_outputs(execution_outputs),
                        handoffs=[
                            *current.handoffs,
                            AgentHandoff(
                                role="executor",
                                summary="Skipped plan step after approval denial.",
                                status="skipped",
                                detail=approval.reason,
                                step_id=step.id,
                                next_action="ask the user whether to retry or skip this step",
                            ),
                        ],
                        created_at=current.created_at,
                    )
                )
                continue

            running_plan = current.plan.with_updated_step(step.id, status="running")
            current = self.store.save(
                PlanRun(
                    plan_id=current.plan_id,
                    goal=current.goal,
                    plan=running_plan,
                    status=PlanRunStatus.RUNNING,
                    execution_result=_join_outputs(execution_outputs),
                    handoffs=current.handoffs,
                    created_at=current.created_at,
                )
            )

            try:
                output = self.agent_factory().run(_format_step_goal(current.goal or "", step))
            except Exception as exc:  # noqa: BLE001 - execution failures become plan state.
                failed_plan = current.plan.with_updated_step(
                    step.id,
                    status="failed",
                    result_summary=f"{type(exc).__name__}: {exc}",
                )
                return self.store.save(
                    PlanRun(
                        plan_id=current.plan_id,
                        goal=current.goal,
                        plan=failed_plan,
                        status=PlanRunStatus.FAILED,
                        execution_result=_join_outputs(execution_outputs + [f"{step.id}: failed: {exc}"]),
                        handoffs=[
                            *current.handoffs,
                            AgentHandoff(
                                role="executor",
                                summary="Plan step failed during execution.",
                                status="failed",
                                detail=f"{type(exc).__name__}: {exc}",
                                step_id=step.id,
                                next_action="retry this step after inspecting the failure",
                            ),
                        ],
                        created_at=current.created_at,
                    )
                )

            summary = _summarize_output(output)
            execution_outputs.append(f"{step.id}: {summary}")
            succeeded_plan = current.plan.with_updated_step(
                step.id,
                status="success",
                result_summary=summary,
            )
            current = self.store.save(
                PlanRun(
                    plan_id=current.plan_id,
                    goal=current.goal,
                    plan=succeeded_plan,
                    status=PlanRunStatus.RUNNING,
                    execution_result=_join_outputs(execution_outputs),
                    handoffs=[
                        *current.handoffs,
                        AgentHandoff(
                            role="executor",
                            summary="Completed plan step.",
                            status="success",
                            detail=summary,
                            step_id=step.id,
                        ),
                    ],
                    created_at=current.created_at,
                )
            )

        return self.store.save(
            PlanRun(
                plan_id=current.plan_id,
                goal=current.goal,
                plan=current.plan,
                status=PlanRunStatus.SUCCESS,
                execution_result=_join_outputs(execution_outputs),
                handoffs=[
                    *current.handoffs,
                    AgentHandoff(
                        role="executor",
                        summary="Finished plan execution.",
                        status="success",
                        next_action="run reviewer gate",
                    ),
                ],
                created_at=current.created_at,
            )
        )


def _format_step_goal(original_goal: str, step: PlanStep) -> str:
    return ExecutorStepContract.from_step(original_goal=original_goal, step=step).format_goal()


def _approve_step(step: PlanStep, approval_handler: ApprovalHandler):
    risk_level = _risk_level_from_step(step)
    if risk_level == RiskLevel.READ:
        decision = SafetyDecision(SafetyAction.ALLOW, "Read-only plan step.")
    else:
        decision = SafetyDecision(SafetyAction.ASK, f"{risk_level} plan step requires approval.")
    return approval_handler.request(
        tool_name=f"plan_step:{step.id}",
        risk_level=risk_level,
        args={
            "title": step.title,
            "description": step.description,
            "suggested_tools": step.suggested_tools,
        },
        decision=decision,
        preview=None,
    )


def _risk_level_from_step(step: PlanStep) -> RiskLevel:
    try:
        return RiskLevel(str(step.risk).upper())
    except ValueError:
        return RiskLevel.CRITICAL


def _summarize_output(output: str) -> str:
    clean = " ".join(output.split())
    if len(clean) > 300:
        return clean[:297] + "..."
    return clean


def _join_outputs(outputs: list[str]) -> str | None:
    if not outputs:
        return None
    return "\n".join(outputs)
