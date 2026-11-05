import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import CLASS_NAMES
from app.federated.differential_privacy import protect_update
from app.federated.fedavg import fedavg
from app.services.evaluation_service import evaluate_predictions
from app.services.training_service import focal_loss
from app.models.mobilenet_model import build_model
from app.services.prediction_agent import PredictionAgent


def test_canonical_class_mapping():
    assert CLASS_NAMES[0] == "No DR"
    assert CLASS_NAMES[4] == "Proliferative DR"


def test_fedavg_is_weighted():
    result = fedavg([[np.array([1.0])], [np.array([3.0])]], [1, 3])
    assert result[0][0] == 2.5


def test_dp_clips_and_reports():
    protected, report = protect_update([np.array([3.0, 4.0])], 1.0, 0.0)
    assert report["raw_update_norm"] == 5.0
    assert np.isclose(np.linalg.norm(protected[0]), 1.0)


def test_dp_noise_is_scaled_to_the_full_update_size():
    protected, _ = protect_update([np.zeros(10000, dtype=np.float32)], 1.0, 0.2, np.random.default_rng(7))
    assert 0.18 < np.linalg.norm(protected[0]) < 0.22


def test_dp_rejects_non_finite_client_updates():
    with pytest.raises(ValueError, match="NaN or infinite"):
        protect_update([np.array([np.nan], dtype=np.float32)], 1.0, 0.1)


def test_evaluation_has_ordinal_metrics():
    metrics = evaluate_predictions([0, 1, 2], [0, 2, 2])
    assert "qwk" in metrics and "mae" in metrics


def test_supported_models_and_focal_loss():
    assert build_model(weights=None, architecture="EfficientNetB0").output_shape[-1] == 5
    assert build_model(weights=None, architecture="MobileNetV3Small").output_shape[-1] == 5
    assert focal_loss()(np.eye(5, dtype=np.float32), np.full((5, 5), 0.2, dtype=np.float32)).shape == (5,)


def test_prediction_agent_contract():
    assert callable(PredictionAgent().predict)
