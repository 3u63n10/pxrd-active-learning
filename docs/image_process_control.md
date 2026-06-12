# Image_Process_Control

`Image_Process_Control` measures visual activity in a selected reactor region.
It is intended to answer questions such as:

- Is material visibly moving while the kneader is commanded to run?
- Did visible motion start or stop?
- Is activity becoming irregular between nominally identical runs?
- Did the camera become dark, blocked, or badly out of focus?

It does **not** identify chemical phases and must not replace the emergency
stop, lid interlock, current protection, or operator inspection.

## Method

For every frame, the routine:

1. crops a normalized region of interest (ROI);
2. converts it to grayscale and downsamples it;
3. compares it with a slowly updated background image;
4. calculates changed-pixel fraction, mean difference, brightness, sharpness,
   and a normalized activity score;
5. applies separate start/stop thresholds and consecutive-frame requirements;
6. stores the metrics in SQLite and writes transition/error events.

Separate start and stop thresholds provide hysteresis and reduce flickering
between active and inactive states.

## Camera placement

- Fix the camera rigidly to the enclosure, not to a vibrating motor plate.
- Keep exposure, focus, white balance, and illumination as constant as
  possible.
- Illuminate the reactor with diffuse flicker-free LEDs.
- Avoid reflections from rotating metal and direct views of bright lamps.
- Select an ROI containing the material or moving interface, not the motor.
- Prevent people and unrelated equipment from entering the ROI.

The default routine stores metrics only. Images are saved only when
`--evidence-dir` is supplied, and then only at activity transitions.

## Run with a camera

Install the image option:

```bash
python -m pip install -e ".[image]"
```

Start a run in the database, then:

```bash
python -m Image_Process_Control.camera \
  --db data/runs.sqlite \
  --run-id run-20260612-001 \
  --camera 0 \
  --roi 0.15,0.20,0.85,0.90 \
  --interval 0.5 \
  --expect-activity \
  --no-activity-seconds 20
```

ROI values are normalized fractions: `x0,y0,x1,y1`.

## Calibration

1. Record 30-60 seconds with the system stationary.
2. Record normal motion at low, medium, and high loads.
3. Review changed fraction and activity score in the web dashboard.
4. Set the active threshold above stationary vibration/light noise.
5. Set the inactive threshold lower than the active threshold.
6. Validate with changes in illumination, material color, fill level, and RPM.
7. Compare visual events with current and encoder data.

The most useful failure signal is usually agreement between multiple sources:
motor command present, encoder RPM abnormal, current elevated, and visual
activity absent.

## Privacy and storage

Aim the camera only at the device. Do not record people or unrelated laboratory
areas. Metrics require little storage and are the default. If evidence images
are enabled, define retention and access rules before remote viewing.
