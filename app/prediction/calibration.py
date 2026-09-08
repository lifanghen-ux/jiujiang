from dataclasses import dataclass

import numpy as np


@dataclass
class CalibratedRiskModel:
    estimator: object
    calibrator: object

    def predict_proba(self, features) -> np.ndarray:
        raw = self.estimator.predict_proba(features)[:, 1]
        calibrated = np.asarray(self.calibrator.predict(raw), dtype=float)
        calibrated = np.clip(calibrated, 0.0, 1.0)
        return np.column_stack([1.0 - calibrated, calibrated])
