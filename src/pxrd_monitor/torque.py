"""Calibrated motor-current torque estimates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TorqueCalibration:
    no_load_current_a: float
    torque_constant_nm_per_a: float
    gear_ratio: float = 1.0
    drivetrain_efficiency: float = 1.0


def estimate_output_torque(
    current_a: float,
    calibration: TorqueCalibration,
) -> float:
    """Estimate non-negative output torque from calibrated motor current."""
    load_current = max(0.0, abs(current_a) - calibration.no_load_current_a)
    return (
        load_current
        * calibration.torque_constant_nm_per_a
        * calibration.gear_ratio
        * calibration.drivetrain_efficiency
    )
