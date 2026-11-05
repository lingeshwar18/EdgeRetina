import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import Config
from app.services.dataset_validator import validate_dataset

if __name__ == "__main__":
    print(validate_dataset(Config.CSV_PATH, Config.IMAGE_DIR, Path(__file__).resolve().parents[1] / "reports" / "validation"))
