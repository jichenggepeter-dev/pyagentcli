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
class CodingTaskCase:
    case_id: str
    name: str
    goal: str
    initial_files: dict[str, str]
    expected_files: tuple[ExpectedFile, ...]
    expected_tools: tuple[str, ...]
    forbidden_tools: tuple[str, ...] = ()
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
class TraceEvalCase:
    case_id: str
    name: str
    goal: str
    trace: tuple[dict[str, Any], ...]
    expected_tools: tuple[str, ...]
    forbidden_tools: tuple[str, ...] = ()
    expected_final_contains: str | None = None


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


BUILTIN_AGENT_TRACE_CASES = [
    CodingTaskCase(
        case_id="agent_trace.list_workspace",
        name="Agent loop captures list_files trace",
        goal="Summarize this project workspace.",
        initial_files={"README.md": "# Demo\n"},
        expected_files=(),
        expected_tools=("list_files",),
        forbidden_tools=("run_shell",),
    )
]


def workspace_for_case(root: Path, case: EvalCase) -> Path:
    safe_id = case.case_id.replace("/", "_").replace(".", "_")
    return root / safe_id
