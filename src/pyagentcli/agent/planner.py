from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from pyagentcli.llm.base import LLMClient, Message

VALID_STEP_STATUSES = {"pending", "running", "success", "failed", "skipped", "cancelled"}


PLANNER_PROMPT = """You are PyAgentCLI Planner.

Create a concise execution plan for a local coding agent.
Do not call tools.
Do not edit files.
Return only JSON with this shape:

{
  "summary": "one sentence",
  "steps": [
    {
      "id": "S1",
      "title": "short title",
      "description": "what the executor should do",
      "suggested_tools": ["list_files", "read_file"],
      "risk": "READ"
    }
  ]
}

Risk must be one of READ, WRITE, EXECUTE, NETWORK, CRITICAL.
Prefer small, reviewable steps.
Put approval-sensitive write or shell actions in their own steps.
"""


@dataclass(frozen=True)
class PlanStep:
    id: str
    title: str
    description: str
    suggested_tools: list[str] = field(default_factory=list)
    risk: str = "READ"
    status: str = "pending"
    result_summary: str | None = None


@dataclass(frozen=True)
class PlanPreview:
    summary: str
    steps: list[PlanStep]
    raw_content: str | None = None

    def format_text(self) -> str:
        lines = [f"Plan: {self.summary}", ""]
        for step in self.steps:
            tools = ", ".join(step.suggested_tools) if step.suggested_tools else "none"
            lines.append(f"{step.id}. [{step.status}] {step.title}")
            lines.append(f"   Risk: {step.risk}")
            lines.append(f"   Tools: {tools}")
            lines.append(f"   {step.description}")
            if step.result_summary:
                lines.append(f"   Result: {step.result_summary}")
        return "\n".join(lines).rstrip()

    def format_executor_goal(self, original_goal: str) -> str:
        return (
            "The user approved the following execution plan. "
            "Execute the original task by following this plan, while still using tools for real workspace information.\n\n"
            f"Original task:\n{original_goal}\n\n"
            f"Approved plan:\n{self.format_text()}"
        )

    def with_step_status(self, status: str, *, result_summary: str | None = None) -> "PlanPreview":
        return PlanPreview(
            summary=self.summary,
            raw_content=self.raw_content,
            steps=[
                PlanStep(
                    id=step.id,
                    title=step.title,
                    description=step.description,
                    suggested_tools=step.suggested_tools,
                    risk=step.risk,
                    status=status,
                    result_summary=result_summary,
                )
                for step in self.steps
            ],
        )

    def with_updated_step(
        self,
        step_id: str,
        *,
        status: str,
        result_summary: str | None = None,
    ) -> "PlanPreview":
        updated_steps: list[PlanStep] = []
        found = False
        for step in self.steps:
            if step.id == step_id:
                found = True
                updated_steps.append(
                    PlanStep(
                        id=step.id,
                        title=step.title,
                        description=step.description,
                        suggested_tools=step.suggested_tools,
                        risk=step.risk,
                        status=status,
                        result_summary=result_summary,
                    )
                )
            else:
                updated_steps.append(step)
        if not found:
            raise ValueError(f"Step not found: {step_id}")
        return PlanPreview(summary=self.summary, raw_content=self.raw_content, steps=updated_steps)

    def with_retry_from_step(self, step_id: str) -> "PlanPreview":
        found = False
        updated_steps: list[PlanStep] = []
        for step in self.steps:
            if step.id == step_id:
                found = True
            if found:
                updated_steps.append(
                    PlanStep(
                        id=step.id,
                        title=step.title,
                        description=step.description,
                        suggested_tools=step.suggested_tools,
                        risk=step.risk,
                        status="pending",
                        result_summary=None,
                    )
                )
            else:
                updated_steps.append(step)
        if not found:
            raise ValueError(f"Step not found: {step_id}")
        return PlanPreview(summary=self.summary, raw_content=self.raw_content, steps=updated_steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "raw_content": self.raw_content,
            "steps": [asdict(step) for step in self.steps],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanPreview":
        steps = [
            PlanStep(
                id=str(item.get("id") or ""),
                title=str(item.get("title") or ""),
                description=str(item.get("description") or ""),
                suggested_tools=[str(tool) for tool in item.get("suggested_tools") or []],
                risk=str(item.get("risk") or "READ"),
                status=str(item.get("status") or "pending"),
                result_summary=item.get("result_summary"),
            )
            for item in payload.get("steps") or []
            if isinstance(item, dict)
        ]
        return cls(
            summary=str(payload.get("summary") or "Planned coding task."),
            raw_content=payload.get("raw_content"),
            steps=steps,
        )


@dataclass(frozen=True)
class AgentHandoff:
    role: str
    summary: str
    status: str
    detail: str | None = None
    step_id: str | None = None
    next_action: str | None = None

    def format_text(self) -> str:
        prefix = f"- {self.role}: {self.summary} [{self.status}]"
        suffixes: list[str] = []
        if self.step_id:
            suffixes.append(f"step={self.step_id}")
        if self.next_action:
            suffixes.append(f"next={self.next_action}")
        if suffixes:
            prefix = f"{prefix} ({'; '.join(suffixes)})"
        if self.detail:
            return f"{prefix}\n  {self.detail}"
        return prefix

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "summary": self.summary,
            "status": self.status,
            "detail": self.detail,
            "step_id": self.step_id,
            "next_action": self.next_action,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentHandoff":
        return cls(
            role=str(payload.get("role") or "unknown"),
            summary=str(payload.get("summary") or ""),
            status=str(payload.get("status") or "unknown"),
            detail=payload.get("detail"),
            step_id=payload.get("step_id"),
            next_action=payload.get("next_action"),
        )


class PlanRunStatus(StrEnum):
    PLANNED = "planned"
    APPROVED = "approved"
    CANCELLED = "cancelled"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class PlanRun:
    plan_id: str | None
    plan: PlanPreview
    status: PlanRunStatus
    goal: str | None = None
    execution_result: str | None = None
    review_result: str | None = None
    handoffs: list[AgentHandoff] = field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None

    def format_text(self) -> str:
        lines = [f"PlanRun status: {self.status}"]
        if self.plan_id:
            lines.append(f"Plan id: {self.plan_id}")
        if self.goal:
            lines.append(f"Goal: {self.goal}")
        lines.extend(["", self.plan.format_text()])
        if self.execution_result is not None:
            lines.extend(["", "Execution result:", self.execution_result])
        if self.review_result is not None:
            lines.extend(["", "Review result:", self.review_result])
        if self.handoffs:
            lines.extend(["", "Agent handoffs:"])
            lines.extend(handoff.format_text() for handoff in self.handoffs)
        return "\n".join(lines).rstrip()

    def with_handoff(self, handoff: AgentHandoff) -> "PlanRun":
        return PlanRun(
            plan_id=self.plan_id,
            goal=self.goal,
            status=self.status,
            plan=self.plan,
            execution_result=self.execution_result,
            review_result=self.review_result,
            handoffs=[*self.handoffs, handoff],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "status": str(self.status),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "execution_result": self.execution_result,
            "review_result": self.review_result,
            "handoffs": [handoff.to_dict() for handoff in self.handoffs],
            "plan": self.plan.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanRun":
        return cls(
            plan_id=payload.get("plan_id"),
            goal=payload.get("goal"),
            status=PlanRunStatus(str(payload.get("status") or PlanRunStatus.PLANNED)),
            created_at=payload.get("created_at"),
            updated_at=payload.get("updated_at"),
            execution_result=payload.get("execution_result"),
            review_result=payload.get("review_result"),
            handoffs=[
                AgentHandoff.from_dict(item)
                for item in payload.get("handoffs") or []
                if isinstance(item, dict)
            ],
            plan=PlanPreview.from_dict(payload.get("plan") or {}),
        )


class Planner:
    def __init__(self, llm: LLMClient, *, system_prompt: str = PLANNER_PROMPT) -> None:
        self.llm = llm
        self.system_prompt = system_prompt

    def preview(self, goal: str) -> PlanPreview:
        response = self.llm.chat(
            [Message.system(self.system_prompt), Message.user(goal)],
            tools=[],
        )
        content = response.content or ""
        parsed = _parse_plan_json(content)
        if parsed is not None:
            return parsed
        return _fallback_plan(goal, raw_content=content)


def _parse_plan_json(content: str) -> PlanPreview | None:
    cleaned = _strip_json_fence(content.strip())
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list):
        return None

    steps: list[PlanStep] = []
    for index, item in enumerate(raw_steps, start=1):
        if not isinstance(item, dict):
            continue
        suggested_tools = item.get("suggested_tools") or []
        if not isinstance(suggested_tools, list):
            suggested_tools = []
        steps.append(
            PlanStep(
                id=str(item.get("id") or f"S{index}"),
                title=str(item.get("title") or f"Step {index}"),
                description=str(item.get("description") or ""),
                suggested_tools=[str(tool) for tool in suggested_tools],
                risk=str(item.get("risk") or "READ"),
                status=str(item.get("status") or "pending"),
                result_summary=item.get("result_summary"),
            )
        )

    if not steps:
        return None
    return PlanPreview(
        summary=str(payload.get("summary") or "Planned coding task."),
        steps=steps,
        raw_content=content,
    )


def _strip_json_fence(content: str) -> str:
    if content.startswith("```json"):
        content = content.removeprefix("```json").strip()
    elif content.startswith("```"):
        content = content.removeprefix("```").strip()
    if content.endswith("```"):
        content = content.removesuffix("```").strip()
    return content


def _fallback_plan(goal: str, *, raw_content: str | None = None) -> PlanPreview:
    return PlanPreview(
        summary=f"Plan for: {goal}",
        steps=[
            PlanStep(
                id="S1",
                title="Inspect workspace",
                description="List files and read the most relevant files before making changes.",
                suggested_tools=["list_files", "read_file"],
                risk="READ",
            ),
            PlanStep(
                id="S2",
                title="Apply minimal change",
                description="Use edit_file for localized edits or write_file only for new files.",
                suggested_tools=["edit_file", "write_file"],
                risk="WRITE",
            ),
            PlanStep(
                id="S3",
                title="Verify result",
                description="Run a focused command or test if the user approves shell execution.",
                suggested_tools=["run_shell"],
                risk="EXECUTE",
            ),
        ],
        raw_content=raw_content,
    )
