/*
 * Primary Actuator Step-by-Step Test
 *
 * Purpose:
 * - Move the first actuator bit by bit using short motor pulses.
 * - Tune step size, pause, and speed from Serial Monitor.
 *
 * Wiring (same as automated_refill_system.ino):
 *   ENA -> D9  (PWM)
 *   IN1 -> D5
 *   IN2 -> D6
 *
 * Serial Monitor: 9600 baud, Newline
 *
 * Commands:
 *   HELP                Show all commands
 *   STEP                One extend step (short pulse)
 *   BACK                One retract step
 *   AUTO_EXTEND         Repeating extend steps until STOP
 *   AUTO_RETRACT        Repeating retract steps until STOP
 *   STOP                Stop immediately and cancel auto mode
 *   SPEED <0-255>       Set PWM speed
 *   STEP_MS <10-2000>   Set pulse duration per step
 *   PAUSE_MS <0-5000>   Set pause between steps in auto mode
 *   STATUS              Show current settings and mode
 */

const int ACTUATOR_ENA = 9;
const int ACTUATOR_IN1 = 5;
const int ACTUATOR_IN2 = 6;

int actuatorSpeed = 130;
unsigned long stepMs = 250;
unsigned long pauseMs = 350;

bool autoExtend = false;
bool autoRetract = false;

bool pulseActive = false;
unsigned long pulseStartedAt = 0;
unsigned long lastStepEndedAt = 0;

String motionState = "STOPPED";

void setup() {
  Serial.begin(9600);

  // Preload safe outputs to avoid twitch on startup.
  digitalWrite(ACTUATOR_IN1, LOW);
  digitalWrite(ACTUATOR_IN2, LOW);
  analogWrite(ACTUATOR_ENA, 0);

  pinMode(ACTUATOR_ENA, OUTPUT);
  pinMode(ACTUATOR_IN1, OUTPUT);
  pinMode(ACTUATOR_IN2, OUTPUT);

  stopActuator();

  while (!Serial) { ; }

  Serial.println("READY:PRIMARY_ACTUATOR_STEP_TEST");
  printHelp();
}

void loop() {
  handleSerial();
  runAutoStepEngine();
}

void handleSerial() {
  if (Serial.available() <= 0) {
    return;
  }

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  cmd.toUpperCase();

  if (cmd.length() == 0) {
    return;
  }

  if (cmd == "HELP") {
    printHelp();
    return;
  }

  if (cmd == "STEP") {
    autoExtend = false;
    autoRetract = false;
    startExtendPulse();
    Serial.println("ACTUATOR:STEP_EXTEND");
    return;
  }

  if (cmd == "BACK") {
    autoExtend = false;
    autoRetract = false;
    startRetractPulse();
    Serial.println("ACTUATOR:STEP_RETRACT");
    return;
  }

  if (cmd == "AUTO_EXTEND") {
    autoExtend = true;
    autoRetract = false;
    Serial.println("ACTUATOR:AUTO_EXTEND_ON");
    return;
  }

  if (cmd == "AUTO_RETRACT") {
    autoExtend = false;
    autoRetract = true;
    Serial.println("ACTUATOR:AUTO_RETRACT_ON");
    return;
  }

  if (cmd == "STOP") {
    autoExtend = false;
    autoRetract = false;
    stopActuator();
    Serial.println("ACTUATOR:STOPPED");
    return;
  }

  if (cmd == "STATUS") {
    printStatus();
    return;
  }

  if (cmd.startsWith("SPEED ")) {
    int value = cmd.substring(6).toInt();
    if (value < 0 || value > 255) {
      Serial.println("ERROR:SPEED_RANGE_0_TO_255");
      return;
    }
    actuatorSpeed = value;
    Serial.print("ACTUATOR:SPEED=");
    Serial.println(actuatorSpeed);
    return;
  }

  if (cmd.startsWith("STEP_MS ")) {
    long value = cmd.substring(8).toInt();
    if (value < 10 || value > 2000) {
      Serial.println("ERROR:STEP_MS_RANGE_10_TO_2000");
      return;
    }
    stepMs = (unsigned long)value;
    Serial.print("ACTUATOR:STEP_MS=");
    Serial.println(stepMs);
    return;
  }

  if (cmd.startsWith("PAUSE_MS ")) {
    long value = cmd.substring(9).toInt();
    if (value < 0 || value > 5000) {
      Serial.println("ERROR:PAUSE_MS_RANGE_0_TO_5000");
      return;
    }
    pauseMs = (unsigned long)value;
    Serial.print("ACTUATOR:PAUSE_MS=");
    Serial.println(pauseMs);
    return;
  }

  Serial.print("ERROR:UNKNOWN_COMMAND ");
  Serial.println(cmd);
}

void runAutoStepEngine() {
  unsigned long now = millis();

  // End active pulse when its step duration is done.
  if (pulseActive && (now - pulseStartedAt >= stepMs)) {
    stopActuator();
    pulseActive = false;
    lastStepEndedAt = now;
  }

  // Start next pulse in auto mode after pause interval.
  if (!pulseActive) {
    if (autoExtend && (now - lastStepEndedAt >= pauseMs)) {
      startExtendPulse();
    } else if (autoRetract && (now - lastStepEndedAt >= pauseMs)) {
      startRetractPulse();
    }
  }
}

void startExtendPulse() {
  digitalWrite(ACTUATOR_IN1, HIGH);
  digitalWrite(ACTUATOR_IN2, LOW);
  analogWrite(ACTUATOR_ENA, actuatorSpeed);
  pulseActive = true;
  pulseStartedAt = millis();
  motionState = "EXTENDING";
}

void startRetractPulse() {
  digitalWrite(ACTUATOR_IN1, LOW);
  digitalWrite(ACTUATOR_IN2, HIGH);
  analogWrite(ACTUATOR_ENA, actuatorSpeed);
  pulseActive = true;
  pulseStartedAt = millis();
  motionState = "RETRACTING";
}

void stopActuator() {
  digitalWrite(ACTUATOR_IN1, LOW);
  digitalWrite(ACTUATOR_IN2, LOW);
  analogWrite(ACTUATOR_ENA, 0);
  motionState = "STOPPED";
}

void printStatus() {
  Serial.print("ACTUATOR:STATE=");
  Serial.println(motionState);
  Serial.print("ACTUATOR:SPEED=");
  Serial.println(actuatorSpeed);
  Serial.print("ACTUATOR:STEP_MS=");
  Serial.println(stepMs);
  Serial.print("ACTUATOR:PAUSE_MS=");
  Serial.println(pauseMs);
  Serial.print("ACTUATOR:AUTO_EXTEND=");
  Serial.println(autoExtend ? "ON" : "OFF");
  Serial.print("ACTUATOR:AUTO_RETRACT=");
  Serial.println(autoRetract ? "ON" : "OFF");
}

void printHelp() {
  Serial.println("Commands:");
  Serial.println("  HELP");
  Serial.println("  STEP");
  Serial.println("  BACK");
  Serial.println("  AUTO_EXTEND");
  Serial.println("  AUTO_RETRACT");
  Serial.println("  STOP");
  Serial.println("  SPEED <0-255>");
  Serial.println("  STEP_MS <10-2000>");
  Serial.println("  PAUSE_MS <0-5000>");
  Serial.println("  STATUS");
}
