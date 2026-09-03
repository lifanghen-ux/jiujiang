from dataclasses import dataclass
from typing import Protocol


class ProbabilityModel(Protocol):
    def fit(self, features, labels) -> "ProbabilityModel": ...
    def predict_proba(self, features): ...


@dataclass(slots=True)
class ModelDefinition:
    name: str
    estimator: object


def build_sklearn_models(random_state: int = 42) -> list[ModelDefinition]:
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
    except ImportError as exc:
        raise RuntimeError("Install the 'ml' extra to build baseline models") from exc

    models = [
        ModelDefinition("logistic_regression", LogisticRegression(max_iter=1000, random_state=random_state)),
        ModelDefinition(
            "random_forest",
            RandomForestClassifier(n_estimators=200, random_state=random_state, class_weight="balanced"),
        ),
    ]
    try:
        from xgboost import XGBClassifier

        models.append(
            ModelDefinition(
                "xgboost",
                XGBClassifier(
                    n_estimators=200,
                    max_depth=4,
                    learning_rate=0.05,
                    random_state=random_state,
                    eval_metric="logloss",
                ),
            )
        )
    except ImportError:
        pass
    return models

