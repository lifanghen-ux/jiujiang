from app.schemas.contracts import PredictionResult


class MockPredictionService:
    """Deterministic placeholder; replace after member B's CSV review."""

    def __init__(self, *, model_version: str = "mock-untrained", threshold: float = 0.5) -> None:
        self.model_version = model_version
        self.threshold = threshold

    def predict(self, *, risk_score: float, event_count_4w: float, business_exposure: float) -> PredictionResult:
        raw = 0.08 + 0.035 * risk_score + 0.08 * event_count_4w + 0.18 * business_exposure
        probability = min(max(raw, 0.0), 0.99)
        return PredictionResult(
            pred_upgrade_label=int(probability >= self.threshold),
            upgrade_probability=round(probability, 4),
            model_version=self.model_version,
            model_status="MOCK",
        )

