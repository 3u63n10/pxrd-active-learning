"""Synthetic condition-phase maps used before experimental integration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def make_grid(points_per_axis: int) -> FloatArray:
    """Return a regular two-dimensional candidate grid on [0, 1] x [0, 1]."""
    if points_per_axis < 2:
        raise ValueError("points_per_axis must be at least 2")

    axis = np.linspace(0.0, 1.0, points_per_axis)
    x_coord, y_coord = np.meshgrid(axis, axis)
    return np.column_stack((x_coord.ravel(), y_coord.ravel()))


@dataclass(frozen=True)
class SyntheticPhaseMap:
    """Smooth three-phase test environment with uncertain phase boundaries."""

    observation_noise: float = 0.12
    seed: int = 17

    def _scores(self, conditions: FloatArray) -> FloatArray:
        points = np.asarray(conditions, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2:
            raise ValueError("conditions must have shape (n_samples, 2)")

        x_coord = points[:, 0]
        y_coord = points[:, 1]
        centers = np.array(
            [
                [0.22, 0.25],
                [0.78, 0.30],
                [0.50, 0.82],
            ]
        )

        squared_distance = np.sum(
            (points[:, None, :] - centers[None, :, :]) ** 2,
            axis=2,
        )
        scores = -squared_distance / 0.16

        # Curved boundaries make the benchmark less like a simple Voronoi map.
        scores[:, 0] += 0.28 * np.sin(3.0 * np.pi * y_coord)
        scores[:, 1] += 0.24 * np.cos(2.5 * np.pi * y_coord + 0.4)
        scores[:, 2] += 0.22 * np.sin(3.5 * np.pi * x_coord + 0.7)
        return scores

    def phase(self, conditions: FloatArray) -> IntArray:
        """Return the noise-free phase label for each condition."""
        return np.argmax(self._scores(conditions), axis=1).astype(np.int64)

    def purity(self, conditions: FloatArray) -> FloatArray:
        """Return a synthetic phase-purity score based on latent-score margin."""
        sorted_scores = np.sort(self._scores(conditions), axis=1)
        margin = sorted_scores[:, -1] - sorted_scores[:, -2]
        return 1.0 / (1.0 + np.exp(-7.0 * (margin - 0.12)))

    def observe(
        self,
        conditions: FloatArray,
        *,
        observation_ids: IntArray | None = None,
    ) -> IntArray:
        """Return noisy labels, with most ambiguity near phase boundaries."""
        points = np.asarray(conditions, dtype=float)
        labels = self.phase(points)
        purity = self.purity(points)

        if observation_ids is None:
            observation_ids = np.arange(len(points), dtype=np.int64)
        ids = np.asarray(observation_ids, dtype=np.int64)
        if ids.shape != labels.shape:
            raise ValueError("observation_ids must match the number of conditions")

        observed = labels.copy()
        for row, observation_id in enumerate(ids):
            local_rng = np.random.default_rng(self.seed + int(observation_id))
            flip_probability = self.observation_noise * (1.0 - purity[row])
            if local_rng.random() < flip_probability:
                alternatives = np.delete(np.arange(3), labels[row])
                observed[row] = local_rng.choice(alternatives)
        return observed
