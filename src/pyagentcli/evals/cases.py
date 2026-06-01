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


def workspace_for_case(root: Path, case: EvalCase) -> Path:
    safe_id = case.case_id.replace("/", "_").replace(".", "_")
    return root / safe_id
