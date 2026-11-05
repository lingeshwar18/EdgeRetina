"""Keep a live federated status file valid JSON while an older worker is active."""
import json
import math
import time
from pathlib import Path


STATUS = Path(__file__).resolve().parents[1] / "reports" / "federated" / "status.json"


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


while True:
    try:
        raw = STATUS.read_text(encoding="utf-8")
        state = json.loads(raw)
        cleaned = json.dumps(clean(state), indent=2, allow_nan=False)
        if cleaned != raw:
            temp = STATUS.with_suffix(".sanitized.tmp")
            temp.write_text(cleaned, encoding="utf-8")
            if STATUS.read_text(encoding="utf-8") == raw:
                temp.replace(STATUS)
            else:
                temp.unlink(missing_ok=True)
        if state.get("status") not in ("queued", "running") and "NaN" not in cleaned:
            break
    except (OSError, json.JSONDecodeError):
        pass
    time.sleep(0.2)
