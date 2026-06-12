#include <TimedMotorControl.h>

// Example pin assignment for an Arduino Uno and three external H-bridges.
// Each motor requires one PWM input and two direction inputs.
pxrd::TimedPwmMotor reservoirMotor(5, 2, 4);
pxrd::TimedPwmMotor centralBarMotor(6, 7, 8);
pxrd::TimedPwmMotor kneaderMotor(9, 10, 11);

pxrd::LagMotorController motors(reservoirMotor, centralBarMotor, kneaderMotor);

const uint8_t emergencyStopPin = 12;
bool programStarted = false;

void setup() {
  pinMode(emergencyStopPin, INPUT_PULLUP);
  motors.begin();

  // A normally closed stop contact connects the input to ground while safe.
  if (digitalRead(emergencyStopPin) == LOW) {
    // Independent speed and time commands for each motor:
    // reservoir:  35% forward for 60 s
    // central bar: 70% forward for 45 s
    // kneader:    55% reverse for 30 s
    motors.start(
        pxrd::MotorCommand(35, 60000UL),
        pxrd::MotorCommand(70, 45000UL),
        pxrd::MotorCommand(-55, 30000UL));
    programStarted = true;
  }
}

void loop() {
  // HIGH means the stop was pressed, its wire broke, or it was disconnected.
  if (digitalRead(emergencyStopPin) == HIGH) {
    motors.stopAll();
    return;
  }

  motors.update();

  if (programStarted && !motors.anyRunning()) {
    programStarted = false;
    // The complete timed program has finished. Add the next experimental
    // action here, or wait for a command from the host computer.
  }
}
