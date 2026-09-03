def explain_with_shap(model, features, *, max_display: int = 8):
    try:
        import shap
    except ImportError as exc:
        raise RuntimeError("Install the 'ml' extra to use SHAP") from exc
    explainer = shap.Explainer(model, features)
    values = explainer(features)
    return values[:, :max_display] if getattr(values, "ndim", 1) > 1 else values

