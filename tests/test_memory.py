from pathlib import Path
from datetime import UTC, datetime, timedelta

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


def test_project_memory_compresses_sessions_into_note(tmp_path: Path) -> None:
    memory = ProjectMemory(tmp_path)
    memory.record_session(
        goal="update README",
        mode="agent",
        status="completed",
        result="Read README and updated status.",
    )

    result = memory.compress_sessions()

    assert "Compressed sessions into project memory" in result
    assert "Session summary:" in memory.read_project_memory()
    assert "update README" in memory.read_project_memory()


def test_project_memory_deletes_line(tmp_path: Path) -> None:
    memory = ProjectMemory(tmp_path)
    memory.remember("First note.")
    memory.remember("Second note.")

    result = memory.delete_project_memory_line(3)

    assert "Deleted memory line 3" in result
    assert "First note." not in memory.read_project_memory()
    assert "Second note." in memory.read_project_memory()


def test_project_memory_reports_stale_notes(tmp_path: Path) -> None:
    memory = ProjectMemory(tmp_path)
    memory.memory_dir.mkdir(parents=True)
    old_timestamp = (datetime.now(UTC) - timedelta(days=45)).isoformat()
    memory.project_path.write_text(
        f"# Project Memory\n\n- {old_timestamp}: Old note.\n",
        encoding="utf-8",
    )

    result = memory.format_stale_notes(older_than_days=30)

    assert "Old note." in result
    assert "older than 30 days" in result
