from app.agents.helpers import trace


def association_analysis_node(state: dict) -> dict:
    context = state.get("business_context", {})
    exposure = float(context.get("business_exposure", 0.0))
    return {
        "association_result": {
            "business_exposure": exposure,
            "is_high_impact": exposure >= 0.75,
            "status": "MOCK",
        },
        "audit_trace": trace("AssociationAnalysisAgent", "PASS", detail="mock association completed"),
    }

