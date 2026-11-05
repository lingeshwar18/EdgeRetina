import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import Config, SEED
from app.services.dataset_splitter import create_splits

if __name__ == "__main__":
    splits = create_splits(Config.CSV_PATH, Path(__file__).resolve().parents[1] / "data" / "splits", SEED)
    print({name: len(frame) for name, frame in splits.items()})
