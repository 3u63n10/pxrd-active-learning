import unittest

import numpy as np

from pxrd_active import SyntheticPhaseMap, make_grid, run_mapping


class SyntheticPhaseMapTests(unittest.TestCase):
    def test_grid_shape_and_limits(self) -> None:
        grid = make_grid(7)
        self.assertEqual(grid.shape, (49, 2))
        self.assertTrue(np.all(grid >= 0.0))
        self.assertTrue(np.all(grid <= 1.0))

    def test_observations_are_reproducible(self) -> None:
        world = SyntheticPhaseMap(observation_noise=0.5, seed=9)
        points = make_grid(8)
        ids = np.arange(len(points))
        first = world.observe(points, observation_ids=ids)
        second = world.observe(points, observation_ids=ids)
        np.testing.assert_array_equal(first, second)


class MappingTests(unittest.TestCase):
    def test_mapping_respects_budget(self) -> None:
        world = SyntheticPhaseMap()
        candidates = make_grid(10)
        evaluation = make_grid(20)
        result = run_mapping(
            world,
            candidates,
            evaluation,
            strategy="rf_uncertainty",
            budget=16,
            initial_samples=5,
        )
        self.assertEqual(len(result.selected_indices), 16)
        self.assertEqual(len(np.unique(result.selected_indices)), 16)
        self.assertEqual(result.accuracy.shape, (12,))
        self.assertTrue(np.all((result.accuracy >= 0.0) & (result.accuracy <= 1.0)))


if __name__ == "__main__":
    unittest.main()
