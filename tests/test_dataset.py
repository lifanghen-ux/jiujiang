from pathlib import Path

from app.prediction.dataset import (
    FEATURE_COLUMNS,
    build_feature_frame,
    load_source_tables,
    rolling_origin_splits,
    temporal_split,
    validate_source_tables,
)


SOURCE_DIR = Path("data/source")


def test_full_source_data_passes_integrity_checks() -> None:
    tables = load_source_tables(SOURCE_DIR)
    report = validate_source_tables(tables)

    assert report["status"] == "PASS"
    assert report["row_counts"]["weekly_snapshot.csv"] == 10_400
    assert report["duplicate_counts"]["supplier_week"] == 0
    assert report["leading_indicators"]["status"] == "PASS_SIMULATED"
    assert report["leading_indicators"]["rows"] == 10_400
    assert sum(report["foreign_key_error_counts"].values()) == 0
    assert sum(report["calculation_mismatches"].values()) == 0


def test_feature_frame_and_temporal_split_are_model_ready() -> None:
    frame = build_feature_frame(load_source_tables(SOURCE_DIR))
    train, validation, test, _tail = temporal_split(frame)

    assert len(frame) == 10_400
    assert frame[FEATURE_COLUMNS].isna().sum().sum() == 0
    assert len(FEATURE_COLUMNS) == 40
    assert train["week"].max() < validation["week"].min()
    assert validation["week"].max() < test["week"].min()
    assert train["upgrade_label"].sum() == 136
    assert validation["upgrade_label"].sum() == 94
    assert test["upgrade_label"].sum() == 40


def test_rolling_origin_splits_preserve_time_order() -> None:
    frame = build_feature_frame(load_source_tables(SOURCE_DIR))
    folds = rolling_origin_splits(frame)

    assert len(folds) == 3
    for _name, train, validation in folds:
        assert train["week"].max() < validation["week"].min()
        assert train["upgrade_label"].nunique() == 2
        assert validation["upgrade_label"].nunique() == 2
