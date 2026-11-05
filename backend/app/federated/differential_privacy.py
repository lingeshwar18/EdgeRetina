import numpy as np


def protect_update(update: list[np.ndarray], clip_norm: float | None, noise_multiplier: float, rng: np.random.Generator | None = None) -> tuple[list[np.ndarray], dict]:
    rng = rng or np.random.default_rng(42)
    update = [np.asarray(value) for value in update]
    if any(not np.isfinite(value).all() for value in update):
        raise ValueError("Client update contains NaN or infinite weights.")
    norm = float(np.sqrt(sum(np.sum(np.square(value, dtype=np.float64)) for value in update)))
    scale = 1.0 if clip_norm is None or norm == 0 else min(1.0, clip_norm / norm)
    clipped = [value * scale for value in update]
    parameter_count = max(sum(value.size for value in clipped), 1)
    # Bound the full flattened update's expected noise norm instead of adding
    # sigma*C independently to millions of weights and overwhelming the model.
    noise_scale = float((clip_norm or 0.0) * noise_multiplier / np.sqrt(parameter_count))
    protected = [value + rng.normal(0.0, noise_scale, size=value.shape) for value in clipped]
    if any(not np.isfinite(value).all() for value in protected):
        raise ValueError("Processed client update contains NaN or infinite weights.")
    protected_norm = float(np.sqrt(sum(np.sum(np.square(value)) for value in protected)))
    return protected, {"raw_update_norm": norm, "clipped_update_norm": norm * scale, "noise_scale_per_parameter": noise_scale, "protected_update_norm": protected_norm}
