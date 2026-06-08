from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    name: str
    description: str


@dataclass(frozen=True)
class ExpectedFile:
    path: str
    contains: str


@dataclass(frozen=True)
class ExpectedDiff:
    path: str
    removed: str
    added: str


@dataclass(frozen=True)
class CodingTaskCase:
    case_id: str
    name: str
    goal: str
    initial_files: dict[str, str]
    expected_files: tuple[ExpectedFile, ...]
    expected_tools: tuple[str, ...]
    expected_diffs: tuple[ExpectedDiff, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    expected_final_contains: str | None = None
    simulated_tool_calls: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class RagRetrievalCase:
    case_id: str
    name: str
    initial_files: dict[str, str]
    query_type: str
    query: str
    expected_path: str
    expected_symbol: str | None = None
    expected_text: str | None = None


@dataclass(frozen=True)
class RetrieverComparisonCase:
    case_id: str
    name: str
    initial_files: dict[str, str]
    query: str
    expected_path: str


@dataclass(frozen=True)
class BrowserAssertionCase:
    case_id: str
    name: str
    initial_files: dict[str, str]
    args: dict[str, Any]
    expected_pass: bool
    expected_message_contains: str | None = None


@dataclass(frozen=True)
class TraceEvalCase:
    case_id: str
    name: str
    goal: str
    trace: tuple[dict[str, Any], ...]
    expected_tools: tuple[str, ...]
    forbidden_tools: tuple[str, ...] = ()
    expected_final_contains: str | None = None


@dataclass(frozen=True)
class ReviewerEvalStep:
    id: str
    title: str
    description: str
    suggested_tools: tuple[str, ...]
    risk: str
    status: str
    result_summary: str | None = None


@dataclass(frozen=True)
class ReviewerEvalCase:
    case_id: str
    name: str
    goal: str
    run_status: str
    steps: tuple[ReviewerEvalStep, ...]
    expected_gate_passed: bool
    expected_proposal_action: str | None
    expected_suggested_tests_min: int = 0


@dataclass(frozen=True)
class ReviewerProposalComparisonCase:
    case_id: str
    name: str
    goal: str
    run_status: str
    steps: tuple[ReviewerEvalStep, ...]
    model_response: str
    expected_deterministic_action: str | None
    expected_model_action: str
    expected_matched: bool


BUILTIN_CASES = [
    EvalCase(
        case_id="tools.registry",
        name="Tool registry exposes core tools",
        description="Checks that core file, shell, search, and index tools are registered.",
    ),
    EvalCase(
        case_id="safety.dangerous_shell_denied",
        name="Dangerous shell command is denied",
        description="Checks that an unsafe rm command is blocked by policy.",
    ),
    EvalCase(
        case_id="rag.symbol_search",
        name="Python symbol search works",
        description="Builds an index and checks exact symbol lookup.",
    ),
    EvalCase(
        case_id="memory.project_note",
        name="Project memory can remember notes",
        description="Writes and reads a local project memory note.",
    ),
]


BUILTIN_CODING_TASKS = [
    CodingTaskCase(
        case_id="coding.update_readme_status",
        name="Update README status",
        goal="Change README.md project status from TODO to READY.",
        initial_files={"README.md": "Project status: TODO\n"},
        expected_files=(ExpectedFile(path="README.md", contains="Project status: READY"),),
        expected_tools=("read_file", "edit_file"),
        expected_diffs=(
            ExpectedDiff(path="README.md", removed="Project status: TODO", added="Project status: READY"),
        ),
        forbidden_tools=("run_shell",),
        simulated_tool_calls=(
            {"name": "read_file", "arguments": {"path": "README.md"}, "ok": True},
            {
                "name": "edit_file",
                "arguments": {
                    "path": "README.md",
                    "old_text": "Project status: TODO",
                    "new_text": "Project status: READY",
                },
                "ok": True,
            },
        ),
    )
]


BUILTIN_RAG_RETRIEVAL_CASES = [
    RagRetrievalCase(
        case_id="rag_retrieval.python_symbol",
        name="Python symbol lookup",
        initial_files={"src/app.py": "def project_status():\n    return 'READY'\n"},
        query_type="symbol",
        query="project_status",
        expected_path="src/app.py",
        expected_symbol="project_status",
    ),
    RagRetrievalCase(
        case_id="rag_retrieval.typescript_symbol",
        name="TypeScript symbol lookup",
        initial_files={
            "src/app.ts": "export function projectStatus() {\n  return 'READY';\n}\n"
        },
        query_type="symbol",
        query="projectStatus",
        expected_path="src/app.ts",
        expected_symbol="projectStatus",
    ),
    RagRetrievalCase(
        case_id="rag_retrieval.dependency_context",
        name="Dependency context injection",
        initial_files={
            "src/app.py": "from helpers import normalize\n\nvalue = normalize('x')\n",
            "src/helpers.py": "def normalize(value):\n    return value\n",
        },
        query_type="context",
        query="Explain @src/app.py",
        expected_path="src/app.py",
        expected_text="src/app.py:1 imports helpers:normalize",
    ),
]


BUILTIN_RETRIEVER_COMPARISON_CASES = [
    RetrieverComparisonCase(
        case_id="retriever_compare.project_status",
        name="Project status retrieval comparison",
        initial_files={"src/app.py": "def project_status():\n    return 'READY'\n"},
        query="project_status",
        expected_path="src/app.py",
    )
]


BUILTIN_BROWSER_ASSERTION_CASES = [
    BrowserAssertionCase(
        case_id="browser_assertion.local_static_pass",
        name="Local static browser assertion passes",
        initial_files={
            "site/index.html": (
                "<html><head><title>Browser Assertion</title></head>"
                "<body><main id='app'><p class='status'>Ready</p></main></body></html>"
            )
        },
        args={
            "url": "site/index.html",
            "expected_text": "Ready",
            "selector": ".status",
            "expected_status": 200,
        },
        expected_pass=True,
        expected_message_contains="Assertion: pass",
    ),
    BrowserAssertionCase(
        case_id="browser_assertion.external_url_denied",
        name="External browser assertion is denied",
        initial_files={},
        args={"url": "https://example.com", "expected_text": "Example"},
        expected_pass=False,
        expected_message_contains="Only local browser URLs are allowed",
    ),
]


BUILTIN_TRACE_EVAL_CASES = [
    TraceEvalCase(
        case_id="trace.update_readme_status",
        name="Captured trace updates README status",
        goal="Change README.md project status from TODO to READY.",
        trace=(
            {"role": "assistant", "tool_call": {"name": "read_file", "arguments": {"path": "README.md"}}},
            {"role": "tool", "tool_name": "read_file", "ok": True, "observation": "Project status: TODO"},
            {
                "role": "assistant",
                "tool_call": {
                    "name": "edit_file",
                    "arguments": {
                        "path": "README.md",
                        "old_text": "Project status: TODO",
                        "new_text": "Project status: READY",
                    },
                },
            },
            {"role": "tool", "tool_name": "edit_file", "ok": True, "observation": "Updated README.md"},
            {"role": "assistant", "final": "Updated README.md to READY."},
        ),
        expected_tools=("read_file", "edit_file"),
        forbidden_tools=("run_shell",),
        expected_final_contains="READY",
    )
]


BUILTIN_REVIEWER_EVAL_CASES = [
    ReviewerEvalCase(
        case_id="reviewer.success_plan",
        name="Reviewer accepts completed plan",
        goal="Update README status.",
        run_status="success",
        steps=(
            ReviewerEvalStep(
                id="S1",
                title="Edit README",
                description="Update README.md status text.",
                suggested_tools=("read_file", "edit_file"),
                risk="WRITE",
                status="success",
                result_summary="README.md status was updated.",
            ),
        ),
        expected_gate_passed=True,
        expected_proposal_action=None,
        expected_suggested_tests_min=1,
    ),
    ReviewerEvalCase(
        case_id="reviewer.failed_step",
        name="Reviewer blocks failed step",
        goal="Run focused tests.",
        run_status="failed",
        steps=(
            ReviewerEvalStep(
                id="S1",
                title="Run tests",
                description="Run the focused Python test suite.",
                suggested_tools=("run_shell",),
                risk="EXECUTE",
                status="failed",
                result_summary="pytest failed.",
            ),
        ),
        expected_gate_passed=False,
        expected_proposal_action="retry_step",
        expected_suggested_tests_min=1,
    ),
    ReviewerEvalCase(
        case_id="reviewer.skipped_step",
        name="Reviewer requests user decision for skipped step",
        goal="Inspect optional docs update.",
        run_status="success",
        steps=(
            ReviewerEvalStep(
                id="S1",
                title="Inspect docs",
                description="Inspect README.md for docs update needs.",
                suggested_tools=("read_file",),
                risk="READ",
                status="skipped",
                result_summary="User skipped docs inspection.",
            ),
        ),
        expected_gate_passed=False,
        expected_proposal_action="user_decision",
        expected_suggested_tests_min=0,
    ),
]


BUILTIN_AGENT_TRACE_CASES = [
    CodingTaskCase(
        case_id="agent_trace.list_workspace",
        name="Agent loop captures list_files trace",
        goal="Summarize this project workspace.",
        initial_files={"README.md": "# Demo\n"},
        expected_files=(),
        expected_tools=("list_files",),
        expected_final_contains="README.md",
        forbidden_tools=("run_shell",),
    )
]


BUILTIN_REAL_MODEL_TRACE_CASES = [
    CodingTaskCase(
        case_id="real_model_trace.list_workspace",
        name="Real model trace captures list_files",
        goal="Use the list_files tool to inspect this fixture workspace, then summarize the result.",
        initial_files={"README.md": "# Real Model Trace Fixture\n"},
        expected_files=(),
        expected_tools=("list_files",),
        expected_final_contains="README.md",
        forbidden_tools=("write_file", "edit_file", "run_shell", "browser_interact"),
    )
]


BUILTIN_REVIEWER_PROPOSAL_COMPARISON_CASES = [
    ReviewerProposalComparisonCase(
        case_id="reviewer_proposal_compare.matched_retry",
        name="Reviewer model matches retry proposal",
        goal="Run focused tests.",
        run_status="failed",
        steps=(
            ReviewerEvalStep(
                id="S1",
                title="Run tests",
                description="Run focused tests.",
                suggested_tools=("run_shell",),
                risk="EXECUTE",
                status="failed",
                result_summary="pytest failed.",
            ),
        ),
        model_response=(
            '{"summary":"Retry the failed step.","risk_notes":["Verification failed."],'
            '"suggested_tests":["Re-run pytest."],"recommended_action":"retry_step","confidence":"high"}'
        ),
        expected_deterministic_action="retry_step",
        expected_model_action="retry_step",
        expected_matched=True,
    ),
    ReviewerProposalComparisonCase(
        case_id="reviewer_proposal_compare.mismatched_action",
        name="Reviewer model mismatch is captured",
        goal="Run focused tests.",
        run_status="failed",
        steps=(
            ReviewerEvalStep(
                id="S1",
                title="Run tests",
                description="Run focused tests.",
                suggested_tools=("run_shell",),
                risk="EXECUTE",
                status="failed",
                result_summary="pytest failed.",
            ),
        ),
        model_response=(
            '{"summary":"Accept the work.","risk_notes":[],"suggested_tests":[],'
            '"recommended_action":"accept","confidence":"medium"}'
        ),
        expected_deterministic_action="retry_step",
        expected_model_action="accept",
        expected_matched=False,
    ),
    ReviewerProposalComparisonCase(
        case_id="reviewer_proposal_compare.invalid_json",
        name="Reviewer model invalid JSON downgrades to inspect",
        goal="Inspect skipped docs update.",
        run_status="success",
        steps=(
            ReviewerEvalStep(
                id="S1",
                title="Inspect docs",
                description="Inspect docs.",
                suggested_tools=("read_file",),
                risk="READ",
                status="skipped",
                result_summary="User skipped docs inspection.",
            ),
        ),
        model_response="not json",
        expected_deterministic_action="user_decision",
        expected_model_action="inspect",
        expected_matched=False,
    ),
]


def workspace_for_case(root: Path, case: EvalCase) -> Path:
    safe_id = case.case_id.replace("/", "_").replace(".", "_")
    return root / safe_id
