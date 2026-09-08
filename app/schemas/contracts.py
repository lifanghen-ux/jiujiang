from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PredictionResult(StrictModel):
    pred_upgrade_label: Literal[0, 1]
    upgrade_probability: float = Field(ge=0.0, le=1.0)
    model_version: str
    model_status: Literal["MOCK", "UNTRAINED", "TRAINED"] = "MOCK"


class TrendResult(StrictModel):
    trend_type: Literal["RISING", "STEADY", "FALLING", "SUDDEN_JUMP"]
    trend_desc: str = Field(min_length=1, max_length=500)
    trend_support_evidence_ids: list[str] = Field(default_factory=list, max_length=20)


class EvidenceItem(StrictModel):
    evidence_id: str = Field(min_length=1, max_length=100)
    supplier_id: str = Field(min_length=1, max_length=100)
    event_category: str = Field(min_length=1, max_length=50)
    event_subtype: str = Field(min_length=1, max_length=100)
    event_severity: int = Field(ge=0, le=5)
    event_week: int = Field(ge=1, le=52)
    source_type: str = Field(min_length=1, max_length=100)


class EvidenceResult(StrictModel):
    status: Literal["PASS", "FAIL"]
    evidence_items: list[EvidenceItem] = Field(default_factory=list, max_length=50)
    reasons: list[str] = Field(default_factory=list, max_length=20)


class CandidateAction(StrictModel):
    suggest_type: Literal["rectify", "observe", "alert"]
    suggest_content: str = Field(min_length=1, max_length=500)
    suggest_priority: Literal["HIGH", "MEDIUM", "LOW"]
    execution_status: Literal["PENDING_HUMAN_REVIEW"] = "PENDING_HUMAN_REVIEW"


class AdvisoryResult(StrictModel):
    risk_summary: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=1000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    policy_chunk_ids: list[str] = Field(default_factory=list, max_length=10)
    candidate_actions: list[CandidateAction] = Field(min_length=1, max_length=5)
