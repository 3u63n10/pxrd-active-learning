# Arduino motor control

`src/TimedMotorControl.h` provides non-blocking speed and time control for the
three conceptual LAG-device motors:

- rotating reservoir;
- central rotating bar;
- eccentric kneading bar.

The fixed wall scraper does not require a motor.

## Electrical interface

The current implementation assumes brushed DC motors connected through
external H-bridge drivers. Each motor uses:

- one PWM-capable Arduino pin for relative speed;
- two digital pins for direction;
- a separate motor power supply sized for the motor current.

The recommended controller is now an Arduino Mega 2560 because the complete
sensor and encoder set exceeds the comfortable pin budget of an Uno. Install
the `arduino` folder as an Arduino library, then open
`examples/LagMotorDemo/LagMotorDemo.ino`.

Do not power a motor directly from an Arduino output pin. Connect the Arduino
ground and motor-driver logic ground together. The emergency stop should also
interrupt motor power in hardware; the software input shown in the example is
only an additional stop request.

The example assumes a normally closed emergency-stop contact between Mega pin
`31` and ground; see
[`../docs/arduino_wiring.md`](../docs/arduino_wiring.md). Pressing the stop,
breaking its wire, or disconnecting it produces a `HIGH` input and stops all
three software commands.

## Commands

```cpp
pxrd::MotorCommand(speedPercent, durationMs)
```

- `speedPercent`: from `-100` to `100`; the sign selects direction.
- `durationMs`: run time in milliseconds; `0` means continuous operation.

The example starts all three motors with independent commands:

```cpp
motors.start(
    pxrd::MotorCommand(35, 60000UL),
    pxrd::MotorCommand(70, 45000UL),
    pxrd::MotorCommand(-55, 30000UL));
```

Call `motors.update()` on every pass through `loop()`. Timing uses `millis()`
and does not block serial communication, sensors, or future host commands.
`motors.stopAll()` immediately commands all PWM outputs to zero.

## Speed limitation

The percentage is an open-loop PWM command, not a measured rotational speed.
Actual RPM depends on the motor, driver, supply voltage, load, and gearing.
Reliable RPM control requires an encoder or tachometer and a feedback
controller. Motor pin assignments, safe speed limits, and rotation directions
must be confirmed on the physical prototype before unattended operation.

## Telemetry and error log

`src/ProcessTelemetry.h` writes newline-delimited JSON records over serial.
The host monitor stores these records in SQLite. Open
`examples/TelemetryProtocolDemo/TelemetryProtocolDemo.ino` for a compilable
protocol example.

The example values are synthetic placeholders. Replace them with readings from
the selected ambient sensor, reactor RTD interface, motor-current sensors, and
encoders after the electrical design is fixed.
