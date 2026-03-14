/*
 * SECOND ARDUINO - SOLENOID FILL CONTROLLER
 *
 * Behavior:
 * - Wait for ENABLE command from main app (after no defect)
 * - Detect gallon with ultrasonic sensor
 * - Wait 3 seconds after detection
 * - Open solenoid valve
 * - Close valve when level sensor reports near full
 * - Safety close if gallon moves away
 */

// Pin Definitions
const int TRIG_PIN = 9;
const int ECHO_PIN = 10;
const int RELAY_PIN = 7;
const int LEVEL_SENSOR_PIN = 8;

// Settings
const float DETECTION_DISTANCE_CM = 20.0;
const unsigned long FILL_START_DELAY_MS = 3000;
const int RELAY_ON = LOW;   // Most relay modules are ACTIVE LOW
const int RELAY_OFF = HIGH;

bool isFilling = false;
bool fillEnabled = false;
bool gallonDetected = false;
unsigned long gallonDetectedAt = 0;

void setup() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LEVEL_SENSOR_PIN, INPUT);

  digitalWrite(RELAY_PIN, RELAY_OFF); // Start with solenoid closed
  Serial.begin(9600);
  while (!Serial) { ; }

  Serial.println("READY");
  Serial.println("Commands: ENABLE | DISABLE | STATUS");
}

float getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout
  if (duration == 0) return 999.0;
  return (duration * 0.034) / 2.0;
}

void handleCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "ENABLE") {
    fillEnabled = true;
    Serial.println("FILL:ENABLED");
  } else if (cmd == "DISABLE") {
    fillEnabled = false;
    isFilling = false;
    gallonDetected = false;
    digitalWrite(RELAY_PIN, RELAY_OFF);
    Serial.println("FILL:DISABLED");
  } else if (cmd == "STATUS") {
    Serial.print("FILL:STATE=");
    Serial.println(fillEnabled ? "ENABLED" : "DISABLED");
    Serial.print("FILLING:");
    Serial.println(isFilling ? "YES" : "NO");
  }
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    handleCommand(command);
  }

  float distance = getDistance();
  int levelSensor = digitalRead(LEVEL_SENSOR_PIN);
  bool waterNearFull = (levelSensor == LOW); // LOW = water detected
  bool gallonInRange = (distance <= DETECTION_DISTANCE_CM);

  // Track first moment gallon appears in range.
  if (fillEnabled && gallonInRange) {
    if (!gallonDetected) {
      gallonDetected = true;
      gallonDetectedAt = millis();
      Serial.println("GALLON:DETECTED");
    }
  } else {
    gallonDetected = false;
    gallonDetectedAt = 0;
  }

  // Open valve only after 3-second stable detection window.
  if (fillEnabled && !isFilling && gallonDetected && !waterNearFull) {
    if (millis() - gallonDetectedAt >= FILL_START_DELAY_MS) {
      digitalWrite(RELAY_PIN, RELAY_ON);
      isFilling = true;
      Serial.println("FILLING:START");
    }
  }

  // Close valve when near full.
  if (isFilling && waterNearFull) {
    digitalWrite(RELAY_PIN, RELAY_OFF);
    isFilling = false;
    fillEnabled = false;
    Serial.println("FILLING:COMPLETE");
  }

  // Safety: close if gallon moves away while filling.
  if (isFilling && !gallonInRange && !waterNearFull) {
    digitalWrite(RELAY_PIN, RELAY_OFF);
    isFilling = false;
    fillEnabled = false;
    Serial.println("FILLING:STOPPED_NO_GALLON");
  }

  delay(200);
}
