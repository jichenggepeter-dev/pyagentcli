from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.error
import urllib.request
from typing import Protocol

from pyagentcli.config import EmbeddingConfig


class EmbeddingProvider(Protocol):
    name: str

    @property
    def available(self) -> bool:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


class NullEmbeddingProvider:
    name = "none"

    @property
    def available(self) -> bool:
        return False

    def embed_query(self, text: str) -> list[float]:
        raise RuntimeError("No embedding provider is configured.")


class HashEmbeddingProvider:
    """Deterministic local embedding stub for tests and future vector-store plumbing."""

    name = "hash"

    def __init__(self, *, dimensions: int = 16) -> None:
        self.dimensions = max(4, dimensions)

    @property
    def available(self) -> bool:
        return True

    def embed_query(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [((digest[index % len(digest)] / 255.0) * 2.0) - 1.0 for index in range(self.dimensions)]
        magnitude = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / magnitude for value in values]


class OpenAICompatibleEmbeddingProvider:
    name = "openai-compatible"

    def __init__(self, *, api_key: str | None, base_url: str, model: str, timeout_seconds: int = 30) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def embed_query(self, text: str) -> list[float]:
        if not self.api_key:
            raise RuntimeError("Embedding API key is not configured.")
        body = {"model": self.model, "input": text}
        request = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Embedding HTTP error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Embedding connection error: {exc.reason}") from exc

        embedding = ((data.get("data") or [{}])[0]).get("embedding")
        if not isinstance(embedding, list):
            raise RuntimeError("Embedding response did not include an embedding vector.")
        return [float(value) for value in embedding]


def build_embedding_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    provider = config.provider.strip().lower()
    if provider == "hash":
        return HashEmbeddingProvider(dimensions=config.dimensions)
    if provider in {"openai", "openai-compatible"}:
        return OpenAICompatibleEmbeddingProvider(
            api_key=os.getenv(config.api_key_env) or None,
            base_url=config.base_url,
            model=config.model,
        )
    return NullEmbeddingProvider()
