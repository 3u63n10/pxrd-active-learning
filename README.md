# PXRD Active Learning

Sequential experimental design for PXRD-guided phase mapping and phase
purification.

This repository develops and benchmarks methods that suggest which synthesis
condition should be tested next. It is intended for later integration with
experimental observations derived from powder X-ray diffraction (PXRD).

> **Current status:** no experimental dataset is included. Synthetic phase
> maps are used to develop, test, and compare sequential-design strategies
> before experimental integration.

## Scientific workflow

Each future experiment will connect synthesis conditions to an assigned phase
and PXRD-derived quality metrics. The model will operate in two modes:

- **Mapping mode:** improve the condition-phase map near boundaries and poorly
  sampled regions.
- **Purification mode:** refine conditions around a promising pattern to
  enhance the target phase and suppress competing phases.

The current prototype implements:

- a reproducible two-dimensional synthetic phase-map generator;
- configurable observation noise near phase boundaries;
- random sequential sampling as a baseline;
- random-forest uncertainty sampling with spatial diversity for mapping;
- global and boundary-region map-accuracy metrics;
- an initial Arduino header for timed PWM control of three LAG-device motors;
- a local SQLite run database and read-only process-monitoring website;
- a reproducible demonstration figure and unit tests.

![Synthetic phase map and learning curves](docs/mapping_demo.png)

## Quick start

```bash
python -m pip install -e .
python examples/run_mapping_demo.py
python -m unittest discover -s tests -v
```

The example writes `docs/mapping_demo.png` and prints the final mapping
accuracy for both strategies.

## Roadmap

- [x] Synthetic phase-map environment
- [x] Random-sampling baseline
- [x] Random-forest uncertainty sampling
- [ ] Gaussian-process classification for mapping
- [ ] Boundary-aware acquisition functions
- [ ] Bayesian optimization for purification mode
- [ ] Robustness benchmarks against observation noise
- [ ] Interface for PXRD-derived experimental records
- [x] Initial Arduino motor speed and timing interface
- [ ] Encoder-based closed-loop RPM control
- [x] Run, telemetry, and error/event persistence in SQLite
- [x] Local web dashboard with optional Tailscale access

## Repository layout

```text
src/pxrd_active/       Core simulation and sequential-design code
examples/              Reproducible demonstrations
tests/                 Unit tests
docs/                  Generated figures and method notes
arduino/               Motor-control header, example, and hardware notes
```

## Arduino motor control

The initial firmware interface is documented in
[`arduino/README.md`](arduino/README.md). It controls reservoir, central-bar,
and kneader motors using independent signed PWM percentages and run times.
This module is currently a hardware-interface prototype and has not yet been
validated on the physical device.

## Hardware and monitoring

The proposed basic hardware, temperature/current sensing, safety chain, and
torque-estimation limits are described in
[`docs/hardware.md`](docs/hardware.md), with the detailed Arduino Mega wiring
in [`docs/arduino_wiring.md`](docs/arduino_wiring.md). The local database, web dashboard,
serial protocol, and private remote viewing with Tailscale Serve are described
in [`docs/monitoring.md`](docs/monitoring.md).

Start the monitor with:

```bash
python -m pxrd_monitor.server --db data/runs.sqlite --port 8000
```

![Local process monitor](docs/monitor_demo.png)

The first version is intentionally read-only with respect to motor motion.

## Scope

This is a methodological research prototype. Synthetic results demonstrate
software behavior and do not represent experimental discovery or phase
identification.

## License

MIT
