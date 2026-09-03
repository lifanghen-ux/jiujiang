from app.prediction.label_builder import build_upgrade_labels


def test_future_three_week_label_excludes_current_and_earlier_weeks():
    events = [
        {
            "supplier_id": "S-A01",
            "event_week": 18,
            "event_severity": 3,
        }
    ]
    rows = build_upgrade_labels(events, supplier_ids=["S-A01"], max_week=20)
    labels = {row["week"]: row["upgrade_label"] for row in rows}
    assert labels[13] == 0
    assert labels[14] == 0
    assert labels[15] == 1
    assert labels[16] == 1
    assert labels[17] == 1
    assert labels[18] == 0


def test_end_of_series_boundary_is_zero_without_future_event():
    rows = build_upgrade_labels([], supplier_ids=["S-1"], max_week=52)
    labels = {row["week"]: row["upgrade_label"] for row in rows}
    assert labels[50] == labels[51] == labels[52] == 0

