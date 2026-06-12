#ifndef PXRD_TIMED_MOTOR_CONTROL_H
#define PXRD_TIMED_MOTOR_CONTROL_H

#include <Arduino.h>

namespace pxrd {

struct MotorCommand {
  int16_t speedPercent;
  uint32_t durationMs;

  MotorCommand(int16_t speed = 0, uint32_t duration = 0)
      : speedPercent(speed), durationMs(duration) {}
};

class TimedPwmMotor {
 public:
  TimedPwmMotor(uint8_t pwmPin, uint8_t directionPinA, uint8_t directionPinB)
      : pwmPin_(pwmPin),
        directionPinA_(directionPinA),
        directionPinB_(directionPinB),
        speedPercent_(0),
        startTimeMs_(0),
        durationMs_(0),
        running_(false) {}

  void begin() {
    pinMode(pwmPin_, OUTPUT);
    pinMode(directionPinA_, OUTPUT);
    pinMode(directionPinB_, OUTPUT);
    stop();
  }

  // Positive speed rotates forward, negative speed rotates in reverse.
  // A duration of zero means run continuously until stop() is called.
  void start(int16_t speedPercent, uint32_t durationMs = 0) {
    speedPercent_ = constrain(speedPercent, -100, 100);
    durationMs_ = durationMs;
    startTimeMs_ = millis();

    if (speedPercent_ == 0) {
      stop();
      return;
    }

    if (speedPercent_ > 0) {
      digitalWrite(directionPinA_, HIGH);
      digitalWrite(directionPinB_, LOW);
    } else {
      digitalWrite(directionPinA_, LOW);
      digitalWrite(directionPinB_, HIGH);
    }

    const uint8_t dutyCycle =
        static_cast<uint8_t>((static_cast<uint16_t>(abs(speedPercent_)) * 255U) /
                             100U);
    analogWrite(pwmPin_, dutyCycle);
    running_ = true;
  }

  void start(const MotorCommand& command) {
    start(command.speedPercent, command.durationMs);
  }

  // Call frequently from loop(); this function does not block execution.
  void update() {
    if (!running_ || durationMs_ == 0) {
      return;
    }

    const uint32_t elapsedMs = millis() - startTimeMs_;
    if (elapsedMs >= durationMs_) {
      stop();
    }
  }

  void stop() {
    analogWrite(pwmPin_, 0);
    digitalWrite(directionPinA_, LOW);
    digitalWrite(directionPinB_, LOW);
    speedPercent_ = 0;
    durationMs_ = 0;
    running_ = false;
  }

  bool isRunning() const { return running_; }

  int16_t speedPercent() const { return speedPercent_; }

  uint32_t remainingMs() const {
    if (!running_ || durationMs_ == 0) {
      return 0;
    }

    const uint32_t elapsedMs = millis() - startTimeMs_;
    return elapsedMs >= durationMs_ ? 0 : durationMs_ - elapsedMs;
  }

 private:
  uint8_t pwmPin_;
  uint8_t directionPinA_;
  uint8_t directionPinB_;
  int16_t speedPercent_;
  uint32_t startTimeMs_;
  uint32_t durationMs_;
  bool running_;
};

class LagMotorController {
 public:
  LagMotorController(TimedPwmMotor& reservoir, TimedPwmMotor& centralBar,
                     TimedPwmMotor& kneader)
      : reservoir_(reservoir),
        centralBar_(centralBar),
        kneader_(kneader) {}

  void begin() {
    reservoir_.begin();
    centralBar_.begin();
    kneader_.begin();
  }

  void start(const MotorCommand& reservoirCommand,
             const MotorCommand& centralBarCommand,
             const MotorCommand& kneaderCommand) {
    reservoir_.start(reservoirCommand);
    centralBar_.start(centralBarCommand);
    kneader_.start(kneaderCommand);
  }

  void update() {
    reservoir_.update();
    centralBar_.update();
    kneader_.update();
  }

  void stopAll() {
    reservoir_.stop();
    centralBar_.stop();
    kneader_.stop();
  }

  bool anyRunning() const {
    return reservoir_.isRunning() || centralBar_.isRunning() ||
           kneader_.isRunning();
  }

 private:
  TimedPwmMotor& reservoir_;
  TimedPwmMotor& centralBar_;
  TimedPwmMotor& kneader_;
};

}  // namespace pxrd

#endif  // PXRD_TIMED_MOTOR_CONTROL_H
