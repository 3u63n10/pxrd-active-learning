"""Sequential strategies for reconstructing a condition-phase map."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from sklearn.ensemble import RandomForestClassifier

from .synthetic import FloatArray, SyntheticPhaseMap


Strategy = Literal["random", "rf_uncertainty"]


@dataclass(frozen=True)
class MappingResult:
    """Learning history from one sequential phase-mapping run."""

    strategy: Strategy
    selected_indices: NDArray[np.int64]
    selected_points: FloatArray
    accuracy: FloatArray
    boundary_accuracy: FloatArray


def _fit_model(
    conditions: FloatArray,
    labels: NDArray[np.int64],
    seed: int,
) -> RandomForestClassifier:
    model = RandomForestClassifier(
        n_estimators=64,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(conditions, labels)
    return model


def _entropy(probabilities: FloatArray) -> FloatArray:
    clipped = np.clip(probabilities, 1e-12, 1.0)
    return -np.sum(clipped * np.log(clipped), axis=1)


def run_mapping(
    world: SyntheticPhaseMap,
    candidates: FloatArray,
    evaluation_points: FloatArray,
    *,
    strategy: Strategy,
    budget: int = 50,
    initial_samples: int = 8,
    seed: int = 5,
) -> MappingResult:
    """Run a sequential mapping experiment and return its learning curves."""
    candidate_points = np.asarray(candidates, dtype=float)
    evaluation = np.asarray(evaluation_points, dtype=float)
    if budget > len(candidate_points):
        raise ValueError("budget cannot exceed the number of candidates")
    if not 2 <= initial_samples <= budget:
        raise ValueError("initial_samples must be between 2 and budget")
    if strategy not in ("random", "rf_uncertainty"):
        raise ValueError(f"unknown strategy: {strategy}")

    rng = np.random.default_rng(seed)
    selected = list(
        rng.choice(len(candidate_points), size=initial_samples, replace=False)
    )
    available = set(range(len(candidate_points))) - set(selected)
    true_evaluation_labels = world.phase(evaluation)
    boundary_mask = world.purity(evaluation) < 0.65
    accuracy_history: list[float] = []
    boundary_history: list[float] = []

    while len(selected) <= budget:
        selected_array = np.asarray(selected, dtype=np.int64)
        observed_labels = world.observe(
            candidate_points[selected_array],
            observation_ids=selected_array,
        )

        if np.unique(observed_labels).size >= 2:
            model = _fit_model(
                candidate_points[selected_array],
                observed_labels,
                seed + len(selected),
            )
            predictions = model.predict(evaluation)
        else:
            model = None
            predictions = np.full_like(true_evaluation_labels, observed_labels[0])

        accuracy_history.append(float(np.mean(predictions == true_evaluation_labels)))
        boundary_history.append(
            float(np.mean(predictions[boundary_mask] == true_evaluation_labels[boundary_mask]))
        )

        if len(selected) == budget:
            break

        remaining = np.asarray(sorted(available), dtype=np.int64)
        if strategy == "random" or model is None:
            next_index = int(rng.choice(remaining))
        else:
            probabilities = model.predict_proba(candidate_points[remaining])
            uncertainty = _entropy(probabilities)
            uncertainty /= max(float(np.max(uncertainty)), 1e-12)

            observed_points = candidate_points[selected_array]
            distances = np.linalg.norm(
                candidate_points[remaining, None, :] - observed_points[None, :, :],
                axis=2,
            )
            nearest_distance = np.min(distances, axis=1)
            nearest_distance /= max(float(np.max(nearest_distance)), 1e-12)

            # A modest diversity term prevents repeated queries in one small
            # uncertain region while keeping uncertainty as the main signal.
            acquisition = uncertainty + 0.30 * nearest_distance
            next_index = int(remaining[np.argmax(acquisition)])

        selected.append(next_index)
        available.remove(next_index)

    selected_indices = np.asarray(selected, dtype=np.int64)
    return MappingResult(
        strategy=strategy,
        selected_indices=selected_indices,
        selected_points=candidate_points[selected_indices],
        accuracy=np.asarray(accuracy_history),
        boundary_accuracy=np.asarray(boundary_history),
    )
