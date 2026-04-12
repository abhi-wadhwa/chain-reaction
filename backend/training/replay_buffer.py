from __future__ import annotations

import numpy as np
import pickle
from dataclasses import dataclass
from training.self_play import TrainingExample


class ReplayBuffer:
    def __init__(self, window_size: int = 5, recency_half_life: float = 2.0):
        self.window_size = window_size
        self.recency_half_life = recency_half_life
        self._iterations: dict[int, list[TrainingExample]] = {}
        self._latest_iteration = -1

    def add_iteration(self, examples: list[TrainingExample], iteration: int):
        self._iterations[iteration] = examples
        self._latest_iteration = max(self._latest_iteration, iteration)
        self._evict_old()

    def _evict_old(self):
        if self._latest_iteration < 0:
            return
        min_iter = self._latest_iteration - self.window_size + 1
        to_remove = [k for k in self._iterations if k < min_iter]
        for k in to_remove:
            del self._iterations[k]

    def sample(self, batch_size: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Sample batch with recency weighting. Returns (tensors, policies, values)."""
        all_examples = []
        all_weights = []

        for iteration, examples in self._iterations.items():
            age = self._latest_iteration - iteration
            weight = 0.5 ** (age / self.recency_half_life)
            for ex in examples:
                all_examples.append(ex)
                all_weights.append(weight)

        weights = np.array(all_weights, dtype=np.float64)
        weights /= weights.sum()

        n = min(batch_size, len(all_examples))
        indices = np.random.choice(len(all_examples), size=n, replace=False, p=weights)

        tensors = np.stack([all_examples[i].board_tensor for i in indices])
        policies = np.stack([all_examples[i].policy_target for i in indices])
        values = np.array([all_examples[i].value_target for i in indices], dtype=np.float32)

        return tensors, policies, values

    def size(self) -> int:
        return sum(len(exs) for exs in self._iterations.values())

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump({
                "iterations": self._iterations,
                "latest_iteration": self._latest_iteration,
                "window_size": self.window_size,
                "recency_half_life": self.recency_half_life,
            }, f)

    @classmethod
    def load(cls, path: str) -> ReplayBuffer:
        with open(path, "rb") as f:
            data = pickle.load(f)
        buf = cls(
            window_size=data["window_size"],
            recency_half_life=data["recency_half_life"],
        )
        buf._iterations = data["iterations"]
        buf._latest_iteration = data["latest_iteration"]
        return buf
