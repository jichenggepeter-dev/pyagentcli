from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyagentcli.rag.embeddings import EmbeddingProvider, NullEmbeddingProvider
from pyagentcli.rag.indexer import CodeIndexer, IndexSearchHit


@dataclass(frozen=True)
class RetrievalHit:
    source: str
    score: float
    path: str
    start_line: int
    end_line: int
    snippet: str
    symbol_name: str | None = None
    kind: str = "text"
    content: str = ""

    @classmethod
    def from_index_hit(cls, hit: IndexSearchHit, *, score: float) -> "RetrievalHit":
        return cls(
            source="fts",
            score=score,
            path=hit.path,
            start_line=hit.start_line,
            end_line=hit.end_line,
            snippet=hit.snippet,
            symbol_name=hit.symbol_name,
            kind=hit.kind,
            content=hit.content,
        )

    def location(self) -> str:
        return f"{self.path}:{self.start_line}-{self.end_line}"

    def label(self) -> str:
        if self.symbol_name:
            return f"{self.location()} {self.kind} {self.symbol_name}"
        return self.location()


@dataclass(frozen=True)
class HybridSearchResult:
    query: str
    hits: list[RetrievalHit]
    stale_paths: list[str]
    database_path: Path
    embedding_provider: str
    vector_enabled: bool

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


class HybridRetriever:
    def __init__(
        self,
        workspace_root: Path,
        *,
        indexer: CodeIndexer | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.indexer = indexer or CodeIndexer(self.workspace_root)
        self.embedding_provider = embedding_provider or NullEmbeddingProvider()

    def search(self, query: str, *, max_results: int = 20) -> HybridSearchResult:
        fts_result = self.indexer.search(query, max_results=max_results)
        fts_hits = [
            RetrievalHit.from_index_hit(hit, score=1.0 / (index + 1))
            for index, hit in enumerate(fts_result.hits)
        ]
        vector_hits = self._vector_hits(query=query)
        merged = _dedupe_hits([*fts_hits, *vector_hits])[:max_results]
        return HybridSearchResult(
            query=query,
            hits=merged,
            stale_paths=fts_result.stale_paths,
            database_path=fts_result.database_path,
            embedding_provider=self.embedding_provider.name,
            vector_enabled=self.embedding_provider.available,
        )

    def _vector_hits(self, *, query: str) -> list[RetrievalHit]:
        if not self.embedding_provider.available:
            return []
        # The provider call is intentionally wired before vector storage exists.
        # This proves missing embeddings are optional while keeping the future integration point executable.
        self.embedding_provider.embed_query(query)
        return []


def _dedupe_hits(hits: list[RetrievalHit]) -> list[RetrievalHit]:
    seen: set[tuple[str, int, int, str | None]] = set()
    deduped: list[RetrievalHit] = []
    for hit in hits:
        key = (hit.path, hit.start_line, hit.end_line, hit.symbol_name)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(hit)
    return deduped
