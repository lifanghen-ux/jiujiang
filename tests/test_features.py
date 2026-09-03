from app.prediction.features import rolling_event_features, weeks_since_last_event


EVENTS = [
    {"supplier_id": "S-1", "event_week": 2, "event_severity": 2, "event_category": "履约"},
    {"supplier_id": "S-1", "event_week": 5, "event_severity": 3, "event_category": "人员"},
]


def test_rolling_features_never_read_future_events():
    result = rolling_event_features(EVENTS, supplier_id="S-1", week=4, window=4)
    assert result["event_count_4w"] == 1
    assert result["severity_max_4w"] == 2


def test_weeks_since_last_event():
    assert weeks_since_last_event(EVENTS, supplier_id="S-1", week=4) == 2

