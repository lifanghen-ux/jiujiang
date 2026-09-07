from app.agents.helpers import trace
from app.prediction.features import rolling_event_features
from app.config import get_settings
from app.prediction.service import MockPredictionService, TrainedPredictionService
from app.schemas.contracts import TrendResult


def dynamic_prediction_node(state: dict) -> dict:
    supplier_id = state["supplier_id"]
    current_week = int(state["current_week"])
    visible = state.get("visible_events", [])
    context = state.get("business_context", {})
    features = rolling_event_features(visible, supplier_id=supplier_id, week=current_week, window=4)
    model_features = state.get("model_features")
    settings = get_settings()
    if model_features and settings.model_artifact_path.exists() and settings.model_metadata_path.exists():
        service = TrainedPredictionService(
            model_path=settings.model_artifact_path,
            metadata_path=settings.model_metadata_path,
        )
        prediction = service.predict_features(model_features)
        prediction_source = "TRAINED_SIMULATION_MODEL"
        features = {name: float(model_features[name]) for name in service.feature_columns}
    else:
        service = MockPredictionService(model_version="mock-untrained")
        prediction = service.predict(
            risk_score=float(context.get("risk_score", 0.0)),
            event_count_4w=features["event_count_4w"],
            business_exposure=float(context.get("business_exposure", 0.0)),
        )
        prediction_source = "MOCK_FALLBACK"
    evidence_ids = [event["evidence_id"] for event in visible[-5:]]
    trend = TrendResult(
        trend_type="RISING" if prediction.pred_upgrade_label else "STEADY",
        trend_desc=(
            "模拟数据训练模型给出的测试趋势，不代表正式研判。"
            if prediction_source == "TRAINED_SIMULATION_MODEL"
            else "Mock 规则与历史事件生成的测试趋势，不代表正式研判。"
        ),
        trend_support_evidence_ids=evidence_ids,
    )
    return {
        "features": features,
        "prediction": prediction.model_dump(),
        "prediction_source": prediction_source,
        "risk_trend": trend.model_dump(),
        "audit_trace": trace("DynamicPredictionAgent", "PASS", detail=f"prediction_source={prediction_source}"),
    }
