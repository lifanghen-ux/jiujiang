from app.prediction.service import MockPredictionService, TrainedPredictionService


def _components(features: dict[str, float], probability: float = 0.8) -> dict:
    prediction = MockPredictionService(threshold=0.5).predict(
        risk_score=probability * 10,
        event_count_4w=1,
        business_exposure=0.5,
    )
    return TrainedPredictionService.risk_components(object(), features, prediction)


def test_current_red_line_is_separate_from_advance_prediction() -> None:
    result = _components({"severity_max_1w": 4, "has_rectify": 0, "risk_score_delta_1w": 0})

    assert result["risk_mode"] == "SUDDEN_CURRENT"
    assert result["sudden_current"]["red_line_detected"] is True
    assert "不代表提前预测" in result["sudden_current"]["meaning"]


def test_recovery_requires_active_rectification_and_improving_score() -> None:
    result = _components({"severity_max_1w": 0, "has_rectify": 1, "risk_score_delta_1w": -1.2})

    assert result["risk_mode"] == "RECOVERY"
    assert result["recovery"]["improving"] is True
