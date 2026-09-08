from app.agents.helpers import trace
from app.schemas.output_contract import OUTPUT_SCHEMA_VERSION


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
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "audit_trace": trace("Coordinator", "PASS", detail=f"output_schema={OUTPUT_SCHEMA_VERSION}"),
    }
