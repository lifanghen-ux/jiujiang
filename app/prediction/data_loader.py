import csv
from pathlib import Path

from app.common.errors import DataValidationError


def load_csv(path: Path, *, required_fields: set[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = required_fields - fields
        if missing:
            raise DataValidationError(f"Missing required fields: {sorted(missing)}")
        return list(reader)

