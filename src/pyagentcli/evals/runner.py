from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Callable

from pyagentcli.evals.cases import BUILTIN_CASES, EvalCase, workspace_for_case
from pyagentcli.evals.metrics import EvalSummary
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

    def run_builtin(self) -> tuple[EvalSummary, list[EvalResult], Path]:
        with TemporaryDirectory() as tmp:
            eval_root = Path(tmp)
            results = [self._run_case(case, eval_root) for case in BUILTIN_CASES]

        summary = EvalSummary(
            total=len(results),
            passed=sum(1 for result in results if result.passed),
            failed=sum(1 for result in results if not result.passed),
        )
        report_path = self._write_report(results)
        return summary, results, report_path

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

    def _write_report(self, results: list[EvalResult]) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.report_dir / f"eval_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.jsonl"
        with report_path.open("w", encoding="utf-8") as handle:
            for result in results:
                handle.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
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
