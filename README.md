# IOT Based Automated Inspection and Refilling System
## Water Gallon Inventory Management System

This application manages inventory for water gallons in water refilling stations with QR code tracking.

## Features
- Generate QR codes for each water gallon
- Scan QR codes to track inventory:
  - 🔴 **USB Handheld Scanner** (MH-ET LIVE) - Fastest method!
  - 📷 Camera scanning
  - 🖼️ Image file upload
- Local SQLite database storage
- Track refills and defects
- Text file backup system
- Automated leak detection with pressure sensor (Raspberry Pi)
- **🤖 NEW: Full Automation System** - Integrated pressure check, conveyor control, ultrasonic detection, and automatic filling
- Easy-to-use GUI interface
- Touchscreen-friendly design
- Fullscreen mode (F11)

## 🚀 Quick Start

### Software Only (Inventory Management)

**Easy Way (Recommended)**
**Just double-click `run.bat`** - it will automatically:
- ✅ Set up the Python environment
- ✅ Install all required packages
- ✅ Launch the application

**Manual Installation**
1. Install Python 3.8 or higher
2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

### 🤖 Complete Automation System (Hardware + Software)

For fully automated gallon refilling with pressure checking, conveyor control, and automatic filling:

1. **Wire the hardware** - Connect Arduino, sensors, motor, and valve
2. **Upload Arduino code** - Flash `automated_refill_system.ino` to Arduino
3. **Run Python controller** - Execute `automated_system_control.py`

📖 **Complete Guide:** [AUTOMATED_SYSTEM_SETUP.md](AUTOMATED_SYSTEM_SETUP.md)

---

## Database Structure
- **Inventory ID**: Unique identifier for each gallon
- **Name**: Name/description of the gallon
- **Refills**: Number of times the gallon has been refilled
- **Defects**: Number of defects detected

## Usage
1. **Add New Gallon**: Enter gallon details and generate QR code
2. **Scan QR Code**: Choose your scanning method:
   - **USB Scanner** (Recommended): Click yellow field, press scanner button → Instant!
   - **Camera**: Opens webcam to scan QR codes
   - **Image Upload**: Select QR code image from file
3. **Track Refills**: Increment refill count when gallon is refilled
4. **Report Defect**: Mark gallon as defective
5. **Fix Defect**: Remove defect status and return to active inventory

## 📱 Hardware Support

### USB Handheld Scanners (Recommended) 🔴
- **MH-ET LIVE Scanner** and compatible USB QR/barcode scanners
- Plug-and-play - no drivers needed
- Fastest scanning method (instant processing)
- Works on both Windows and Raspberry Pi

### Raspberry Pi Setup 🥧
- Full support for Raspberry Pi 3B+ and newer
- Touchscreen-friendly interface
- USB scanner support
- Optional pressure sensor for leak detection
- See [RUN_ON_RASPBERRY_PI.md](RUN_ON_RASPBERRY_PI.md) for setup guide

### Arduino Setup (Hardware Sensors) 🔧
- Upload Arduino sketches from Raspberry Pi
- Pressure sensor integration
- Solenoid valve control
- **NEW: Fully Automated Refill System** - Interconnected pressure sensor, conveyor, ultrasonic, and valve
- See [ARDUINO_UPLOAD_GUIDE.md](ARDUINO_UPLOAD_GUIDE.md) for upload instructions
- See [AUTOMATED_SYSTEM_SETUP.md](AUTOMATED_SYSTEM_SETUP.md) for complete automation setup

### Cameras 📷
- USB webcams
- Built-in laptop cameras
- Raspberry Pi Camera Module
- Any V4L2 compatible camera

## 🔧 Requirements
- Python 3.8 or higher
- Windows 10/11 or Raspberry Pi OS
- (Optional) USB QR scanner for fast processing
- (Optional) Webcam for camera scanning
- (Optional) Pressure sensor for leak detection (Raspberry Pi only)