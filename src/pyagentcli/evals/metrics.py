from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalSummary:
    total: int
    passed: int
    failed: int

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    def format_text(self) -> str:
        return (
            f"Eval summary: {self.passed}/{self.total} passed "
            f"({self.pass_rate:.0%}); {self.failed} failed."
        )
