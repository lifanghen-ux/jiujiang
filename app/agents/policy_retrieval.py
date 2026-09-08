from app.agents.helpers import trace
from app.config import get_settings
from app.rag.service import RAGService


def policy_retrieval_node(state: dict) -> dict:
    settings = get_settings()
    evidence = state.get("evidence_result", {}).get("evidence_items", [])
    categories = sorted({str(item.get("event_category", "")) for item in evidence if item.get("event_category")})
    query = " ".join(
        [
            "银行外包供应商风险",
            *categories,
            str(state.get("risk_trend", {}).get("trend_type", "")),
            "证据核验 人工复核 候选处置",
        ]
    )
    service = RAGService(settings.vector_index_path)
    matches = service.search(query, top_k=settings.rag_top_k, approved_only=True)
    context = [
        {
            "chunk_id": item["chunk_id"],
            "document_name": item["document_name"],
            "version": item["version"],
            "text": item["text"],
            "score": round(float(item["score"]), 6),
        }
        for item in matches
        if float(item["score"]) > 0
    ]
    status = "PASS" if context else "EMPTY"
    return {
        "policy_context": context,
        "audit_trace": trace(
            "PolicyRetrievalAgent",
            status,
            detail=f"approved_policy_chunks={len(context)}",
        ),
    }
