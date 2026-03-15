/*
 * SECOND ARDUINO - SOLENOID FILL CONTROLLER
 *
 * Behavior:
 * - After NO DEFECT decision (ENABLE command), ultrasonic detection is active
 * - Detect gallon with ultrasonic sensor
 * - Wait 3 seconds of stable detection before opening valve
 * - Stop valve immediately when liquid level sensor detects water
 * - Stop valve if gallon is removed while filling
 *
 * Serial commands are supported for integration with the Python app:
 * ENABLE | DISABLE | STATUS
 */

const int TRIG_PIN = 9;
const int ECHO_PIN = 10;
const int RELAY_PIN = 7;
const int LEVEL_SENSOR_PIN = 8;
const int MOTOR_EN_PIN = 5;
const int MOTOR_IN1_PIN = 6;
const int MOTOR_IN2_PIN = 4;

const float DETECTION_DISTANCE_CM = 7.0;
const unsigned long FILL_START_DELAY_MS = 3000;
const unsigned long MIN_FILL_TIME_MS = 1500;
const unsigned long LEVEL_CONFIRM_MS = 400;
const unsigned long LOOP_DELAY_MS = 120;
const int CONVEYOR_SPEED = 200;

const int RELAY_ON = LOW;
const int RELAY_OFF = HIGH;
const int LEVEL_WATER_DETECTED_STATE = HIGH; // <-- flipped from LOW to HIGH

bool fillEnabled = true;
bool isFilling = false;
bool gallonDetected = false;
bool conveyorRunning = false;
unsigned long gallonDetectedAt = 0;
unsigned long fillStartedAt = 0;
unsigned long levelDetectedAt = 0;

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long durationUs = pulseIn(ECHO_PIN, HIGH, 60000);
  if (durationUs == 0) {
    return 999.0;
  }

  return (durationUs * 0.034f) / 2.0f;
}

void setValve(bool open) {
  digitalWrite(RELAY_PIN, open ? RELAY_ON : RELAY_OFF);
}

void startConveyor() {
  if (conveyorRunning) {
    return;
  }

  digitalWrite(MOTOR_IN1_PIN, HIGH);
  digitalWrite(MOTOR_IN2_PIN, LOW);
  analogWrite(MOTOR_EN_PIN, CONVEYOR_SPEED);
  conveyorRunning = true;
  Serial.println("CONVEYOR:MOVING");
}

void stopConveyor() {
  if (!conveyorRunning) {
    return;
  }

  analogWrite(MOTOR_EN_PIN, 0);
  digitalWrite(MOTOR_IN1_PIN, LOW);
  digitalWrite(MOTOR_IN2_PIN, LOW);
  conveyorRunning = false;
  Serial.println("CONVEYOR:STOPPED");
}

void stopFilling(const char* reason) {
  setValve(false);
  isFilling = false;
  gallonDetected = false;
  gallonDetectedAt = 0;
  fillStartedAt = 0;
  levelDetectedAt = 0;
  Serial.println(reason);
}

void handleCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "ENABLE") {
    fillEnabled = true;
    isFilling = false;
    gallonDetected = false;
    gallonDetectedAt = 0;
    fillStartedAt = 0;
    levelDetectedAt = 0;
    setValve(false);
    startConveyor();
    Serial.println("FILL:ENABLED");
  } else if (cmd == "DISABLE") {
    fillEnabled = false;
    isFilling = false;
    gallonDetected = false;
    gallonDetectedAt = 0;
    fillStartedAt = 0;
    levelDetectedAt = 0;
    setValve(false);
    stopConveyor();
    Serial.println("FILL:DISABLED");
  } else if (cmd == "STATUS") {
    Serial.print("FILL:STATE=");
    Serial.println(fillEnabled ? "ENABLED" : "DISABLED");
    Serial.print("CONVEYOR:");
    Serial.println(conveyorRunning ? "MOVING" : "STOPPED");
    Serial.print("FILLING:");
    Serial.println(isFilling ? "YES" : "NO");
    Serial.print("DISTANCE:");
    Serial.println(readDistanceCm(), 1);
    Serial.print("LEVEL_SENSOR_RAW:");
    Serial.println(digitalRead(LEVEL_SENSOR_PIN));
    Serial.print("WATER_DETECTED:");
    Serial.println((digitalRead(LEVEL_SENSOR_PIN) == LEVEL_WATER_DETECTED_STATE) ? "YES" : "NO");
  }
}

void setup() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LEVEL_SENSOR_PIN, INPUT_PULLUP);
  pinMode(MOTOR_EN_PIN, OUTPUT);
  pinMode(MOTOR_IN1_PIN, OUTPUT);
  pinMode(MOTOR_IN2_PIN, OUTPUT);

  setValve(false);
  stopConveyor();

  Serial.begin(9600);
  while (!Serial) { ; }

  Serial.println("READY");
  Serial.println("Commands: ENABLE | DISABLE | STATUS");
  Serial.print("DETECTION_DISTANCE_CM:");
  Serial.println(DETECTION_DISTANCE_CM, 1);
  Serial.print("FILL_START_DELAY_MS:");
  Serial.println(FILL_START_DELAY_MS);
  Serial.print("LEVEL_SENSOR_INITIAL:");
  Serial.println(digitalRead(LEVEL_SENSOR_PIN)); // shows state at boot
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    handleCommand(command);
  }

  const float distance = fillEnabled ? readDistanceCm() : 999.0;
  const bool gallonInRange = fillEnabled && (distance <= DETECTION_DISTANCE_CM);
  const bool waterNearFull = (digitalRead(LEVEL_SENSOR_PIN) == LEVEL_WATER_DETECTED_STATE);

  if (fillEnabled && !isFilling && !gallonInRange) {
    startConveyor();
  } else {
    stopConveyor();
  }

  if (gallonInRange) {
    if (!gallonDetected) {
      gallonDetected = true;
      gallonDetectedAt = millis();
      Serial.println("GALLON:DETECTED");
    }
  } else {
    if (fillEnabled && gallonDetected && !isFilling) {
      Serial.println("GALLON:REMOVED");
    }
    gallonDetected = false;
    gallonDetectedAt = 0;
  }

  if (fillEnabled && !isFilling) {
    setValve(false);
  }

  if (fillEnabled && !isFilling && gallonDetected) {
    unsigned long detectedForMs = millis() - gallonDetectedAt;
    if (detectedForMs >= FILL_START_DELAY_MS) {
      setValve(true);
      isFilling = true;
      fillStartedAt = millis();
      levelDetectedAt = 0;
      Serial.println("FILLING:START");
    }
  }

  if (isFilling) {
    if (waterNearFull) {
      if (levelDetectedAt == 0) {
        levelDetectedAt = millis();
      }

      bool minFillElapsed = (millis() - fillStartedAt) >= MIN_FILL_TIME_MS;
      bool levelStable = (millis() - levelDetectedAt) >= LEVEL_CONFIRM_MS;
      if (minFillElapsed && levelStable) {
        stopFilling("FILLING:COMPLETE");
      }
    } else {
      levelDetectedAt = 0;
    }

    if (!gallonInRange) {
      stopFilling("FILLING:STOPPED_NO_GALLON");
    }
  }

  delay(LOOP_DELAY_MS);
}