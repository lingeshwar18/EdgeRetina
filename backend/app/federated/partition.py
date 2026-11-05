from pathlib import Path

import numpy as np
import pandas as pd


def dirichlet_partition(frame: pd.DataFrame, clients: list[str], alpha: float = 2.0, seed: int = 42) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    assignments = {client: [] for client in clients}
    for label in sorted(frame["diagnosis"].unique()):
        indices = frame.index[frame["diagnosis"] == label].to_numpy()
        rng.shuffle(indices)
        proportions = rng.dirichlet(np.full(len(clients), alpha))
        boundaries = (np.cumsum(proportions) * len(indices)).astype(int)[:-1]
        for client, values in zip(clients, np.split(indices, boundaries)):
            assignments[client].extend(values.tolist())
    return {client: frame.loc[sorted(indices)].reset_index(drop=True) for client, indices in assignments.items()}


def save_distribution(partitions: dict[str, pd.DataFrame], output_path: Path) -> None:
    rows = []
    for client, frame in partitions.items():
        counts = frame["diagnosis"].value_counts().to_dict()
        rows.append({"client": client, **{f"class_{label}": int(counts.get(label, 0)) for label in range(5)}, "total": len(frame)})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
