from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol


class RiskLevel(StrEnum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    NETWORK = "NETWORK"
    CRITICAL = "CRITICAL"


@dataclass
class ToolResult:
    ok: bool
    content: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, content: str, **metadata: Any) -> "ToolResult":
        return cls(ok=True, content=content, metadata=metadata)

    @classmethod
    def failure(cls, error: str, **metadata: Any) -> "ToolResult":
        return cls(ok=False, content="", error=error, metadata=metadata)

    def to_message_content(self) -> str:
        if self.ok:
            return self.content
        return f"Tool failed: {self.error}"


@dataclass
class ToolContext:
    workspace_root: Path
    safety_policy: Any
    approval_handler: Any
    audit_logger: Any
    goal: str
    step: int


class Tool(Protocol):
    name: str
    description: str
    risk_level: RiskLevel

    def schema(self) -> dict[str, Any]:
        ...

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        ...

    def preview(self, args: dict[str, Any], context: ToolContext) -> str | None:
        ...


def function_schema(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }
