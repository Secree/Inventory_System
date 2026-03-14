/*
 * PRESSURE SENSOR TEST - OUT/SCK DIGITAL MODULE ONLY
 *
 * Wiring:
 *   VCC -> 5V
 *   GND -> GND
 *   OUT -> D2
 *   SCK -> D3
 *
 * Serial commands at 9600 baud:
 *   READ   -> one reading
 *   ZERO   -> set current reading as baseline
 *   STATUS -> print raw, absolute, and relative pressure
 *   AUTO   -> print readings continuously every 500 ms
 *   STOP   -> stop AUTO mode
 */

const int PRESSURE_OUT_PIN = 2;
const int PRESSURE_SCK_PIN = 3;

const long PRESSURE_RAW_AT_0 = 0;
const long PRESSURE_RAW_AT_MAX = 8388607;
const float PRESSURE_MAX = 710.0;
const long PRESSURE_READ_TIMEOUT_SENTINEL = -2147483647L;
const unsigned long READ_INTERVAL_MS = 500;

bool autoMode = false;
unsigned long lastReadAt = 0;
float baselinePressure = -1.0;

long readPressureRaw24();
float rawToPressure(long raw);
float toRelativePressure(float absolutePressure, float zeroBaseline);
void printPressureLine();

void setup() {
  Serial.begin(9600);

  pinMode(PRESSURE_OUT_PIN, INPUT);
  pinMode(PRESSURE_SCK_PIN, OUTPUT);
  digitalWrite(PRESSURE_SCK_PIN, LOW);

  while (!Serial) { ; }

  Serial.println("PRESSURE SENSOR TEST READY");
  Serial.println("Wiring: VCC->5V, GND->GND, OUT->D2, SCK->D3");
  Serial.println("Commands: READ | ZERO | STATUS | AUTO | STOP");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toUpperCase();

    if (command == "READ") {
      printPressureLine();
    } else if (command == "ZERO") {
      long raw = readPressureRaw24();
      if (raw == PRESSURE_READ_TIMEOUT_SENTINEL) {
        Serial.println("ERROR: Sensor timeout while zeroing");
      } else {
        baselinePressure = rawToPressure(raw);
        Serial.print("BASELINE SET: ");
        Serial.println(baselinePressure, 1);
      }
    } else if (command == "STATUS") {
      printPressureLine();
    } else if (command == "AUTO") {
      autoMode = true;
      lastReadAt = 0;
      Serial.println("AUTO:ON");
    } else if (command == "STOP") {
      autoMode = false;
      Serial.println("AUTO:OFF");
    } else {
      Serial.print("ERROR: Unknown command: ");
      Serial.println(command);
    }
  }

  if (autoMode && millis() - lastReadAt >= READ_INTERVAL_MS) {
    lastReadAt = millis();
    printPressureLine();
  }
}

void printPressureLine() {
  long raw = readPressureRaw24();
  if (raw == PRESSURE_READ_TIMEOUT_SENTINEL) {
    Serial.println("ERROR: Sensor timeout");
    return;
  }

  float absolutePressure = rawToPressure(raw);
  float relativePressure = toRelativePressure(absolutePressure, baselinePressure);

  Serial.print("RAW:");
  Serial.print(raw);
  Serial.print(" ABS:");
  Serial.print(absolutePressure, 1);
  Serial.print(" REL:");
  Serial.println(relativePressure, 1);
}

long readPressureRaw24() {
  unsigned long start = millis();
  while (digitalRead(PRESSURE_OUT_PIN)) {
    if (millis() - start > 1000) {
      return PRESSURE_READ_TIMEOUT_SENTINEL;
    }
  }

  long result = 0;
  for (int i = 0; i < 24; i++) {
    digitalWrite(PRESSURE_SCK_PIN, HIGH);
    digitalWrite(PRESSURE_SCK_PIN, LOW);
    result = result << 1;
    if (digitalRead(PRESSURE_OUT_PIN)) {
      result++;
    }
  }

  result = result ^ 0x800000;

  for (byte i = 0; i < 3; i++) {
    digitalWrite(PRESSURE_SCK_PIN, HIGH);
    digitalWrite(PRESSURE_SCK_PIN, LOW);
  }

  return result;
}

float rawToPressure(long raw) {
  float span = (float)(PRESSURE_RAW_AT_MAX - PRESSURE_RAW_AT_0);
  if (span == 0.0) {
    return 0.0;
  }

  float pressure = ((float)(raw - PRESSURE_RAW_AT_0) / span) * PRESSURE_MAX;
  if (pressure < 0.0) {
    pressure = 0.0;
  }
  return pressure;
}

float toRelativePressure(float absolutePressure, float zeroBaseline) {
  if (zeroBaseline < 0.0) {
    return absolutePressure;
  }

  float relative = absolutePressure - zeroBaseline;
  if (relative < 0.0) {
    relative = 0.0;
  }
  return relative;
}
