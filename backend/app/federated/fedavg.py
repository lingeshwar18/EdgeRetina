import numpy as np


def fedavg(weight_sets: list[list[np.ndarray]], sample_counts: list[int]) -> list[np.ndarray]:
    if not weight_sets or len(weight_sets) != len(sample_counts) or sum(sample_counts) <= 0:
        raise ValueError("FedAvg requires non-empty client weights and positive sample counts")
    total = float(sum(sample_counts))
    return [sum(weights[index] * (count / total) for weights, count in zip(weight_sets, sample_counts)) for index in range(len(weight_sets[0]))]
