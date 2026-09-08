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
        risk_components = service.risk_components(features, prediction)
    else:
        service = MockPredictionService(model_version="mock-untrained")
        prediction = service.predict(
            risk_score=float(context.get("risk_score", 0.0)),
            event_count_4w=features["event_count_4w"],
            business_exposure=float(context.get("business_exposure", 0.0)),
        )
        prediction_source = "MOCK_FALLBACK"
        risk_components = {
            "risk_mode": "GRADUAL_WARNING" if prediction.pred_upgrade_label else "STABLE",
            "gradual_upgrade": {
                "pred_upgrade_label": prediction.pred_upgrade_label,
                "upgrade_probability": prediction.upgrade_probability,
            },
            "sudden_current": {
                "red_line_detected": False,
                "current_max_severity": 0.0,
                "meaning": "Mock 模式不执行红线检测",
            },
            "recovery": {
                "rectify_active": False,
                "improving": False,
                "risk_score_delta_1w": 0.0,
            },
        }
    evidence_ids = [event["evidence_id"] for event in visible[-5:]]
    trend_type = {
        "SUDDEN_CURRENT": "SUDDEN_JUMP",
        "RECOVERY": "FALLING",
        "GRADUAL_WARNING": "RISING",
        "STABLE": "STEADY",
    }[risk_components["risk_mode"]]
    trend = TrendResult(
        trend_type=trend_type,
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
        "risk_components": risk_components,
        "risk_trend": trend.model_dump(),
        "audit_trace": trace("DynamicPredictionAgent", "PASS", detail=f"prediction_source={prediction_source}"),
    }
