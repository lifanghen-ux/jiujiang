import csv
from pathlib import Path
from uuid import uuid4

from app.workflow.graph import build_workflow


def load_mock_events(path: Path = Path("data/mock/risk_events.csv")) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["event_severity"] = int(row["event_severity"])
        row["event_week"] = int(row["event_week"])
    return rows


def run_demo(*, current_week: int = 10, include_events: bool = True) -> dict:
    workflow = build_workflow()
    return workflow.invoke(
        {
            "run_id": str(uuid4()),
            "supplier_id": "S-MOCK-01",
            "current_week": current_week,
            "events": load_mock_events() if include_events else [],
            "business_context": {"risk_score": 5.0, "business_exposure": 0.80},
            "status": "CREATED",
            "errors": [],
            "audit_trace": [],
        }
    )

