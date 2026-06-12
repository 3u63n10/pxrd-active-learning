"""Compare random and uncertainty-based sampling on a synthetic phase map."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pxrd_active import SyntheticPhaseMap, make_grid, run_mapping


def main() -> None:
    world = SyntheticPhaseMap(observation_noise=0.12, seed=17)
    candidates = make_grid(25)
    evaluation = make_grid(120)
    random_result = run_mapping(
        world,
        candidates,
        evaluation,
        strategy="random",
        budget=50,
        seed=8,
    )
    active_result = run_mapping(
        world,
        candidates,
        evaluation,
        strategy="rf_uncertainty",
        budget=50,
        seed=8,
    )

    output_path = Path(__file__).resolve().parents[1] / "docs" / "mapping_demo.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    phase_grid = world.phase(evaluation).reshape(120, 120)
    figure, axes = plt.subplots(1, 3, figsize=(13.0, 3.8))

    axes[0].imshow(
        phase_grid,
        origin="lower",
        extent=(0, 1, 0, 1),
        cmap="viridis",
        interpolation="nearest",
    )
    axes[0].scatter(
        active_result.selected_points[:, 0],
        active_result.selected_points[:, 1],
        s=15,
        facecolors="white",
        edgecolors="black",
        linewidths=0.5,
    )
    axes[0].set_title("Synthetic phase map\nRF-selected experiments")
    axes[0].set_xlabel("Ligand/metal ratio (scaled)")
    axes[0].set_ylabel("Additive amount (scaled)")

    experiments = np.arange(8, 51)
    axes[1].plot(experiments, random_result.accuracy, label="Random", linewidth=2)
    axes[1].plot(
        experiments,
        active_result.accuracy,
        label="RF uncertainty",
        linewidth=2,
    )
    axes[1].set_title("Global map accuracy\n(preliminary single run)")
    axes[1].set_xlabel("Experiments")
    axes[1].set_ylabel("Accuracy")
    axes[1].set_ylim(0.35, 1.0)
    axes[1].legend(frameon=False)

    axes[2].plot(
        experiments,
        random_result.boundary_accuracy,
        label="Random",
        linewidth=2,
    )
    axes[2].plot(
        experiments,
        active_result.boundary_accuracy,
        label="RF uncertainty",
        linewidth=2,
    )
    axes[2].set_title("Boundary-region accuracy\n(preliminary single run)")
    axes[2].set_xlabel("Experiments")
    axes[2].set_ylabel("Accuracy")
    axes[2].set_ylim(0.2, 1.0)

    figure.tight_layout()
    figure.savefig(output_path, dpi=180)
    plt.close(figure)

    print(f"Random final accuracy: {random_result.accuracy[-1]:.3f}")
    print(f"RF final accuracy:     {active_result.accuracy[-1]:.3f}")
    print(f"Figure written to:     {output_path}")


if __name__ == "__main__":
    main()
