from collections import defaultdict


def build_upgrade_labels(
    events: list[dict],
    *,
    supplier_ids: list[str] | None = None,
    max_week: int = 52,
    horizon: int = 3,
    severity_threshold: int = 3,
) -> list[dict]:
    """Create label(t) using events strictly in t+1..t+horizon."""
    high_risk_weeks: dict[str, set[int]] = defaultdict(set)
    inferred_suppliers: set[str] = set()
    for event in events:
        supplier_id = str(event["supplier_id"])
        inferred_suppliers.add(supplier_id)
        if int(event["event_severity"]) >= severity_threshold:
            high_risk_weeks[supplier_id].add(int(event["event_week"]))

    suppliers = sorted(supplier_ids or inferred_suppliers)
    labels: list[dict] = []
    for supplier_id in suppliers:
        for week in range(1, max_week + 1):
            future_weeks = range(week + 1, min(week + horizon, max_week) + 1)
            label = int(any(future in high_risk_weeks[supplier_id] for future in future_weeks))
            labels.append({"supplier_id": supplier_id, "week": week, "upgrade_label": label})
    return labels

