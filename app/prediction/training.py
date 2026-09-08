from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.prediction.calibration import CalibratedRiskModel
from app.prediction.dataset import (
    FEATURE_COLUMNS,
    build_feature_frame,
    load_source_tables,
    rolling_origin_splits,
    temporal_split,
    validate_source_tables,
)


def _json_dump(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_auc(metric, labels: pd.Series | np.ndarray, probabilities: np.ndarray) -> float | None:
    if len(np.unique(labels)) < 2:
        return None
    return float(metric(labels, probabilities))


def _metrics(labels: pd.Series | np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    labels_array = np.asarray(labels, dtype=int)
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(labels_array, predictions, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(labels_array, predictions, zero_division=0)),
        "recall": float(recall_score(labels_array, predictions, zero_division=0)),
        "f1": float(f1_score(labels_array, predictions, zero_division=0)),
        "f2": float(fbeta_score(labels_array, predictions, beta=2, zero_division=0)),
        "alert_rate": float(predictions.mean()),
        "brier_score": float(brier_score_loss(labels_array, probabilities)),
        "roc_auc": _safe_auc(roc_auc_score, labels_array, probabilities),
        "pr_auc": _safe_auc(average_precision_score, labels_array, probabilities),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "rows": int(len(labels_array)),
        "positive_rows": int(labels_array.sum()),
    }


def _select_threshold(labels: pd.Series | np.ndarray, probabilities: np.ndarray) -> float:
    """Select on rolling validation only, prioritising missed-risk reduction with F2."""
    candidates = np.arange(0.01, 0.991, 0.01)
    scored = [
        (
            fbeta_score(labels, probabilities >= threshold, beta=2, zero_division=0),
            precision_score(labels, probabilities >= threshold, zero_division=0),
            -float((probabilities >= threshold).mean()),
            float(threshold),
        )
        for threshold in candidates
    ]
    return max(scored)[3]


def _build_models(positive_weight: float, random_state: int = 42) -> dict[str, object]:
    return {
        "logistic_regression": Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=3,
            max_features="sqrt",
            class_weight="balanced_subsample",
            random_state=random_state,
            n_jobs=-1,
        ),
        "xgboost": XGBClassifier(
            n_estimators=400,
            max_depth=4,
            learning_rate=0.035,
            min_child_weight=3,
            subsample=0.9,
            colsample_bytree=0.9,
            scale_pos_weight=positive_weight,
            random_state=random_state,
            n_jobs=-1,
            eval_metric="logloss",
        ),
    }


def _fresh_model(name: str, labels: pd.Series, random_state: int = 42) -> object:
    positive_weight = float((labels == 0).sum() / max((labels == 1).sum(), 1))
    return _build_models(positive_weight, random_state=random_state)[name]


def _rolling_validation(name: str, features: pd.DataFrame) -> tuple[object, float, dict]:
    pooled_labels: list[int] = []
    pooled_raw_probabilities: list[float] = []
    fold_reports: list[dict] = []
    for fold_number, (fold_name, fold_train, fold_validation) in enumerate(rolling_origin_splits(features), start=1):
        model = _fresh_model(name, fold_train["upgrade_label"], random_state=41 + fold_number)
        model.fit(fold_train[FEATURE_COLUMNS], fold_train["upgrade_label"])
        raw_probability = model.predict_proba(fold_validation[FEATURE_COLUMNS])[:, 1]
        pooled_labels.extend(fold_validation["upgrade_label"].astype(int).tolist())
        pooled_raw_probabilities.extend(raw_probability.astype(float).tolist())
        fold_reports.append(
            {
                "fold": fold_name,
                "train_rows": int(len(fold_train)),
                "validation_rows": int(len(fold_validation)),
                "validation_positive_rows": int(fold_validation["upgrade_label"].sum()),
                "raw_pr_auc": float(average_precision_score(fold_validation["upgrade_label"], raw_probability)),
                "raw_roc_auc": float(roc_auc_score(fold_validation["upgrade_label"], raw_probability)),
            }
        )

    label_array = np.asarray(pooled_labels, dtype=int)
    raw_array = np.asarray(pooled_raw_probabilities, dtype=float)
    calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    calibrator.fit(raw_array, label_array)
    calibrated = np.asarray(calibrator.predict(raw_array), dtype=float)
    threshold = _select_threshold(label_array, calibrated)
    fold_pr_auc = [fold["raw_pr_auc"] for fold in fold_reports]
    report = {
        "folds": fold_reports,
        "mean_raw_pr_auc": float(np.mean(fold_pr_auc)),
        "std_raw_pr_auc": float(np.std(fold_pr_auc)),
        "selection_score": float(np.mean(fold_pr_auc) - 0.25 * np.std(fold_pr_auc)),
        "pooled_calibrated": _metrics(label_array, calibrated, threshold),
    }
    return calibrator, threshold, report


def _scenario_slices(test: pd.DataFrame, probabilities: np.ndarray, threshold: float) -> dict:
    """IDs are used for evaluation slices only and are never model features."""
    scenarios = (
        test["supplier_id"]
        .astype(str)
        .str.extract(r"(ACC|SUD|PER|STA|NOR)", expand=False)
        .fillna("OTHER")
    )
    report: dict[str, dict] = {}
    for scenario in sorted(scenarios.unique()):
        mask = scenarios.eq(scenario).to_numpy()
        report[str(scenario)] = _metrics(test.loc[mask, "upgrade_label"], probabilities[mask], threshold)
    return report


def _save_shap_report(model: object, sample: pd.DataFrame, report_path: Path) -> list[dict]:
    import shap

    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(sample)
    if isinstance(values, list):
        values = values[-1]
    importance = np.abs(np.asarray(values)).mean(axis=0)
    records = [
        {"feature": feature, "mean_abs_shap": float(value)}
        for feature, value in sorted(
            zip(sample.columns, importance, strict=True), key=lambda item: item[1], reverse=True
        )
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(report_path, index=False, encoding="utf-8-sig")
    return records


def _incumbent_metrics(model_dir: Path, report_dir: Path, test: pd.DataFrame) -> dict | None:
    model_path = model_dir / "champion.joblib"
    metadata_path = report_dir / "model_metadata.json"
    if not model_path.exists() or not metadata_path.exists():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        columns = metadata["feature_columns"]
        if any(column not in test.columns for column in columns):
            return None
        model = joblib.load(model_path)
        probabilities = model.predict_proba(test[columns])[:, 1]
        return _metrics(test["upgrade_label"], probabilities, float(metadata["champion_threshold"]))
    except (KeyError, ValueError, TypeError, OSError):
        return None


def _promotion_decision(candidate: dict, incumbent: dict | None, test_positive_rate: float) -> dict:
    if incumbent is None:
        gates = {
            "pr_auc_above_random": candidate["pr_auc"] >= test_positive_rate,
            "recall_at_least_10_percent": candidate["recall"] >= 0.10,
            "precision_above_base_rate": candidate["precision"] >= test_positive_rate,
        }
    else:
        gates = {
            "pr_auc_not_materially_worse": candidate["pr_auc"] >= incumbent["pr_auc"] - 0.005,
            "recall_not_materially_worse": candidate["recall"] >= incumbent["recall"] - 0.02,
            "precision_at_least_80_percent_of_incumbent": candidate["precision"] >= incumbent["precision"] * 0.8,
        }
    return {"promoted": all(gates.values()), "gates": gates, "incumbent_test": incumbent}


def _promote_candidate(
    *,
    model_dir: Path,
    report_dir: Path,
    candidate_metrics: dict,
    candidate_metadata: dict,
    decision: dict,
) -> dict:
    created_at = datetime.now(timezone.utc)
    version = created_at.strftime("%Y%m%dT%H%M%SZ")
    rollback_model_path: str | None = None
    rollback_metadata_path: str | None = None
    rollback_metrics_path: str | None = None
    rollback_shap_csv_path: str | None = None
    rollback_shap_json_path: str | None = None
    if decision["promoted"]:
        rollback_model_dir = model_dir / "rollback"
        rollback_report_dir = report_dir / "rollback"
        rollback_model_dir.mkdir(parents=True, exist_ok=True)
        rollback_report_dir.mkdir(parents=True, exist_ok=True)
        if (model_dir / "champion.joblib").exists():
            destination = rollback_model_dir / f"champion_{version}.joblib"
            shutil.copy2(model_dir / "champion.joblib", destination)
            rollback_model_path = str(destination)
        if (report_dir / "model_metadata.json").exists():
            destination = rollback_report_dir / f"model_metadata_{version}.json"
            shutil.copy2(report_dir / "model_metadata.json", destination)
            rollback_metadata_path = str(destination)
        if (report_dir / "model_metrics.json").exists():
            destination = rollback_report_dir / f"model_metrics_{version}.json"
            shutil.copy2(report_dir / "model_metrics.json", destination)
            rollback_metrics_path = str(destination)
        if (report_dir / "shap_global.csv").exists():
            destination = rollback_report_dir / f"shap_global_{version}.csv"
            shutil.copy2(report_dir / "shap_global.csv", destination)
            rollback_shap_csv_path = str(destination)
        if (report_dir / "shap_top_features.json").exists():
            destination = rollback_report_dir / f"shap_top_features_{version}.json"
            shutil.copy2(report_dir / "shap_top_features.json", destination)
            rollback_shap_json_path = str(destination)
        shutil.copy2(model_dir / "candidate_champion.joblib", model_dir / "champion.joblib")
        _json_dump(report_dir / "model_metrics.json", candidate_metrics)
        promoted_metadata = {**candidate_metadata, "model_status": "PROMOTED_SIMULATION"}
        _json_dump(report_dir / "model_metadata.json", promoted_metadata)

    registry_path = report_dir / "model_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else []
    entry = {
        "version": version,
        "created_at": created_at.isoformat(),
        "candidate_model": candidate_metadata["champion_model"],
        "status": "PROMOTED" if decision["promoted"] else "REJECTED_KEEP_INCUMBENT",
        "promotion_gates": decision["gates"],
        "candidate_test": candidate_metrics[candidate_metadata["champion_model"]]["test"],
        "incumbent_test": decision["incumbent_test"],
        "rollback_model_path": rollback_model_path,
        "rollback_metadata_path": rollback_metadata_path,
        "rollback_metrics_path": rollback_metrics_path,
        "rollback_shap_csv_path": rollback_shap_csv_path,
        "rollback_shap_json_path": rollback_shap_json_path,
        "rollback_status": "AVAILABLE" if rollback_model_path else "NOT_AVAILABLE",
    }
    registry.append(entry)
    _json_dump(registry_path, registry)
    return entry


def rollback_latest(*, artifact_dir: Path = Path("artifacts")) -> dict:
    report_dir = artifact_dir / "reports"
    model_dir = artifact_dir / "models"
    registry_path = report_dir / "model_registry.json"
    if not registry_path.exists():
        raise FileNotFoundError("No model registry exists; nothing can be rolled back")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    target = next(
        (
            entry
            for entry in reversed(registry)
            if entry.get("status") == "PROMOTED"
            and entry.get("rollback_status") == "AVAILABLE"
            and entry.get("rollback_shap_csv_path")
            and entry.get("rollback_shap_json_path")
        ),
        None,
    )
    if target is None:
        raise FileNotFoundError("No promoted model with an available rollback snapshot")
    paths = {
        "model": Path(target["rollback_model_path"]),
        "metadata": Path(target["rollback_metadata_path"]),
        "metrics": Path(target["rollback_metrics_path"]),
        "shap_csv": Path(target["rollback_shap_csv_path"]),
        "shap_json": Path(target["rollback_shap_json_path"]),
    }
    if not all(path.exists() for path in paths.values()):
        raise FileNotFoundError("Rollback snapshot is incomplete")
    shutil.copy2(paths["model"], model_dir / "champion.joblib")
    shutil.copy2(paths["metadata"], report_dir / "model_metadata.json")
    shutil.copy2(paths["metrics"], report_dir / "model_metrics.json")
    shutil.copy2(paths["shap_csv"], report_dir / "shap_global.csv")
    shutil.copy2(paths["shap_json"], report_dir / "shap_top_features.json")
    target["rollback_status"] = "EXECUTED"
    target["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
    _json_dump(registry_path, registry)
    return {"status": "ROLLED_BACK", "restored_version_before": target["version"]}


def train_all(
    *,
    source_dir: Path = Path("data/source"),
    artifact_dir: Path = Path("artifacts"),
) -> dict:
    tables = load_source_tables(source_dir)
    quality = validate_source_tables(tables)
    features = build_feature_frame(tables)
    train, validation, test, tail = temporal_split(features)

    report_dir = artifact_dir / "reports"
    model_dir = artifact_dir / "models"
    feature_dir = artifact_dir / "features"
    report_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    feature_dir.mkdir(parents=True, exist_ok=True)
    features.to_csv(feature_dir / "model_features.csv", index=False, encoding="utf-8-sig")
    _json_dump(report_dir / "data_quality.json", quality)

    split_summary = {
        name: {
            "week_range": [int(part["week"].min()), int(part["week"].max())],
            "rows": int(len(part)),
            "positive_rows": int(part["upgrade_label"].sum()),
            "positive_rate": float(part["upgrade_label"].mean()),
        }
        for name, part in (("train", train), ("validation", validation), ("test", test), ("tail_not_scored", tail))
    }

    development = features[features["week"] <= 34].copy()
    rolling_results: dict[str, dict] = {}
    calibrators: dict[str, object] = {}
    thresholds: dict[str, float] = {}
    for name in _build_models(1.0):
        calibrator, threshold, rolling_report = _rolling_validation(name, features)
        calibrators[name] = calibrator
        thresholds[name] = threshold
        rolling_results[name] = rolling_report

    champion_name = max(rolling_results, key=lambda name: rolling_results[name]["selection_score"])
    results: dict[str, dict] = {}
    fitted_estimators: dict[str, object] = {}
    calibrated_models: dict[str, CalibratedRiskModel] = {}
    for name in rolling_results:
        estimator = _fresh_model(name, development["upgrade_label"])
        estimator.fit(development[FEATURE_COLUMNS], development["upgrade_label"])
        calibrated_model = CalibratedRiskModel(estimator=estimator, calibrator=calibrators[name])
        test_probability = calibrated_model.predict_proba(test[FEATURE_COLUMNS])[:, 1]
        results[name] = {
            "rolling_validation": rolling_results[name],
            "test": _metrics(test["upgrade_label"], test_probability, thresholds[name]),
            "test_scenarios": _scenario_slices(test, test_probability, thresholds[name]),
        }
        fitted_estimators[name] = estimator
        calibrated_models[name] = calibrated_model
        joblib.dump(calibrated_model, model_dir / f"candidate_{name}.joblib")

    joblib.dump(calibrated_models[champion_name], model_dir / "candidate_champion.joblib")
    shap_records = _save_shap_report(
        fitted_estimators["xgboost"],
        test[FEATURE_COLUMNS].sample(n=min(500, len(test)), random_state=42),
        report_dir / "candidate_shap_global.csv",
    )

    candidate_metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_scope": "200 simulated suppliers, 52 weeks each",
        "feature_columns": FEATURE_COLUMNS,
        "split_summary": split_summary,
        "selection_metric": "rolling_mean_pr_auc_minus_0.25_std",
        "threshold_metric": "rolling_validation_f2",
        "calibration": "isotonic_on_pooled_rolling_out_of_time_predictions",
        "champion_model": champion_name,
        "champion_threshold": thresholds[champion_name],
        "model_status": "CANDIDATE_SIMULATION",
        "risk_separation": {
            "gradual_upgrade": "machine-learning probability for the next three weeks",
            "sudden_current": "same-week severity red-line rule; not claimed as advance prediction",
            "recovery": "rectification-active plus improving risk trajectory",
        },
        "leakage_controls": [
            "Only current and historical weeks are used as model features",
            "Supplier scenario prefixes are evaluation slices only and never features",
            "The frozen weeks 35-44 test set is used only for release gates, not threshold tuning",
        ],
        "limitations": [
            "Synthetic competition data only",
            "Sudden samples lack observable precursor fields and cannot be reliably predicted in advance",
            "Weeks after 44 are excluded from performance scoring because they contain no positive labels",
            "Formal API, business thresholds and rollback authority remain pending team review",
        ],
    }
    _json_dump(report_dir / "candidate_model_metrics.json", results)
    _json_dump(report_dir / "candidate_model_metadata.json", candidate_metadata)
    _json_dump(report_dir / "candidate_shap_top_features.json", shap_records)

    incumbent = _incumbent_metrics(model_dir, report_dir, test)
    candidate_test = results[champion_name]["test"]
    decision = _promotion_decision(candidate_test, incumbent, float(test["upgrade_label"].mean()))
    registry_entry = _promote_candidate(
        model_dir=model_dir,
        report_dir=report_dir,
        candidate_metrics=results,
        candidate_metadata=candidate_metadata,
        decision=decision,
    )
    if decision["promoted"]:
        shutil.copy2(report_dir / "candidate_shap_global.csv", report_dir / "shap_global.csv")
        _json_dump(report_dir / "shap_top_features.json", shap_records)

    return {
        "quality": quality,
        "candidate_metrics": results,
        "candidate_metadata": candidate_metadata,
        "promotion": registry_entry,
    }
