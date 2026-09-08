from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.common.errors import DataValidationError

SOURCE_SCHEMAS = {
    "suppliers.csv": ["supplier_id", "name"],
    "contracts.csv": [
        "contract_id",
        "supplier_id",
        "name",
        "start_week",
        "end_week",
        "contract_importance",
    ],
    "projects.csv": ["project_id", "contract_id", "project_stage"],
    "bank_systems.csv": ["system_id", "system_name", "system_level", "project_id"],
    "risk_events.csv": [
        "evidence_id",
        "supplier_id",
        "event_category",
        "event_subtype",
        "event_severity",
        "event_week",
        "source_type",
    ],
    "rectify_records.csv": ["rectify_id", "supplier_id", "start_week", "end_week"],
    "weekly_snapshot.csv": [
        "supplier_id",
        "week",
        "event_count",
        "risk_score",
        "has_rectify",
        "business_exposure",
        "upgrade_label",
    ],
}

FEATURE_COLUMNS = [
    "risk_score",
    "event_count_1w",
    "event_count_4w",
    "event_count_8w",
    "event_count_lifetime",
    "event_count_acceleration_4w",
    "severity_max_1w",
    "severity_sum_4w",
    "severity_sum_8w",
    "severity_sum_lifetime",
    "severity_max_4w",
    "high_severity_count_4w",
    "risk_score_delta_1w",
    "risk_score_slope_4w",
    "risk_score_mean_4w",
    "risk_score_mean_8w",
    "category_count_4w",
    "cross_category_count_4w",
    "weeks_since_last_event",
    "has_rectify",
    "rectify_weeks_elapsed",
    "rectify_weeks_remaining",
    "business_exposure",
    "system_level_score",
    "contract_importance_score",
    "project_stage_code",
    "category_performance_4w",
    "category_personnel_4w",
    "category_security_4w",
    "category_operation_4w",
    "category_compliance_4w",
    "category_sentiment_4w",
]

CATEGORY_FEATURES = {
    "履约": "category_performance_4w",
    "人员": "category_personnel_4w",
    "安全": "category_security_4w",
    "经营": "category_operation_4w",
    "合规": "category_compliance_4w",
    "舆情": "category_sentiment_4w",
}


def load_source_tables(source_dir: Path) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for filename, expected_columns in SOURCE_SCHEMAS.items():
        path = source_dir / filename
        if not path.exists():
            raise DataValidationError(f"Missing source file: {filename}")
        frame = pd.read_csv(path, encoding="utf-8-sig")
        if frame.columns.tolist() != expected_columns:
            raise DataValidationError(
                f"{filename} columns differ: expected={expected_columns}, actual={frame.columns.tolist()}"
            )
        tables[filename] = frame
    return tables


def _duplicate_count(frame: pd.DataFrame, columns: list[str]) -> int:
    return int(frame.duplicated(columns).sum())


def validate_source_tables(tables: dict[str, pd.DataFrame]) -> dict:
    suppliers = tables["suppliers.csv"]
    contracts = tables["contracts.csv"]
    projects = tables["projects.csv"]
    systems = tables["bank_systems.csv"]
    events = tables["risk_events.csv"]
    rectifies = tables["rectify_records.csv"]
    weekly = tables["weekly_snapshot.csv"].copy()

    duplicate_counts = {
        "supplier_id": _duplicate_count(suppliers, ["supplier_id"]),
        "contract_id": _duplicate_count(contracts, ["contract_id"]),
        "project_id": _duplicate_count(projects, ["project_id"]),
        "system_id": _duplicate_count(systems, ["system_id"]),
        "evidence_id": _duplicate_count(events, ["evidence_id"]),
        "rectify_id": _duplicate_count(rectifies, ["rectify_id"]),
        "supplier_week": _duplicate_count(weekly, ["supplier_id", "week"]),
    }
    if any(duplicate_counts.values()):
        raise DataValidationError(f"Duplicate keys detected: {duplicate_counts}")

    supplier_ids = set(suppliers["supplier_id"])
    foreign_key_errors = {
        "contracts.supplier_id": sorted(set(contracts["supplier_id"]) - supplier_ids),
        "events.supplier_id": sorted(set(events["supplier_id"]) - supplier_ids),
        "rectifies.supplier_id": sorted(set(rectifies["supplier_id"]) - supplier_ids),
        "weekly.supplier_id": sorted(set(weekly["supplier_id"]) - supplier_ids),
        "projects.contract_id": sorted(set(projects["contract_id"]) - set(contracts["contract_id"])),
        "systems.project_id": sorted(set(systems["project_id"]) - set(projects["project_id"])),
    }
    if any(foreign_key_errors.values()):
        raise DataValidationError(f"Broken foreign keys detected: {foreign_key_errors}")

    weekly["week"] = weekly["week"].astype(int)
    weekly["upgrade_label"] = weekly["upgrade_label"].astype(int)
    events["event_week"] = events["event_week"].astype(int)
    events["event_severity"] = events["event_severity"].astype(int)

    counts = weekly.groupby("supplier_id")["week"].nunique()
    if len(counts) != len(suppliers) or not counts.eq(52).all():
        raise DataValidationError("Every supplier must have exactly 52 unique weekly snapshots")
    if not weekly["week"].between(1, 52).all():
        raise DataValidationError("weekly_snapshot.week must be within 1..52")
    if not events["event_week"].between(1, 52).all():
        raise DataValidationError("risk_events.event_week must be within 1..52")
    if not events["event_severity"].between(0, 5).all():
        raise DataValidationError("risk_events.event_severity must be within 0..5")
    if not weekly["upgrade_label"].isin([0, 1]).all():
        raise DataValidationError("upgrade_label must be binary")

    consistency = recompute_consistency(tables)
    if any(consistency.values()):
        raise DataValidationError(f"Source calculations are inconsistent: {consistency}")

    label_counts = weekly["upgrade_label"].value_counts().sort_index().to_dict()
    return {
        "status": "PASS",
        "row_counts": {name: int(len(frame)) for name, frame in tables.items()},
        "duplicate_counts": duplicate_counts,
        "foreign_key_error_counts": {key: len(value) for key, value in foreign_key_errors.items()},
        "weekly_rows_per_supplier": sorted(counts.unique().astype(int).tolist()),
        "label_counts": {str(key): int(value) for key, value in label_counts.items()},
        "positive_rate": float(weekly["upgrade_label"].mean()),
        "event_categories": sorted(events["event_category"].unique().tolist()),
        "calculation_mismatches": consistency,
    }


def recompute_consistency(tables: dict[str, pd.DataFrame]) -> dict[str, int]:
    events = tables["risk_events.csv"].copy()
    rectifies = tables["rectify_records.csv"].copy()
    weekly = tables["weekly_snapshot.csv"].copy()
    events["event_week"] = events["event_week"].astype(int)
    events["event_severity"] = events["event_severity"].astype(int)
    rectifies["start_week"] = rectifies["start_week"].astype(int)
    rectifies["end_week"] = rectifies["end_week"].astype(int)

    event_groups = {supplier: group for supplier, group in events.groupby("supplier_id")}
    rectify_groups = {supplier: group for supplier, group in rectifies.groupby("supplier_id")}
    mismatches = {"event_count": 0, "risk_score": 0, "has_rectify": 0, "upgrade_label": 0}

    for supplier_id, group in weekly.groupby("supplier_id", sort=False):
        supplier_events = event_groups.get(supplier_id, events.iloc[0:0])
        supplier_rectifies = rectify_groups.get(supplier_id, rectifies.iloc[0:0])
        current_risk = 0.0
        for row in group.sort_values("week").itertuples(index=False):
            week_events = supplier_events[supplier_events["event_week"] == int(row.week)]
            current_risk += float(week_events["event_severity"].sum())
            in_rectify = bool(
                ((supplier_rectifies["start_week"] <= int(row.week)) & (supplier_rectifies["end_week"] >= int(row.week))).any()
            )
            if in_rectify:
                current_risk = max(0.0, current_risk - 1.2)
            future = supplier_events[
                supplier_events["event_week"].isin([int(row.week) + 1, int(row.week) + 2, int(row.week) + 3])
            ]
            expected_label = int((future["event_severity"] >= 3).any())
            mismatches["event_count"] += int(int(row.event_count) != len(week_events))
            mismatches["risk_score"] += int(round(float(row.risk_score), 2) != round(current_risk, 2))
            mismatches["has_rectify"] += int(str(row.has_rectify).lower() != str(in_rectify).lower())
            mismatches["upgrade_label"] += int(int(row.upgrade_label) != expected_label)
    return mismatches


def _rolling_slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    return float(np.polyfit(np.arange(len(values), dtype=float), values, 1)[0])


def build_feature_frame(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    weekly = tables["weekly_snapshot.csv"].copy()
    events = tables["risk_events.csv"].copy()
    contracts = tables["contracts.csv"].copy()
    projects = tables["projects.csv"].copy()
    systems = tables["bank_systems.csv"].copy()
    rectifies = tables["rectify_records.csv"].copy()
    weekly["week"] = weekly["week"].astype(int)
    weekly["event_count"] = weekly["event_count"].astype(float)
    weekly["risk_score"] = weekly["risk_score"].astype(float)
    weekly["business_exposure"] = weekly["business_exposure"].astype(float)
    weekly["upgrade_label"] = weekly["upgrade_label"].astype(int)
    weekly["has_rectify"] = weekly["has_rectify"].astype(str).str.lower().eq("true").astype(int)
    weekly = weekly.sort_values(["supplier_id", "week"]).reset_index(drop=True)

    events["event_week"] = events["event_week"].astype(int)
    events["event_severity"] = events["event_severity"].astype(float)
    event_week = (
        events.groupby(["supplier_id", "event_week"], as_index=False)
        .agg(
            severity_sum=("event_severity", "sum"),
            severity_max=("event_severity", "max"),
            high_severity_count=("event_severity", lambda values: int((values >= 3).sum())),
        )
        .rename(columns={"event_week": "week"})
    )
    frame = weekly.merge(event_week, on=["supplier_id", "week"], how="left")
    frame[["severity_sum", "severity_max", "high_severity_count"]] = frame[
        ["severity_sum", "severity_max", "high_severity_count"]
    ].fillna(0.0)
    frame["event_count_1w"] = frame["event_count"]
    frame["severity_max_1w"] = frame["severity_max"]

    grouped = frame.groupby("supplier_id", group_keys=False, sort=False)
    for window in (4, 8):
        frame[f"event_count_{window}w"] = grouped["event_count"].transform(
            lambda values: values.rolling(window, min_periods=1).sum()
        )
    frame["event_count_lifetime"] = grouped["event_count"].cumsum()
    previous_4w = grouped["event_count"].transform(
        lambda values: values.shift(4).rolling(4, min_periods=1).sum().fillna(0.0)
    )
    frame["event_count_acceleration_4w"] = frame["event_count_4w"] - previous_4w
    frame["severity_sum_4w"] = grouped["severity_sum"].transform(
        lambda values: values.rolling(4, min_periods=1).sum()
    )
    frame["severity_sum_8w"] = grouped["severity_sum"].transform(
        lambda values: values.rolling(8, min_periods=1).sum()
    )
    frame["severity_sum_lifetime"] = grouped["severity_sum"].cumsum()
    frame["severity_max_4w"] = grouped["severity_max"].transform(
        lambda values: values.rolling(4, min_periods=1).max()
    )
    frame["high_severity_count_4w"] = grouped["high_severity_count"].transform(
        lambda values: values.rolling(4, min_periods=1).sum()
    )
    frame["risk_score_delta_1w"] = grouped["risk_score"].diff().fillna(0.0)
    frame["risk_score_slope_4w"] = grouped["risk_score"].transform(
        lambda values: values.rolling(4, min_periods=2).apply(_rolling_slope, raw=True).fillna(0.0)
    )
    for window in (4, 8):
        frame[f"risk_score_mean_{window}w"] = grouped["risk_score"].transform(
            lambda values: values.rolling(window, min_periods=1).mean()
        )

    categories = sorted(events["event_category"].unique().tolist())
    category_week = (
        events.assign(present=1)
        .pivot_table(
            index=["supplier_id", "event_week"],
            columns="event_category",
            values="present",
            aggfunc="max",
            fill_value=0,
        )
        .reset_index()
        .rename(columns={"event_week": "week"})
    )
    frame = frame.merge(category_week, on=["supplier_id", "week"], how="left")
    frame[categories] = frame[categories].fillna(0)
    category_active = []
    for category in categories:
        active = frame.groupby("supplier_id", group_keys=False)[category].transform(
            lambda values: values.rolling(4, min_periods=1).max()
        )
        category_active.append(active)
    frame["category_count_4w"] = pd.concat(category_active, axis=1).sum(axis=1)
    frame["cross_category_count_4w"] = (frame["category_count_4w"] - 1).clip(lower=0)
    for category, feature_name in CATEGORY_FEATURES.items():
        if category in categories:
            frame[feature_name] = frame.groupby("supplier_id", group_keys=False)[category].transform(
                lambda values: values.rolling(4, min_periods=1).sum()
            )
        else:
            frame[feature_name] = 0.0

    frame["last_event_week"] = frame["week"].where(frame["event_count"] > 0)
    frame["last_event_week"] = frame.groupby("supplier_id")["last_event_week"].ffill()
    frame["weeks_since_last_event"] = (frame["week"] - frame["last_event_week"]).fillna(53).astype(float)

    static = (
        contracts[["contract_id", "supplier_id", "contract_importance"]]
        .merge(projects, on="contract_id", how="left")
        .merge(systems[["project_id", "system_level"]], on="project_id", how="left")
    )
    static["system_level_score"] = static["system_level"].map({"一般": 1.0, "重要": 2.0, "核心": 3.0})
    static["contract_importance_score"] = static["contract_importance"].map({"一般外包": 1.0, "重要外包": 2.0})
    static["project_stage_code"] = static["project_stage"].map({"开发中": 0.0, "上线运维": 1.0})
    frame = frame.merge(
        static[
            [
                "supplier_id",
                "system_level_score",
                "contract_importance_score",
                "project_stage_code",
            ]
        ],
        on="supplier_id",
        how="left",
    )
    for column in ("system_level_score", "contract_importance_score", "project_stage_code"):
        frame[column] = frame[column].fillna(0.0)

    rectifies["start_week"] = rectifies["start_week"].astype(int)
    rectifies["end_week"] = rectifies["end_week"].astype(int)
    rectify_ranges = {
        supplier_id: list(group[["start_week", "end_week"]].itertuples(index=False, name=None))
        for supplier_id, group in rectifies.groupby("supplier_id")
    }

    def _rectify_timing(row: pd.Series) -> tuple[float, float]:
        for start_week, end_week in rectify_ranges.get(row["supplier_id"], []):
            if start_week <= int(row["week"]) <= end_week:
                return float(int(row["week"]) - start_week + 1), float(end_week - int(row["week"]))
        return 0.0, 0.0

    timing = frame.apply(_rectify_timing, axis=1, result_type="expand")
    frame["rectify_weeks_elapsed"] = timing[0]
    frame["rectify_weeks_remaining"] = timing[1]

    return frame[["supplier_id", "week", *FEATURE_COLUMNS, "upgrade_label"]].copy()


def rolling_origin_splits(
    frame: pd.DataFrame,
    *,
    folds: tuple[tuple[int, int, int], ...] = ((22, 23, 26), (26, 27, 30), (30, 31, 34)),
) -> list[tuple[str, pd.DataFrame, pd.DataFrame]]:
    result: list[tuple[str, pd.DataFrame, pd.DataFrame]] = []
    for train_end, validation_start, validation_end in folds:
        train = frame[frame["week"] <= train_end].copy()
        validation = frame[frame["week"].between(validation_start, validation_end)].copy()
        if train["upgrade_label"].nunique() < 2 or validation["upgrade_label"].nunique() < 2:
            raise DataValidationError(
                f"Rolling fold {train_end}/{validation_start}-{validation_end} must contain both classes"
            )
        result.append((f"train_1_{train_end}__validate_{validation_start}_{validation_end}", train, validation))
    return result


def temporal_split(
    frame: pd.DataFrame,
    *,
    train_end_week: int = 26,
    validation_end_week: int = 34,
    test_end_week: int = 44,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not 1 <= train_end_week < validation_end_week < test_end_week <= 52:
        raise ValueError("Invalid temporal split boundaries")
    train = frame[frame["week"] <= train_end_week].copy()
    validation = frame[(frame["week"] > train_end_week) & (frame["week"] <= validation_end_week)].copy()
    test = frame[(frame["week"] > validation_end_week) & (frame["week"] <= test_end_week)].copy()
    tail = frame[frame["week"] > test_end_week].copy()
    for name, part in (("train", train), ("validation", validation), ("test", test)):
        if part["upgrade_label"].nunique() < 2:
            raise DataValidationError(f"{name} split must contain both label classes")
    return train, validation, test, tail
