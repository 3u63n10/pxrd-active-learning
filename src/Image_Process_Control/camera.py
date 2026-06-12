"""Camera runner that stores visual activity metrics in the run database."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from pxrd_monitor import RunDatabase

from .activity import ActivityConfig, ImageActivityDetector


def parse_roi(text: str) -> tuple[float, float, float, float]:
    values = tuple(float(value) for value in text.split(","))
    if len(values) != 4:
        raise argparse.ArgumentTypeError("ROI must be x0,y0,x1,y1")
    return values  # type: ignore[return-value]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/runs.sqlite")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--roi", type=parse_roi, default=(0.0, 0.0, 1.0, 1.0))
    parser.add_argument("--expect-activity", action="store_true")
    parser.add_argument("--no-activity-seconds", type=float, default=20.0)
    parser.add_argument("--evidence-dir")
    args = parser.parse_args()

    try:
        import cv2
    except ImportError as exc:
        raise SystemExit(
            "Camera capture requires: python -m pip install -e '.[image]'"
        ) from exc

    database = RunDatabase(args.db)
    database.ensure_run(args.run_id)
    detector = ImageActivityDetector(ActivityConfig(roi=args.roi))
    camera = cv2.VideoCapture(args.camera)
    if not camera.isOpened():
        database.add_event(
            {
                "run_id": args.run_id,
                "level": "ERROR",
                "source": "Image_Process_Control",
                "code": "CAMERA_OPEN_FAILED",
                "message": f"Could not open camera index {args.camera}",
            }
        )
        database.close()
        raise SystemExit(f"Could not open camera index {args.camera}")

    evidence_dir = Path(args.evidence_dir) if args.evidence_dir else None
    if evidence_dir:
        evidence_dir.mkdir(parents=True, exist_ok=True)

    started_at = time.monotonic()
    last_active_at = started_at
    no_activity_reported = False
    try:
        while True:
            loop_started = time.monotonic()
            success, frame = camera.read()
            if not success:
                database.add_event(
                    {
                        "run_id": args.run_id,
                        "level": "ERROR",
                        "source": "Image_Process_Control",
                        "code": "FRAME_READ_FAILED",
                        "message": "Camera returned no frame",
                    }
                )
                time.sleep(1.0)
                continue

            metrics = detector.analyze(frame)
            uptime_ms = int((loop_started - started_at) * 1000)
            evidence_path = None

            if metrics.transition and evidence_dir:
                evidence_path = evidence_dir / (
                    f"{args.run_id}-{uptime_ms}-{metrics.transition}.jpg"
                )
                cv2.imwrite(str(evidence_path), frame)

            database.add_image_sample(
                {
                    "run_id": args.run_id,
                    "uptime_ms": uptime_ms,
                    "activity_score": metrics.activity_score,
                    "changed_fraction": metrics.changed_fraction,
                    "mean_difference": metrics.mean_difference,
                    "brightness": metrics.brightness,
                    "sharpness": metrics.sharpness,
                    "is_active": metrics.is_active,
                    "evidence_path": str(evidence_path) if evidence_path else None,
                }
            )

            if metrics.is_active:
                last_active_at = loop_started
                no_activity_reported = False
            if metrics.transition:
                database.add_event(
                    {
                        "run_id": args.run_id,
                        "uptime_ms": uptime_ms,
                        "level": "INFO",
                        "source": "Image_Process_Control",
                        "code": f"ACTIVITY_{metrics.transition.upper()}",
                        "message": f"Visual activity {metrics.transition}",
                    }
                )

            idle_seconds = loop_started - last_active_at
            if (
                args.expect_activity
                and idle_seconds >= args.no_activity_seconds
                and not no_activity_reported
            ):
                database.add_event(
                    {
                        "run_id": args.run_id,
                        "uptime_ms": uptime_ms,
                        "level": "WARNING",
                        "source": "Image_Process_Control",
                        "code": "NO_ACTIVITY",
                        "message": (
                            f"No sustained visual activity for {idle_seconds:.1f} s"
                        ),
                    }
                )
                no_activity_reported = True

            delay = args.interval - (time.monotonic() - loop_started)
            if delay > 0:
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        camera.release()
        database.close()


if __name__ == "__main__":
    main()
