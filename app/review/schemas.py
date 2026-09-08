from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import Field, model_validator

from app.schemas.contracts import StrictModel
from app.schemas.output_contract import OUTPUT_SCHEMA_VERSION


class HumanReviewRequest(StrictModel):
    reviewer_id: str = Field(min_length=1, max_length=100)
    review_result: Literal["APPROVED", "REJECTED", "NEED_MORE_EVIDENCE"]
    final_action: Literal["observe", "alert", "rectify"] | None = None
    review_comment: str = Field(default="", max_length=1000)
    actual_outcome: Literal["RISK_OCCURRED", "NO_RISK", "UNKNOWN"] = "UNKNOWN"
    outcome_week: int | None = Field(default=None, ge=1, le=52)

    @model_validator(mode="after")
    def validate_approved_action(self):
        if self.review_result == "APPROVED" and self.final_action is None:
            raise ValueError("APPROVED review requires final_action")
        return self


class HumanReviewRecord(HumanReviewRequest):
    schema_version: Literal["C-DRAFT-V0.2"] = OUTPUT_SCHEMA_VERSION
    review_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    supplier_id: str
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
