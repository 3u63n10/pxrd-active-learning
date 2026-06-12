"""Background ingestion of newline-delimited JSON from Arduino serial."""

from __future__ import annotations

import json
import threading
from typing import Any

from .database import RunDatabase


class SerialReader(threading.Thread):
    def __init__(
        self,
        database: RunDatabase,
        port: str,
        baud: int = 115200,
    ) -> None:
        super().__init__(daemon=True, name="arduino-serial-reader")
        self.database = database
        self.port = port
        self.baud = baud
        self._stop_event = threading.Event()
        self._serial: Any = None

    def stop(self) -> None:
        self._stop_event.set()
        if self._serial is not None:
            self._serial.close()

    def run(self) -> None:
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError(
                "Serial ingestion requires: python -m pip install -e '.[monitor]'"
            ) from exc

        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=1.0)
            while not self._stop_event.is_set():
                raw_line = self._serial.readline()
                if not raw_line:
                    continue
                text = raw_line.decode("utf-8", errors="replace").strip()
                try:
                    self.database.ingest(json.loads(text))
                except Exception as exc:
                    self.database.add_event(
                        {
                            "type": "event",
                            "level": "ERROR",
                            "source": "serial",
                            "code": "INGEST_ERROR",
                            "message": str(exc),
                            "details": {"line": text[:500]},
                        }
                    )
        except Exception as exc:
            self.database.add_event(
                {
                    "type": "event",
                    "level": "CRITICAL",
                    "source": "serial",
                    "code": "SERIAL_READER_STOPPED",
                    "message": str(exc),
                }
            )
