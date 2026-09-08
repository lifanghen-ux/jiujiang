import json
import logging

from app.agents.helpers import trace
from app.config import get_settings
from app.llm.factory import build_llm_client
from app.schemas.contracts import AdvisoryResult, CandidateAction

logger = logging.getLogger(__name__)

HYPHEN_TRANSLATION = str.maketrans({"‑": "-", "–": "-", "—": "-", "−": "-"})


SYSTEM_PROMPT = """你是银行外包供应商风险辅助研判助手。
只输出 JSON 对象，并严格包含 risk_summary、rationale、evidence_ids、policy_chunk_ids、candidate_actions。
你只能引用输入中列出的 evidence_id 和 policy chunk_id，不得编造事实、制度或编号。
风险概率由结构化模型提供，你不得修改或重新计算。
所有建议仅为候选建议，execution_status 必须为 PENDING_HUMAN_REVIEW。
suggest_type 只能是 rectify、observe、alert；suggest_priority 只能是 HIGH、MEDIUM、LOW。
不得建议自动处罚、自动停服、自动解约或绕过人工复核。
材料不足时必须在说明中明确指出，不得猜测。"""


def _fallback_action(probability: float, *, reason: str) -> CandidateAction:
    suggest_type = "alert" if probability >= 0.5 else "observe"
    priority = "HIGH" if probability >= 0.75 else "MEDIUM" if probability >= 0.5 else "LOW"
    return CandidateAction(
        suggest_type=suggest_type,
        suggest_content=f"规则回退建议：{reason}。请业务人员结合已核验证据进行人工复核。",
        suggest_priority=priority,
    )


def _canonical_id(value: str) -> str:
    return value.translate(HYPHEN_TRANSLATION).strip()


def _align_identifiers(advisory: AdvisoryResult, state: dict) -> None:
    """Restore visually equivalent hyphen variants to the exact supplied identifier."""
    allowed_evidence = [
        item["evidence_id"] for item in state.get("evidence_result", {}).get("evidence_items", [])
    ]
    allowed_policy = [item["chunk_id"] for item in state.get("policy_context", [])]

    def align(references: list[str], allowed: list[str]) -> list[str]:
        canonical = {_canonical_id(item): item for item in allowed}
        return [canonical.get(_canonical_id(item), item) for item in references]

    advisory.evidence_ids = align(advisory.evidence_ids, allowed_evidence)
    advisory.policy_chunk_ids = align(advisory.policy_chunk_ids, allowed_policy)


def _validate_grounding(advisory: AdvisoryResult, state: dict) -> None:
    allowed_evidence = {
        item["evidence_id"] for item in state.get("evidence_result", {}).get("evidence_items", [])
    }
    allowed_policy = {item["chunk_id"] for item in state.get("policy_context", [])}
    unknown_evidence = set(advisory.evidence_ids) - allowed_evidence
    unknown_policy = set(advisory.policy_chunk_ids) - allowed_policy
    if unknown_evidence or unknown_policy:
        raise ValueError(
            f"LLM cited identifiers outside supplied context: evidence={sorted(unknown_evidence)}, "
            f"policy={sorted(unknown_policy)}"
        )


def decision_node(state: dict) -> dict:
    if state.get("evidence_result", {}).get("status") != "PASS":
        return {
            "errors": ["Evidence Gate blocked Decision Agent"],
            "audit_trace": trace("DecisionAgent", "BLOCKED", detail="evidence insufficient"),
        }

    probability = float(state.get("prediction", {}).get("upgrade_probability", 0.0))
    live_llm = bool(state.get("enable_live_llm", False))
    policy_context = state.get("policy_context", [])
    if not live_llm:
        action = _fallback_action(probability, reason="当前未启用大模型")
        return {
            "candidate_actions": [action.model_dump()],
            "llm_advisory": {"status": "DISABLED", "provider": "none"},
            "audit_trace": trace("DecisionAgent", "PASS", detail="deterministic fallback; live_llm=false"),
        }
    if not policy_context:
        action = _fallback_action(probability, reason="未检索到已批准的制度依据")
        return {
            "candidate_actions": [action.model_dump()],
            "llm_advisory": {"status": "FALLBACK", "provider": "none", "reason": "NO_APPROVED_POLICY"},
            "errors": ["No approved policy context; deterministic fallback used"],
            "audit_trace": trace("DecisionAgent", "DEGRADED", detail="no approved policy context"),
        }

    payload = {
        "supplier_id": state["supplier_id"],
        "current_week": state["current_week"],
        "prediction": state.get("prediction", {}),
        "risk_components": state.get("risk_components", {}),
        "risk_trend": state.get("risk_trend", {}),
        "verified_evidence": state.get("evidence_result", {}).get("evidence_items", []),
        "approved_policy_context": policy_context,
    }
    settings = get_settings()
    try:
        advisory = build_llm_client(settings).invoke(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False),
            response_model=AdvisoryResult,
        )
        _align_identifiers(advisory, state)
        _validate_grounding(advisory, state)
        return {
            "candidate_actions": [item.model_dump() for item in advisory.candidate_actions],
            "llm_advisory": {
                "status": "SUCCESS",
                "provider": settings.llm_provider,
                "model": settings.llm_model,
                **advisory.model_dump(exclude={"candidate_actions"}),
            },
            "audit_trace": trace("DecisionAgent", "PASS", detail=f"grounded_llm={settings.llm_model}"),
        }
    except Exception as exc:
        logger.warning("llm_advisory_fallback error_type=%s", type(exc).__name__)
        action = _fallback_action(probability, reason="大模型暂时不可用或输出未通过校验")
        return {
            "candidate_actions": [action.model_dump()],
            "llm_advisory": {
                "status": "FALLBACK",
                "provider": settings.llm_provider,
                "model": settings.llm_model,
                "reason": type(exc).__name__,
            },
            "errors": ["LLM advisory unavailable; deterministic fallback used"],
            "audit_trace": trace("DecisionAgent", "DEGRADED", detail=f"llm_fallback={type(exc).__name__}"),
        }
