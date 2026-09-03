from pathlib import Path

from app.rag.service import RAGService


def test_rag_index_keeps_source_metadata(tmp_path: Path):
    document = tmp_path / "mock.md"
    document.write_text("证据校验失败时不得形成正式处置建议。", encoding="utf-8")
    service = RAGService(tmp_path / "index.json")
    assert service.index_file(document, approved=False) == 1
    result = service.search("证据失败", top_k=1)
    assert result[0]["document_name"] == "mock.md"
    assert result[0]["is_approved"] is False

