# 🔧 Pressure Sensor Integration Guide
## Automatic Leak Detection for Water Gallon Inventory System

---

## 📋 Overview

This guide explains how to integrate a pressure sensor with your Raspberry Pi to automatically detect leaks in water gallons. When pressure drops, the system automatically increments the defect counter for the scanned QR code.

### How It Works:

```
1. Scan QR code on gallon
2. Place gallon on pressure sensor
3. System records baseline pressure
4. Monitors pressure for 30 seconds
5. If pressure drops >5% → LEAK DETECTED!
6. Defect counter automatically increments
7. Log entry created
8. Alert shown to user
```

---

## 🛒 Hardware Shopping List

### Option 1: Analog Pressure Sensor (RECOMMENDED - Cheaper)

**What You Need:**
1. **Pressure Sensor (0-100 PSI)** - $10-20
   - MPX5700AP (Freescale/NXP) - Recommended
   - Or any 0.5V-4.5V analog pressure sensor
   - Must handle water pressure (20-60 PSI typical)

2. **MCP3008 ADC Chip** - $4
   - Converts analog signal to digital for Raspberry Pi
   - 8-channel 10-bit ADC
   - Communicates via SPI

3. **Breadboard and Jumper Wires** - $5
   - For connections

4. **Optional: Pressure Fitting** - $5-10
   - To attach sensor to gallon valve

**Total Cost: ~$25-40**

---

### Option 2: I2C Digital Pressure Sensor (EASIER - No ADC Needed)

**What You Need:**
1. **BMP280 or BME280 Sensor Module** - $5-10
   - Digital I2C pressure sensor
   - Easy to connect (only 4 wires)
   - Good for atmospheric pressure measurement
   - ⚠️ May not handle water pressure directly

**Total Cost: ~$10**

**Note:** BMP280 is better for air pressure. For water gallons under pressure, use Option 1.

---

## 🔌 Hardware Connections

### Option 1: Analog Sensor with MCP3008

```
MCP3008 ADC → Raspberry Pi:
├─ VDD  → Pin 1 (3.3V)
├─ VREF → Pin 1 (3.3V)
├─ AGND → Pin 6 (GND)
├─ DGND → Pin 6 (GND)
├─ CLK  → Pin 23 (GPIO11/SCLK)
├─ DOUT → Pin 21 (GPIO9/MISO)
├─ DIN  → Pin 19 (GPIO10/MOSI)
└─ CS   → Pin 24 (GPIO8/CE0)

Pressure Sensor → MCP3008:
├─ +5V  → Raspberry Pi Pin 2 (5V)
├─ GND  → Raspberry Pi Pin 6 (GND)
└─ OUT  → MCP3008 CH0 (Pin 1)
```

**Visual Diagram:**
```
Pressure Sensor                MCP3008 ADC              Raspberry Pi
┌──────────┐                  ┌──────────┐            ┌────────────┐
│  +5V     │─────────────────→│ VDD/VREF │───────────→│ 3.3V (Pin1)│
│  GND     │─────────────────→│ GND      │───────────→│ GND (Pin6) │
│  SIGNAL  │─────────────────→│ CH0      │            │            │
└──────────┘                  │ CLK      │───────────→│GPIO11(Pin23)│
                              │ DOUT     │───────────→│GPIO9 (Pin21)│
                              │ DIN      │←───────────│GPIO10(Pin19)│
                              │ CS       │───────────→│GPIO8 (Pin24)│
                              └──────────┘            └────────────┘
```

---

### Option 2: I2C Digital Sensor (BMP280)

```
BMP280 → Raspberry Pi:
├─ VCC → Pin 1 (3.3V)
├─ GND → Pin 6 (GND)
├─ SCL → Pin 5 (GPIO3/SCL)
└─ SDA → Pin 3 (GPIO2/SDA)
```

**Much simpler - only 4 wires!**

---

## 💻 Software Installation

### Step 1: Enable SPI and I2C

```bash
# On Raspberry Pi Terminal:
sudo raspi-config
```

Navigate to:
- **Interface Options** → **SPI** → **Yes**
- **Interface Options** → **I2C** → **Yes**
- **Finish** → **Reboot**

---

### Step 2: Install Required Libraries

```bash
# Update system
sudo apt update

# Install Python libraries for sensors
sudo pip3 install adafruit-circuitpython-mcp3xxx --break-system-packages
sudo pip3 install adafruit-circuitpython-bmp280 --break-system-packages

# Or install both:
sudo pip3 install adafruit-circuitpython-mcp3xxx adafruit-circuitpython-bmp280 --break-system-packages
```

---

### Step 3: Test Your Sensor

```bash
# Navigate to your project
cd ~/Inventory_System

# Test the pressure sensor module
python3 pressure_sensor.py
```

**What you should see:**
```
🧪 Testing Pressure Sensor Module

✅ Analog pressure sensor initialized on MCP3008 CH0
Starting leak detection test...
⏱️ 0.0s | Pressure: 30.45 PSI | Drop: 0.00%
⏱️ 2.0s | Pressure: 29.87 PSI | Drop: 1.90%
⏱️ 4.0s | Pressure: 29.12 PSI | Drop: 4.35%
...
🚨 LEAK DETECTED! Pressure drop: 5.20%
   Baseline: 30.00 PSI → Current: 28.44 PSI
```

---

## 🔧 Integration with Main App

The `pressure_sensor.py` module is already created. Now let's integrate it:

### Modify main.py to add leak detection:

Add this to your imports section:
```python
from pressure_sensor import PressureSensor
```

Add initialization in `__init__`:
```python
# Initialize pressure sensor
self.pressure_sensor = PressureSensor(
    sensor_type='analog',  # or 'i2c' for BMP280
    threshold=5.0,         # 5% pressure drop triggers leak
    monitoring_duration=30 # Monitor for 30 seconds
)
```

Add leak detection callback:
```python
def on_leak_detected(self, inventory_id, drop_pct, baseline, current):
    """Called automatically when leak is detected"""
    # Add defect to database
    success, message = self.db.add_defect(inventory_id)
    
    # Show alert
    messagebox.showerning(
        "🚨 LEAK DETECTED!",
        f"Gallon {inventory_id} has a leak!\n\n"
        f"Pressure Drop: {drop_pct:.2f}%\n"
        f"Baseline: {baseline:.2f} PSI\n"
        f"Current: {current:.2f} PSI\n\n"
        f"Defect counter incremented automatically."
    )
    
    # Log the event
    self.logger.log(
        f"LEAK DETECTED - {inventory_id}: "
        f"Pressure dropped {drop_pct:.2f}% "
        f"({baseline:.2f} → {current:.2f} PSI)"
    )
    
    # Refresh display
    self.refresh_inventory_list()
    self.update_statistics()
```

---

## 🎯 Usage Workflow

### For Manual Testing:

1. **Scan QR Code** on gallon
2. **Click "Start Leak Test" button** (we'll add this)
3. **Place gallon on pressure sensor**
4. **Wait 30 seconds** while system monitors
5. **If leak detected:** Defect counter automatically increments
6. **Remove gallon** and proceed to next

### For Automated Station:

1. Worker scans QR code
2. Places gallon on pressure testing station
3. System automatically starts monitoring
4. LED indicators show status:
   - 🟡 Yellow: Testing in progress
   - 🟢 Green: No leak detected (PASS)
   - 🔴 Red: Leak detected (FAIL)
5. Buzzer sounds if leak detected
6. Worker removes gallon

---

## 📊 Pressure Sensor Specifications

### Typical Water Gallon Pressure:
- **Sealed gallon:** 20-40 PSI (normal)
- **Pressurized gallon:** 30-60 PSI
- **Leak threshold:** 5-10% drop in 30 seconds

### Sensor Range Needed:
- **Minimum:** 0-60 PSI
- **Recommended:** 0-100 PSI (for safety margin)

### Detection Sensitivity:
- **High sensitivity:** 3% drop = early detection, more false positives
- **Medium sensitivity:** 5% drop = balanced (RECOMMENDED)
- **Low sensitivity:** 10% drop = only major leaks, fewer false alarms

---

## 🔍 Troubleshooting

### Sensor Not Detected:

**For Analog (MCP3008):**
```bash
# Check SPI is enabled
lsmod | grep spi
# Should show: spi_bcm2835

# Test SPI devices
ls /dev/spi*
# Should show: /dev/spidev0.0 /dev/spidev0.1
```

**For I2C (BMP280):**
```bash
# Check I2C is enabled
lsmod | grep i2c
# Should show: i2c_bcm2835

# Detect I2C devices
sudo i2cdetect -y 1
# Should show device at address 0x76 or 0x77
```

### Inaccurate Readings:

1. **Check connections** - loose wires cause noise
2. **Add capacitor** - 10µF between sensor VCC and GND
3. **Increase averaging** - take more samples
4. **Calibrate sensor** - compare with known pressure gauge

### False Leak Alarms:

1. **Increase threshold** - from 5% to 7-8%
2. **Increase monitoring time** - from 30s to 45-60s
3. **Check for vibrations** - sensor should be stable
4. **Temperature compensation** - pressure changes with temperature

---

## 🎓 Thesis Documentation Tips

### For Your Thesis Paper:

**Hardware Section:**
- Include circuit diagrams (use Fritzing software)
- Specify all component part numbers
- Document voltage levels and pin connections
- Include photos of actual setup

**Software Section:**
- Explain pressure monitoring algorithm
- Document threshold calculation method
- Show flowchart of leak detection logic
- Include code snippets with comments

**Testing Section:**
- Create test plan with various leak sizes
- Document true positive / false positive rates
- Show pressure drop graphs
- Compare manual vs automatic detection accuracy

**Results Section:**
- Accuracy: X% leak detection rate
- Speed: Detection within 30 seconds
- Reliability: False positive rate < 5%
- Cost: Total BOM cost breakdown

---

## 📈 Advanced Features (Optional)

### 1. Pressure Graph Display
Show real-time pressure graph during monitoring

### 2. Multiple Leak Severity Levels
- Minor leak: 5-10% drop
- Major leak: 10-20% drop
- Critical leak: >20% drop

### 3. Calibration Mode
Allow manual calibration with known pressure source

### 4. Historical Pressure Data
Store pressure readings for each gallon
Analyze leak patterns over time

### 5. LED/Buzzer Alerts
Physical indicators for operators:
- 🟡 Yellow LED: Testing
- 🟢 Green LED: Pass
- 🔴 Red LED + Buzzer: Leak detected

---

## 🔗 Wiring Example (Step-by-Step)

### Physical Setup:

1. **Mount pressure sensor** on testing station
2. **Connect sensor to fitting** that mates with gallon valve
3. **Wire sensor to MCP3008** on breadboard
4. **Connect MCP3008 to Raspberry Pi** GPIO pins
5. **Secure all connections** with proper strain relief
6. **Test with water** to ensure no electrical shorts

### Safety Notes:
- ⚠️ Keep electronics away from water
- ⚠️ Use waterproof enclosure for sensor
- ⚠️ Proper grounding to prevent static damage
- ⚠️ Test without power first
- ⚠️ Never exceed sensor pressure rating

---

## ✅ Integration Checklist

- [ ] Purchase pressure sensor
- [ ] Purchase MCP3008 ADC (if using analog sensor)
- [ ] Breadboard and jumper wires
- [ ] Connect hardware to Raspberry Pi
- [ ] Enable SPI/I2C in raspi-config
- [ ] Install Adafruit libraries
- [ ] Test sensor with test script
- [ ] Integrate with main.py
- [ ] Add "Start Leak Test" button to GUI
- [ ] Test with actual water gallons
- [ ] Calibrate threshold values
- [ ] Document results for thesis

---

## 📝 Quick Start Commands

```bash
# 1. Install libraries
sudo pip3 install adafruit-circuitpython-mcp3xxx adafruit-circuitpython-bmp280 --break-system-packages

# 2. Enable interfaces
sudo raspi-config
# → Interface Options → SPI → Yes
# → Interface Options → I2C → Yes

# 3. Test sensor
cd ~/Inventory_System
python3 pressure_sensor.py

# 4. Run main app with leak detection
python3 main.py
```

---

## 🎯 Expected Results

**Detection Accuracy:** 95%+ for leaks >5% pressure drop
**False Positive Rate:** <5% with proper calibration
**Detection Time:** 30-60 seconds per gallon
**Cost:** ~$25-40 for complete sensor system

---

## 📚 Additional Resources

- [MCP3008 Datasheet](https://www.microchip.com/en-us/product/MCP3008)
- [Adafruit MCP3008 Tutorial](https://learn.adafruit.com/mcp3008-spi-adc/python-circuitpython)
- [BMP280 Guide](https://learn.adafruit.com/adafruit-bmp280-barometric-pressure-plus-temperature-sensor-breakout)
- [Raspberry Pi GPIO Pinout](https://pinout.xyz/)

---

**Need help? Check the main README.md or create an issue on GitHub!**
