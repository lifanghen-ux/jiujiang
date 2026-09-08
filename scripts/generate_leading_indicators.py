from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from app.prediction.dataset import LEADING_INDICATOR_SCHEMA

SIMULATION_VERSION = "LEADING-SIM-V0.1"


def generate(source_dir: Path, *, seed: int = 20260908) -> pd.DataFrame:
    """Create hypothetical observable precursors for a controlled simulation experiment."""
    suppliers = pd.read_csv(source_dir / "suppliers.csv", encoding="utf-8-sig")
    events = pd.read_csv(source_dir / "risk_events.csv", encoding="utf-8-sig")
    rng = np.random.default_rng(seed)
    grid = pd.MultiIndex.from_product(
        [suppliers["supplier_id"].astype(str), range(1, 53)], names=["supplier_id", "week"]
    ).to_frame(index=False)
    rows = len(grid)
    grid["sla_compliance_rate"] = np.clip(rng.normal(0.985, 0.006, rows), 0.94, 1.0)
    grid["overdue_days"] = rng.poisson(0.15, rows).astype(float)
    grid["critical_staff_turnover_rate"] = np.clip(rng.beta(1.2, 35, rows), 0.0, 0.15)
    grid["unresolved_ticket_count"] = rng.poisson(0.35, rows).astype(float)
    grid["system_availability_rate"] = np.clip(rng.normal(0.997, 0.0015, rows), 0.985, 1.0)
    grid["complaint_count"] = rng.binomial(1, 0.04, rows).astype(float)
    grid["negative_sentiment_count"] = rng.binomial(1, 0.015, rows).astype(float)

    sudden_suppliers = sorted(
        supplier for supplier in suppliers["supplier_id"].astype(str) if "SUD" in supplier
    )
    observable_sudden = set(sudden_suppliers[: int(len(sudden_suppliers) * 0.6)])

    for event in events.itertuples(index=False):
        supplier_id = str(event.supplier_id)
        is_gradual = "ACC" in supplier_id
        is_observable_sudden = "SUD" in supplier_id and supplier_id in observable_sudden
        if not (is_gradual or is_observable_sudden) or int(event.event_severity) < 3:
            continue
        for distance in range(4, 0, -1):
            week = int(event.event_week) - distance
            if week < 1:
                continue
            mask = grid["supplier_id"].eq(supplier_id) & grid["week"].eq(week)
            ramp = (5 - distance) / 4
            severity = float(event.event_severity)
            grid.loc[mask, "sla_compliance_rate"] -= 0.012 * severity * ramp
            grid.loc[mask, "overdue_days"] += np.ceil(1.5 * severity * ramp)
            grid.loc[mask, "unresolved_ticket_count"] += np.ceil(1.2 * severity * ramp)
            grid.loc[mask, "complaint_count"] += float(ramp >= 0.5)
            category = str(event.event_category)
            if category == "人员":
                grid.loc[mask, "critical_staff_turnover_rate"] += 0.035 * severity * ramp
            elif category in {"安全", "经营"}:
                grid.loc[mask, "system_availability_rate"] -= 0.003 * severity * ramp
            elif category in {"合规", "舆情"}:
                grid.loc[mask, "negative_sentiment_count"] += float(ramp >= 0.5)

    rate_columns = [
        "sla_compliance_rate",
        "critical_staff_turnover_rate",
        "system_availability_rate",
    ]
    for column in rate_columns:
        grid[column] = grid[column].clip(0.0, 1.0).round(4)
    count_columns = [
        "overdue_days",
        "unresolved_ticket_count",
        "complaint_count",
        "negative_sentiment_count",
    ]
    for column in count_columns:
        grid[column] = grid[column].clip(lower=0).round().astype(int)
    grid["is_simulated"] = True
    grid["simulation_version"] = SIMULATION_VERSION
    return grid[LEADING_INDICATOR_SCHEMA]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate simulated leading indicators")
    parser.add_argument("--source-dir", type=Path, default=Path("data/source"))
    parser.add_argument("--seed", type=int, default=20260908)
    args = parser.parse_args()
    output = args.source_dir / "leading_indicators.csv"
    frame = generate(args.source_dir, seed=args.seed)
    frame.to_csv(output, index=False, encoding="utf-8-sig")
    print(
        {
            "output": str(output),
            "rows": len(frame),
            "simulation_version": SIMULATION_VERSION,
            "is_simulated": True,
        }
    )


if __name__ == "__main__":
    main()
