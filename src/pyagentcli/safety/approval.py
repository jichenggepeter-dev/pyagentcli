from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from pyagentcli.safety.policy import SafetyAction, SafetyDecision
from pyagentcli.tools.base import RiskLevel


@dataclass(frozen=True)
class ApprovalResult:
    approved: bool
    reason: str


class ApprovalHandler:
    def __init__(self, *, interactive: bool = True) -> None:
        self.interactive = interactive

    def request(
        self,
        *,
        tool_name: str,
        risk_level: RiskLevel,
        args: dict[str, Any],
        decision: SafetyDecision,
        preview: str | None = None,
    ) -> ApprovalResult:
        if decision.action == SafetyAction.ALLOW:
            return ApprovalResult(True, decision.reason)
        if decision.action == SafetyAction.DENY:
            return ApprovalResult(False, decision.reason)
        if not self.interactive:
            return ApprovalResult(False, "Approval required but session is non-interactive.")

        print("\nTool approval required", file=sys.stderr)
        print(f"Tool: {tool_name}", file=sys.stderr)
        print(f"Risk: {risk_level}", file=sys.stderr)
        print(f"Reason: {decision.reason}", file=sys.stderr)
        print(f"Args: {self._summarize_args(args)}", file=sys.stderr)
        if preview:
            print("\nPreview:", file=sys.stderr)
            print(preview, file=sys.stderr)
        answer = input("Approve? [y/N] ").strip().lower()
        if answer in {"y", "yes"}:
            return ApprovalResult(True, "Approved by user.")
        return ApprovalResult(False, "Denied by user.")

    @staticmethod
    def _summarize_args(args: dict[str, Any]) -> dict[str, Any]:
        summarized: dict[str, Any] = {}
        for key, value in args.items():
            if key == "content" and isinstance(value, str):
                summarized[key] = f"<{len(value)} chars>"
            else:
                summarized[key] = value
        return summarized
