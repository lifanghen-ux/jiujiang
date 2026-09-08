import json
from pathlib import Path

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


class TrainedPredictionService:
    def __init__(self, *, model_path: Path, metadata_path: Path) -> None:
        import joblib

        if not model_path.exists() or not metadata_path.exists():
            raise FileNotFoundError("Trained model artifact or metadata is missing; run the training command first")
        self.model = joblib.load(model_path)
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.feature_columns = self.metadata["feature_columns"]
        self.threshold = float(self.metadata["champion_threshold"])

    def predict_features(self, features: dict[str, float]) -> PredictionResult:
        import pandas as pd

        missing = [name for name in self.feature_columns if name not in features]
        if missing:
            raise ValueError(f"Missing model features: {missing}")
        frame = pd.DataFrame([{name: features[name] for name in self.feature_columns}])
        probability = float(self.model.predict_proba(frame)[:, 1][0])
        return PredictionResult(
            pred_upgrade_label=int(probability >= self.threshold),
            upgrade_probability=round(probability, 6),
            model_version=f"{self.metadata['champion_model']}-simulation-v0.1",
            model_status="TRAINED",
        )

    def risk_components(self, features: dict[str, float], prediction: PredictionResult) -> dict:
        current_max_severity = float(features.get("severity_max_1w", 0.0))
        rectify_active = bool(float(features.get("has_rectify", 0.0)) >= 0.5)
        improving = rectify_active and float(features.get("risk_score_delta_1w", 0.0)) < 0
        red_line = current_max_severity >= 4.0
        if red_line:
            mode = "SUDDEN_CURRENT"
        elif improving:
            mode = "RECOVERY"
        elif prediction.pred_upgrade_label:
            mode = "GRADUAL_WARNING"
        else:
            mode = "STABLE"
        return {
            "risk_mode": mode,
            "gradual_upgrade": {
                "pred_upgrade_label": prediction.pred_upgrade_label,
                "upgrade_probability": prediction.upgrade_probability,
            },
            "sudden_current": {
                "red_line_detected": red_line,
                "current_max_severity": current_max_severity,
                "meaning": "当周红线检测，不代表提前预测",
            },
            "recovery": {
                "rectify_active": rectify_active,
                "improving": improving,
                "risk_score_delta_1w": float(features.get("risk_score_delta_1w", 0.0)),
            },
        }
