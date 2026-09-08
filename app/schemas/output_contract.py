from typing import Literal

from pydantic import Field

from app.schemas.contracts import (
    CandidateAction,
    EvidenceResult,
    PredictionResult,
    StrictModel,
    TrendResult,
)

OUTPUT_SCHEMA_VERSION = "C-DRAFT-V0.2"


class GradualUpgradeComponent(StrictModel):
    pred_upgrade_label: Literal[0, 1]
    upgrade_probability: float = Field(ge=0.0, le=1.0)


class SuddenCurrentComponent(StrictModel):
    red_line_detected: bool
    current_max_severity: float = Field(ge=0.0, le=5.0)
    meaning: str


class RecoveryComponent(StrictModel):
    rectify_active: bool
    improving: bool
    risk_score_delta_1w: float


class RiskComponents(StrictModel):
    risk_mode: Literal["GRADUAL_WARNING", "SUDDEN_CURRENT", "RECOVERY", "STABLE"]
    gradual_upgrade: GradualUpgradeComponent
    sudden_current: SuddenCurrentComponent
    recovery: RecoveryComponent


class PublicLLMAdvisory(StrictModel):
    status: Literal["SUCCESS", "FALLBACK", "DISABLED"]
    provider: str
    model: str | None = None
    reason: str | None = None
    risk_summary: str | None = None
    rationale: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    policy_chunk_ids: list[str] = Field(default_factory=list)


class AuditEntry(StrictModel):
    agent_name: str
    status: str
    detail: str
    timestamp: str


class AssessmentOutput(StrictModel):
    schema_version: Literal["C-DRAFT-V0.2"] = OUTPUT_SCHEMA_VERSION
    run_id: str
    supplier_id: str
    current_week: int = Field(ge=1, le=52)
    prediction: PredictionResult
    prediction_source: str
    risk_components: RiskComponents
    risk_trend: TrendResult
    evidence_result: EvidenceResult
    llm_advisory: PublicLLMAdvisory
    candidate_actions: list[CandidateAction] = Field(default_factory=list)
    status: str
    errors: list[str] = Field(default_factory=list)
    audit_trace: list[AuditEntry] = Field(default_factory=list)


def build_public_assessment(state: dict) -> dict:
    payload = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "run_id": state["run_id"],
        "supplier_id": state["supplier_id"],
        "current_week": state["current_week"],
        "prediction": state["prediction"],
        "prediction_source": state["prediction_source"],
        "risk_components": state["risk_components"],
        "risk_trend": state["risk_trend"],
        "evidence_result": state["evidence_result"],
        "llm_advisory": state.get("llm_advisory", {"status": "DISABLED", "provider": "none"}),
        "candidate_actions": state.get("candidate_actions", []),
        "status": state["status"],
        "errors": state.get("errors", []),
        "audit_trace": state.get("audit_trace", []),
    }
    return AssessmentOutput.model_validate(payload).model_dump(mode="json")
