from pathlib import Path

from pyagentcli.rag.embeddings import HashEmbeddingProvider, NullEmbeddingProvider
from pyagentcli.rag.indexer import CodeIndexer
from pyagentcli.rag.retriever import HybridRetriever


def test_hybrid_retriever_uses_fts_when_embeddings_are_disabled(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def project_status():\n    return 'READY'\n", encoding="utf-8")
    CodeIndexer(tmp_path).rebuild()

    result = HybridRetriever(tmp_path, embedding_provider=NullEmbeddingProvider()).search("project_status")

    assert result.vector_enabled is False
    assert result.embedding_provider == "none"
    assert result.hits[0].source == "fts"
    assert result.hits[0].symbol_name == "project_status"
    assert "src/app.py:1-2 function project_status:" in result.format_text()


def test_hybrid_retriever_calls_available_embedding_provider(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Project status READY\n", encoding="utf-8")
    CodeIndexer(tmp_path).rebuild()
    provider = HashEmbeddingProvider(dimensions=8)

    result = HybridRetriever(tmp_path, embedding_provider=provider).search("READY")

    assert result.vector_enabled is True
    assert result.embedding_provider == "hash"
    assert len(provider.embed_query("READY")) == 8
    assert result.hits


def test_hash_embedding_provider_is_deterministic() -> None:
    provider = HashEmbeddingProvider(dimensions=8)

    assert provider.embed_query("same") == provider.embed_query("same")
    assert provider.embed_query("same") != provider.embed_query("different")
