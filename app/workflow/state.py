import operator
from typing import Annotated, Any, TypedDict


class WorkflowState(TypedDict, total=False):
    run_id: str
    supplier_id: str
    current_week: int
    events: list[dict[str, Any]]
    visible_events: list[dict[str, Any]]
    business_context: dict[str, Any]
    association_result: dict[str, Any]
    features: dict[str, float]
    model_features: dict[str, float]
    prediction: dict[str, Any]
    prediction_source: str
    risk_components: dict[str, Any]
    risk_trend: dict[str, Any]
    evidence_result: dict[str, Any]
    policy_context: list[dict[str, Any]]
    enable_live_llm: bool
    llm_advisory: dict[str, Any]
    candidate_actions: list[dict[str, Any]]
    status: str
    errors: Annotated[list[str], operator.add]
    audit_trace: Annotated[list[dict[str, Any]], operator.add]
