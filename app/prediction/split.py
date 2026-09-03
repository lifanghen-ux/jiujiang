def temporal_split(rows: list[dict], *, train_end_week: int, validation_end_week: int) -> tuple[list[dict], list[dict], list[dict]]:
    if train_end_week >= validation_end_week:
        raise ValueError("train_end_week must be before validation_end_week")
    train = [row for row in rows if int(row["week"]) <= train_end_week]
    validation = [row for row in rows if train_end_week < int(row["week"]) <= validation_end_week]
    test = [row for row in rows if int(row["week"]) > validation_end_week]
    return train, validation, test

