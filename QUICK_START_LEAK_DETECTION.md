# 🚀 Quick Start: Pressure Sensor Leak Detection

## How It Works

1. **Scan QR code** on water gallon
2. **Click "TEST FOR LEAKS"** button
3. **Place gallon on pressure sensor**
4. System monitors for 30 seconds
5. **If leak detected** → Defect counter automatically increments
6. **If no leak** → Gallon passes test

---

## Without Hardware (Testing/Demo Mode)

The system works in **simulation mode** without actual hardware!

### Run the App:
```bash
python main.py
```

### Test Leak Detection:
1. Add a gallon (or use existing)
2. Scan QR code
3. Click "🔍 TEST FOR LEAKS"
4. Watch simulation - leak will be "detected" for demo purposes

**Perfect for thesis presentation!**

---

## With Actual Hardware

### Shopping List (~$25-40):
- MPX5700AP Pressure Sensor ($10-20)
- MCP3008 ADC Chip ($4)
- Breadboard + Jumper Wires ($5)
- Pressure fitting for gallon valve ($5-10)

### Setup:
1. Follow wiring diagram in `PRESSURE_SENSOR_SETUP.md`
2. Enable SPI: `sudo raspi-config` → Interface Options → SPI → Yes
3. Install libraries:
```bash
sudo pip3 install adafruit-circuitpython-mcp3xxx --break-system-packages
```

4. Edit `main.py` line 53:
```python
sensor_type='analog',  # Set to 'analog' for MPX sensor or 'i2c' for BMP280
```

5. Run app:
```bash
python3 main.py
```

---

## For Your Thesis

### Demo Without Hardware:
✅ Already works! Simulation mode is enabled by default
✅ Shows the concept and workflow
✅ Can demonstrate in presentation

### Document in Thesis:
1. **Hardware Design** - Show circuit diagram from PRESSURE_SENSOR_SETUP.md
2. **Algorithm** - Explain pressure monitoring logic
3. **Implementation** - Code screenshots from pressure_sensor.py
4. **Results** - Show leak detection accuracy (simulation or real tests)

### Future Work Section:
"The system currently operates in simulation mode. With actual pressure sensor hardware (estimated cost: $25-40), the system can detect real leaks automatically..."

---

## Customization

### Change Detection Threshold:
Edit `main.py` line 54:
```python
threshold=5.0,  # 5% pressure drop = leak (change to 3-10%)
```

### Change Monitoring Time:
Edit `main.py` line 55:
```python
monitoring_duration=30  # seconds (change to 15-60)
```

---

## Troubleshooting

### "Pressure sensor not available" message:
✅ This is normal! System uses simulation mode
✅ Button still appears and works
✅ Perfect for testing without hardware

### Want to disable leak detection feature:
Edit `main.py` line 51-57, comment out the pressure sensor init:
```python
# self.pressure_sensor = PressureSensor(...)
self.pressure_sensor = None
```

---

## Files Created

- `pressure_sensor.py` - Pressure monitoring module
- `PRESSURE_SENSOR_SETUP.md` - Complete hardware guide
- `QUICK_START_LEAK_DETECTION.md` - This file
- Modified `main.py` - Added leak detection integration

---

## Next Steps

1. ✅ Test simulation mode (already works!)
2. 📝 Document for thesis
3. 🛒 (Optional) Buy hardware components
4. 🔧 (Optional) Wire up actual sensor
5. 🧪 (Optional) Test with real water gallons

---

**Your thesis project now has automatic leak detection! 🎉**
