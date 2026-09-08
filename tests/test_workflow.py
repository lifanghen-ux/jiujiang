from app.demo import run_demo
from app.schemas.output_contract import build_public_assessment


def test_workflow_reaches_human_review_with_verified_evidence():
    result = run_demo(current_week=10, include_events=True)
    assert result["evidence_result"]["status"] == "PASS"
    assert result["status"] == "PENDING_HUMAN_REVIEW"
    assert result["candidate_actions"][0]["execution_status"] == "PENDING_HUMAN_REVIEW"
    public = build_public_assessment(result)
    assert public["schema_version"] == "C-DRAFT-V0.2"
    assert "events" not in public


def test_evidence_fail_blocks_decision_agent():
    result = run_demo(current_week=10, include_events=False)
    assert result["evidence_result"]["status"] == "FAIL"
    assert result["status"] == "EVIDENCE_INSUFFICIENT"
    assert not result.get("candidate_actions")
    assert all(item["agent_name"] != "DecisionAgent" for item in result["audit_trace"])
