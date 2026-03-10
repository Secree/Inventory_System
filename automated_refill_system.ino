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
 * PRESSURE SENSOR (MPX5700AP):
 *   Pin 1 (Vout) -> Arduino A0
 *   Pin 2 (GND)  -> Arduino GND
 *   Pin 3 (+5V)  -> Arduino 5V
 * 
 * CONVEYOR MOTOR (via Relay/Motor Driver):
 *   IN1  -> Arduino Pin 7
 *   IN2  -> Arduino Pin 8
 *   ENA  -> Arduino Pin 6 (PWM for speed control)
 *   Motor power -> External 12V supply
 * 
 * ULTRASONIC SENSOR (HC-SR04):
 *   VCC  -> Arduino 5V
 *   GND  -> Arduino GND
 *   TRIG -> Arduino Pin 9
 *   ECHO -> Arduino Pin 10
 * 
 * SOLENOID VALVE (12V via Relay):
 *   VCC  -> Arduino 5V
 *   GND  -> Arduino GND
 *   IN   -> Arduino Pin 5
 *   Valve power -> External 12V supply
 * 
 * Serial Commands (9600 baud):
 *   "START"  -> Start automated system
 *   "STOP"   -> Stop system
 *   "STATUS" -> Get current system status
 *   "RESET"  -> Reset to initial state
 * 
 * Serial Responses:
 *   "LEAK:DETECTED"     -> Leak found, system stopped
 *   "LEAK:OK"           -> No leak detected
 *   "CONVEYOR:MOVING"   -> Conveyor is running
 *   "CONVEYOR:STOPPED"  -> Conveyor stopped
 *   "GALLON:DETECTED"   -> Gallon at fill station
 *   "FILLING:START"     -> Valve opened, filling
 *   "FILLING:COMPLETE"  -> Gallon full, valve closed
 *   "CYCLE:COMPLETE"    -> One gallon processed
 */

// ═══════════════════════════════════════════════════════════════════════════
// PIN CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════

// Pressure Sensor
const int PRESSURE_PIN = A0;

// Conveyor Motor (L298N or similar)
const int MOTOR_IN1 = 7;      // Direction control 1
const int MOTOR_IN2 = 8;      // Direction control 2
const int MOTOR_ENA = 6;      // PWM speed control (0-255)

// Ultrasonic Sensor
const int TRIG_PIN = 9;
const int ECHO_PIN = 10;

// Solenoid Valve
const int VALVE_PIN = 5;

// Status LEDs (optional)
const int LED_STATUS = 13;    // System running indicator

// ═══════════════════════════════════════════════════════════════════════════
// SYSTEM PARAMETERS
// ═══════════════════════════════════════════════════════════════════════════

// Pressure sensor calibration (MPX5700AP)
const float PRESSURE_V_MIN = 0.5;
const float PRESSURE_V_MAX = 4.5;
const float PRESSURE_P_MAX = 101.5;  // PSI
const float LEAK_THRESHOLD = 5.0;    // PSI - below this indicates leak

// Ultrasonic distances (cm)
const int GALLON_DETECTION_DISTANCE = 25;  // Gallon present at fill station
const int WATER_FULL_DISTANCE = 8;         // Water level reached (close to sensor)

// Conveyor timing
const int CONVEYOR_SPEED = 200;           // PWM value (0-255)
const int CONVEYOR_MOVE_TIME = 3000;      // ms - time to move to next position

// Fill timing
const int MIN_FILL_TIME = 2000;           // ms - minimum fill time
const int MAX_FILL_TIME = 15000;          // ms - maximum fill time (timeout)

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
int gallonsProcessed = 0;

// ═══════════════════════════════════════════════════════════════════════════
// SETUP
// ═══════════════════════════════════════════════════════════════════════════

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  
  // Configure pins
  pinMode(PRESSURE_PIN, INPUT);
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_ENA, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(VALVE_PIN, OUTPUT);
  pinMode(LED_STATUS, OUTPUT);
  
  // Initialize all outputs to safe state
  stopConveyor();
  closeValve();
  digitalWrite(LED_STATUS, LOW);
  
  // Wait for serial
  while (!Serial) { ; }
  
  Serial.println("READY");
  Serial.println("=================================");
  Serial.println("Automated Gallon Refill System");
  Serial.println("=================================");
  Serial.println("Commands: START | STOP | STATUS | RESET");
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
      // Check pressure sensor for leaks
      if (millis() - lastPressureCheck >= PRESSURE_CHECK_INTERVAL) {
        lastPressureCheck = millis();
        float pressure = readPressure();
        
        Serial.print("PRESSURE:");
        Serial.print(pressure, 1);
        Serial.println(" PSI");
        
        if (pressure < LEAK_THRESHOLD) {
          Serial.println("LEAK:DETECTED");
          changeState(ERROR_LEAK);
        } else {
          Serial.println("LEAK:OK");
          changeState(MOVING_TO_FILL_STATION);
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
      digitalWrite(LED_STATUS, LOW);
      systemRunning = false;
      Serial.println("SYSTEM STOPPED: Leak detected");
      Serial.println("Fix leak and send RESET command");
      changeState(IDLE);
      break;
    
    case ERROR_TIMEOUT:
      // Stop and wait for user
      stopConveyor();
      closeValve();
      systemRunning = false;
      Serial.println("SYSTEM STOPPED: Timeout error");
      Serial.println("Check system and send RESET command");
      changeState(IDLE);
      break;
  }
}

void changeState(SystemState newState) {
  currentState = newState;
  stateStartTime = millis();
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
  digitalWrite(VALVE_PIN, LOW);  // Relay active-LOW for most modules
}

void closeValve() {
  digitalWrite(VALVE_PIN, HIGH);  // Relay off
}

float readPressure() {
  float voltage_sum = 0.0;
  
  // Take 10 samples for stability
  for (int i = 0; i < 10; i++) {
    int raw_value = analogRead(PRESSURE_PIN);
    float voltage = (raw_value / 1023.0) * 5.0;
    voltage_sum += voltage;
    delay(10);
  }
  
  float avg_voltage = voltage_sum / 10.0;
  
  // Convert voltage to pressure (linear interpolation)
  if (avg_voltage < PRESSURE_V_MIN) {
    return 0.0;
  }
  
  float pressure = ((avg_voltage - PRESSURE_V_MIN) / 
                   (PRESSURE_V_MAX - PRESSURE_V_MIN)) * PRESSURE_P_MAX;
  
  return pressure;
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
        digitalWrite(LED_STATUS, HIGH);
        gallonsProcessed = 0;
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
      digitalWrite(LED_STATUS, LOW);
      changeState(IDLE);
      Serial.println("SYSTEM:STOPPED");
    }
    else if (command == "STATUS") {
      Serial.print("State: ");
      printState();
      Serial.print("Running: ");
      Serial.println(systemRunning ? "YES" : "NO");
      Serial.print("Gallons processed: ");
      Serial.println(gallonsProcessed);
      Serial.print("Pressure: ");
      Serial.print(readPressure(), 1);
      Serial.println(" PSI");
      Serial.print("Distance: ");
      Serial.print(getUltrasonicDistance());
      Serial.println(" cm");
    }
    else if (command == "RESET") {
      systemRunning = false;
      stopConveyor();
      closeValve();
      digitalWrite(LED_STATUS, LOW);
      changeState(IDLE);
      gallonsProcessed = 0;
      Serial.println("SYSTEM:RESET");
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
