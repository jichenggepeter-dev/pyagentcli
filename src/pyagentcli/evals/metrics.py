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
    expected_diffs: int
    matched_diffs: int
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

    @property
    def diff_accuracy(self) -> float:
        if self.expected_diffs == 0:
            return 1.0
        return self.matched_diffs / self.expected_diffs

    def format_text(self) -> str:
        return (
            "Coding task eval: "
            f"{self.succeeded}/{self.total} succeeded "
            f"({self.task_success_rate:.0%}); "
            f"tool-call accuracy {self.tool_call_accuracy:.0%}; "
            f"diff accuracy {self.diff_accuracy:.0%}; "
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
class RetrieverComparisonSummary:
    total: int
    enabled: int
    disabled: int
    passed: int
    failed: int

    @property
    def pass_rate(self) -> float:
        if self.enabled == 0:
            return 0.0
        return self.passed / self.enabled

    def format_text(self) -> str:
        return (
            "Retriever comparison eval: "
            f"{self.passed}/{self.enabled} enabled comparisons passed "
            f"({self.pass_rate:.0%}); "
            f"{self.failed} failed; {self.disabled} disabled."
        )


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


@dataclass(frozen=True)
class RealModelTraceSummary:
    total: int
    passed: int
    failed: int
    expected_tool_calls: int
    matched_tool_calls: int
    safety_violations: int
    enabled: bool
    disabled_reason: str | None = None

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
        if not self.enabled:
            reason = self.disabled_reason or "not enabled"
            return f"Real model trace eval: disabled ({reason})."
        return (
            "Real model trace eval: "
            f"{self.passed}/{self.total} passed "
            f"({self.pass_rate:.0%}); "
            f"tool-call accuracy {self.tool_call_accuracy:.0%}; "
            f"safety violations {self.safety_violations}."
        )


@dataclass(frozen=True)
class ModelTraceComparisonSummary:
    total: int
    passed: int
    failed: int
    model_count: int
    expected_tool_calls: int
    matched_tool_calls: int
    safety_violations: int
    enabled: bool
    disabled_reason: str | None = None

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
        if not self.enabled:
            reason = self.disabled_reason or "not enabled"
            return f"Per-model trace comparison eval: disabled ({reason})."
        return (
            "Per-model trace comparison eval: "
            f"{self.passed}/{self.total} passed "
            f"({self.pass_rate:.0%}); "
            f"models {self.model_count}; "
            f"tool-call accuracy {self.tool_call_accuracy:.0%}; "
            f"safety violations {self.safety_violations}."
        )


@dataclass(frozen=True)
class ReviewerEvalSummary:
    total: int
    passed: int
    failed: int
    gate_matches: int
    proposal_matches: int
    suggested_tests_matches: int

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    def format_text(self) -> str:
        return (
            "Reviewer eval: "
            f"{self.passed}/{self.total} passed "
            f"({self.pass_rate:.0%}); "
            f"gate matches {self.gate_matches}/{self.total}; "
            f"proposal matches {self.proposal_matches}/{self.total}; "
            f"suggested-tests matches {self.suggested_tests_matches}/{self.total}."
        )


@dataclass(frozen=True)
class ReviewerProposalComparisonSummary:
    total: int
    passed: int
    failed: int
    matched: int
    mismatched: int

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    @property
    def match_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.matched / self.total

    def format_text(self) -> str:
        return (
            "Reviewer proposal comparison eval: "
            f"{self.passed}/{self.total} passed "
            f"({self.pass_rate:.0%}); "
            f"model-action match rate {self.match_rate:.0%}; "
            f"mismatches {self.mismatched}."
        )
