from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pyagentcli.tools.base import RiskLevel


class SafetyAction(StrEnum):
    ALLOW = "ALLOW"
    ASK = "ASK"
    DENY = "DENY"


@dataclass(frozen=True)
class SafetyDecision:
    action: SafetyAction
    reason: str


class SafetyPolicy:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self.path_denylist = {".git", ".env", ".venv", "node_modules", "__pycache__"}
        self.command_deny_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in [
                r"\brm\s+-rf\b",
                r"\bsudo\b",
                r"\bchmod\s+-R\b",
                r"\bchown\s+-R\b",
                r"\bmkfs\b",
                r"\bdd\s+if=",
                r":\s*\(\)\s*\{",
                r"\bcurl\b.*\|\s*(sh|bash)\b",
                r"\bwget\b.*\|\s*(sh|bash)\b",
            ]
        ]

    def resolve_workspace_path(self, raw_path: str) -> Path:
        candidate = (self.workspace_root / raw_path).expanduser().resolve()
        try:
            candidate.relative_to(self.workspace_root)
        except ValueError as exc:
            raise PermissionError(f"Path escapes workspace: {raw_path}") from exc

        relative_parts = candidate.relative_to(self.workspace_root).parts
        for part in relative_parts:
            if part in self.path_denylist:
                raise PermissionError(f"Path is denied by policy: {raw_path}")
        return candidate

    def evaluate_tool(self, tool_name: str, risk_level: RiskLevel, args: dict) -> SafetyDecision:
        if risk_level == RiskLevel.READ:
            return SafetyDecision(SafetyAction.ALLOW, "Read-only tool.")
        if risk_level == RiskLevel.WRITE:
            return SafetyDecision(SafetyAction.ASK, "Writing files requires approval.")
        if risk_level == RiskLevel.EXECUTE:
            command = str(args.get("command", ""))
            for pattern in self.command_deny_patterns:
                if pattern.search(command):
                    return SafetyDecision(SafetyAction.DENY, f"Command denied by policy: {pattern.pattern}")
            return SafetyDecision(SafetyAction.ASK, "Shell execution requires approval.")
        if risk_level in {RiskLevel.NETWORK, RiskLevel.CRITICAL}:
            return SafetyDecision(SafetyAction.DENY, f"{risk_level} tools are disabled in v0.1.")
        return SafetyDecision(SafetyAction.DENY, f"Unknown risk level for {tool_name}.")

