import sqlite3
from pathlib import Path

from pyagentcli.rag.indexer import CodeIndexer


def test_code_indexer_rebuilds_sqlite_fts_index(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def project_status():\n    return 'READY'\n", encoding="utf-8")
    (tmp_path / ".pyagent").mkdir()
    (tmp_path / ".pyagent" / "secret.txt").write_text("SECRET\n", encoding="utf-8")

    result = CodeIndexer(tmp_path).rebuild()

    assert result.indexed_files == 1
    assert result.indexed_chunks == 1
    assert result.indexed_vectors == 0
    assert result.database_path.exists()
    with sqlite3.connect(result.database_path) as connection:
        rows = connection.execute(
            "SELECT path FROM files_fts WHERE files_fts MATCH ?",
            ("project_status",),
        ).fetchall()
        chunk_rows = connection.execute(
            "SELECT path, start_line, end_line FROM chunks_fts WHERE chunks_fts MATCH ?",
            ("project_status",),
        ).fetchall()
        secret_rows = connection.execute("SELECT path FROM files WHERE path LIKE ?", ("%secret%",)).fetchall()

    assert rows == [("src/app.py",)]
    assert chunk_rows == [("src/app.py", 1, 2)]
    assert secret_rows == []


def test_code_indexer_searches_existing_index(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def project_status():\n    return 'READY'\n", encoding="utf-8")

    indexer = CodeIndexer(tmp_path)
    indexer.rebuild()
    result = indexer.search("project_status")

    assert result.hits
    assert result.hits[0].path == "src/app.py"
    assert result.hits[0].start_line == 1
    assert result.hits[0].end_line == 2
    assert result.hits[0].symbol_name == "project_status"
    assert result.hits[0].kind == "function"
    assert "[project_status]" in result.hits[0].snippet


def test_code_indexer_search_result_formats_chunk_locations(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def project_status():\n    return 'READY'\n", encoding="utf-8")

    indexer = CodeIndexer(tmp_path)
    indexer.rebuild()

    assert "src/app.py:1-2 function project_status:" in indexer.search("project_status").format_text()


def test_code_indexer_searches_exact_python_symbols(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "\n".join(
            [
                "def project_status():",
                "    return 'READY'",
                "",
                "class Runner:",
                "    def run(self):",
                "        return project_status()",
            ]
        ),
        encoding="utf-8",
    )

    indexer = CodeIndexer(tmp_path)
    indexer.rebuild()
    function_result = indexer.search_symbol("project_status")
    method_result = indexer.search_symbol("Runner.run")

    assert function_result.hits[0].kind == "function"
    assert function_result.hits[0].symbol_name == "project_status"
    assert method_result.hits[0].kind == "method"
    assert method_result.hits[0].symbol_name == "Runner.run"


def test_code_indexer_searches_typescript_symbols(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.ts").write_text(
        "\n".join(
            [
                "export function projectStatus() {",
                "  return 'READY';",
                "}",
                "",
                "const refreshStatus = () => {",
                "  return projectStatus();",
                "};",
            ]
        ),
        encoding="utf-8",
    )

    indexer = CodeIndexer(tmp_path)
    indexer.rebuild()
    function_result = indexer.search_symbol("projectStatus")
    arrow_result = indexer.search_symbol("refreshStatus")

    assert function_result.hits[0].path == "src/app.ts"
    assert function_result.hits[0].kind == "function"
    assert function_result.hits[0].symbol_name == "projectStatus"
    assert arrow_result.hits[0].kind == "function"
    assert arrow_result.hits[0].symbol_name == "refreshStatus"


def test_code_indexer_reports_changed_files_as_stale(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "app.py"
    target.write_text("def project_status():\n    return 'READY'\n", encoding="utf-8")

    indexer = CodeIndexer(tmp_path)
    indexer.rebuild()
    target.write_text("def project_status():\n    return 'STALE'\n", encoding="utf-8")
    result = indexer.search("project_status")

    assert result.stale_paths == ["src/app.py"]
    assert indexer.stale_paths() == ["src/app.py"]
    assert "Warning: index may be stale for: src/app.py" in result.format_text()


def test_code_indexer_reports_new_files_as_stale(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def project_status():\n    return 'READY'\n", encoding="utf-8")

    indexer = CodeIndexer(tmp_path)
    indexer.rebuild()
    (tmp_path / "src" / "new_feature.py").write_text("def new_feature():\n    pass\n", encoding="utf-8")

    assert indexer.search("project_status").stale_paths == ["src/new_feature.py"]


def test_code_indexer_can_persist_chunk_vectors(tmp_path: Path) -> None:
    from pyagentcli.rag.embeddings import HashEmbeddingProvider

    (tmp_path / "README.md").write_text("Project status READY\n", encoding="utf-8")

    result = CodeIndexer(tmp_path, embedding_provider=HashEmbeddingProvider(dimensions=8)).rebuild()

    assert result.indexed_vectors == result.indexed_chunks
    with sqlite3.connect(result.database_path) as connection:
        rows = connection.execute("SELECT path, provider, dimensions FROM chunk_vectors").fetchall()

    assert rows == [("README.md", "hash", 8)]


def test_code_indexer_extracts_python_import_graph(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "\n".join(
            [
                "import os",
                "import pathlib as pl",
                "from collections import defaultdict",
                "from .helpers import normalize",
                "",
                "def run():",
                "    return normalize(defaultdict)",
            ]
        ),
        encoding="utf-8",
    )

    indexer = CodeIndexer(tmp_path)
    indexer.rebuild()
    edges = indexer.imports_for("src/app.py")

    assert [edge.format_text() for edge in edges] == [
        "src/app.py:1 imports os",
        "src/app.py:2 imports pathlib",
        "src/app.py:3 imports collections:defaultdict",
        "src/app.py:4 imports .helpers:normalize",
    ]


def test_code_indexer_finds_files_importing_module_or_name(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "from helpers import normalize\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "other.py").write_text(
        "import helpers\n",
        encoding="utf-8",
    )

    indexer = CodeIndexer(tmp_path)
    indexer.rebuild()

    by_module = indexer.imported_by("helpers")
    by_name = indexer.imported_by("normalize")

    assert [edge.path for edge in by_module] == ["src/app.py", "src/other.py"]
    assert [edge.path for edge in by_name] == ["src/app.py"]
