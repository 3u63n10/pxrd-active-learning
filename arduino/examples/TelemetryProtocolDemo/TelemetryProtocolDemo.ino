#include <ProcessTelemetry.h>

pxrd::ProcessTelemetry telemetry(Serial, "run-arduino-demo");

uint32_t lastSampleMs = 0;
bool warningSent = false;

void setup() {
  Serial.begin(115200);
  telemetry.publishEvent(millis(), "INFO", "controller", "STARTUP",
                         "Telemetry protocol demo started");
}

void loop() {
  const uint32_t now = millis();
  if (now - lastSampleMs < 1000UL) {
    return;
  }
  lastSampleMs = now;

  // Replace these demonstration values with measurements from the selected
  // ambient sensor, RTD interface, current sensors, and encoders.
  const float ambientC = 24.0;
  const float reactorC = 24.0 + 0.002 * static_cast<float>(now / 1000UL);
  pxrd::MotorTelemetry motors[] = {
      pxrd::MotorTelemetry("reservoir", 35, 0.72, 18.0),
      pxrd::MotorTelemetry("central_bar", 70, 1.25, 93.0),
      pxrd::MotorTelemetry("kneader", -55, 1.45, 42.0),
  };
  telemetry.publishSample(now, ambientC, reactorC, motors, 3);

  if (!warningSent && now >= 10000UL) {
    telemetry.publishEvent(now, "WARNING", "kneader", "DEMO_HIGH_LOAD",
                           "Demonstration warning; no physical fault detected");
    warningSent = true;
  }
}
