# 🤖 Automated Gallon Refill System

Complete interconnected system that automatically processes water gallons through the refill cycle.

## 🎯 System Flow

```
┌─────────────────────────────────────────────────────────┐
│                   AUTOMATED CYCLE                        │
└─────────────────────────────────────────────────────────┘

1. CHECK PRESSURE
   └─> Pressure sensor checks for leaks
       ├─> LEAK DETECTED → STOP SYSTEM (alert)
       └─> NO LEAK → Continue

2. MOVE TO FILL STATION
   └─> Conveyor motor starts
       └─> Move gallon forward

3. DETECT GALLON
   └─> Ultrasonic sensor detects gallon
       └─> Stop conveyor when in position

4. FILL GALLON
   └─> Solenoid valve opens
       └─> Water flows into gallon
           └─> Ultrasonic detects water level rising

5. GALLON FULL
   └─> Water reaches target level
       └─> Close solenoid valve

6. MOVE TO NEXT POSITION
   └─> Conveyor moves gallon forward
       └─> Next gallon ready

7. REPEAT → Back to step 1
```

---

## 🔧 Hardware Requirements

### Components Needed

| Component | Quantity | Purpose |
|-----------|----------|---------|
| Arduino Uno/Mega | 1 | Master controller |
| Pressure Sensor (MPX5700AP) | 1 | Leak detection |
| Ultrasonic Sensor (HC-SR04) | 1 | Gallon position & water level |
| Solenoid Valve (12V) | 1 | Water control |
| DC Motor or Conveyor Belt | 1 | Move gallons |
| L298N Motor Driver | 1 | Control conveyor motor |
| 2-Channel Relay Module (5V) | 1 | Control solenoid valve |
| 12V Power Supply | 1 | Power motors & valve |
| 5V Power Supply | 1 | Power Arduino & sensors |
| Jumper Wires | ~20 | Connections |

### Optional Components
- LED indicators for status display
- Emergency stop button
- Buzzer for alerts

---

## 🔌 Wiring Diagram

### Complete Wiring

```
PRESSURE SENSOR (digital module with GND/SCK/OUT/VCC) → Arduino:
    GND -> Arduino GND
    VCC -> Arduino 5V (or 3.3V if your sensor board requires 3.3V)
  SCK -> Arduino Pin 3
  OUT -> Arduino Pin 2
CONVEYOR MOTOR (via L298N Driver) → Arduino:
  ENA (Speed Control) ────────> Arduino Pin 6 (PWM)
  IN1 (Direction)     ────────> Arduino Pin 7
  IN2 (Direction)     ────────> Arduino Pin 8
  Motor Power         ────────> 12V External Supply
  Driver GND          ────────> Arduino GND (common ground)

ULTRASONIC SENSOR (HC-SR04) → Arduino:
  VCC   ──────────────────────> Arduino 5V
  GND   ──────────────────────> Arduino GND
  TRIG  ──────────────────────> Arduino Pin 9
  ECHO  ──────────────────────> Arduino Pin 10

SOLENOID VALVE (via Relay) → Arduino:
  Relay VCC   ────────────────> Arduino 5V
  Relay GND   ────────────────> Arduino GND
  Relay IN    ────────────────> Arduino Pin 5
  Relay COM   ────────────────> 12V Power Supply +
  Relay NO    ────────────────> Solenoid Valve +
  Solenoid -  ────────────────> 12V Power Supply GND

STATUS LED (Optional):
  LED +       ────────────────> Arduino Pin 13 (built-in)
  LED -       ────────────────> Arduino GND
```

### Power Connections

```
12V POWER SUPPLY:
  + ──> L298N Motor Driver (12V Input)
  + ──> Relay COM (for solenoid valve)
  - ──> Common GND with Arduino

5V POWER SUPPLY (or Arduino):
  + ──> Arduino 5V
  + ──> All sensor VCC pins
  - ──> Common GND
```

⚠️ **IMPORTANT**: All grounds (Arduino, sensors, motor driver, power supplies) must be connected together (common ground).

---

## 📥 Upload Arduino Code

### 1. Connect Arduino to Computer/Raspberry Pi

```bash
# Connect Arduino via USB
```

### 2. Upload the Integrated Sketch

**Using Arduino CLI:**
```bash
# Compile
arduino-cli compile --fqbn arduino:avr:uno automated_refill_system.ino

# Upload (replace port as needed)
arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:uno automated_refill_system.ino
```

**Using Arduino IDE:**
1. Open `automated_refill_system.ino`
2. Select your board: **Tools → Board → Arduino Uno**
3. Select port: **Tools → Port → /dev/ttyUSB0** (or COM port on Windows)
4. Click **Upload** (→)

### 3. Test Serial Connection

```bash
# Monitor serial output
screen /dev/ttyUSB0 9600

# Or use Arduino IDE Serial Monitor
# Tools → Serial Monitor (set to 9600 baud)
```

You should see:
```
READY
=================================
Automated Gallon Refill System
=================================
Commands: START | STOP | STATUS | RESET
System in IDLE state
```

---

## 🐍 Run Python Control Software

### Install Dependencies

```bash
# Install PySerial
pip install pyserial
```

### Run the Controller

**Automatic Port Detection:**
```bash
python automated_system_control.py
```

**Specify Port Manually:**
```bash
# Windows
python automated_system_control.py COM3

# Linux/Raspberry Pi
python3 automated_system_control.py /dev/ttyUSB0
```

### Interactive Commands

Once connected, you can use these commands:

| Command | Description |
|---------|-------------|
| `start` | Start automated system |
| `stop` | Stop system |
| `status` | Get current system status |
| `reset` | Reset system to idle |
| `monitor` | Real-time monitoring (Ctrl+C to exit) |
| `stats` | Show processing statistics |
| `quit` | Exit program |

### Example Session

```
>>> start
==================================================
Starting Automated Refill System
==================================================
✓ System started

>>> monitor
==================================================
Monitoring System (Ctrl+C to stop)
==================================================
[10:23:45] SYSTEM:STARTED
[10:23:46] PRESSURE:45.2 PSI
[10:23:46] LEAK:OK
[10:23:46] CONVEYOR:MOVING
[10:23:50] GALLON:DETECTED
[10:23:50] CONVEYOR:STOPPED
[10:23:51] FILLING:START
[10:24:03] FILLING:COMPLETE
[10:24:03] Fill time: 12340 ms
[10:24:04] CONVEYOR:MOVING
[10:24:07] CONVEYOR:STOPPED
[10:24:07] CYCLE:COMPLETE (Total: 1)

Monitoring stopped

>>> stats
==================================================
SYSTEM STATISTICS
==================================================
Gallons Processed: 1
Leaks Detected: 0
Errors: 0
Runtime: 0:00:22
Processing Rate: 163.64 gallons/hour
==================================================

>>> quit
Stopping system...
✓ System stopped
Disconnected
Goodbye!
```

---

## ⚙️ Configuration & Tuning

### Adjust Parameters in Arduino Code

Edit `automated_refill_system.ino` at the top:

```cpp
// Pressure sensor
const float LEAK_THRESHOLD = 5.0;    // PSI - adjust for your needs

// Ultrasonic distances (cm)
const int GALLON_DETECTION_DISTANCE = 25;  // Detection range
const int WATER_FULL_DISTANCE = 8;         // Water level target

// Conveyor
const int CONVEYOR_SPEED = 200;            // 0-255 PWM
const int CONVEYOR_MOVE_TIME = 3000;       // ms - time between stations

// Fill timing
const int MIN_FILL_TIME = 2000;            // ms - minimum fill
const int MAX_FILL_TIME = 15000;           // ms - timeout
```

### Testing Individual Components

Before running the full system, test each component:

**Test Pressure Sensor:**
```
Send: STATUS
Expected: PRESSURE:XX.X PSI
```

**Test Ultrasonic:**
Position object at different distances and check readings in STATUS.

**Test Conveyor:**
Manually start/stop using Arduino pins temporarily or modify code.

**Test Solenoid:**
Temporarily modify code to open/close valve.

---

## 🐛 Troubleshooting

### System Won't Start

**Check:**
- Arduino is connected and powered
- `READY` message appears in serial monitor
- No errors in upload process

**Solution:**
```bash
# Reset Arduino
>>> reset

# Check status
>>> status
```

### Leak Detection False Positives

**Symptom:** System stops immediately with `LEAK:DETECTED`

**Solution:**
1. Check pressure sensor wiring
2. Adjust `LEAK_THRESHOLD` in code
3. Verify sensor calibration

### Gallon Not Detected

**Symptom:** `ERROR: No gallon detected (timeout)`

**Solutions:**
- Adjust `GALLON_DETECTION_DISTANCE` (increase range)
- Check ultrasonic sensor position
- Ensure sensor has clear line of sight
- Check ultrasonic wiring

### Valve Not Opening/Closing

**Check:**
- Relay wiring (IN pin to Arduino Pin 5)
- 12V power supply connected
- Relay LED indicator (should light up when active)
- Valve actually connected to relay output

**Test:**
Modify code temporarily to manually control valve and test.

### Conveyor Not Moving

**Check:**
- Motor driver (L298N) power connections
- 12V supply adequate for motor load
- ENA jumper on L298N (if present)
- Motor wiring polarity
- PWM speed setting (increase if too low)

### Serial Communication Issues

**Linux Permission Error:**
```bash
sudo usermod -a -G dialout $USER
sudo reboot
```

**Port Not Found:**
```bash
# List available ports
ls /dev/ttyUSB* /dev/ttyACM*

# Or
arduino-cli board list
```

---

## 🛡️ Safety Features

### Built-in Safety

1. **Leak Detection**: System stops if pressure drops
2. **Fill Timeout**: Valve closes after maximum time
3. **Emergency Stop**: Send `STOP` command anytime
4. **Gallon Detection Timeout**: Prevents infinite waiting

### Add Emergency Stop Button (Optional)

Wire a button between Arduino Pin 2 and GND. Add to code:

```cpp
const int ESTOP_PIN = 2;

void setup() {
  pinMode(ESTOP_PIN, INPUT_PULLUP);
  // ... rest of setup
}

void loop() {
  // Check emergency stop
  if (digitalRead(ESTOP_PIN) == LOW) {
    systemRunning = false;
    stopConveyor();
    closeValve();
    Serial.println("EMERGENCY STOP ACTIVATED");
  }
  // ... rest of loop
}
```

---

## 📊 Monitoring & Logs

### Save Logs to File

```bash
# Redirect output to log file
python3 automated_system_control.py /dev/ttyUSB0 2>&1 | tee refill_log.txt
```

### Parse Logs

```python
# Example: Count cycles
grep "CYCLE:COMPLETE" refill_log.txt | wc -l
```

---

## 🚀 Next Steps

1. **Upload Arduino Code** → `automated_refill_system.ino`
2. **Test Individual Components** → Use STATUS command
3. **Run Python Controller** → `automated_system_control.py`
4. **Start System** → Type `start` in interactive mode
5. **Monitor Operations** → Type `monitor` to watch real-time

---

## 📝 Quick Reference

### Arduino Serial Commands

| Command | Action |
|---------|--------|
| `START` | Start automated cycle |
| `STOP` | Stop all operations |
| `STATUS` | Get current state & sensor readings |
| `RESET` | Reset to idle state |

### Status Messages

| Message | Meaning |
|---------|---------|
| `LEAK:DETECTED` | Pressure drop detected |
| `LEAK:OK` | Pressure normal |
| `GALLON:DETECTED` | Gallon at fill station |
| `FILLING:START` | Valve opened |
| `FILLING:COMPLETE` | Gallon full |
| `CYCLE:COMPLETE` | One gallon processed |
| `CONVEYOR:MOVING` | Motor running |
| `CONVEYOR:STOPPED` | Motor off |

---

**Ready to automate?** Upload the code and start your first cycle! 🚀
