from app.agents.helpers import trace


def coordinator_node(state: dict) -> dict:
    required = ("run_id", "supplier_id", "current_week")
    missing = [key for key in required if state.get(key) in (None, "")]
    if missing:
        return {
            "status": "FAILED_VALIDATION",
            "errors": [f"Missing workflow fields: {missing}"],
            "audit_trace": trace("Coordinator", "FAIL", detail="missing workflow fields"),
        }
    return {
        "status": "RUNNING",
        "audit_trace": trace("Coordinator", "PASS", detail="draft workflow accepted"),
    }

