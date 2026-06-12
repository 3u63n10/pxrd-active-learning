# Local monitoring and remote access

The monitoring service stores runs, temperature, motor measurements, and
events in SQLite. It uses only the Python standard library for the database,
HTTP API, and dashboard. `pyserial` is optional for live Arduino ingestion.

## Data flow

```text
Arduino -> USB serial JSONL -> local monitor -> SQLite -> browser
```

The local computer adds UTC timestamps when messages are received. Arduino
also sends `uptime_ms`, which preserves experiment-relative time if the local
clock changes.

## Start locally

```bash
python -m pxrd_monitor.server --db data/runs.sqlite --port 8000
```

Open <http://127.0.0.1:8000>. To include Arduino serial input:

```bash
python -m pip install -e ".[monitor]"
python -m pxrd_monitor.server --db data/runs.sqlite --port 8000 \
  --serial-port COM5 --baud 115200
```

The dashboard and API bind to localhost by default.

## Remote viewing with Tailscale

Install Tailscale on the monitoring computer and on the phone/laptop used for
viewing. Keep the Python service on localhost, then run:

```bash
tailscale serve 8000
```

Tailscale Serve exposes the local service only inside the private tailnet and
provides an HTTPS URL. This is preferable to router port forwarding. The
official documentation recommends keeping backends on localhost when relying
on Tailscale identity headers:

- <https://tailscale.com/docs/features/tailscale-serve>

Tailscale Funnel publishes a service to the public internet. It is not
recommended for this laboratory monitor unless application authentication,
authorization, rate limiting, and operational review are added:

- <https://tailscale.com/docs/features/tailscale-funnel>

The first version is monitoring-oriented. Remote motor start/reversal is
intentionally excluded; motion should remain local until physical interlocks,
authenticated commands, command acknowledgements, and a safety review exist.

## Serial message protocol

One compact JSON object is sent per line.

Telemetry:

```json
{
  "type": "telemetry",
  "run_id": "run-20260612-001",
  "uptime_ms": 15240,
  "ambient_c": 24.1,
  "reactor_c": 31.7,
  "motors": [
    {"name": "reservoir", "pwm_percent": 35, "current_a": 0.82, "rpm": 18.2},
    {"name": "central_bar", "pwm_percent": 70, "current_a": 1.41, "rpm": 92.5},
    {"name": "kneader", "pwm_percent": -55, "current_a": 1.86, "rpm": 41.0}
  ]
}
```

Event or error:

```json
{
  "type": "event",
  "run_id": "run-20260612-001",
  "uptime_ms": 15410,
  "level": "ERROR",
  "source": "kneader",
  "code": "OVERCURRENT",
  "message": "Current exceeded configured warning threshold"
}
```

The host stores malformed serial lines as ingestion errors when possible,
rather than silently discarding them.
