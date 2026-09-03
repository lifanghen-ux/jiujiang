from collections import defaultdict


def rolling_event_features(events: list[dict], *, supplier_id: str, week: int, window: int = 4) -> dict[str, float]:
    start = max(1, week - window + 1)
    history = [
        row
        for row in events
        if str(row["supplier_id"]) == supplier_id and start <= int(row["event_week"]) <= week
    ]
    severities = [int(row["event_severity"]) for row in history]
    categories = {str(row["event_category"]) for row in history}
    return {
        f"event_count_{window}w": float(len(history)),
        f"severity_sum_{window}w": float(sum(severities)),
        f"severity_max_{window}w": float(max(severities, default=0)),
        f"high_severity_count_{window}w": float(sum(value >= 3 for value in severities)),
        f"category_count_{window}w": float(len(categories)),
        f"cross_category_count_{window}w": float(max(len(categories) - 1, 0)),
    }


def weeks_since_last_event(events: list[dict], *, supplier_id: str, week: int) -> int | None:
    previous = [
        int(row["event_week"])
        for row in events
        if str(row["supplier_id"]) == supplier_id and int(row["event_week"]) <= week
    ]
    return week - max(previous) if previous else None

