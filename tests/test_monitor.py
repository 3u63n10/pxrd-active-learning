import tempfile
import unittest
from pathlib import Path

from pxrd_monitor import RunDatabase, TorqueCalibration, estimate_output_torque


class RunDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        path = Path(self.temporary_directory.name) / "runs.sqlite"
        self.database = RunDatabase(path)

    def tearDown(self) -> None:
        self.database.close()
        self.temporary_directory.cleanup()

    def test_run_telemetry_and_event_round_trip(self) -> None:
        run = self.database.create_run("test", run_id="run-test")
        self.database.add_telemetry(
            {
                "run_id": run["id"],
                "uptime_ms": 1000,
                "ambient_c": 23.4,
                "reactor_c": 29.2,
                "motors": [
                    {
                        "name": "kneader",
                        "pwm_percent": 55,
                        "current_a": 1.8,
                        "rpm": 41.0,
                    }
                ],
            }
        )
        self.database.add_event(
            {
                "run_id": run["id"],
                "level": "WARNING",
                "source": "kneader",
                "code": "HIGH_LOAD",
                "message": "load increased",
            }
        )

        samples = self.database.get_samples(run["id"])
        events = self.database.get_events(run["id"])
        self.assertEqual(samples[0]["ambient_c"], 23.4)
        self.assertEqual(samples[0]["motors"][0]["name"], "kneader")
        self.assertEqual(events[0]["code"], "HIGH_LOAD")

    def test_image_sample_round_trip(self) -> None:
        run = self.database.create_run("image-test", run_id="run-image")
        self.database.add_image_sample(
            {
                "run_id": run["id"],
                "uptime_ms": 1500,
                "activity_score": 0.72,
                "changed_fraction": 0.08,
                "mean_difference": 0.05,
                "brightness": 0.44,
                "sharpness": 0.02,
                "is_active": True,
            }
        )
        samples = self.database.get_image_samples(run["id"])
        self.assertEqual(len(samples), 1)
        self.assertTrue(samples[0]["is_active"])
        self.assertAlmostEqual(samples[0]["activity_score"], 0.72)

    def test_finish_run(self) -> None:
        self.database.create_run("test", run_id="run-finish")
        finished = self.database.finish_run("run-finish")
        self.assertEqual(finished["status"], "completed")
        self.assertIsNotNone(finished["ended_at"])


class TorqueTests(unittest.TestCase):
    def test_calibrated_output_torque(self) -> None:
        calibration = TorqueCalibration(
            no_load_current_a=0.5,
            torque_constant_nm_per_a=0.08,
            gear_ratio=20.0,
            drivetrain_efficiency=0.75,
        )
        estimate = estimate_output_torque(1.5, calibration)
        self.assertAlmostEqual(estimate, 1.2)

    def test_no_load_current_returns_zero(self) -> None:
        calibration = TorqueCalibration(0.5, 0.08)
        self.assertEqual(estimate_output_torque(0.3, calibration), 0.0)


if __name__ == "__main__":
    unittest.main()
