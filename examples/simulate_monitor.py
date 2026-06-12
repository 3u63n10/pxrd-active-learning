"""Write a short synthetic run into the local monitoring database."""

from __future__ import annotations

import argparse
import math
import time

from pxrd_monitor import RunDatabase


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/runs.sqlite")
    parser.add_argument("--samples", type=int, default=90)
    parser.add_argument("--delay", type=float, default=0.05)
    args = parser.parse_args()

    database = RunDatabase(args.db)
    run = database.create_run(
        "Synthetic hardware test",
        recipe={"reservoir_pwm": 35, "central_bar_pwm": 70, "kneader_pwm": -55},
        notes="Generated monitor demonstration; no physical measurements.",
    )
    try:
        for index in range(args.samples):
            elapsed_ms = index * 1000
            load_peak = 1.4 * math.exp(-((index - 55) / 8) ** 2)
            database.add_telemetry(
                {
                    "type": "telemetry",
                    "run_id": run["id"],
                    "uptime_ms": elapsed_ms,
                    "ambient_c": 24.0 + 0.15 * math.sin(index / 15),
                    "reactor_c": 24.5 + 0.065 * index + 0.2 * math.sin(index / 8),
                    "motors": [
                        {
                            "name": "reservoir",
                            "pwm_percent": 35,
                            "current_a": 0.72 + 0.03 * math.sin(index / 5),
                            "rpm": 18.0,
                        },
                        {
                            "name": "central_bar",
                            "pwm_percent": 70,
                            "current_a": 1.25 + 0.05 * math.sin(index / 3),
                            "rpm": 93.0,
                        },
                        {
                            "name": "kneader",
                            "pwm_percent": -55,
                            "current_a": 1.45 + load_peak,
                            "rpm": 42.0 - 5.0 * load_peak,
                        },
                    ],
                }
            )
            if index == 55:
                database.add_event(
                    {
                        "type": "event",
                        "run_id": run["id"],
                        "uptime_ms": elapsed_ms,
                        "level": "WARNING",
                        "source": "kneader",
                        "code": "HIGH_LOAD",
                        "message": "Synthetic current peak detected",
                    }
                )
            time.sleep(args.delay)
        database.finish_run(run["id"])
        print(f"Created run {run['id']} in {args.db}")
    finally:
        database.close()


if __name__ == "__main__":
    main()
