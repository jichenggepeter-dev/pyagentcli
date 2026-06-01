from pathlib import Path

from pyagentcli.context_injection import inject_context_references
from pyagentcli.rag.indexer import CodeIndexer


def test_injects_file_reference(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Hello context\n", encoding="utf-8")

    injected = inject_context_references("Summarize @README.md", tmp_path)

    assert injected.references == ["README.md"]
    assert "### @README.md" in injected.enriched_goal
    assert "Hello context" in injected.enriched_goal


def test_file_reference_includes_dependency_context_when_index_exists(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "from helpers import normalize\n\nvalue = normalize('x')\n",
        encoding="utf-8",
    )
    CodeIndexer(tmp_path).rebuild()

    injected = inject_context_references("Explain @src/app.py", tmp_path)

    assert "Dependency context:" in injected.enriched_goal
    assert "src/app.py:1 imports helpers:normalize" in injected.enriched_goal


def test_file_reference_works_without_dependency_index(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("from helpers import normalize\n", encoding="utf-8")

    injected = inject_context_references("Explain @src/app.py", tmp_path)

    assert "from helpers import normalize" in injected.enriched_goal
    assert "Dependency context:" not in injected.enriched_goal


def test_injects_directory_reference(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")

    injected = inject_context_references("Inspect @src/", tmp_path)

    assert injected.references == ["src/"]
    assert "### @src/" in injected.enriched_goal
    assert "src/app.py" in injected.enriched_goal


def test_context_reference_respects_path_policy(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET=value\n", encoding="utf-8")

    injected = inject_context_references("Read @.env", tmp_path)

    assert "Unable to load reference" in injected.enriched_goal
    assert "SECRET=value" not in injected.enriched_goal


def test_no_references_returns_original_goal(tmp_path: Path) -> None:
    injected = inject_context_references("No context here", tmp_path)

    assert injected.enriched_goal == "No context here"
    assert injected.references == []


def test_injects_symbol_reference_from_index(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def project_status():\n    return 'READY'\n", encoding="utf-8")
    CodeIndexer(tmp_path).rebuild()

    injected = inject_context_references("Explain @project_status", tmp_path)

    assert injected.references == ["project_status"]
    assert "### @project_status" in injected.enriched_goal
    assert "#### src/app.py:1-2 function project_status" in injected.enriched_goal
    assert "def project_status()" in injected.enriched_goal


def test_symbol_reference_includes_dependency_context(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "from helpers import status_value\n\n"
        "def project_status():\n"
        "    return status_value()\n",
        encoding="utf-8",
    )
    CodeIndexer(tmp_path).rebuild()

    injected = inject_context_references("Explain @project_status", tmp_path)

    assert "Dependency context:" in injected.enriched_goal
    assert "src/app.py:1 imports helpers:status_value" in injected.enriched_goal


def test_injects_method_symbol_reference_from_index(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "class Runner:\n    def run(self):\n        return 'READY'\n",
        encoding="utf-8",
    )
    CodeIndexer(tmp_path).rebuild()

    injected = inject_context_references("Explain @Runner.run", tmp_path)

    assert injected.references == ["Runner.run"]
    assert "#### src/app.py:2-3 method Runner.run" in injected.enriched_goal
    assert "def run(self)" in injected.enriched_goal


def test_symbol_reference_reports_missing_index(tmp_path: Path) -> None:
    injected = inject_context_references("Explain @project_status", tmp_path)

    assert injected.references == ["project_status"]
    assert "index not found" in injected.enriched_goal


def test_existing_path_wins_over_symbol_lookup(tmp_path: Path) -> None:
    (tmp_path / "project_status").write_text("path content\n", encoding="utf-8")

    injected = inject_context_references("Explain @project_status", tmp_path)

    assert "path content" in injected.enriched_goal
    assert "index not found" not in injected.enriched_goal


def test_symbol_reference_warns_when_index_is_stale(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "app.py"
    target.write_text("def project_status():\n    return 'READY'\n", encoding="utf-8")
    CodeIndexer(tmp_path).rebuild()
    target.write_text("def project_status():\n    return 'STALE'\n", encoding="utf-8")

    injected = inject_context_references("Explain @project_status", tmp_path)

    assert "Warning: index may be stale for: src/app.py" in injected.enriched_goal
    assert "Run `pyagent --index` to refresh" in injected.enriched_goal
