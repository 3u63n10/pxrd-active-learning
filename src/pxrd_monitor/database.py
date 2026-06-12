"""SQLite persistence for experimental runs, telemetry, and events."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class RunDatabase:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _create_schema(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    recipe_json TEXT NOT NULL DEFAULT '{}',
                    notes TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    recorded_at TEXT NOT NULL,
                    uptime_ms INTEGER,
                    ambient_c REAL,
                    reactor_c REAL
                );

                CREATE TABLE IF NOT EXISTS motor_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_id INTEGER NOT NULL REFERENCES samples(id)
                        ON DELETE CASCADE,
                    motor_name TEXT NOT NULL,
                    pwm_percent REAL,
                    current_a REAL,
                    rpm REAL,
                    torque_estimate_nm REAL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT REFERENCES runs(id) ON DELETE CASCADE,
                    recorded_at TEXT NOT NULL,
                    uptime_ms INTEGER,
                    level TEXT NOT NULL,
                    source TEXT NOT NULL,
                    code TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_samples_run_time
                    ON samples(run_id, recorded_at);
                CREATE INDEX IF NOT EXISTS idx_events_run_time
                    ON events(run_id, recorded_at);
                """
            )

    def create_run(
        self,
        name: str,
        *,
        run_id: str | None = None,
        recipe: dict[str, Any] | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        identifier = run_id or f"run-{uuid.uuid4().hex[:12]}"
        started_at = utc_now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO runs
                    (id, name, status, started_at, recipe_json, notes)
                VALUES (?, ?, 'running', ?, ?, ?)
                """,
                (identifier, name, started_at, json.dumps(recipe or {}), notes),
            )
        return self.get_run(identifier)

    def ensure_run(self, run_id: str) -> dict[str, Any]:
        existing = self.get_run(run_id, required=False)
        if existing is not None:
            return existing
        return self.create_run(run_id, run_id=run_id)

    def finish_run(self, run_id: str, status: str = "completed") -> dict[str, Any]:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE runs SET status = ?, ended_at = ?
                WHERE id = ?
                """,
                (status, utc_now(), run_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(run_id)
        return self.get_run(run_id)

    def get_run(
        self,
        run_id: str,
        *,
        required: bool = True,
    ) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            if required:
                raise KeyError(run_id)
            return None
        return self._decode_run(row)

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._decode_run(row) for row in rows]

    def add_telemetry(self, message: dict[str, Any]) -> int:
        run_id = str(message["run_id"])
        self.ensure_run(run_id)
        recorded_at = str(message.get("recorded_at") or utc_now())
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO samples
                    (run_id, recorded_at, uptime_ms, ambient_c, reactor_c)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    recorded_at,
                    message.get("uptime_ms"),
                    message.get("ambient_c"),
                    message.get("reactor_c"),
                ),
            )
            sample_id = int(cursor.lastrowid)
            for motor in message.get("motors", []):
                self._connection.execute(
                    """
                    INSERT INTO motor_samples
                        (sample_id, motor_name, pwm_percent, current_a, rpm,
                         torque_estimate_nm)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sample_id,
                        motor["name"],
                        motor.get("pwm_percent"),
                        motor.get("current_a"),
                        motor.get("rpm"),
                        motor.get("torque_estimate_nm"),
                    ),
                )
        return sample_id

    def add_event(self, message: dict[str, Any]) -> int:
        run_id = message.get("run_id")
        if run_id:
            self.ensure_run(str(run_id))
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO events
                    (run_id, recorded_at, uptime_ms, level, source, code,
                     message, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    message.get("recorded_at") or utc_now(),
                    message.get("uptime_ms"),
                    str(message.get("level", "INFO")).upper(),
                    str(message.get("source", "system")),
                    str(message.get("code", "MESSAGE")),
                    str(message.get("message", "")),
                    json.dumps(message.get("details", {})),
                ),
            )
        return int(cursor.lastrowid)

    def ingest(self, message: dict[str, Any]) -> int:
        message_type = message.get("type")
        if message_type == "telemetry":
            return self.add_telemetry(message)
        if message_type == "event":
            return self.add_event(message)
        raise ValueError(f"unsupported message type: {message_type!r}")

    def get_samples(self, run_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM samples
                WHERE run_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
            samples = [dict(row) for row in reversed(rows)]
            for sample in samples:
                motors = self._connection.execute(
                    """
                    SELECT motor_name AS name, pwm_percent, current_a, rpm,
                           torque_estimate_nm
                    FROM motor_samples WHERE sample_id = ?
                    ORDER BY motor_name
                    """,
                    (sample["id"],),
                ).fetchall()
                sample["motors"] = [dict(motor) for motor in motors]
        return samples

    def get_events(self, run_id: str, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM events
                WHERE run_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
        events = []
        for row in rows:
            event = dict(row)
            event["details"] = json.loads(event.pop("details_json"))
            events.append(event)
        return events

    @staticmethod
    def _decode_run(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["recipe"] = json.loads(result.pop("recipe_json"))
        return result
