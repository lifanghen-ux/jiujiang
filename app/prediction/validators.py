from collections import Counter

from app.common.errors import DataValidationError


EVENT_FIELDS = {
    "evidence_id",
    "supplier_id",
    "event_category",
    "event_subtype",
    "event_severity",
    "event_week",
    "source_type",
}


def validate_events(rows: list[dict]) -> None:
    evidence_ids = [str(row["evidence_id"]) for row in rows]
    duplicates = [key for key, count in Counter(evidence_ids).items() if count > 1]
    if duplicates:
        raise DataValidationError(f"Duplicate evidence_id values: {duplicates}")
    for row in rows:
        week = int(row["event_week"])
        severity = int(row["event_severity"])
        if not 1 <= week <= 52:
            raise DataValidationError(f"event_week out of range: {week}")
        if not 0 <= severity <= 5:
            raise DataValidationError(f"event_severity out of range: {severity}")

