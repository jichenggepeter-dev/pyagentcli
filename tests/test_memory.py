from pathlib import Path

from pyagentcli.memory.project_memory import ProjectMemory


def test_project_memory_remembers_notes(tmp_path: Path) -> None:
    memory = ProjectMemory(tmp_path)

    result = memory.remember("Prefer edit_file for localized changes.")

    assert "Remembered note" in result
    assert "Prefer edit_file" in memory.read_project_memory()
    assert "Project memory follows" in memory.format_context_block()


def test_project_memory_records_sessions(tmp_path: Path) -> None:
    memory = ProjectMemory(tmp_path)

    session = memory.record_session(
        goal="update README",
        mode="agent",
        status="completed",
        result="Read README and updated status.",
    )

    assert session.goal == "update README"
    assert session.result_summary == "Read README and updated status."
    assert memory.list_sessions()[0].goal == "update README"
    assert "Recent sessions:" in memory.format_memory()
