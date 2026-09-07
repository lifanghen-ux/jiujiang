from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.prediction.dataset import (
    FEATURE_COLUMNS,
    build_feature_frame,
    load_source_tables,
    temporal_split,
    validate_source_tables,
)


def _json_dump(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _metrics(labels: pd.Series, probabilities: np.ndarray, threshold: float) -> dict:
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "pr_auc": float(average_precision_score(labels, probabilities)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "rows": int(len(labels)),
        "positive_rows": int(labels.sum()),
    }


def _select_threshold(labels: pd.Series, probabilities: np.ndarray) -> float:
    candidates = np.arange(0.05, 0.951, 0.01)
    scored = [
        (
            f1_score(labels, probabilities >= threshold, zero_division=0),
            recall_score(labels, probabilities >= threshold, zero_division=0),
            -abs(float(threshold) - 0.5),
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
            n_estimators=300,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            random_state=random_state,
            n_jobs=-1,
        ),
        "xgboost": XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.04,
            subsample=0.9,
            colsample_bytree=0.9,
            scale_pos_weight=positive_weight,
            random_state=random_state,
            n_jobs=-1,
            eval_metric="logloss",
        ),
    }


def _save_shap_report(model: object, sample: pd.DataFrame, report_path: Path) -> list[dict]:
    import shap

    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(sample)
    if isinstance(values, list):
        values = values[-1]
    importance = np.abs(np.asarray(values)).mean(axis=0)
    records = [
        {"feature": feature, "mean_abs_shap": float(value)}
        for feature, value in sorted(zip(sample.columns, importance, strict=True), key=lambda item: item[1], reverse=True)
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(report_path, index=False, encoding="utf-8-sig")
    return records


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

    x_train = train[FEATURE_COLUMNS]
    y_train = train["upgrade_label"]
    x_validation = validation[FEATURE_COLUMNS]
    y_validation = validation["upgrade_label"]
    x_test = test[FEATURE_COLUMNS]
    y_test = test["upgrade_label"]
    positive_weight = float((y_train == 0).sum() / max((y_train == 1).sum(), 1))

    results: dict[str, dict] = {}
    fitted: dict[str, object] = {}
    for name, model in _build_models(positive_weight).items():
        model.fit(x_train, y_train)
        validation_probability = model.predict_proba(x_validation)[:, 1]
        threshold = _select_threshold(y_validation, validation_probability)
        test_probability = model.predict_proba(x_test)[:, 1]
        results[name] = {
            "validation": _metrics(y_validation, validation_probability, threshold),
            "test": _metrics(y_test, test_probability, threshold),
        }
        fitted[name] = model
        joblib.dump(model, model_dir / f"{name}.joblib")

    champion_name = max(results, key=lambda name: results[name]["validation"]["pr_auc"])
    champion = fitted[champion_name]
    joblib.dump(champion, model_dir / "champion.joblib")
    shap_records = _save_shap_report(
        fitted["xgboost"],
        x_test.sample(n=min(500, len(x_test)), random_state=42),
        report_dir / "shap_global.csv",
    )

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_scope": "200 simulated suppliers, 52 weeks each",
        "feature_columns": FEATURE_COLUMNS,
        "split_summary": split_summary,
        "selection_metric": "validation_pr_auc",
        "champion_model": champion_name,
        "champion_threshold": results[champion_name]["validation"]["threshold"],
        "model_status": "TRAINED_SIMULATION",
        "limitations": [
            "Synthetic competition data only",
            "Weeks after 44 are excluded from performance scoring because they contain no positive labels",
            "Formal API and risk-level thresholds remain pending team review",
        ],
    }
    _json_dump(report_dir / "model_metrics.json", results)
    _json_dump(report_dir / "model_metadata.json", metadata)
    _json_dump(report_dir / "shap_top_features.json", shap_records)
    return {"quality": quality, "metrics": results, "metadata": metadata}

