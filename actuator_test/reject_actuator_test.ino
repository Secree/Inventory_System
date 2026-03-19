/*
 * Reject Actuator Test Sketch
 *
 * Purpose:
 * - Verify reject actuator wiring and direction using L298N driver.
 * - Run manual commands over Serial Monitor at 9600 baud.
 *
 * Wiring (same as automated_refill_system.ino):
 *   ENA -> D10 (PWM)
 *   IN1 -> D7
 *   IN2 -> D8
 *
 * Serial commands:
 *   HELP            Show commands
 *   EXTEND          Push reject actuator out
 *   RETRACT         Pull reject actuator back
 *   STOP            Stop actuator immediately
 *   CYCLE           Extend, hold, retract, stop
 *   SPEED <0-255>   Set PWM speed
 *   STATUS          Show current speed and state
 */

const int REJECT_ACTUATOR_ENA = 10;
const int REJECT_ACTUATOR_IN1 = 7;
const int REJECT_ACTUATOR_IN2 = 8;

int rejectSpeed = 200;
const unsigned long REJECT_PUSH_TIME_MS = 5000;
const unsigned long REJECT_RETRACT_TIME_MS = 5000;

String rejectState = "STOPPED";

void setup() {
  Serial.begin(9600);

  // Set safe output levels before pinMode to avoid startup twitch.
  digitalWrite(REJECT_ACTUATOR_IN1, LOW);
  digitalWrite(REJECT_ACTUATOR_IN2, LOW);
  analogWrite(REJECT_ACTUATOR_ENA, 0);

  pinMode(REJECT_ACTUATOR_ENA, OUTPUT);
  pinMode(REJECT_ACTUATOR_IN1, OUTPUT);
  pinMode(REJECT_ACTUATOR_IN2, OUTPUT);

  stopRejectActuator();

  while (!Serial) { ; }

  Serial.println("READY:REJECT_ACTUATOR_TEST");
  printHelp();
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    cmd.toUpperCase();
    handleCommand(cmd);
  }
}

void handleCommand(String cmd) {
  if (cmd.length() == 0) {
    return;
  }

  if (cmd == "HELP") {
    printHelp();
  } else if (cmd == "EXTEND") {
    extendRejectActuator();
    Serial.println("REJECT:EXTENDING");
  } else if (cmd == "RETRACT") {
    retractRejectActuator();
    Serial.println("REJECT:RETRACTING");
  } else if (cmd == "STOP") {
    stopRejectActuator();
    Serial.println("REJECT:STOPPED");
  } else if (cmd == "CYCLE") {
    Serial.println("REJECT:CYCLE_START");
    extendRejectActuator();
    delay(REJECT_PUSH_TIME_MS);
    retractRejectActuator();
    delay(REJECT_RETRACT_TIME_MS);
    stopRejectActuator();
    Serial.println("REJECT:CYCLE_DONE");
  } else if (cmd.startsWith("SPEED ")) {
    String value = cmd.substring(6);
    int parsed = value.toInt();

    if (parsed < 0 || parsed > 255) {
      Serial.println("ERROR:SPEED_RANGE_0_TO_255");
      return;
    }

    rejectSpeed = parsed;
    // Re-apply speed if currently moving.
    if (rejectState != "STOPPED") {
      analogWrite(REJECT_ACTUATOR_ENA, rejectSpeed);
    }

    Serial.print("REJECT:SPEED=");
    Serial.println(rejectSpeed);
  } else if (cmd == "STATUS") {
    Serial.print("REJECT:STATE=");
    Serial.println(rejectState);
    Serial.print("REJECT:SPEED=");
    Serial.println(rejectSpeed);
  } else {
    Serial.print("ERROR:UNKNOWN_COMMAND ");
    Serial.println(cmd);
  }
}

void extendRejectActuator() {
  digitalWrite(REJECT_ACTUATOR_IN1, HIGH);
  digitalWrite(REJECT_ACTUATOR_IN2, LOW);
  analogWrite(REJECT_ACTUATOR_ENA, rejectSpeed);
  rejectState = "EXTENDING";
}

void retractRejectActuator() {
  digitalWrite(REJECT_ACTUATOR_IN1, LOW);
  digitalWrite(REJECT_ACTUATOR_IN2, HIGH);
  analogWrite(REJECT_ACTUATOR_ENA, rejectSpeed);
  rejectState = "RETRACTING";
}

void stopRejectActuator() {
  digitalWrite(REJECT_ACTUATOR_IN1, LOW);
  digitalWrite(REJECT_ACTUATOR_IN2, LOW);
  analogWrite(REJECT_ACTUATOR_ENA, 0);
  rejectState = "STOPPED";
}

void printHelp() {
  Serial.println("Commands:");
  Serial.println("  HELP");
  Serial.println("  EXTEND");
  Serial.println("  RETRACT");
  Serial.println("  STOP");
  Serial.println("  CYCLE");
  Serial.println("  SPEED <0-255>");
  Serial.println("  STATUS");
}
