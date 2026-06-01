from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from pyagentcli.rag.chunker import CodeChunk
from pyagentcli.rag.embeddings import EmbeddingProvider


@dataclass(frozen=True)
class VectorSearchHit:
    path: str
    start_line: int
    end_line: int
    snippet: str
    content: str
    score: float
    symbol_name: str | None = None
    kind: str = "text"


class SQLiteVectorStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def init_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chunk_vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                symbol_name TEXT,
                kind TEXT NOT NULL DEFAULT 'text',
                content TEXT NOT NULL,
                provider TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                embedding TEXT NOT NULL
            )
            """
        )

    def insert_chunks(
        self,
        connection: sqlite3.Connection,
        chunks: list[CodeChunk],
        *,
        provider: EmbeddingProvider,
    ) -> int:
        if not provider.available:
            return 0

        inserted = 0
        for chunk in chunks:
            embedding = provider.embed_query(chunk.content)
            connection.execute(
                """
                INSERT INTO chunk_vectors(
                    path, start_line, end_line, symbol_name, kind, content, provider, dimensions, embedding
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.path,
                    chunk.start_line,
                    chunk.end_line,
                    chunk.symbol_name,
                    chunk.kind,
                    chunk.content,
                    provider.name,
                    len(embedding),
                    json.dumps(embedding),
                ),
            )
            inserted += 1
        return inserted

    def search(
        self,
        query: str,
        *,
        provider: EmbeddingProvider,
        max_results: int = 20,
    ) -> list[VectorSearchHit]:
        if not provider.available or not self.database_path.exists():
            return []

        query_embedding = provider.embed_query(query)
        with sqlite3.connect(self.database_path) as connection:
            self.init_schema(connection)
            rows = connection.execute(
                """
                SELECT path, start_line, end_line, symbol_name, kind, content, embedding
                FROM chunk_vectors
                WHERE provider = ? AND dimensions = ?
                """,
                (provider.name, len(query_embedding)),
            ).fetchall()

        scored: list[VectorSearchHit] = []
        for path, start_line, end_line, symbol_name, kind, content, raw_embedding in rows:
            embedding = _loads_embedding(str(raw_embedding))
            if not embedding:
                continue
            score = _cosine_similarity(query_embedding, embedding)
            scored.append(
                VectorSearchHit(
                    path=str(path),
                    start_line=int(start_line),
                    end_line=int(end_line),
                    symbol_name=str(symbol_name) if symbol_name is not None else None,
                    kind=str(kind),
                    content=str(content),
                    snippet=_clean_snippet(content),
                    score=score,
                )
            )
        return sorted(scored, key=lambda hit: hit.score, reverse=True)[:max_results]


def _loads_embedding(raw: str) -> list[float]:
    try:
        values = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(values, list):
        return []
    return [float(value) for value in values if isinstance(value, int | float)]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_mag = math.sqrt(sum(value * value for value in left))
    right_mag = math.sqrt(sum(value * value for value in right))
    denominator = left_mag * right_mag
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _clean_snippet(value: str) -> str:
    text = value.replace("\n", " ").strip()
    return " ".join(text.split())
