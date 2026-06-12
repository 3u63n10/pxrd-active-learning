import unittest

import numpy as np

from Image_Process_Control import ActivityConfig, ImageActivityDetector


class ImageActivityDetectorTests(unittest.TestCase):
    def test_static_frames_remain_inactive(self) -> None:
        detector = ImageActivityDetector(
            ActivityConfig(active_frames_required=2, inactive_frames_required=2)
        )
        frame = np.full((80, 100, 3), 120, dtype=np.uint8)
        results = [detector.analyze(frame) for _ in range(6)]
        self.assertFalse(any(result.is_active for result in results))
        self.assertLess(results[-1].changed_fraction, 0.001)

    def test_sustained_motion_changes_state(self) -> None:
        detector = ImageActivityDetector(
            ActivityConfig(
                active_fraction_threshold=0.02,
                inactive_fraction_threshold=0.005,
                active_frames_required=2,
                inactive_frames_required=2,
                background_alpha=0.01,
            )
        )
        base = np.zeros((80, 100), dtype=np.uint8)
        detector.analyze(base)

        moving_one = base.copy()
        moving_one[20:50, 20:45] = 255
        moving_two = base.copy()
        moving_two[20:50, 35:60] = 255
        first = detector.analyze(moving_one)
        second = detector.analyze(moving_two)

        self.assertFalse(first.is_active)
        self.assertTrue(second.is_active)
        self.assertEqual(second.transition, "started")

        detector.analyze(base)
        stopped = detector.analyze(base)
        self.assertFalse(stopped.is_active)
        self.assertEqual(stopped.transition, "stopped")

    def test_roi_ignores_motion_outside_selected_region(self) -> None:
        detector = ImageActivityDetector(
            ActivityConfig(
                roi=(0.0, 0.0, 0.5, 1.0),
                active_frames_required=1,
            )
        )
        base = np.zeros((60, 100), dtype=np.uint8)
        detector.analyze(base)
        changed = base.copy()
        changed[:, 70:95] = 255
        result = detector.analyze(changed)
        self.assertFalse(result.is_active)


if __name__ == "__main__":
    unittest.main()
