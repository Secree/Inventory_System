# IOT Based Automated Inspection and Refilling System
## Water Gallon Inventory Management System

This application manages inventory for water gallons in water refilling stations with QR code tracking.

## Features
- Generate QR codes for each water gallon
- Scan QR codes to track inventory
- Local SQLite database storage
- Track refills and defects
- Text file backup system
- Easy-to-use GUI interface

## 🚀 Quick Start

### Easy Way (Recommended)
**Just double-click `run.bat`** - it will automatically:
- ✅ Set up the Python environment
- ✅ Install all required packages
- ✅ Launch the application

### Manual Installation
1. Install Python 3.8 or higher
2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Database Structure
- **Inventory ID**: Unique identifier for each gallon
- **Name**: Name/description of the gallon
- **Refills**: Number of times the gallon has been refilled
- **Defects**: Number of defects detected

## Usage
1. **Add New Gallon**: Enter gallon details and generate QR code
2. **Scan QR Code**: Use camera or upload image to scan QR codes
3. **Track Refills**: Increment refill count when gallon is refilled
4. **Report Defect**: Mark gallon as defective
5. **Fix Defect**: Remove defect status and return to active inventory
pip install -r requirements.txt