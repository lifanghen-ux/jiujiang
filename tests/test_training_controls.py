import json
from pathlib import Path

from app.prediction.training import _promotion_decision, rollback_latest


def test_worse_candidate_is_not_promoted() -> None:
    incumbent = {"pr_auc": 0.20, "recall": 0.50, "precision": 0.30}
    candidate = {"pr_auc": 0.10, "recall": 0.20, "precision": 0.10}

    decision = _promotion_decision(candidate, incumbent, test_positive_rate=0.02)

    assert decision["promoted"] is False
    assert not all(decision["gates"].values())


def test_rollback_restores_complete_snapshot(tmp_path: Path) -> None:
    model_dir = tmp_path / "models"
    report_dir = tmp_path / "reports"
    snapshot_dir = tmp_path / "snapshot"
    model_dir.mkdir()
    report_dir.mkdir()
    snapshot_dir.mkdir()

    current = {
        model_dir / "champion.joblib": "new model",
        report_dir / "model_metadata.json": "new metadata",
        report_dir / "model_metrics.json": "new metrics",
        report_dir / "shap_global.csv": "new shap csv",
        report_dir / "shap_top_features.json": "new shap json",
    }
    snapshot = {
        "rollback_model_path": snapshot_dir / "old.joblib",
        "rollback_metadata_path": snapshot_dir / "old_metadata.json",
        "rollback_metrics_path": snapshot_dir / "old_metrics.json",
        "rollback_shap_csv_path": snapshot_dir / "old_shap.csv",
        "rollback_shap_json_path": snapshot_dir / "old_shap.json",
    }
    for path, content in current.items():
        path.write_text(content, encoding="utf-8")
    for path in snapshot.values():
        path.write_text(f"old {path.suffix}", encoding="utf-8")

    registry = [
        {
            "version": "test-v1",
            "status": "PROMOTED",
            "rollback_status": "AVAILABLE",
            **{key: str(path) for key, path in snapshot.items()},
        }
    ]
    (report_dir / "model_registry.json").write_text(json.dumps(registry), encoding="utf-8")

    result = rollback_latest(artifact_dir=tmp_path)

    assert result["status"] == "ROLLED_BACK"
    assert (model_dir / "champion.joblib").read_text(encoding="utf-8") == "old .joblib"
    updated = json.loads((report_dir / "model_registry.json").read_text(encoding="utf-8"))
    assert updated[0]["rollback_status"] == "EXECUTED"
