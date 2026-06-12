"""Small local HTTP dashboard and JSON API."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .database import RunDatabase
from .serial_reader import SerialReader


STATIC_DIR = Path(__file__).with_name("static")
RUN_ACTION = re.compile(r"^/api/runs/([^/]+)/(finish|samples|events)$")


class MonitorHandler(BaseHTTPRequestHandler):
    database: RunDatabase

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length))

    def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_file(STATIC_DIR / "index.html")
            return
        if parsed.path == "/api/health":
            self._send_json({"status": "ok"})
            return
        if parsed.path == "/api/runs":
            self._send_json({"runs": self.database.list_runs()})
            return

        match = RUN_ACTION.match(parsed.path)
        if match:
            run_id, action = match.groups()
            limit = int(parse_qs(parsed.query).get("limit", ["1000"])[0])
            if action == "samples":
                self._send_json(
                    {"run_id": run_id, "samples": self.database.get_samples(run_id, limit)}
                )
                return
            if action == "events":
                self._send_json(
                    {"run_id": run_id, "events": self.database.get_events(run_id, limit)}
                )
                return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        try:
            payload = self._json_body()
            if self.path == "/api/runs":
                run = self.database.create_run(
                    str(payload.get("name", "Untitled run")),
                    run_id=payload.get("run_id"),
                    recipe=payload.get("recipe"),
                    notes=str(payload.get("notes", "")),
                )
                self._send_json(run, HTTPStatus.CREATED)
                return
            if self.path == "/api/telemetry":
                payload["type"] = "telemetry"
                identifier = self.database.add_telemetry(payload)
                self._send_json({"sample_id": identifier}, HTTPStatus.CREATED)
                return
            if self.path == "/api/events":
                payload["type"] = "event"
                identifier = self.database.add_event(payload)
                self._send_json({"event_id": identifier}, HTTPStatus.CREATED)
                return

            match = RUN_ACTION.match(self.path)
            if match and match.group(2) == "finish":
                run = self.database.finish_run(
                    match.group(1),
                    str(payload.get("status", "completed")),
                )
                self._send_json(run)
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except KeyError as exc:
            self._send_json({"error": f"not found: {exc}"}, HTTPStatus.NOT_FOUND)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def build_server(host: str, port: int, database: RunDatabase) -> ThreadingHTTPServer:
    handler = type("ConfiguredMonitorHandler", (MonitorHandler,), {"database": database})
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/runs.sqlite")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--serial-port")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    database = RunDatabase(args.db)
    serial_reader = None
    if args.serial_port:
        serial_reader = SerialReader(database, args.serial_port, args.baud)
        serial_reader.start()

    server = build_server(args.host, args.port, database)
    print(f"PXRD monitor: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if serial_reader:
            serial_reader.stop()
            serial_reader.join(timeout=2)
        database.close()


if __name__ == "__main__":
    main()
