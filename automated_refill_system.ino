/*
 * AUTOMATED GALLON REFILL SYSTEM - Master Controller
 * Integrates: Pressure Sensor -> Conveyor -> Ultrasonic -> Solenoid Valve
 * 
 * SYSTEM FLOW:
 * 1. Pressure sensor checks for leaks
 * 2. If NO leak: Conveyor moves gallon forward
 * 3. Ultrasonic detects gallon at fill station -> Stop conveyor
 * 4. Solenoid valve opens to fill gallon
 * 5. When full (water level detected): Close valve
 * 6. Conveyor moves to next position
 * 7. Repeat
 * 
 * Hardware Setup:
 * 
 * PRESSURE SENSOR (digital module with GND/SCK/OUT/VCC):
 *   GND -> Arduino GND
 *   VCC -> Arduino 5V (or 3.3V if your module requires)
 *   SCK -> Arduino Pin 3 (clock)
 *   OUT -> Arduino Pin 2 (data)
 * 
 * CONVEYOR MOTOR (via Relay/Motor Driver):
 *   IN1  -> Arduino Pin A1
 *   IN2  -> Arduino Pin A2
 *   ENA  -> Arduino Pin 11 (PWM for speed control)
 *   Motor power -> External 12V supply
 * 
 * ULTRASONIC SENSOR (HC-SR04):
 *   VCC  -> Arduino 5V
 *   GND  -> Arduino GND
 *   TRIG -> Arduino Pin 12
 *   ECHO -> Arduino Pin A0
 * 
 * SOLENOID VALVE:
 *   Controlled by Arduino2 fill controller (RELAY_PIN = 7)
 *   Arduino1 no longer drives a valve relay pin directly

 * PRIMARY ACTUATOR (seal actuator via L298N):
 *   ENA  -> Arduino Pin 5
 *   IN1  -> Arduino Pin 6
 *   IN2  -> Arduino Pin 9

 * REJECT ACTUATOR (pusher via L298N):
 *   ENA  -> Arduino Pin 10
 *   IN1  -> Arduino Pin 7
 *   IN2  -> Arduino Pin 8
 * 
 * Serial Commands (9600 baud):
 *   "START"  -> Start automated system
 *   "STOP"   -> Stop system
 *   "STATUS" -> Get current system status
 *   "RESET"  -> Reset to initial state
 *   "CONVEYOR_START" -> Start conveyor motor
 *   "CONVEYOR_STOP"  -> Stop conveyor motor
 *   "REJECT" -> Extend reject actuator to eject defective gallon
 *   "LOWER"  -> Extend actuator down (seal gallon for pressure test)
 *   "RAISE"  -> Retract actuator up
 *
 * Serial Responses:
 *   "ACTUATOR:LOWERED"  -> Actuator fully extended
 *   "ACTUATOR:RAISED"   -> Actuator retracted
 *   "LEAK:DETECTED"     -> Leak found, system stopped
 *   "LEAK:OK"           -> No leak detected
 *   "CONVEYOR:MOVING"   -> Conveyor is running
 *   "CONVEYOR:STOPPED"  -> Conveyor stopped
 *   "GALLON:DETECTED"   -> Gallon at fill station
 *   "FILLING:START"     -> Valve opened, filling
 *   "FILLING:COMPLETE"  -> Gallon full, valve closed
 *   "CYCLE:COMPLETE"    -> One gallon processed
 *   "REJECT:START"      -> Reject actuator extended
 *   "REJECT:DONE"       -> Reject actuator retracted
 */

// ═══════════════════════════════════════════════════════════════════════════
// PIN CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════

// Pressure Sensor (clock/data style, 24-bit reading)
const int PRESSURE_OUT_PIN = 2;
const int PRESSURE_SCK_PIN = 3;

// Raw-to-pressure conversion. Tune these from your sensor calibration.
const long PRESSURE_RAW_AT_0 = 0;
const long PRESSURE_RAW_AT_MAX = 8388607;
const float PRESSURE_MAX = 710.0;
const long PRESSURE_READ_TIMEOUT_SENTINEL = -2147483647L;

// Conveyor Motor (L298N or similar)
const int MOTOR_IN1 = A1;     // Direction control 1
const int MOTOR_IN2 = A2;     // Direction control 2
const int MOTOR_ENA = 11;     // PWM speed control (0-255)

// Ultrasonic Sensor
const int TRIG_PIN = 12;
const int ECHO_PIN = A0;

// Primary actuator DC motor (L298N via 12V supply)
//   12V supply  -> L298N 12V / motor power
//   ENA  -> Arduino Pin 5 (PWM speed)
//   IN1  -> Arduino Pin 6
//   IN2  -> Arduino Pin 9
const int ACTUATOR_ENA   = 9;   // PWM enable
const int ACTUATOR_IN1   = 5;   // Direction control 1 (extend = lower)
const int ACTUATOR_IN2   = 6;   // Direction control 2 (retract = raise)
const int ACTUATOR_SPEED = 200; // PWM speed (0-255)

// Reject actuator DC motor (L298N via 12V supply)
//   ENA  -> Arduino Pin 10
//   IN1  -> Arduino Pin 7
//   IN2  -> Arduino Pin 8
const int REJECT_ACTUATOR_ENA   = 10;
const int REJECT_ACTUATOR_IN1   = 7;
const int REJECT_ACTUATOR_IN2   = 8;
const int REJECT_ACTUATOR_SPEED = 200;

// Air pump relay (relay module on pin 13)
const int AIR_PUMP_RELAY = 13;
const int AIR_PUMP_ON    = LOW;  
const int AIR_PUMP_OFF   = HIGH;   

// ═══════════════════════════════════════════════════════════════════════════
// SYSTEM PARAMETERS
// ═══════════════════════════════════════════════════════════════════════════

const float NO_LEAK_PRESSURE = 36.0;      // Required relative pressure rise above baseline for no-leak
const unsigned long PRESSURE_TEST_TIME_MS = 15000;  // Wait 15 seconds before leak decision
const unsigned long PUMP_ON_TIME_MS = 3000;         // Keep pump ON for first 3 seconds of pressure test
const int CONSISTENT_HIGH_READS_REQUIRED = 3;        // Consecutive reads above threshold needed for no-leak

// Ultrasonic distances (cm)
const int GALLON_DETECTION_DISTANCE = 25;  // Gallon present at fill station
const int WATER_FULL_DISTANCE = 8;         // Water level reached (close to sensor)

// Conveyor timing
const int CONVEYOR_SPEED = 60;            // PWM value (0-255)
const int CONVEYOR_MOVE_TIME = 3000;      // ms - time to move to next position

// Fill timing
const int MIN_FILL_TIME = 2000;           // ms - minimum fill time
const int MAX_FILL_TIME = 15000;          // ms - maximum fill time (timeout)
const int ACTUATOR_EXTEND_TIME = 5000;   // ms - time for primary actuator to fully extend
const int ACTUATOR_RETRACT_TIME = 5000;  // ms - time for primary actuator to fully retract
const int ACTUATOR_HALF_EXTEND_TIME = ACTUATOR_EXTEND_TIME / 2;  // ms - 50% extension stroke
const int REJECT_PUSH_TIME = 5000;        // ms - reject pusher extend time
const int REJECT_RETRACT_TIME = 5000;     // ms - reject pusher retract time

// Sampling delays
const int PRESSURE_CHECK_INTERVAL = 1000;  // ms
const int ULTRASONIC_CHECK_INTERVAL = 200; // ms

// ═══════════════════════════════════════════════════════════════════════════
// SYSTEM STATE
// ═══════════════════════════════════════════════════════════════════════════

enum SystemState {
  IDLE,
  CHECKING_PRESSURE,
  MOVING_TO_FILL_STATION,
  WAITING_FOR_GALLON,
  FILLING,
  MOVING_TO_NEXT,
  ERROR_LEAK,
  ERROR_TIMEOUT
};

SystemState currentState = IDLE;
bool systemRunning = false;
unsigned long stateStartTime = 0;
unsigned long lastPressureCheck = 0;
unsigned long lastPressureLog = 0;  // Tracks 1-second pressure logging interval
int gallonsProcessed = 0;
float pressureBaseline = -1.0;
float lastPressure = 0.0;
int highPressureStreak = 0;
bool pumpIsOn = false;

long readPressureRaw24();
float rawToPressure(long raw);
bool isLeakDetected(float pressureValue);
float toRelativePressure(float absolutePressure, float baselinePressure);
float requiredRiseForNoLeak(float baselinePressure);
void lowerPrimaryActuator(bool announceComplete = true);
void lowerPrimaryActuatorHalf(bool announceComplete = true);
void raisePrimaryActuator(bool announceComplete = true);
void stopPrimaryActuator();
void extendRejectActuator();
void retractRejectActuator();
void stopRejectActuator();
void pumpOn();
void pumpOff();

// ═══════════════════════════════════════════════════════════════════════════
// SETUP
// ═══════════════════════════════════════════════════════════════════════════

void setup() {
  // Initialize serial communication
  Serial.begin(9600);

  // Preload actuator motor driver to stopped state before setting as OUTPUT.
  digitalWrite(ACTUATOR_IN1, LOW);
  digitalWrite(ACTUATOR_IN2, LOW);
  analogWrite(ACTUATOR_ENA, 0);

  // Preload reject actuator motor driver to stopped state.
  digitalWrite(REJECT_ACTUATOR_IN1, LOW);
  digitalWrite(REJECT_ACTUATOR_IN2, LOW);
  analogWrite(REJECT_ACTUATOR_ENA, 0);
  
  // Configure pins
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_ENA, OUTPUT);
  pinMode(PRESSURE_OUT_PIN, INPUT);
  pinMode(PRESSURE_SCK_PIN, OUTPUT);
  digitalWrite(PRESSURE_SCK_PIN, LOW);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(ACTUATOR_ENA, OUTPUT);
  pinMode(ACTUATOR_IN1, OUTPUT);
  pinMode(ACTUATOR_IN2, OUTPUT);
  pinMode(REJECT_ACTUATOR_ENA, OUTPUT);
  pinMode(REJECT_ACTUATOR_IN1, OUTPUT);
  pinMode(REJECT_ACTUATOR_IN2, OUTPUT);
  pinMode(AIR_PUMP_RELAY, OUTPUT);
  
  // Initialize all outputs to safe state
  stopConveyor();
  closeValve();
  retractActuator();
  stopRejectActuator();
  pumpOff();

  // Wait for serial
  while (!Serial) { ; }
  
  Serial.println("READY");
  Serial.println("=================================");
  Serial.println("Automated Gallon Refill System");
  Serial.println("=================================");
  Serial.println("Commands: START | STOP | STATUS | RESET | REJECT | LOWER | LOWER_HALF | RAISE");
  Serial.println("PRESSURE:SCK_OUT_MODE (OUT->D2, SCK->D3)");
  Serial.println("System in IDLE state");
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN LOOP
// ═══════════════════════════════════════════════════════════════════════════

void loop() {
  // Handle serial commands
  handleSerialCommands();
  
  // Run state machine if system is active
  if (systemRunning) {
    runStateMachine();

    // Log air pressure every second throughout the workflow.
    // Sends relative pressure when baseline is set (same 0-based scale as NO_LEAK_PRESSURE = 36),
    // or absolute pressure before any test baseline is established.
    if (millis() - lastPressureLog >= 1000) {
      lastPressureLog = millis();
      float absP = readPressure();
      float logP = (pressureBaseline >= 0.0)
                    ? toRelativePressure(absP, pressureBaseline)
                    : absP;
      Serial.print("PRESSURE_LOG:");
      Serial.println(logP, 1);
    }
  }
  
  delay(50);  // Small delay to prevent excessive CPU usage
}

// ═══════════════════════════════════════════════════════════════════════════
// STATE MACHINE
// ═══════════════════════════════════════════════════════════════════════════

void runStateMachine() {
  switch (currentState) {
    
    case IDLE:
      // System waiting to start
      break;
    
    case CHECKING_PRESSURE:
      // Check for leaks over 15 seconds
      if (millis() - lastPressureCheck >= PRESSURE_CHECK_INTERVAL) {
        lastPressureCheck = millis();
        float absolutePressure = readPressure();
        unsigned long elapsed = millis() - stateStartTime;

        // Pump runs only during the first few seconds of the pressure test.
        if (pumpIsOn && elapsed >= PUMP_ON_TIME_MS) {
          pumpOff();
          Serial.println("PUMP:OFF");
        }

        // First reading in this check window is the baseline.
        if (pressureBaseline < 0.0) {
          pressureBaseline = absolutePressure;
          Serial.print("PRESSURE:BASELINE ");
          Serial.println(0.0, 1);
        }

        float pressure = toRelativePressure(absolutePressure, pressureBaseline);
        float requiredRise = requiredRiseForNoLeak(pressureBaseline);

        if (pressure >= requiredRise) {
          highPressureStreak++;
        } else {
          highPressureStreak = 0;
        }
        
          Serial.print("PRESSURE:");
          Serial.println(pressure, 1);
          Serial.print("WORKLOG PRESSURE:");
          Serial.println(pressure, 1);

        // Wait complete test duration before making pass/fail decision.
        if (elapsed >= PRESSURE_TEST_TIME_MS) {
          Serial.print("PRESSURE:FINAL ");
          Serial.println(pressure, 1);

          if (highPressureStreak >= CONSISTENT_HIGH_READS_REQUIRED) {
            Serial.println("LEAK:OK");
            changeState(MOVING_TO_FILL_STATION);
          } else {
            Serial.println("LEAK:DETECTED");
            changeState(ERROR_LEAK);
          }
        }
      }
      break;
    
    case MOVING_TO_FILL_STATION:
      // Move conveyor until gallon detected
      startConveyor();
      Serial.println("CONVEYOR:MOVING");
      changeState(WAITING_FOR_GALLON);
      break;
    
    case WAITING_FOR_GALLON:
      // Wait for ultrasonic to detect gallon
      {
        long distance = getUltrasonicDistance();
        if (distance > 0 && distance <= GALLON_DETECTION_DISTANCE) {
          stopConveyor();
          Serial.println("GALLON:DETECTED");
          Serial.println("CONVEYOR:STOPPED");
          delay(500);  // Let gallon settle
          changeState(FILLING);
        }
        
        // Timeout check
        if (millis() - stateStartTime > 10000) {
          stopConveyor();
          Serial.println("ERROR: No gallon detected (timeout)");
          changeState(ERROR_TIMEOUT);
        }
      }
      break;
    
    case FILLING:
      // Open valve and fill until water level detected
      {
        if (millis() - stateStartTime < 100) {
          openValve();
          Serial.println("FILLING:START");
        }
        
        // Check water level
        long distance = getUltrasonicDistance();
        unsigned long fillTime = millis() - stateStartTime;
        
        // Check if full (water close to sensor)
        if (distance > 0 && distance <= WATER_FULL_DISTANCE && fillTime > MIN_FILL_TIME) {
          closeValve();
          Serial.println("FILLING:COMPLETE");
          Serial.print("Fill time: ");
          Serial.print(fillTime);
          Serial.println(" ms");
          delay(500);
          changeState(MOVING_TO_NEXT);
        }
        
        // Timeout safety
        if (fillTime > MAX_FILL_TIME) {
          closeValve();
          Serial.println("FILLING:TIMEOUT");
          changeState(MOVING_TO_NEXT);  // Continue anyway
        }
      }
      break;
    
    case MOVING_TO_NEXT:
      // Move conveyor forward for fixed time
      {
        if (millis() - stateStartTime < 100) {
          startConveyor();
          Serial.println("CONVEYOR:MOVING");
        }
        
        if (millis() - stateStartTime >= CONVEYOR_MOVE_TIME) {
          stopConveyor();
          Serial.println("CONVEYOR:STOPPED");
          
          gallonsProcessed++;
          Serial.print("CYCLE:COMPLETE (Total: ");
          Serial.print(gallonsProcessed);
          Serial.println(")");
          
          delay(1000);
          changeState(CHECKING_PRESSURE);  // Start next cycle
        }
      }
      break;
    
    case ERROR_LEAK:
      // Stop everything and wait for manual intervention
      stopConveyor();
      closeValve();
      retractActuator();
      stopPrimaryActuator();
      stopRejectActuator();
      systemRunning = false;
      Serial.println("SYSTEM STOPPED: Leak detected");
      Serial.println("Fix leak and send RESET command");
      changeState(IDLE);
      break;
    
    case ERROR_TIMEOUT:
      // Stop and wait for user
      stopConveyor();
      closeValve();
      retractActuator();
      stopPrimaryActuator();
      stopRejectActuator();
      systemRunning = false;
      Serial.println("SYSTEM STOPPED: Timeout error");
      Serial.println("Check system and send RESET command");
      changeState(IDLE);
      break;
  }
}

void pumpOn() {
  digitalWrite(AIR_PUMP_RELAY, AIR_PUMP_ON);
  pumpIsOn = true;
}

void pumpOff() {
  digitalWrite(AIR_PUMP_RELAY, AIR_PUMP_OFF);
  pumpIsOn = false;
}

void changeState(SystemState newState) {
  // Pump runs only during pressure check.
  if (newState == CHECKING_PRESSURE && !pumpIsOn) {
    pumpOn();
    Serial.println("PUMP:ON");
  } else if (currentState == CHECKING_PRESSURE && pumpIsOn) {
    pumpOff();
    Serial.println("PUMP:OFF");
  }

  currentState = newState;
  stateStartTime = millis();

  // Reset pressure baseline each time a new pressure test cycle starts.
  if (newState == CHECKING_PRESSURE) {
    pressureBaseline = -1.0;
    lastPressureCheck = 0;
    highPressureStreak = 0;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// HARDWARE CONTROL FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

void startConveyor() {
  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  analogWrite(MOTOR_ENA, CONVEYOR_SPEED);
}

void stopConveyor() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  analogWrite(MOTOR_ENA, 0);
}

void openValve() {
  // Valve is controlled by Arduino2 fill controller.
}

void closeValve() {
  // Valve is controlled by Arduino2 fill controller.
}

void extendActuator() {
  // Drive motor forward (lower actuator)
  digitalWrite(ACTUATOR_IN1, HIGH);
  digitalWrite(ACTUATOR_IN2, LOW);
  analogWrite(ACTUATOR_ENA, ACTUATOR_SPEED);
}

void retractActuator() {
  // Drive motor reverse (raise actuator)
  digitalWrite(ACTUATOR_IN1, LOW);
  digitalWrite(ACTUATOR_IN2, HIGH);
  analogWrite(ACTUATOR_ENA, ACTUATOR_SPEED);
}

void lowerPrimaryActuator(bool announceComplete) {
  extendActuator();
  delay(ACTUATOR_EXTEND_TIME);
  stopPrimaryActuator();

  if (announceComplete) {
    Serial.println("ACTUATOR:LOWERED");
  }
}

void lowerPrimaryActuatorHalf(bool announceComplete) {
  extendActuator();
  delay(ACTUATOR_HALF_EXTEND_TIME);
  stopPrimaryActuator();

  if (announceComplete) {
    Serial.println("ACTUATOR:LOWERED_HALF");
  }
}

void raisePrimaryActuator(bool announceComplete) {
  retractActuator();
  delay(ACTUATOR_RETRACT_TIME);
  stopPrimaryActuator();

  if (announceComplete) {
    Serial.println("ACTUATOR:RAISED");
  }
}

void stopPrimaryActuator() {
  digitalWrite(ACTUATOR_IN1, LOW);
  digitalWrite(ACTUATOR_IN2, LOW);
  analogWrite(ACTUATOR_ENA, 0);
}

void extendRejectActuator() {
  digitalWrite(REJECT_ACTUATOR_IN1, HIGH);
  digitalWrite(REJECT_ACTUATOR_IN2, LOW);
  analogWrite(REJECT_ACTUATOR_ENA, REJECT_ACTUATOR_SPEED);
}

void retractRejectActuator() {
  digitalWrite(REJECT_ACTUATOR_IN1, LOW);
  digitalWrite(REJECT_ACTUATOR_IN2, HIGH);
  analogWrite(REJECT_ACTUATOR_ENA, REJECT_ACTUATOR_SPEED);
}

void stopRejectActuator() {
  digitalWrite(REJECT_ACTUATOR_IN1, LOW);
  digitalWrite(REJECT_ACTUATOR_IN2, LOW);
  analogWrite(REJECT_ACTUATOR_ENA, 0);
}

void rejectDefectiveGallon() {
  stopConveyor();
  closeValve();

  Serial.println("REJECT:START");

  // Step 1: Ensure primary actuator is fully retracted before reject push.
  raisePrimaryActuator(false);

  // Step 2: Use second actuator to push defective gallon out.
  extendRejectActuator();
  delay(REJECT_PUSH_TIME);
  retractRejectActuator();
  delay(REJECT_RETRACT_TIME);
  stopRejectActuator();

  Serial.println("REJECT:DONE");
}

float readPressure() {
  long raw = readPressureRaw24();
  if (raw == PRESSURE_READ_TIMEOUT_SENTINEL) {
    lastPressure = 0.0;
    return 0.0;
  }

  float pressure = rawToPressure(raw);
  lastPressure = pressure;
  return pressure;
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

  // Convert from two's complement representation used by this module.
  result = result ^ 0x800000;

  // Start next reading cycle.
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
  if (pressure < 0.0) pressure = 0.0;
  return pressure;
}

bool isLeakDetected(float pressureValue) {
  return pressureValue < NO_LEAK_PRESSURE;
}

float toRelativePressure(float absolutePressure, float baselinePressure) {
  if (baselinePressure < 0.0) {
    return absolutePressure;
  }

  float relative = absolutePressure - baselinePressure;
  if (relative < 0.0) {
    relative = 0.0;
  }
  return relative;
}

float requiredRiseForNoLeak(float baselinePressure) {
  return NO_LEAK_PRESSURE;
}

long getUltrasonicDistance() {
  // Send trigger pulse
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // Read echo pulse
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);  // 30ms timeout
  
  if (duration == 0) {
    return -1;  // No echo received
  }
  
  // Calculate distance in cm
  long distance = duration * 0.034 / 2;
  
  return distance;
}

// ═══════════════════════════════════════════════════════════════════════════
// SERIAL COMMAND HANDLER
// ═══════════════════════════════════════════════════════════════════════════

void handleSerialCommands() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toUpperCase();
    
    if (command == "START") {
      if (!systemRunning) {
        systemRunning = true;
        gallonsProcessed = 0;
        pressureBaseline = -1.0;
        changeState(CHECKING_PRESSURE);
        Serial.println("SYSTEM:STARTED");
      } else {
        Serial.println("ERROR: System already running");
      }
    }
    else if (command == "STOP") {
      systemRunning = false;
      stopConveyor();
      closeValve();
      raisePrimaryActuator(false);
      stopRejectActuator();
      pumpOff();
      changeState(IDLE);
      Serial.println("SYSTEM:STOPPED");
    }
    else if (command == "STATUS") {

      float baselineAbs = readPressure();
      pressureBaseline = baselineAbs;
      float latestAbs = baselineAbs;
      int statusHighStreak = 0;
      unsigned long testStart = millis();

      Serial.println("PRESSURE:TEST_START");
      Serial.print("PRESSURE:BASELINE ");
      Serial.println(0.0, 1);
      pumpOn();
      Serial.println("PUMP:ON");

      while (millis() - testStart < PRESSURE_TEST_TIME_MS) {
        unsigned long elapsed = millis() - testStart;

        if (pumpIsOn && elapsed >= PUMP_ON_TIME_MS) {
          pumpOff();
          Serial.println("PUMP:OFF");
        }

        latestAbs = readPressure();
        float latestRel = toRelativePressure(latestAbs, pressureBaseline);
        float requiredRiseNow = requiredRiseForNoLeak(pressureBaseline);

        if (latestRel >= requiredRiseNow) {
          statusHighStreak++;
        } else {
          statusHighStreak = 0;
        }

        Serial.print("PRESSURE:");
        Serial.println(latestRel, 1);
        
        Serial.print("WORKLOG PRESSURE:");
        Serial.println(latestRel, 1);
        delay(PRESSURE_CHECK_INTERVAL);
      }

      if (pumpIsOn) {
        pumpOff();
        Serial.println("PUMP:OFF");
      }

      float latestRel = toRelativePressure(latestAbs, pressureBaseline);
      float requiredRise = requiredRiseForNoLeak(pressureBaseline);
      bool leakDetected = (statusHighStreak < CONSISTENT_HIGH_READS_REQUIRED);

      Serial.print("State: ");
      printState();
      Serial.print("Running: ");
      Serial.println(systemRunning ? "YES" : "NO");
      Serial.print("Gallons processed: ");
      Serial.println(gallonsProcessed);

      // Machine-readable lines used by the Python workflow parser
      Serial.print("PRESSURE:");
      Serial.println(latestRel, 1);

      Serial.print("PRESSURE:THRESHOLD=");
      Serial.println(requiredRise, 1);

      if (leakDetected) {
        Serial.println("LEAK:DETECTED");
      } else {
        Serial.println("LEAK:OK");
      }

      // Human-readable diagnostics
      Serial.print("Pressure: ");
      Serial.println(latestRel, 1);
      Serial.print("Distance: ");
      Serial.print(getUltrasonicDistance());
      Serial.println(" cm");
    }
    else if (command == "RESET") {
      systemRunning = false;
      stopConveyor();
      closeValve();
      raisePrimaryActuator(false);
      stopRejectActuator();
      pumpOff();
      changeState(IDLE);
      gallonsProcessed = 0;
      pressureBaseline = -1.0;
      Serial.println("SYSTEM:RESET");
    }
    else if (command == "CONVEYOR_START") {
      startConveyor();
      Serial.println("CONVEYOR:MOVING");
    }
    else if (command == "CONVEYOR_STOP") {
      stopConveyor();
      Serial.println("CONVEYOR:STOPPED");
    }
    else if (command == "REJECT") {
      rejectDefectiveGallon();
    }
    else if (command == "LOWER") {
      lowerPrimaryActuator();
    }
    else if (command == "LOWER_HALF") {
      lowerPrimaryActuatorHalf();
    }
    else if (command == "RAISE") {
      raisePrimaryActuator();
    }
    else {
      Serial.print("ERROR: Unknown command: ");
      Serial.println(command);
    }
  }
}

void printState() {
  switch (currentState) {
    case IDLE: Serial.println("IDLE"); break;
    case CHECKING_PRESSURE: Serial.println("CHECKING_PRESSURE"); break;
    case MOVING_TO_FILL_STATION: Serial.println("MOVING_TO_FILL_STATION"); break;
    case WAITING_FOR_GALLON: Serial.println("WAITING_FOR_GALLON"); break;
    case FILLING: Serial.println("FILLING"); break;
    case MOVING_TO_NEXT: Serial.println("MOVING_TO_NEXT"); break;
    case ERROR_LEAK: Serial.println("ERROR_LEAK"); break;
    case ERROR_TIMEOUT: Serial.println("ERROR_TIMEOUT"); break;
  }
}
