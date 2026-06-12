#ifndef PXRD_PROCESS_TELEMETRY_H
#define PXRD_PROCESS_TELEMETRY_H

#include <Arduino.h>

namespace pxrd {

struct MotorTelemetry {
  const char* name;
  int16_t pwmPercent;
  float currentA;
  float rpm;
  float torqueEstimateNm;

  MotorTelemetry(const char* motorName, int16_t pwm, float current, float speed,
                 float torque = NAN)
      : name(motorName),
        pwmPercent(pwm),
        currentA(current),
        rpm(speed),
        torqueEstimateNm(torque) {}
};

class ProcessTelemetry {
 public:
  ProcessTelemetry(Stream& output, const char* runId)
      : output_(output), runId_(runId) {}

  void setRunId(const char* runId) { runId_ = runId; }

  void publishSample(uint32_t uptimeMs, float ambientC, float reactorC,
                     const MotorTelemetry* motors, size_t motorCount) {
    output_.print(F("{\"type\":\"telemetry\",\"run_id\":"));
    printQuoted(runId_);
    output_.print(F(",\"uptime_ms\":"));
    output_.print(uptimeMs);
    printOptionalFloat(F(",\"ambient_c\":"), ambientC, 2);
    printOptionalFloat(F(",\"reactor_c\":"), reactorC, 2);
    output_.print(F(",\"motors\":["));

    for (size_t index = 0; index < motorCount; ++index) {
      if (index > 0) {
        output_.print(',');
      }
      const MotorTelemetry& motor = motors[index];
      output_.print(F("{\"name\":"));
      printQuoted(motor.name);
      output_.print(F(",\"pwm_percent\":"));
      output_.print(motor.pwmPercent);
      printOptionalFloat(F(",\"current_a\":"), motor.currentA, 3);
      printOptionalFloat(F(",\"rpm\":"), motor.rpm, 2);
      printOptionalFloat(F(",\"torque_estimate_nm\":"),
                         motor.torqueEstimateNm, 4);
      output_.print('}');
    }

    output_.println(F("]}"));
  }

  void publishEvent(uint32_t uptimeMs, const char* level, const char* source,
                    const char* code, const char* message) {
    output_.print(F("{\"type\":\"event\",\"run_id\":"));
    printQuoted(runId_);
    output_.print(F(",\"uptime_ms\":"));
    output_.print(uptimeMs);
    output_.print(F(",\"level\":"));
    printQuoted(level);
    output_.print(F(",\"source\":"));
    printQuoted(source);
    output_.print(F(",\"code\":"));
    printQuoted(code);
    output_.print(F(",\"message\":"));
    printQuoted(message);
    output_.println('}');
  }

 private:
  Stream& output_;
  const char* runId_;

  void printOptionalFloat(const __FlashStringHelper* key, float value,
                          uint8_t digits) {
    output_.print(key);
    if (isnan(value)) {
      output_.print(F("null"));
    } else {
      output_.print(value, digits);
    }
  }

  void printQuoted(const char* text) {
    output_.print('"');
    if (text != nullptr) {
      while (*text != '\0') {
        const char character = *text++;
        if (character == '"' || character == '\\') {
          output_.print('\\');
          output_.print(character);
        } else if (character == '\n') {
          output_.print(F("\\n"));
        } else if (character != '\r') {
          output_.print(character);
        }
      }
    }
    output_.print('"');
  }
};

}  // namespace pxrd

#endif  // PXRD_PROCESS_TELEMETRY_H
