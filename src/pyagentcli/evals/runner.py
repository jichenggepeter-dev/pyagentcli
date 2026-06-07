from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Callable

from pyagentcli.context_injection import inject_context_references
from pyagentcli.evals.cases import (
    BUILTIN_CASES,
    BUILTIN_CODING_TASKS,
    BUILTIN_RAG_RETRIEVAL_CASES,
    BUILTIN_TRACE_EVAL_CASES,
    CodingTaskCase,
    EvalCase,
    RagRetrievalCase,
    TraceEvalCase,
    workspace_for_case,
)
from pyagentcli.evals.metrics import CodingTaskSummary, EvalSummary, RagRetrievalSummary, TraceEvalSummary
from pyagentcli.memory.project_memory import ProjectMemory
from pyagentcli.rag.indexer import CodeIndexer
from pyagentcli.safety.approval import ApprovalResult
from pyagentcli.safety.audit_log import AuditLogger
from pyagentcli.safety.policy import SafetyDecision, SafetyPolicy
from pyagentcli.tools.base import RiskLevel, ToolContext
from pyagentcli.tools.registry import default_registry


@dataclass(frozen=True)
class EvalResult:
    case_id: str
    name: str
    passed: bool
    message: str
    duration_ms: int


@dataclass(frozen=True)
class CodingTaskResult:
    case_id: str
    name: str
    succeeded: bool
    message: str
    expected_tools: list[str]
    used_tools: list[str]
    matched_tool_calls: int
    safety_violations: int
    duration_ms: int


@dataclass(frozen=True)
class RagRetrievalResult:
    case_id: str
    name: str
    passed: bool
    message: str
    query_type: str
    query: str
    expected_path: str
    duration_ms: int


@dataclass(frozen=True)
class TraceEvalResult:
    case_id: str
    name: str
    passed: bool
    message: str
    expected_tools: list[str]
    used_tools: list[str]
    matched_tool_calls: int
    safety_violations: int
    final_output: str
    duration_ms: int


class ApproveAll:
    def request(
        self,
        *,
        tool_name: str,
        risk_level: RiskLevel,
        args: dict,
        decision: SafetyDecision,
        preview: str | None = None,
    ) -> ApprovalResult:
        return ApprovalResult(True, "approved by eval")


class EvalRunner:
    def __init__(self, *, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self.report_dir = self.workspace_root / ".pyagent" / "evals"

    def run_builtin(
        self,
    ) -> tuple[
        EvalSummary,
        list[EvalResult],
        Path,
        CodingTaskSummary,
        list[CodingTaskResult],
        RagRetrievalSummary,
        list[RagRetrievalResult],
        TraceEvalSummary,
        list[TraceEvalResult],
    ]:
        with TemporaryDirectory() as tmp:
            eval_root = Path(tmp)
            results = [self._run_case(case, eval_root) for case in BUILTIN_CASES]
            coding_results = [self._run_coding_task(case, eval_root) for case in BUILTIN_CODING_TASKS]
            rag_results = [self._run_rag_retrieval(case, eval_root) for case in BUILTIN_RAG_RETRIEVAL_CASES]
            trace_results = [self._run_trace_eval(case) for case in BUILTIN_TRACE_EVAL_CASES]

        summary = EvalSummary(
            total=len(results),
            passed=sum(1 for result in results if result.passed),
            failed=sum(1 for result in results if not result.passed),
        )
        coding_summary = CodingTaskSummary(
            total=len(coding_results),
            succeeded=sum(1 for result in coding_results if result.succeeded),
            failed=sum(1 for result in coding_results if not result.succeeded),
            expected_tool_calls=sum(len(result.expected_tools) for result in coding_results),
            matched_tool_calls=sum(result.matched_tool_calls for result in coding_results),
            safety_violations=sum(result.safety_violations for result in coding_results),
        )
        rag_summary = RagRetrievalSummary(
            total=len(rag_results),
            passed=sum(1 for result in rag_results if result.passed),
            failed=sum(1 for result in rag_results if not result.passed),
        )
        trace_summary = TraceEvalSummary(
            total=len(trace_results),
            passed=sum(1 for result in trace_results if result.passed),
            failed=sum(1 for result in trace_results if not result.passed),
            expected_tool_calls=sum(len(result.expected_tools) for result in trace_results),
            matched_tool_calls=sum(result.matched_tool_calls for result in trace_results),
            safety_violations=sum(result.safety_violations for result in trace_results),
        )
        report_path = self._write_report(results, coding_results, rag_results, trace_results)
        return summary, results, report_path, coding_summary, coding_results, rag_summary, rag_results, trace_summary, trace_results

    def _run_case(self, case: EvalCase, eval_root: Path) -> EvalResult:
        started = perf_counter()
        workspace = workspace_for_case(eval_root, case)
        workspace.mkdir(parents=True, exist_ok=True)
        try:
            _CASE_RUNNERS[case.case_id](workspace)
        except Exception as exc:  # noqa: BLE001 - eval failures should be reported, not raised.
            return EvalResult(
                case_id=case.case_id,
                name=case.name,
                passed=False,
                message=f"{type(exc).__name__}: {exc}",
                duration_ms=int((perf_counter() - started) * 1000),
            )
        return EvalResult(
            case_id=case.case_id,
            name=case.name,
            passed=True,
            message="passed",
            duration_ms=int((perf_counter() - started) * 1000),
        )

    def _run_coding_task(self, case: CodingTaskCase, eval_root: Path) -> CodingTaskResult:
        started = perf_counter()
        workspace = workspace_for_case(eval_root, EvalCase(case.case_id, case.name, case.goal))
        workspace.mkdir(parents=True, exist_ok=True)
        for relative_path, content in case.initial_files.items():
            target = workspace / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        used_tools: list[str] = []
        safety_violations = 0
        registry = default_registry()
        context = ToolContext(
            workspace_root=workspace,
            safety_policy=SafetyPolicy(workspace),
            approval_handler=ApproveAll(),
            audit_logger=AuditLogger(workspace),
            goal=case.goal,
            step=1,
        )

        for call in case.simulated_tool_calls:
            tool_name = str(call.get("name") or "")
            used_tools.append(tool_name)
            if tool_name in case.forbidden_tools:
                safety_violations += 1
            result = registry.execute(tool_name, dict(call.get("arguments") or {}), context)
            expected_ok = bool(call.get("ok", True))
            if result.ok != expected_ok:
                return CodingTaskResult(
                    case_id=case.case_id,
                    name=case.name,
                    succeeded=False,
                    message=f"Tool {tool_name} ok={result.ok}, expected {expected_ok}: {result.error}",
                    expected_tools=list(case.expected_tools),
                    used_tools=used_tools,
                    matched_tool_calls=_count_matched_tools(case.expected_tools, used_tools),
                    safety_violations=safety_violations,
                    duration_ms=int((perf_counter() - started) * 1000),
                )

        failures: list[str] = []
        for expected_file in case.expected_files:
            target = workspace / expected_file.path
            if not target.exists():
                failures.append(f"Missing expected file: {expected_file.path}")
                continue
            content = target.read_text(encoding="utf-8")
            if expected_file.contains not in content:
                failures.append(f"{expected_file.path} does not contain expected text.")

        matched_tool_calls = _count_matched_tools(case.expected_tools, used_tools)
        if matched_tool_calls < len(case.expected_tools):
            failures.append("Expected tool sequence was not fully observed.")
        if safety_violations:
            failures.append(f"Observed forbidden tools: {safety_violations}")

        succeeded = not failures
        return CodingTaskResult(
            case_id=case.case_id,
            name=case.name,
            succeeded=succeeded,
            message="passed" if succeeded else "; ".join(failures),
            expected_tools=list(case.expected_tools),
            used_tools=used_tools,
            matched_tool_calls=matched_tool_calls,
            safety_violations=safety_violations,
            duration_ms=int((perf_counter() - started) * 1000),
        )

    def _run_rag_retrieval(self, case: RagRetrievalCase, eval_root: Path) -> RagRetrievalResult:
        started = perf_counter()
        workspace = workspace_for_case(eval_root, EvalCase(case.case_id, case.name, case.query))
        workspace.mkdir(parents=True, exist_ok=True)
        for relative_path, content in case.initial_files.items():
            target = workspace / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        try:
            CodeIndexer(workspace).rebuild()
            if case.query_type == "symbol":
                result = CodeIndexer(workspace).search_symbol(case.query)
                passed = bool(result.hits) and result.hits[0].path == case.expected_path
                if case.expected_symbol is not None:
                    passed = passed and result.hits[0].symbol_name == case.expected_symbol
                message = "passed" if passed else f"Unexpected symbol hits: {result.format_text()}"
            elif case.query_type == "context":
                result = inject_context_references(case.query, workspace)
                passed = case.expected_text is not None and case.expected_text in result.enriched_goal
                message = "passed" if passed else "Expected dependency context was not injected."
            else:
                passed = False
                message = f"Unknown RAG query type: {case.query_type}"
        except Exception as exc:  # noqa: BLE001 - eval failures should be reported.
            passed = False
            message = f"{type(exc).__name__}: {exc}"

        return RagRetrievalResult(
            case_id=case.case_id,
            name=case.name,
            passed=passed,
            message=message,
            query_type=case.query_type,
            query=case.query,
            expected_path=case.expected_path,
            duration_ms=int((perf_counter() - started) * 1000),
        )

    def _run_trace_eval(self, case: TraceEvalCase) -> TraceEvalResult:
        started = perf_counter()
        used_tools: list[str] = []
        safety_violations = 0
        final_output = ""
        failures: list[str] = []

        for event in case.trace:
            tool_call = event.get("tool_call") if isinstance(event.get("tool_call"), dict) else None
            if tool_call is not None:
                tool_name = str(tool_call.get("name") or "")
                if tool_name:
                    used_tools.append(tool_name)
                    if tool_name in case.forbidden_tools:
                        safety_violations += 1
            if "final" in event:
                final_output = str(event.get("final") or "")

        matched_tool_calls = _count_matched_tools(case.expected_tools, used_tools)
        if matched_tool_calls < len(case.expected_tools):
            failures.append("Expected trace tool sequence was not fully observed.")
        if safety_violations:
            failures.append(f"Observed forbidden tools: {safety_violations}")
        if case.expected_final_contains and case.expected_final_contains not in final_output:
            failures.append("Final output did not contain expected text.")

        passed = not failures
        return TraceEvalResult(
            case_id=case.case_id,
            name=case.name,
            passed=passed,
            message="passed" if passed else "; ".join(failures),
            expected_tools=list(case.expected_tools),
            used_tools=used_tools,
            matched_tool_calls=matched_tool_calls,
            safety_violations=safety_violations,
            final_output=final_output,
            duration_ms=int((perf_counter() - started) * 1000),
        )

    def _write_report(
        self,
        results: list[EvalResult],
        coding_results: list[CodingTaskResult],
        rag_results: list[RagRetrievalResult],
        trace_results: list[TraceEvalResult],
    ) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.report_dir / f"eval_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.jsonl"
        with report_path.open("w", encoding="utf-8") as handle:
            for result in results:
                payload = {"kind": "platform", **asdict(result)}
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            for result in coding_results:
                payload = {"kind": "coding_task", **asdict(result)}
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            for result in rag_results:
                payload = {"kind": "rag_retrieval", **asdict(result)}
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            for result in trace_results:
                payload = {"kind": "trace_eval", **asdict(result)}
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return report_path


def _case_tools_registry(workspace: Path) -> None:
    tool_names = {schema["function"]["name"] for schema in default_registry().schemas()}
    expected = {"list_files", "read_file", "write_file", "edit_file", "run_shell", "search_text", "search_index"}
    missing = expected - tool_names
    if missing:
        raise AssertionError(f"Missing tools: {sorted(missing)}")


def _case_safety_dangerous_shell_denied(workspace: Path) -> None:
    registry = default_registry()
    context = ToolContext(
        workspace_root=workspace,
        safety_policy=SafetyPolicy(workspace),
        approval_handler=ApproveAll(),
        audit_logger=AuditLogger(workspace),
        goal="eval dangerous shell",
        step=1,
    )
    result = registry.execute("run_shell", {"command": "rm -rf ."}, context)
    if result.ok:
        raise AssertionError("Dangerous shell command unexpectedly succeeded.")


def _case_rag_symbol_search(workspace: Path) -> None:
    (workspace / "src").mkdir()
    (workspace / "src" / "app.py").write_text(
        "def project_status():\n    return 'READY'\n",
        encoding="utf-8",
    )
    indexer = CodeIndexer(workspace)
    indexer.rebuild()
    result = indexer.search_symbol("project_status")
    if not result.hits:
        raise AssertionError("Expected project_status symbol hit.")
    hit = result.hits[0]
    if hit.symbol_name != "project_status" or hit.kind != "function":
        raise AssertionError(f"Unexpected symbol hit: {hit}")


def _case_memory_project_note(workspace: Path) -> None:
    memory = ProjectMemory(workspace)
    memory.remember("Prefer focused edits.")
    if "Prefer focused edits." not in memory.read_project_memory():
        raise AssertionError("Memory note was not persisted.")


_CASE_RUNNERS: dict[str, Callable[[Path], None]] = {
    "tools.registry": _case_tools_registry,
    "safety.dangerous_shell_denied": _case_safety_dangerous_shell_denied,
    "rag.symbol_search": _case_rag_symbol_search,
    "memory.project_note": _case_memory_project_note,
}


def _count_matched_tools(expected: tuple[str, ...], used: list[str]) -> int:
    position = 0
    for tool_name in used:
        if position < len(expected) and tool_name == expected[position]:
            position += 1
    return position
