from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pyagentcli.llm.base import Message


@dataclass
class AgentState:
    user_goal: str
    workspace_root: Path
    max_steps: int
    messages: list[Message] = field(default_factory=list)
    step_count: int = 0

