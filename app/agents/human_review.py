from app.agents.helpers import trace


def human_review_node(state: dict) -> dict:
    evidence_passed = state.get("evidence_result", {}).get("status") == "PASS"
    status = "PENDING_HUMAN_REVIEW" if evidence_passed else "EVIDENCE_INSUFFICIENT"
    return {
        "status": status,
        "audit_trace": trace("HumanReview", "PENDING" if evidence_passed else "BLOCKED", detail=status),
    }

