import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

from app.rag.models import DocumentChunk

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def _vectorize(text: str, dimensions: int = 256) -> list[float]:
    counts: Counter[int] = Counter()
    for token in TOKEN_PATTERN.findall(text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        counts[int.from_bytes(digest[:4], "big") % dimensions] += 1
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return [counts[index] / norm for index in range(dimensions)]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


class LocalVectorStore:
    """Small deterministic local index for skeleton validation, not production scale."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.records: list[dict] = []

    def add(self, chunks: list[DocumentChunk]) -> None:
        self.records.extend({"chunk": chunk.to_dict(), "vector": _vectorize(chunk.text)} for chunk in chunks)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.records, ensure_ascii=False), encoding="utf-8")

    def load(self) -> None:
        self.records = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []

    def search(self, query: str, *, top_k: int = 3, approved_only: bool = False) -> list[dict]:
        query_vector = _vectorize(query)
        candidates = []
        for record in self.records:
            chunk = record["chunk"]
            if approved_only and not chunk["is_approved"]:
                continue
            candidates.append({"score": _dot(query_vector, record["vector"]), **chunk})
        return sorted(candidates, key=lambda item: item["score"], reverse=True)[:top_k]

