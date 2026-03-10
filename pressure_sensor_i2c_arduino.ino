/*
 * Pressure Sensor Reader for I2C Digital Sensors (MLE02951, etc.)
 * Reads I2C pressure sensor and sends data via USB serial
 * 
 * Hardware Setup for MLE02951:
 * - MLE02951 Pressure Sensor Module
 *   VCC ---> Arduino 5V (or 3.3V if module requires)
 *   GND ---> Arduino GND
 *   SCK (SCL) ---> Arduino A5 (I2C Clock)
 *   OUT (SDA) ---> Arduino A4 (I2C Data)
 * 
 * - Arduino USB -> Computer USB port (COM8 on Windows)
 * 
 * Serial Format: "PRESSURE:XX.XX\n" (pressure in PSI or kPa)
 */

#include <Wire.h>

// I2C Configuration for MLE02951
// Note: Different sensors may use different I2C addresses
// Common addresses: 0x28, 0x76, 0x77, 0x5C, 0x5D
const byte I2C_ADDRESS = 0x28;  // Default for many pressure sensors (try 0x5C if this doesn't work)

// Sensor Configuration
const int READ_INTERVAL = 500;  // Interval between readings (ms)

// Conversion factors (adjust based on your sensor specs)
// For MLE02951: Check datasheet for pressure range and output format
const float PRESSURE_MAX = 100.0;  // Maximum pressure in PSI (adjust to your sensor)
const float PRESSURE_MIN = 0.0;    // Minimum pressure in PSI

// Variables
float currentPressure = 0.0;
bool sensorFound = false;

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  
  // Initialize I2C communication
  Wire.begin();
  
  // Wait for serial connection
  while (!Serial) {
    ; // Wait for serial port to connect
  }
  
  Serial.println("READY");
  Serial.println("I2C Pressure Sensor Arduino Interface (MLE02951)");
  Serial.println("Scanning for I2C devices...");
  
  // Scan for I2C devices
  scanI2C();
  
  delay(1000);
  Serial.println("Sending pressure data...");
}

void loop() {
  // Read pressure from I2C sensor
  float pressure = readPressureI2C();
  
  // Send formatted data to computer
  Serial.print("PRESSURE:");
  Serial.println(pressure, 2);  // 2 decimal places
  
  // Debug: Show sensor status
  if (!sensorFound) {
    Serial.println("DEBUG: No sensor detected - re-scanning...");
    scanI2C();
  }
  
  // Wait before next reading
  delay(READ_INTERVAL);
}

/**
 * Scan I2C bus for connected devices
 */
void scanI2C() {
  byte error, address;
  int deviceCount = 0;
  
  Serial.println("Scanning I2C bus (addresses 0x00 to 0x7F)...");
  
  for (address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    
    if (error == 0) {
      Serial.print("  Found I2C device at address 0x");
      if (address < 16) Serial.print("0");
      Serial.println(address, HEX);
      deviceCount++;
      sensorFound = true;
    }
  }
  
  if (deviceCount == 0) {
    Serial.println("  No I2C devices found!");
    Serial.println("  Check wiring:");
    Serial.println("    SCK -> A5 (SCL)");
    Serial.println("    OUT -> A4 (SDA)");
    Serial.println("    VCC -> 5V");
    Serial.println("    GND -> GND");
  } else {
    Serial.print("Found ");
    Serial.print(deviceCount);
    Serial.println(" device(s)");
  }
}

/**
 * Read pressure from I2C sensor
 * This is a generic implementation - adjust based on your sensor's protocol
 */
float readPressureI2C() {
  if (!sensorFound) {
    return 0.0;  // Return 0 if no sensor detected
  }
  
  // Request data from sensor
  int bytesReceived = Wire.requestFrom(I2C_ADDRESS, (byte)4);  // Request 4 bytes
  
  Serial.print("DEBUG: Requested 4 bytes, received: ");
  Serial.println(bytesReceived);
  
  if (Wire.available() >= 4) {
    // Read 4 bytes from sensor
    byte byte1 = Wire.read();
    byte byte2 = Wire.read();
    byte byte3 = Wire.read();
    byte byte4 = Wire.read();
    
    // DEBUG: Show raw bytes
    Serial.print("DEBUG: Raw bytes: 0x");
    if (byte1 < 16) Serial.print("0");
    Serial.print(byte1, HEX);
    Serial.print(" 0x");
    if (byte2 < 16) Serial.print("0");
    Serial.print(byte2, HEX);
    Serial.print(" 0x");
    if (byte3 < 16) Serial.print("0");
    Serial.print(byte3, HEX);
    Serial.print(" 0x");
    if (byte4 < 16) Serial.print("0");
    Serial.println(byte4, HEX);
    
    // Method 1: Standard 14-bit pressure reading (common for Honeywell sensors)
    byte status = (byte1 & 0xC0) >> 6;
    
    Serial.print("DEBUG: Status bits: ");
    Serial.println(status);
    
    if (status == 0) {  // 0 = normal operation
      // Combine bytes to get 14-bit pressure value
      uint16_t rawPressure = ((uint16_t)(byte1 & 0x3F) << 8) | byte2;
      
      Serial.print("DEBUG: Raw pressure value: ");
      Serial.println(rawPressure);
      
      // Convert to pressure (0-16383 maps to min-max pressure)
      float pressure = ((float)rawPressure / 16383.0) * (PRESSURE_MAX - PRESSURE_MIN) + PRESSURE_MIN;
      
      currentPressure = pressure;
      return pressure;
    } else if (status == 1) {
      Serial.println("Warning: Sensor in command mode");
    } else if (status == 2) {
      Serial.println("Warning: Stale data");
    } else {
      Serial.println("Error: Diagnostic fault");
    }
  } else {
    Serial.println("DEBUG: Not enough bytes available from I2C");
  }
  
  return currentPressure;  // Return last known value if read fails
}

/**
 * ALTERNATIVE READING METHOD (uncomment if above doesn't work)
 * 
 * Some sensors use different protocols. Try this if you get strange readings:
 */
/*
float readPressureI2C_Alternative() {
  Wire.beginTransmission(I2C_ADDRESS);
  Wire.write(0x00);  // Request measurement (some sensors need this)
  Wire.endTransmission();
  
  delay(10);  // Wait for measurement
  
  Wire.requestFrom(I2C_ADDRESS, (byte)2);  // Request 2 bytes
  
  if (Wire.available() >= 2) {
    byte highByte = Wire.read();
    byte lowByte = Wire.read();
    
    // Combine bytes
    uint16_t rawValue = (highByte << 8) | lowByte;
    
    // Convert to pressure (adjust formula based on datasheet)
    float pressure = (float)rawValue / 100.0;  // Example: divide by 100
    
    return pressure;
  }
  
  return 0.0;
}
*/

/**
 * CALIBRATION AND TROUBLESHOOTING:
 * 
 * 1. I2C ADDRESS:
 *    - Default is 0x28 (common for Honeywell sensors)
 *    - Try 0x5C or 0x5D for some MLE sensors
 *    - Try 0x76 or 0x77 for BMP280/BME280
 *    - Run I2C scanner to find your sensor's address
 * 
 * 2. WIRING CHECK:
 *    - SCK (SCL) must connect to Arduino A5
 *    - OUT (SDA) must connect to Arduino A4
 *    - VCC to 5V (or 3.3V if module has voltage regulator)
 *    - GND to GND
 *    - Use pull-up resistors (4.7kΩ) on SDA and SCL if sensor doesn't have them
 * 
 * 3. PRESSURE RANGE:
 *    - Check sensor datasheet for max pressure
 *    - Adjust PRESSURE_MAX constant accordingly
 *    - Common ranges: 10 PSI, 15 PSI, 30 PSI, 100 PSI
 * 
 * 4. OUTPUT FORMAT:
 *    - Some sensors output raw counts (0-16383)
 *    - Some output in mbar, kPa, or PSI directly
 *    - Check datasheet and adjust conversion formula
 * 
 * 5. COMMON I2C ADDRESSES:
 *    - 0x28: Honeywell HSC/SSC series
 *    - 0x5C, 0x5D: Some MLE sensors
 *    - 0x76, 0x77: BMP280, BME280
 *    - 0x18: MS5637
 */
