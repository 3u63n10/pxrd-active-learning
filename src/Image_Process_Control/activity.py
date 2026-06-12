"""Frame-difference activity analysis with hysteresis and ROI support."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


FloatImage = NDArray[np.float32]


@dataclass(frozen=True)
class ActivityConfig:
    roi: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
    difference_threshold: float = 0.08
    active_fraction_threshold: float = 0.025
    inactive_fraction_threshold: float = 0.012
    active_frames_required: int = 2
    inactive_frames_required: int = 4
    background_alpha: float = 0.04
    resize_width: int = 160

    def __post_init__(self) -> None:
        x0, y0, x1, y1 = self.roi
        if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
            raise ValueError("roi must be normalized as (x0, y0, x1, y1)")
        if not 0.0 < self.difference_threshold <= 1.0:
            raise ValueError("difference_threshold must be in (0, 1]")
        if not 0.0 <= self.inactive_fraction_threshold <= self.active_fraction_threshold:
            raise ValueError("inactive threshold must not exceed active threshold")
        if self.active_frames_required < 1 or self.inactive_frames_required < 1:
            raise ValueError("frame requirements must be positive")


@dataclass(frozen=True)
class ActivityMetrics:
    frame_index: int
    activity_score: float
    changed_fraction: float
    mean_difference: float
    brightness: float
    sharpness: float
    is_active: bool
    transition: str | None


class ImageActivityDetector:
    """Detect sustained visual activity without treating it as a safety input."""

    def __init__(self, config: ActivityConfig | None = None) -> None:
        self.config = config or ActivityConfig()
        self._background: FloatImage | None = None
        self._frame_index = 0
        self._active_count = 0
        self._inactive_count = 0
        self._is_active = False

    @property
    def is_active(self) -> bool:
        return self._is_active

    def reset(self) -> None:
        self._background = None
        self._frame_index = 0
        self._active_count = 0
        self._inactive_count = 0
        self._is_active = False

    def analyze(self, frame: NDArray[np.generic]) -> ActivityMetrics:
        gray = self._prepare_frame(frame)
        self._frame_index += 1
        brightness = float(np.mean(gray))
        sharpness = self._sharpness(gray)

        if self._background is None:
            self._background = gray.copy()
            return ActivityMetrics(
                frame_index=self._frame_index,
                activity_score=0.0,
                changed_fraction=0.0,
                mean_difference=0.0,
                brightness=brightness,
                sharpness=sharpness,
                is_active=False,
                transition=None,
            )

        difference = np.abs(gray - self._background)
        changed_fraction = float(
            np.mean(difference >= self.config.difference_threshold)
        )
        mean_difference = float(np.mean(difference))
        activity_score = float(
            np.clip(
                0.65
                * changed_fraction
                / max(self.config.active_fraction_threshold, 1e-9)
                + 0.35
                * mean_difference
                / max(self.config.difference_threshold, 1e-9),
                0.0,
                1.0,
            )
        )

        transition = self._update_state(changed_fraction)
        alpha = self.config.background_alpha
        self._background = (1.0 - alpha) * self._background + alpha * gray

        return ActivityMetrics(
            frame_index=self._frame_index,
            activity_score=activity_score,
            changed_fraction=changed_fraction,
            mean_difference=mean_difference,
            brightness=brightness,
            sharpness=sharpness,
            is_active=self._is_active,
            transition=transition,
        )

    def _update_state(self, changed_fraction: float) -> str | None:
        if changed_fraction >= self.config.active_fraction_threshold:
            self._active_count += 1
            self._inactive_count = 0
        elif changed_fraction <= self.config.inactive_fraction_threshold:
            self._inactive_count += 1
            self._active_count = 0
        else:
            self._active_count = 0
            self._inactive_count = 0

        if not self._is_active and self._active_count >= self.config.active_frames_required:
            self._is_active = True
            self._active_count = 0
            return "started"
        if self._is_active and self._inactive_count >= self.config.inactive_frames_required:
            self._is_active = False
            self._inactive_count = 0
            return "stopped"
        return None

    def _prepare_frame(self, frame: NDArray[np.generic]) -> FloatImage:
        array = np.asarray(frame)
        if array.ndim == 3:
            if array.shape[2] < 3:
                raise ValueError("color frames must have at least three channels")
            # OpenCV supplies BGR; these luminance weights remain suitable for
            # activity detection even when RGB arrays are supplied.
            gray = (
                0.114 * array[..., 0]
                + 0.587 * array[..., 1]
                + 0.299 * array[..., 2]
            )
        elif array.ndim == 2:
            gray = array
        else:
            raise ValueError("frame must have shape (height, width[, channels])")

        gray = gray.astype(np.float32)
        if np.issubdtype(array.dtype, np.integer):
            gray /= float(np.iinfo(array.dtype).max)
        else:
            maximum = float(np.nanmax(gray)) if gray.size else 1.0
            if maximum > 1.0:
                gray /= 255.0
        gray = np.nan_to_num(gray, nan=0.0, posinf=1.0, neginf=0.0)
        gray = np.clip(gray, 0.0, 1.0)

        height, width = gray.shape
        x0, y0, x1, y1 = self.config.roi
        left, right = int(x0 * width), max(int(x1 * width), 1)
        top, bottom = int(y0 * height), max(int(y1 * height), 1)
        cropped = gray[top:bottom, left:right]
        if cropped.size == 0:
            raise ValueError("roi produced an empty image")

        target_width = min(self.config.resize_width, cropped.shape[1])
        target_height = max(
            1, int(round(cropped.shape[0] * target_width / cropped.shape[1]))
        )
        row_indices = np.linspace(0, cropped.shape[0] - 1, target_height).astype(int)
        column_indices = np.linspace(
            0, cropped.shape[1] - 1, target_width
        ).astype(int)
        return cropped[np.ix_(row_indices, column_indices)].astype(np.float32)

    @staticmethod
    def _sharpness(gray: FloatImage) -> float:
        if min(gray.shape) < 2:
            return 0.0
        vertical = np.diff(gray, axis=0)
        horizontal = np.diff(gray, axis=1)
        return float(np.mean(vertical * vertical) + np.mean(horizontal * horizontal))
