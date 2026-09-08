import csv
from pathlib import Path
from uuid import uuid4

from app.prediction.dataset import FEATURE_COLUMNS
from app.workflow.graph import build_workflow


def load_mock_events(path: Path = Path("data/mock/risk_events.csv")) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["event_severity"] = int(row["event_severity"])
        row["event_week"] = int(row["event_week"])
    return rows


def run_demo(*, current_week: int = 10, include_events: bool = True, enable_live_llm: bool = False) -> dict:
    workflow = build_workflow()
    return workflow.invoke(
        {
            "run_id": str(uuid4()),
            "supplier_id": "S-MOCK-01",
            "current_week": current_week,
            "events": load_mock_events() if include_events else [],
            "business_context": {"risk_score": 5.0, "business_exposure": 0.80},
            "enable_live_llm": enable_live_llm,
            "status": "CREATED",
            "errors": [],
            "audit_trace": [],
        }
    )


def run_real_data_demo(
    *,
    source_dir: Path = Path("data/source"),
    feature_path: Path = Path("artifacts/features/model_features.csv"),
    enable_live_llm: bool = False,
) -> dict:
    import pandas as pd

    if not feature_path.exists():
        raise FileNotFoundError("Feature artifact is missing; run `python -m app.main train` first")
    feature_frame = pd.read_csv(feature_path, encoding="utf-8-sig")
    events = pd.read_csv(source_dir / "risk_events.csv", encoding="utf-8-sig")
    candidates = feature_frame[
        (feature_frame["week"].between(35, 44)) & (feature_frame["upgrade_label"] == 1)
    ]
    selected = None
    for row in candidates.itertuples(index=False):
        visible = events[(events["supplier_id"] == row.supplier_id) & (events["event_week"] <= row.week)]
        if not visible.empty:
            selected = row
            break
    if selected is None:
        raise RuntimeError("No positive test example with historical evidence was found")

    supplier_events = events[events["supplier_id"] == selected.supplier_id].to_dict("records")
    workflow = build_workflow()
    return workflow.invoke(
        {
            "run_id": str(uuid4()),
            "supplier_id": selected.supplier_id,
            "current_week": int(selected.week),
            "events": supplier_events,
            "business_context": {
                "risk_score": float(selected.risk_score),
                "business_exposure": float(selected.business_exposure),
            },
            "model_features": {name: float(getattr(selected, name)) for name in FEATURE_COLUMNS},
            "enable_live_llm": enable_live_llm,
            "status": "CREATED",
            "errors": [],
            "audit_trace": [],
        }
    )
