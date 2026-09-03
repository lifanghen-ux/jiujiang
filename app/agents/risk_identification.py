from app.agents.helpers import trace


def risk_identification_node(state: dict) -> dict:
    current_week = int(state["current_week"])
    supplier_id = state["supplier_id"]
    visible = [
        event
        for event in state.get("events", [])
        if event["supplier_id"] == supplier_id and int(event["event_week"]) <= current_week
    ]
    return {
        "visible_events": visible,
        "audit_trace": trace("RiskIdentificationAgent", "PASS", detail=f"visible_events={len(visible)}"),
    }

