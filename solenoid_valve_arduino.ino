/*
 * Automatic Gallon Refill System with Ultrasonic Sensor
 * Controls a solenoid valve to refill gallons when detected
 *
 * Hardware Setup:
 * - Solenoid Valve (12V)
 *   Connect solenoid to relay module output
 *
 * - Relay Module (5V trigger)
 *   VCC  -> Arduino 5V
 *   GND  -> Arduino GND
 *   IN   -> Arduino Pin A5 (SOLENOID_PIN)
 *   COM  -> 12V power supply +
 *   NO   -> Solenoid +
 *   Solenoid - -> 12V power supply GND
 *
 * - Ultrasonic Sensor (HC-SR04)
 *   VCC  -> Arduino 5V
 *   GND  -> Arduino GND
 *   TRIG -> Arduino Pin 9 (TRIG_PIN)
 *   ECHO -> Arduino Pin 10 (ECHO_PIN)
 *
 * - Arduino USB -> Raspberry Pi USB port (or PC)
 *
 * Operation:
 *   - Ultrasonic sensor continuously monitors for gallon presence
 *   - When gallon detected within range, valve opens to refill
 *   - Valve closes when gallon removed or refill complete
 *
 * Serial Commands (9600 baud):
 *   "OPEN"   -> Manually opens the solenoid valve
 *   "CLOSE"  -> Manually closes the solenoid valve
 *   "STATUS" -> Reports current valve state and sensor distance
 *   "PULSE:<ms>" -> Opens valve for <ms> milliseconds, then closes
 *   "AUTO"   -> Enable automatic mode (default)
 *   "MANUAL" -> Disable automatic mode
 *
 * Serial Responses:
 *   "VALVE:OPEN"    -> Valve is open
 *   "VALVE:CLOSED"  -> Valve is closed
 *   "GALLON:DETECTED" -> Gallon detected by sensor
 *   "GALLON:REMOVED"  -> Gallon removed
 *   "READY"         -> System initialized
 */

// Pin Configuration
const int SOLENOID_PIN = A5;   // Analog pin A5 used as digital output to relay
const int TRIG_PIN = 9;        // Ultrasonic sensor trigger pin
const int ECHO_PIN = 10;       // Ultrasonic sensor echo pin
const int STATUS_LED_PIN = 13; // Built-in LED mirrors valve state

// Ultrasonic Sensor Configuration
const int DETECTION_DISTANCE_CM = 30;  // Distance in cm to detect gallon presence
const int SAMPLE_DELAY_MS = 100;       // Delay between sensor readings

// Relay Logic (set to true if relay is active-LOW, false if active-HIGH)
// Most relay modules are active-LOW (LOW = relay ON = valve OPEN)
const bool RELAY_ACTIVE_LOW = true;

// State tracking
bool valveOpen = false;
bool gallonDetected = false;
bool autoMode = true;  // Automatic mode enabled by default
long lastDistance = 0;

// Serial command buffer
String commandBuffer = "";

void setup() {
  // Initialize serial communication
  Serial.begin(9600);

  // Configure output pins
  pinMode(SOLENOID_PIN, OUTPUT);
  pinMode(STATUS_LED_PIN, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Ensure valve starts CLOSED
  setValve(false);

  // Wait for serial connection
  while (!Serial) {
    ;
  }

  Serial.println("READY");
  Serial.println("Automatic Gallon Refill System");
  Serial.println("Commands: OPEN | CLOSE | STATUS | PULSE:<ms> | AUTO | MANUAL");
  Serial.println("Auto mode: ENABLED");
}

void loop() {
  // Read serial commands
  while (Serial.available() > 0) {
    char c = (char)Serial.read();

    if (c == '\n' || c == '\r') {
      commandBuffer.trim();
      if (commandBuffer.length() > 0) {
        processCommand(commandBuffer);
      }
      commandBuffer = "";
    } else {
      commandBuffer += c;
    }
  }

  // Automatic mode: check ultrasonic sensor and control valve
  if (autoMode) {
    checkGallonPresence();
  }

  // Small delay between loop iterations
  delay(SAMPLE_DELAY_MS);
}

// ── Command Processor ────────────────────────────────────────────────────────

void processCommand(String cmd) {
  cmd.toUpperCase();

  if (cmd == "OPEN") {
    autoMode = false;  // Disable auto mode for manual control
    setValve(true);
    Serial.println("VALVE:OPEN");
    Serial.println("Auto mode: DISABLED");

  } else if (cmd == "CLOSE") {
    autoMode = false;  // Disable auto mode for manual control
    setValve(false);
    Serial.println("VALVE:CLOSED");
    Serial.println("Auto mode: DISABLED");

  } else if (cmd == "STATUS") {
    Serial.println(valveOpen ? "VALVE:OPEN" : "VALVE:CLOSED");
    Serial.println(gallonDetected ? "GALLON:DETECTED" : "GALLON:REMOVED");
    Serial.print("DISTANCE:");
    Serial.print(lastDistance);
    Serial.println("cm");
    Serial.print("Auto mode: ");
    Serial.println(autoMode ? "ENABLED" : "DISABLED");

  } else if (cmd == "AUTO") {
    autoMode = true;
    Serial.println("Auto mode: ENABLED");

  } else if (cmd == "MANUAL") {
    autoMode = false;
    Serial.println("Auto mode: DISABLED");

  } else if (cmd.startsWith("PULSE:")) {
    String msStr = cmd.substring(6);
    long duration = msStr.toInt();

    if (duration > 0) {
      pulseValve(duration);
    } else {
      Serial.println("ERROR:Invalid pulse duration");
    }

  } else {
    Serial.println("ERROR:Unknown command - use OPEN | CLOSE | STATUS | PULSE:<ms>");
  }
}

// ── Valve Control Helpers ────────────────────────────────────────────────────

void setValve(bool open) {
  valveOpen = open;

  // Write relay signal (respect active-LOW or active-HIGH logic)
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(SOLENOID_PIN, open ? LOW : HIGH);
  } else {
    digitalWrite(SOLENOID_PIN, open ? HIGH : LOW);
  }

  // Mirror state on status LED
  digitalWrite(STATUS_LED_PIN, open ? HIGH : LOW);
}

void pulseValve(long durationMs) {
  Serial.print("VALVE:PULSE:");
  Serial.println(durationMs);

  setValve(true);
  delay(durationMs);
  setValve(false);

  Serial.println("VALVE:CLOSED");
}

// ── Ultrasonic Sensor Functions ──────────────────────────────────────────────

long measureDistance() {
  // Clear the trigger pin
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  // Send 10 microsecond pulse to trigger
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Read the echo pin (timeout after 30ms = ~5m max range)
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);

  // Calculate distance in cm (speed of sound = 343 m/s)
  // Distance = (duration / 2) / 29.1
  if (duration == 0) {
    return -1;  // No echo received (out of range or error)
  }

  long distance = duration * 0.034 / 2;
  return distance;
}

void checkGallonPresence() {
  long distance = measureDistance();
  lastDistance = distance;

  // Check if gallon is detected within range
  if (distance > 0 && distance <= DETECTION_DISTANCE_CM) {
    // Gallon detected
    if (!gallonDetected) {
      gallonDetected = true;
      Serial.print("GALLON:DETECTED at ");
      Serial.print(distance);
      Serial.println("cm");
      
      // Open valve to start refilling
      setValve(true);
      Serial.println("VALVE:OPEN - Starting refill");
    }
  } else {
    // No gallon detected
    if (gallonDetected) {
      gallonDetected = false;
      Serial.println("GALLON:REMOVED");
      
      // Close valve to stop refilling
      setValve(false);
      Serial.println("VALVE:CLOSED - Refill stopped");
    }
  }
}
