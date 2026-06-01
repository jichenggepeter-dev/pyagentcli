from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from pyagentcli.tools.base import RiskLevel, ToolResult


@dataclass
class AuditEvent:
    timestamp: str
    goal: str
    step: int
    tool_name: str
    tool_args: dict[str, Any]
    risk_level: str
    decision: str
    ok: bool
    error: str | None
    duration_ms: int


class AuditLogger:
    def __init__(self, workspace_root: Path) -> None:
        self.log_dir = workspace_root / ".pyagent"
        self.log_path = self.log_dir / "audit.log.jsonl"

    def record(
        self,
        *,
        goal: str,
        step: int,
        tool_name: str,
        tool_args: dict[str, Any],
        risk_level: RiskLevel,
        decision: str,
        result: ToolResult,
        started_at: float,
    ) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        event = AuditEvent(
            timestamp=datetime.now(UTC).isoformat(),
            goal=goal,
            step=step,
            tool_name=tool_name,
            tool_args=self._redact_args(tool_args),
            risk_level=str(risk_level),
            decision=decision,
            ok=result.ok,
            error=result.error,
            duration_ms=int((perf_counter() - started_at) * 1000),
        )
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    @staticmethod
    def _redact_args(args: dict[str, Any]) -> dict[str, Any]:
        redacted: dict[str, Any] = {}
        for key, value in args.items():
            if key in {"content", "api_key", "password", "token"} and isinstance(value, str):
                redacted[key] = f"<redacted:{len(value)} chars>"
            else:
                redacted[key] = value
        return redacted

