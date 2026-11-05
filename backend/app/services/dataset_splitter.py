from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


def create_splits(csv_path: Path, output_dir: Path, seed: int = 42) -> dict[str, pd.DataFrame]:
    frame = pd.read_csv(csv_path)
    if "diagnosis" not in frame.columns:
        raise ValueError("Dataset CSV must contain a diagnosis column")
    train, remaining = train_test_split(frame, test_size=0.30, random_state=seed, stratify=frame["diagnosis"])
    validation, test = train_test_split(remaining, test_size=0.50, random_state=seed, stratify=remaining["diagnosis"])
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, split in {"train": train, "val": validation, "test": test}.items():
        split.to_csv(output_dir / f"{name}.csv", index=False)
    return {"train": train, "val": validation, "test": test}
