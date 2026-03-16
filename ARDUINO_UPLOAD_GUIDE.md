# 🔧 Arduino Upload Guide - From Raspberry Pi

This guide explains how to upload Arduino sketches from your Raspberry Pi to an Arduino board.

## 📦 Arduino Sketches in This Project

### Individual Component Sketches
- **pressure_sensor_arduino.ino** - Reads pressure sensor for leak detection
- **pressure_sensor_i2c_arduino.ino** - I2C version of pressure sensor reader
- **arduino2_fill_controller.ino** - Controls solenoid valve for automatic refill

### 🤖 Integrated System (Recommended)
- **automated_refill_system.ino** - Complete automated system that interconnects all components:
  - ✅ Pressure sensor → Checks for leaks
  - ✅ Conveyor motor → Moves gallons
  - ✅ Ultrasonic sensor → Detects position & water level
  - ✅ Solenoid valve → Controls filling
  - 📖 **See [AUTOMATED_SYSTEM_SETUP.md](AUTOMATED_SYSTEM_SETUP.md) for complete setup guide**

---

## 🚀 Quick Method: Arduino CLI (Recommended)

### 1. Install Arduino CLI

```bash
# Download and install
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

# Add to PATH
echo 'export PATH=$PATH:$HOME/bin' >> ~/.bashrc
source ~/.bashrc
```

### 2. Setup Arduino Environment

```bash
# Initialize configuration
arduino-cli config init

# Update package index
arduino-cli core update-index

# Install Arduino AVR core (for Uno, Nano, Mega)
arduino-cli core install arduino:avr
```

### 3. Upload Your Sketch

```bash
# Connect Arduino to Raspberry Pi via USB

# Find your Arduino port
arduino-cli board list

# Compile and upload (replace /dev/ttyUSB0 with your port)
arduino-cli compile --fqbn arduino:avr:uno pressure_sensor_arduino.ino
arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:uno pressure_sensor_arduino.ino
```

### Upload All Sketches

**Individual Component Sketches:**
```bash
# Pressure sensor (standard)
arduino-cli compile --fqbn arduino:avr:uno pressure_sensor_arduino.ino
arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:uno pressure_sensor_arduino.ino

# Pressure sensor (I2C version)
arduino-cli compile --fqbn arduino:avr:uno pressure_sensor_i2c_arduino.ino
arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:uno pressure_sensor_i2c_arduino.ino

# Solenoid valve controller
arduino-cli compile --fqbn arduino:avr:uno arduino2_fill_controller.ino
arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:uno arduino2_fill_controller.ino
```

**🤖 Integrated Automated System (Recommended):**
```bash
# Complete automated refill system (all components in one)
arduino-cli compile --fqbn arduino:avr:uno automated_refill_system.ino
arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:uno automated_refill_system.ino

# Then run the Python controller
python3 automated_system_control.py /dev/ttyUSB0
```

---

## 🖥️ Alternative: Arduino IDE on Raspberry Pi

### Install Arduino IDE

```bash
sudo apt-get update
sudo apt-get install arduino
```

### Upload Steps

1. Open Arduino IDE: `arduino` or from Applications menu
2. **File** → **Open** → Select your `.ino` file
3. **Tools** → **Board** → Select your Arduino model (e.g., "Arduino Uno")
4. **Tools** → **Port** → Select `/dev/ttyUSB0` or `/dev/ttyACM0`
5. Click **Upload** button (→) or **Sketch** → **Upload**

---

## 📋 Arduino Board Types

| Board | FQBN for CLI | IDE Selection |
|-------|--------------|---------------|
| Arduino Uno | `arduino:avr:uno` | Tools → Board → Arduino Uno |
| Arduino Nano | `arduino:avr:nano` | Tools → Board → Arduino Nano |
| Arduino Mega | `arduino:avr:mega` | Tools → Board → Arduino Mega 2560 |
| Arduino Nano Every | `arduino:megaavr:nanoevery` | Tools → Board → Arduino Nano Every |

---

## 🔧 Troubleshooting

### Permission Denied Error

```bash
# Add user to dialout group for USB access
sudo usermod -a -G dialout $USER

# Reboot to apply changes
sudo reboot
```

### Find Correct USB Port

```bash
# List USB devices before connecting Arduino
ls /dev/tty*

# Connect Arduino via USB

# List again - new device is your Arduino
ls /dev/tty*

# Or use Arduino CLI
arduino-cli board list
```

Common ports:
- `/dev/ttyUSB0` - USB-to-Serial adapters, Arduino Nano
- `/dev/ttyACM0` - Native USB Arduinos (Uno, Mega)

### Test Serial Connection

```bash
# Install screen
sudo apt-get install screen

# Monitor serial output (9600 baud for our sketches)
screen /dev/ttyUSB0 9600

# Exit: Press Ctrl+A, then K, then Y
```

### "Port Not Found" Error

1. Check USB cable (ensure it's a data cable, not just power)
2. Try a different USB port on the Raspberry Pi
3. Verify Arduino board is powered (LED should be on)
4. Run `dmesg | tail` after connecting to see USB connection messages

### Compilation Errors

```bash
# Update Arduino CLI and cores
arduino-cli core update-index
arduino-cli upgrade

# Reinstall core if needed
arduino-cli core uninstall arduino:avr
arduino-cli core install arduino:avr
```

---

## 🔌 Hardware Setup & Wiring

### Pressure Sensor Arduino

**Option A: Analog Pressure Sensor (MPX5700AP, MPX5010DP)**

```
Pressure Sensor MPX5700AP → Arduino:
  Pin 1 (Vout/Signal) ---> Arduino A0 (Analog Pin 0)
  Pin 2 (GND)         ---> Arduino GND
  Pin 3 (+5V)         ---> Arduino 5V

Arduino → Raspberry Pi:
  USB Port            ---> Any USB port
```

Upload: `pressure_sensor_arduino.ino`

**Option B: I2C Pressure Sensor (MLE02951, BMP280)**

```
I2C Pressure Sensor → Arduino:
  VCC (Power)  ---> Arduino 5V (or 3.3V - check your module specs)
  GND (Ground) ---> Arduino GND
  SCK (SCL)    ---> Arduino A5 (I2C Clock)
  SDA (OUT)    ---> Arduino A4 (I2C Data)

Arduino → Raspberry Pi:
  USB Port     ---> Any USB port
```

Upload: `pressure_sensor_i2c_arduino.ino`

### Solenoid Valve Arduino

```
Ultrasonic Sensor HC-SR04 → Arduino:
  VCC  ---> Arduino 5V
  GND  ---> Arduino GND
  TRIG ---> Arduino Pin 9
  ECHO ---> Arduino Pin 10

Relay Module (for Solenoid Valve) → Arduino:
  VCC  ---> Arduino 5V
  GND  ---> Arduino GND
  IN   ---> Arduino Pin 7 (Control Signal)

Level Sensor (XKC-Y25) → Arduino:
  VCC  ---> Arduino 5V
  GND  ---> Arduino GND
  OUT  ---> Arduino Pin 8

Buzzer → Arduino:
  +    ---> Arduino Pin 4
  -    ---> Arduino GND

Busy/Ready LEDs → Arduino:
  RED LED +    ---> Arduino Pin 11
  GREEN LED +  ---> Arduino Pin 12
  Both LED -   ---> Arduino GND
  
Relay Module → Solenoid Valve:
  COM  ---> 12V Power Supply +
  NO   ---> Solenoid Valve +
  
Solenoid Valve:
  -    ---> 12V Power Supply GND

Arduino → Raspberry Pi:
  USB Port ---> Any USB port
```

Upload: `arduino2_fill_controller.ino`

### What You Need

**For Pressure Sensor:**
- Arduino Uno/Nano/Mega (any model with USB)
- MPX5700AP or MPX5010DP Pressure Sensor (analog) OR I2C pressure sensor
- USB cable (Arduino to Raspberry Pi)
- 3-5 Jumper wires
- Pressure fitting to connect to gallon valve

**For Solenoid Valve:**
- Arduino Uno/Nano/Mega
- HC-SR04 Ultrasonic Sensor
- XKC-Y25 level sensor
- 5V Relay Module
- 2 LEDs (red and green)
- 2 current-limiting resistors
- 5V buzzer
- 12V Solenoid Valve
- 12V Power Supply
- USB cable
- Jumper wires

---

## 🐍 After Upload: Run Python Code

Once Arduino is programmed, the Python code on Raspberry Pi will communicate with it:

```bash
# Run the main application
python3 main.py

# Or test pressure sensor directly
python3 pressure_sensor.py
```

The Python scripts automatically detect and connect to Arduino serial ports.

---

## 📝 Quick Reference Card

```bash
# One-time setup
arduino-cli config init
arduino-cli core install arduino:avr
sudo usermod -a -G dialout $USER

# Every upload
arduino-cli board list                              # Find port
arduino-cli compile --fqbn arduino:avr:uno sketch.ino
arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:uno sketch.ino

# Monitor serial
screen /dev/ttyUSB0 9600
```

---

## 💡 Tips

- **Use USB 2.0 ports** for better Arduino compatibility on Raspberry Pi 4
- **Keep Arduino CLI updated**: `arduino-cli upgrade`
- **Test immediately after upload** using Serial Monitor or screen
- **Label your Arduinos** if using multiple boards
- **Use powered USB hub** if running multiple Arduinos

---

## 🆘 Need Help?

1. Check Arduino is recognized: `lsusb` (should show "Arduino" or "FTDI")
2. Check serial port permissions: `ls -l /dev/ttyUSB0`
3. View kernel messages: `dmesg | grep -i usb`
4. Test with LED blink sketch first to verify upload works

---

**Ready to upload?** Start with Step 1 (Install Arduino CLI) and follow the Quick Method! 🚀
