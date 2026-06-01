from __future__ import annotations

import hashlib
import math
from typing import Protocol


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
