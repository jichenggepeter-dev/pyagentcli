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


@dataclass(frozen=True)
class CodingTaskSummary:
    total: int
    succeeded: int
    failed: int
    expected_tool_calls: int
    matched_tool_calls: int
    safety_violations: int

    @property
    def task_success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.succeeded / self.total

    @property
    def tool_call_accuracy(self) -> float:
        if self.expected_tool_calls == 0:
            return 1.0
        return self.matched_tool_calls / self.expected_tool_calls

    def format_text(self) -> str:
        return (
            "Coding task eval: "
            f"{self.succeeded}/{self.total} succeeded "
            f"({self.task_success_rate:.0%}); "
            f"tool-call accuracy {self.tool_call_accuracy:.0%}; "
            f"safety violations {self.safety_violations}."
        )


@dataclass(frozen=True)
class RagRetrievalSummary:
    total: int
    passed: int
    failed: int

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    def format_text(self) -> str:
        return f"RAG retrieval eval: {self.passed}/{self.total} passed ({self.pass_rate:.0%}); {self.failed} failed."


@dataclass(frozen=True)
class TraceEvalSummary:
    total: int
    passed: int
    failed: int
    expected_tool_calls: int
    matched_tool_calls: int
    safety_violations: int

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    @property
    def tool_call_accuracy(self) -> float:
        if self.expected_tool_calls == 0:
            return 1.0
        return self.matched_tool_calls / self.expected_tool_calls

    def format_text(self) -> str:
        return (
            "Trace eval: "
            f"{self.passed}/{self.total} passed "
            f"({self.pass_rate:.0%}); "
            f"tool-call accuracy {self.tool_call_accuracy:.0%}; "
            f"safety violations {self.safety_violations}."
        )
