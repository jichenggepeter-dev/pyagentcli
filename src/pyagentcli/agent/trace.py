from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TraceEvent:
    role: str
    content: str | None = None
    tool_call: dict[str, Any] | None = None
    tool_name: str | None = None
    ok: bool | None = None
    observation: str | None = None
    final: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            payload["content"] = self.content
        if self.tool_call is not None:
            payload["tool_call"] = self.tool_call
        if self.tool_name is not None:
            payload["tool_name"] = self.tool_name
        if self.ok is not None:
            payload["ok"] = self.ok
        if self.observation is not None:
            payload["observation"] = self.observation
        if self.final is not None:
            payload["final"] = self.final
        return payload


@dataclass(frozen=True)
class AgentTrace:
    goal: str
    events: list[TraceEvent] = field(default_factory=list)

    def to_eval_trace(self) -> tuple[dict[str, Any], ...]:
        return tuple(event.to_dict() for event in self.events)


@dataclass(frozen=True)
class AgentRunResult:
    output: str
    trace: AgentTrace
