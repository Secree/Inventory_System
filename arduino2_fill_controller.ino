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
const int BUZZER_PIN = 4;

const float DETECTION_DISTANCE_CM = 7.0;
const unsigned long FILL_START_DELAY_MS = 3000;
const unsigned long MIN_FILL_TIME_MS = 1500;
const unsigned long LEVEL_CONFIRM_MS = 400;
const unsigned long LOOP_DELAY_MS = 120;

const int RELAY_ON = LOW;
const int RELAY_OFF = HIGH;
const int LEVEL_WATER_DETECTED_STATE = HIGH; // <-- flipped from LOW to HIGH

bool fillEnabled = false;
bool isFilling = false;
bool gallonDetected = false;
unsigned long gallonDetectedAt = 0;
unsigned long fillStartedAt = 0;
unsigned long levelDetectedAt = 0;

void buzzFullAlert() {
  for (int i = 0; i < 3; i++) {
    tone(BUZZER_PIN, 2000, 1000);
    delay(1100);
  }
  noTone(BUZZER_PIN);
}

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
    Serial.println("FILL:ENABLED");
  } else if (cmd == "DISABLE") {
    fillEnabled = false;
    isFilling = false;
    gallonDetected = false;
    gallonDetectedAt = 0;
    fillStartedAt = 0;
    levelDetectedAt = 0;
    setValve(false);
    Serial.println("FILL:DISABLED");
  } else if (cmd == "STATUS") {
    Serial.print("FILL:STATE=");
    Serial.println(fillEnabled ? "ENABLED" : "DISABLED");
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
  pinMode(BUZZER_PIN, OUTPUT);

  setValve(false);
  noTone(BUZZER_PIN);

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
        buzzFullAlert();
        stopFilling("FILLING:COMPLETE");
        fillEnabled = false;
        Serial.println("FILL:DISABLED");
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