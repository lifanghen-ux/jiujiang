from app.agents.helpers import trace
from app.schemas.contracts import EvidenceItem, EvidenceResult


def evidence_node(state: dict) -> dict:
    supplier_id = state["supplier_id"]
    current_week = int(state["current_week"])
    events = {event["evidence_id"]: event for event in state.get("events", [])}
    requested = state.get("risk_trend", {}).get("trend_support_evidence_ids", [])
    reasons: list[str] = []
    items: list[EvidenceItem] = []

    if not requested:
        reasons.append("No evidence_id supports the risk trend")
    for evidence_id in requested:
        event = events.get(evidence_id)
        if event is None:
            reasons.append(f"Unknown evidence_id: {evidence_id}")
            continue
        if event["supplier_id"] != supplier_id:
            reasons.append(f"Evidence belongs to another supplier: {evidence_id}")
            continue
        if int(event["event_week"]) > current_week:
            reasons.append(f"Future evidence is forbidden: {evidence_id}")
            continue
        items.append(EvidenceItem.model_validate(event))

    result = EvidenceResult(status="FAIL" if reasons else "PASS", evidence_items=items, reasons=reasons)
    return {
        "evidence_result": result.model_dump(),
        "audit_trace": trace("EvidenceAgent", result.status, detail="; ".join(reasons) or "evidence verified"),
    }


def route_after_evidence(state: dict) -> str:
    return "decision" if state.get("evidence_result", {}).get("status") == "PASS" else "human_review"

