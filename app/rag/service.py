from pathlib import Path

from app.rag.loaders import load_document, split_document
from app.rag.vector_store import LocalVectorStore


class RAGService:
    def __init__(self, index_path: Path) -> None:
        self.store = LocalVectorStore(index_path)

    def index_file(self, path: Path, *, approved: bool = False) -> int:
        text, metadata = load_document(path, approved=approved)
        chunks = split_document(text, metadata)
        self.store.add(chunks)
        self.store.save()
        return len(chunks)

    def search(self, query: str, *, top_k: int = 3, approved_only: bool = False) -> list[dict]:
        self.store.load()
        return self.store.search(query, top_k=top_k, approved_only=approved_only)

