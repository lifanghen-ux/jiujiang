from pathlib import Path

from app.prediction.dataset import LEADING_INDICATOR_SCHEMA
from scripts.generate_leading_indicators import SIMULATION_VERSION, generate


SOURCE_DIR = Path("data/source")


def test_simulated_leading_indicators_are_complete_and_reproducible() -> None:
    first = generate(SOURCE_DIR)
    second = generate(SOURCE_DIR)

    assert first.columns.tolist() == LEADING_INDICATOR_SCHEMA
    assert len(first) == 10_400
    assert not first.duplicated(["supplier_id", "week"]).any()
    assert first.equals(second)
    assert first["is_simulated"].all()
    assert first["simulation_version"].eq(SIMULATION_VERSION).all()
