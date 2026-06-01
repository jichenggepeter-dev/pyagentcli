from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyagentcli.rag.chunker import CodeChunk, chunk_text


IGNORED_DIRS = {".git", ".pyagent", ".pytest_cache", "__pycache__", ".venv", "node_modules", "dist", "build"}
IGNORED_SUFFIXES = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar", ".gz", ".sqlite"}
MAX_INDEX_CHARS = 200_000


@dataclass(frozen=True)
class IndexResult:
    indexed_files: int
    indexed_chunks: int
    skipped_files: int
    database_path: Path

    def format_text(self) -> str:
        return (
            f"Indexed {self.indexed_files} files into {self.indexed_chunks} chunks; "
            f"skipped {self.skipped_files} files.\n"
            f"Index: {self.database_path}"
        )


@dataclass(frozen=True)
class IndexSearchHit:
    path: str
    start_line: int
    end_line: int
    snippet: str
    content: str = ""
    symbol_name: str | None = None
    kind: str = "text"

    def location(self) -> str:
        return f"{self.path}:{self.start_line}-{self.end_line}"

    def label(self) -> str:
        if self.symbol_name:
            return f"{self.location()} {self.kind} {self.symbol_name}"
        return self.location()


@dataclass(frozen=True)
class IndexSearchResult:
    query: str
    hits: list[IndexSearchHit]
    database_path: Path
    stale_paths: list[str]

    def format_text(self) -> str:
        prefix = ""
        if self.stale_paths:
            stale = ", ".join(self.stale_paths[:10])
            if len(self.stale_paths) > 10:
                stale += ", ..."
            prefix = f"Warning: index may be stale for: {stale}. Run `pyagent --index` to refresh.\n"
        if not self.hits:
            return f"{prefix}No index matches for {self.query!r}."
        matches = "\n".join(f"{hit.label()}: {hit.snippet}" for hit in self.hits)
        return f"{prefix}{matches}"


class CodeIndexer:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self.database_path = self.workspace_root / ".pyagent" / "index.sqlite"

    def rebuild(self) -> IndexResult:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        indexed = 0
        indexed_chunks = 0
        skipped = 0
        with sqlite3.connect(self.database_path) as connection:
            _drop_rebuildable_tables(connection)
            self._init_schema(connection)
            connection.execute("DELETE FROM files")
            connection.execute("DELETE FROM files_fts")
            connection.execute("DELETE FROM chunks")
            connection.execute("DELETE FROM chunks_fts")

            for path in _iter_indexable_files(self.workspace_root):
                try:
                    content = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    skipped += 1
                    continue
                if len(content) > MAX_INDEX_CHARS:
                    content = content[:MAX_INDEX_CHARS]
                    skipped += 1

                stat = path.stat()
                relative_path = str(path.relative_to(self.workspace_root))
                connection.execute(
                    "INSERT INTO files(path, mtime, size, content) VALUES (?, ?, ?, ?)",
                    (relative_path, stat.st_mtime, stat.st_size, content),
                )
                connection.execute(
                    "INSERT INTO files_fts(path, content) VALUES (?, ?)",
                    (relative_path, content),
                )
                chunks = chunk_text(path=relative_path, content=content)
                _insert_chunks(connection, chunks)
                indexed_chunks += len(chunks)
                indexed += 1

        return IndexResult(
            indexed_files=indexed,
            indexed_chunks=indexed_chunks,
            skipped_files=skipped,
            database_path=self.database_path,
        )

    def search(self, query: str, *, max_results: int = 20) -> IndexSearchResult:
        if not query:
            return IndexSearchResult(query=query, hits=[], database_path=self.database_path, stale_paths=[])
        if not self.database_path.exists():
            raise FileNotFoundError(f"Index does not exist: {self.database_path}")

        match_query = _to_fts_phrase(query)
        with sqlite3.connect(self.database_path) as connection:
            stale_paths = _find_stale_paths(connection, self.workspace_root)
            rows = connection.execute(
                """
                SELECT path, start_line, end_line, symbol_name, kind, content, snippet(chunks_fts, 5, '[', ']', ' ... ', 18)
                FROM chunks_fts
                WHERE chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (match_query, _coerce_max_results(max_results)),
            ).fetchall()
        hits = [
            IndexSearchHit(
                path=str(path),
                start_line=int(start_line),
                end_line=int(end_line),
                symbol_name=str(symbol_name) if symbol_name is not None else None,
                kind=str(kind),
                content=str(content),
                snippet=_clean_snippet(snippet),
            )
            for path, start_line, end_line, symbol_name, kind, content, snippet in rows
        ]
        return IndexSearchResult(
            query=query,
            hits=hits,
            database_path=self.database_path,
            stale_paths=stale_paths,
        )

    def search_symbol(self, symbol_name: str, *, max_results: int = 20) -> IndexSearchResult:
        if not symbol_name:
            return IndexSearchResult(query=symbol_name, hits=[], database_path=self.database_path, stale_paths=[])
        if not self.database_path.exists():
            raise FileNotFoundError(f"Index does not exist: {self.database_path}")

        with sqlite3.connect(self.database_path) as connection:
            stale_paths = _find_stale_paths(connection, self.workspace_root)
            rows = connection.execute(
                """
                SELECT path, start_line, end_line, symbol_name, kind, content
                FROM chunks
                WHERE symbol_name = ?
                ORDER BY path, start_line
                LIMIT ?
                """,
                (symbol_name, _coerce_max_results(max_results)),
            ).fetchall()
        hits = [
            IndexSearchHit(
                path=str(path),
                start_line=int(start_line),
                end_line=int(end_line),
                symbol_name=str(found_symbol) if found_symbol is not None else None,
                kind=str(kind),
                content=str(content),
                snippet=_clean_snippet(content),
            )
            for path, start_line, end_line, found_symbol, kind, content in rows
        ]
        return IndexSearchResult(
            query=symbol_name,
            hits=hits,
            database_path=self.database_path,
            stale_paths=stale_paths,
        )

    def stale_paths(self) -> list[str]:
        if not self.database_path.exists():
            return []
        with sqlite3.connect(self.database_path) as connection:
            return _find_stale_paths(connection, self.workspace_root)

    @staticmethod
    def _init_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                mtime REAL NOT NULL,
                size INTEGER NOT NULL,
                content TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts
            USING fts5(path, content)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                symbol_name TEXT,
                kind TEXT NOT NULL DEFAULT 'text',
                content TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
            USING fts5(path UNINDEXED, start_line UNINDEXED, end_line UNINDEXED, symbol_name, kind, content)
            """
        )


def _iter_indexable_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in IGNORED_DIRS for part in relative_parts):
            continue
        if path.suffix.lower() in IGNORED_SUFFIXES:
            continue
        yield path


def _insert_chunks(connection: sqlite3.Connection, chunks: list[CodeChunk]) -> None:
    for chunk in chunks:
        connection.execute(
            "INSERT INTO chunks(path, start_line, end_line, symbol_name, kind, content) VALUES (?, ?, ?, ?, ?, ?)",
            (chunk.path, chunk.start_line, chunk.end_line, chunk.symbol_name, chunk.kind, chunk.content),
        )
        connection.execute(
            "INSERT INTO chunks_fts(path, start_line, end_line, symbol_name, kind, content) VALUES (?, ?, ?, ?, ?, ?)",
            (chunk.path, chunk.start_line, chunk.end_line, chunk.symbol_name, chunk.kind, chunk.content),
        )


def _drop_rebuildable_tables(connection: sqlite3.Connection) -> None:
    connection.execute("DROP TABLE IF EXISTS files_fts")
    connection.execute("DROP TABLE IF EXISTS chunks_fts")
    connection.execute("DROP TABLE IF EXISTS chunks")


def _find_stale_paths(connection: sqlite3.Connection, workspace_root: Path) -> list[str]:
    stale: set[str] = set()
    indexed_rows = connection.execute("SELECT path, mtime, size FROM files").fetchall()
    indexed_paths = {str(path) for path, _mtime, _size in indexed_rows}

    for relative_path, indexed_mtime, indexed_size in indexed_rows:
        current_path = workspace_root / str(relative_path)
        if not current_path.exists():
            stale.add(str(relative_path))
            continue
        try:
            stat = current_path.stat()
        except OSError:
            stale.add(str(relative_path))
            continue
        if stat.st_size != int(indexed_size) or abs(stat.st_mtime - float(indexed_mtime)) > 0.000001:
            stale.add(str(relative_path))

    for path in _iter_indexable_files(workspace_root):
        relative_path = str(path.relative_to(workspace_root))
        if relative_path not in indexed_paths:
            stale.add(relative_path)

    return sorted(stale)


def _to_fts_phrase(query: str) -> str:
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


def _clean_snippet(value: Any) -> str:
    text = str(value).replace("\n", " ").strip()
    return " ".join(text.split())


def _coerce_max_results(value: Any) -> int:
    try:
        return max(1, min(int(value), 100))
    except (TypeError, ValueError):
        return 20
