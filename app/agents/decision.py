from app.agents.helpers import trace
from app.schemas.contracts import CandidateAction


def decision_node(state: dict) -> dict:
    if state.get("evidence_result", {}).get("status") != "PASS":
        return {
            "errors": ["Evidence Gate blocked Decision Agent"],
            "audit_trace": trace("DecisionAgent", "BLOCKED", detail="evidence insufficient"),
        }

    probability = float(state.get("prediction", {}).get("upgrade_probability", 0.0))
    action = CandidateAction(
        suggest_type="alert" if probability >= 0.5 else "observe",
        suggest_content="Mock 候选建议：请业务人员结合证据复核，不得自动执行。",
        suggest_priority="HIGH" if probability >= 0.75 else "MEDIUM" if probability >= 0.5 else "LOW",
    )
    return {
        "candidate_actions": [action.model_dump()],
        "audit_trace": trace("DecisionAgent", "PASS", detail="candidate action only"),
    }

