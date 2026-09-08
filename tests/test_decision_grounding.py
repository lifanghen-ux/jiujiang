import pytest

from app.agents.decision import _align_identifiers, _validate_grounding
from app.schemas.contracts import AdvisoryResult


def test_llm_advisory_rejects_invented_evidence_or_policy_ids() -> None:
    advisory = AdvisoryResult.model_validate(
        {
            "risk_summary": "测试",
            "rationale": "测试",
            "evidence_ids": ["E-INVENTED"],
            "policy_chunk_ids": ["P-INVENTED"],
            "candidate_actions": [
                {
                    "suggest_type": "observe",
                    "suggest_content": "人工复核",
                    "suggest_priority": "LOW",
                    "execution_status": "PENDING_HUMAN_REVIEW",
                }
            ],
        }
    )
    state = {
        "evidence_result": {"evidence_items": [{"evidence_id": "E-REAL"}]},
        "policy_context": [{"chunk_id": "P-REAL"}],
    }

    with pytest.raises(ValueError, match="outside supplied context"):
        _validate_grounding(advisory, state)


def test_visually_equivalent_hyphen_is_restored_to_source_id() -> None:
    advisory = AdvisoryResult.model_validate(
        {
            "risk_summary": "测试",
            "rationale": "测试",
            "evidence_ids": ["E-S-01"],
            "policy_chunk_ids": ["P-01"],
            "candidate_actions": [
                {
                    "suggest_type": "observe",
                    "suggest_content": "人工复核",
                    "suggest_priority": "LOW",
                }
            ],
        }
    )
    state = {
        "evidence_result": {"evidence_items": [{"evidence_id": "E‑S‑01"}]},
        "policy_context": [{"chunk_id": "P-01"}],
    }

    _align_identifiers(advisory, state)
    _validate_grounding(advisory, state)
    assert advisory.evidence_ids == ["E‑S‑01"]
