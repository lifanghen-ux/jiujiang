def evaluate_binary(y_true, probabilities: list[float], *, threshold: float = 0.5) -> dict[str, float]:
    try:
        from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
    except ImportError as exc:
        raise RuntimeError("Install the 'ml' extra to evaluate models") from exc
    predictions = [int(value >= threshold) for value in probabilities]
    return {
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "pr_auc": float(average_precision_score(y_true, probabilities)),
    }

