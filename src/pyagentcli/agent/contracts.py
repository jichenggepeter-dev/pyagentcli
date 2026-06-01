from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pyagentcli.agent.planner import PlanRun, PlanStep


class AgentRole(StrEnum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"


@dataclass(frozen=True)
class ExecutorStepContract:
    original_goal: str
    step_id: str
    title: str
    risk: str
    suggested_tools: tuple[str, ...]
    instructions: str

    @classmethod
    def from_step(cls, *, original_goal: str, step: PlanStep) -> "ExecutorStepContract":
        return cls(
            original_goal=original_goal,
            step_id=step.id,
            title=step.title,
            risk=step.risk,
            suggested_tools=tuple(step.suggested_tools),
            instructions=step.description,
        )

    def format_goal(self) -> str:
        tools = ", ".join(self.suggested_tools) if self.suggested_tools else "none"
        return (
            "Role: Executor Agent\n"
            "Execute exactly this approved plan step. Use tools when workspace information or changes are needed.\n\n"
            f"Original task:\n{self.original_goal}\n\n"
            f"Step {self.step_id}: {self.title}\n"
            f"Risk: {self.risk}\n"
            f"Suggested tools: {tools}\n"
            f"Step instructions:\n{self.instructions}\n\n"
            "Stop after this step and summarize what happened."
        )


@dataclass(frozen=True)
class ReviewerGateDecision:
    passed: bool
    reasons: tuple[str, ...]

    def format_text(self) -> str:
        status = "pass" if self.passed else "block"
        if not self.reasons:
            return f"Gate: {status}"
        return f"Gate: {status} - {'; '.join(self.reasons)}"


@dataclass(frozen=True)
class ReviewerInputContract:
    run: PlanRun

    @property
    def step_statuses(self) -> tuple[str, ...]:
        return tuple(step.status for step in self.run.plan.steps)
