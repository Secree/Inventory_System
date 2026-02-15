/*
 * Pressure Sensor Reader for Raspberry Pi
 * Reads analog pressure sensor and sends data via USB serial
 * 
 * Hardware Setup:
 * - Pressure Sensor MPX5700AP or similar
 *   Pin 1 (Vout) -> Arduino A0
 *   Pin 2 (GND)  -> Arduino GND
 *   Pin 3 (+5V)  -> Arduino 5V
 * 
 * - Arduino USB -> Raspberry Pi USB port
 * 
 * Serial Format: "PRESSURE:XX.XX\n" (pressure in PSI)
 */

// Pin Configuration
const int PRESSURE_PIN = A0;  // Analog input for pressure sensor

// Sensor Calibration (MPX5700AP: 0-700 kPa / 0-101.5 PSI)
// Typical: 0.5V = 0 PSI, 4.5V = 101.5 PSI (or adjust for your sensor)
const float V_MIN = 0.5;      // Voltage at 0 PSI
const float V_MAX = 4.5;      // Voltage at max PSI
const float P_MIN = 0.0;      // Minimum pressure (PSI)
const float P_MAX = 101.5;    // Maximum pressure (PSI) for MPX5700AP

// For MPX5010DP (0-10 PSI): Use P_MAX = 10.0
// const float P_MAX = 10.0;

// Sampling Configuration
const int NUM_SAMPLES = 10;   // Number of samples for averaging
const int SAMPLE_DELAY = 10;  // Delay between samples (ms)
const int READ_INTERVAL = 500; // Interval between readings (ms)

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  
  // Set analog reference to default (5V for Uno, 3.3V for Due/Zero)
  analogReference(DEFAULT);
  
  // Initialize analog pin
  pinMode(PRESSURE_PIN, INPUT);
  
  // Wait for serial connection
  while (!Serial) {
    ; // Wait for serial port to connect
  }
  
  Serial.println("READY");
  Serial.println("Pressure Sensor Arduino Interface");
  Serial.println("Sending pressure data to Raspberry Pi...");
  delay(1000);
}

void loop() {
  // Read and average pressure
  float pressure = readPressure();
  
  // Send formatted data to Raspberry Pi
  Serial.print("PRESSURE:");
  Serial.println(pressure, 2);  // 2 decimal places
  
  // Wait before next reading
  delay(READ_INTERVAL);
}

/**
 * Read pressure from sensor with averaging
 * Returns pressure in PSI
 */
float readPressure() {
  float voltage_sum = 0.0;
  
  // Take multiple samples for stability
  for (int i = 0; i < NUM_SAMPLES; i++) {
    int raw_value = analogRead(PRESSURE_PIN);
    float voltage = (raw_value / 1023.0) * 5.0;  // Convert to voltage (0-5V)
    voltage_sum += voltage;
    delay(SAMPLE_DELAY);
  }
  
  // Calculate average voltage
  float avg_voltage = voltage_sum / NUM_SAMPLES;
  
  // Convert voltage to pressure (linear interpolation)
  float pressure = 0.0;
  
  if (avg_voltage < V_MIN) {
    pressure = P_MIN;
  } else if (avg_voltage > V_MAX) {
    pressure = P_MAX;
  } else {
    // Linear mapping: pressure = ((V - V_MIN) / (V_MAX - V_MIN)) * (P_MAX - P_MIN) + P_MIN
    pressure = ((avg_voltage - V_MIN) / (V_MAX - V_MIN)) * (P_MAX - P_MIN) + P_MIN;
  }
  
  // Ensure pressure is not negative
  if (pressure < 0) {
    pressure = 0.0;
  }
  
  return pressure;
}

/**
 * CALIBRATION NOTES:
 * 
 * MPX5700AP (0-700 kPa / 0-101.5 PSI):
 *   V_MIN = 0.5V, V_MAX = 4.5V
 *   P_MIN = 0 PSI, P_MAX = 101.5 PSI
 * 
 * MPX5010DP (0-10 kPa / 0-1.45 PSI):
 *   V_MIN = 0.5V, V_MAX = 4.5V
 *   P_MIN = 0 PSI, P_MAX = 1.45 PSI
 * 
 * MPX5100DP (0-100 kPa / 0-14.5 PSI):
 *   V_MIN = 0.5V, V_MAX = 4.5V
 *   P_MIN = 0 PSI, P_MAX = 14.5 PSI
 * 
 * To calibrate:
 * 1. Connect sensor with no pressure -> note voltage -> set as V_MIN
 * 2. Apply known pressure -> note voltage -> calculate V_MAX
 * 3. Adjust P_MAX to match your sensor's range
 */
