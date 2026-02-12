# 🥧 Running on Raspberry Pi

## Quick Start

### Option 1: Automatic Setup (Recommended)
```bash
# Make setup script executable
chmod +x setup_raspberry_pi.sh

# Run setup script
./setup_raspberry_pi.sh

# Run the application
python3 main.py
```

### Option 2: Manual Setup

#### 1. Update System
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

#### 2. Install System Dependencies
```bash
sudo apt-get install -y python3 python3-pip python3-tk \
    python3-pil python3-pil.imagetk libzbar0 \
    python3-opencv libatlas-base-dev
```

#### 3. Install Python Packages
```bash
pip3 install -r requirements.txt
```

#### 4. Enable Camera (if using QR scanner)
```bash
sudo raspi-config
# Navigate to: Interface Options → Camera → Enable
# Reboot after enabling
```

#### 5. Run the Application
```bash
python3 main.py
```

## 📋 Raspberry Pi Requirements

### Minimum Hardware:
- **Model**: Raspberry Pi 3B or newer (Pi 4 recommended)
- **RAM**: 1GB minimum (2GB+ recommended)
- **Storage**: 8GB SD card minimum (16GB+ recommended)
- **Display**: Any HDMI display or touchscreen
- **Optional**: USB Camera for QR code scanning

### Recommended Setup:
- Raspberry Pi 4 (4GB RAM)
- 32GB SD card
- Official Raspberry Pi Camera or USB webcam
- Mouse and keyboard (or touchscreen)
- Fan or heatsink for cooling

## 🎯 Performance Tips

### 1. Optimize for Raspberry Pi
The application is already optimized with:
- Lightweight GUI with tabbed interface
- Efficient scrolling
- Compact layouts for small screens
- Touch-friendly buttons

### 2. Improve Performance
```bash
# Increase GPU memory for better graphics
sudo raspi-config
# → Performance Options → GPU Memory → Set to 128 or 256

# Overclock (Pi 4 only, optional)
sudo raspi-config
# → Performance Options → Overclock
```

### 3. Run in Fullscreen
- Press **F11** to toggle fullscreen mode
- Press **Escape** to exit fullscreen

## 📷 Camera Setup

### Built-in Pi Camera
```bash
# Enable legacy camera support
sudo raspi-config
# → Interface Options → Legacy Camera → Enable

# Test camera
raspistill -o test.jpg
```

### USB Webcam
```bash
# Check if camera is detected
ls -l /dev/video*

# Test with fswebcam
sudo apt-get install fswebcam
fswebcam test.jpg

# Add user to video group
sudo usermod -a -G video $USER
# Logout and login for changes to take effect
```

## � USB Handheld Scanner (MH-ET LIVE)

### What is MH-ET LIVE Scanner?
MH-ET LIVE and similar USB handheld QR/barcode scanners are plug-and-play devices that:
- Act as USB HID keyboards (no drivers needed)
- Show red light when button pressed, white light when scanning
- Automatically "type" scanned data and press Enter
- Work perfectly with Raspberry Pi

### Setup on Raspberry Pi

#### 1. Physical Connection
```bash
# Simply plug the USB scanner into any USB port
# Pi will automatically detect it as a keyboard

# Verify detection
lsusb
# You should see an entry like: "Bus 001 Device 004: ID 05e0:1200 Symbol Technologies"
# or similar USB HID device

# Check input devices
ls /dev/input/event*
# Scanner will appear as an event device
```

#### 2. Grant Permissions (if needed)
```bash
# Add user to input group for scanner access
sudo usermod -a -G input $USER

# Logout and login for changes to take effect
exit
# Then log back in
```

#### 3. Test Scanner
```bash
# Open a text editor
nano test.txt

# Press scanner button and scan a QR code
# The data should appear in the text file automatically

# If it works, you're ready to use it with the app!
```

### Using Scanner with the Application

#### 1. Launch the Application
```bash
cd ~/Inventory_System
python3 main.py
```

#### 2. Navigate to Scanner
- Go to **"Add/Scan"** tab
- You'll see **"🔴 Handheld Scanner (MH-ET LIVE)"** section at the top
- Click in the **yellow input field**

#### 3. Scan QR Codes
1. **Click the yellow input field** (cursor should be blinking inside)
2. **Point scanner** at QR code on gallon
3. **Press scanner button** (shows red light)
4. Scanner detects QR code (shows white light)
5. Data automatically appears in field
6. **Action dialog opens automatically** with options:
   - ✅ REFILL - Record refill
   - ❌ DEFECT - Report defect
   - 🔍 TEST FOR LEAKS - Run leak detection (if sensor connected)
   - ✓ FIX DEFECT - Mark as fixed (if already defective)

#### 4. Rapid Scanning
You can scan multiple gallons quickly:
- Scan → Choose action → Scan next
- No need to click field again (stays focused)
- Perfect for batch processing!

### Scanner Troubleshooting on Pi

#### Scanner Not Working
```bash
# 1. Check if detected
lsusb | grep -i "symbol\|barcode\|scanner"

# 2. Check permissions
groups $USER
# Should show: 'input' group

# 3. Test in terminal
cat /dev/input/event0  # Try event0, event1, etc.
# Then scan - you should see binary output

# 4. Reboot if just plugged in
sudo reboot
```

#### Data Not Appearing
- Make sure **input field has focus** (cursor blinking)
- Try clicking field again before scanning
- Check if keyboard layout is correct: `sudo raspi-config` → Localisation
- Test scanner in text editor first to verify it works

#### Wrong Characters Appearing
```bash
# Scanner might be set to wrong keyboard layout
# Check Pi keyboard layout
sudo raspi-config
# → Localisation Options → Keyboard Layout
# Set to your scanner's default (usually US)

# Some scanners have configuration barcodes
# Check scanner manual for keyboard layout config barcodes
```

### Recommended Scanner Settings

Most MH-ET LIVE scanners can be configured by scanning special config QR codes:

1. **Enable Enter/Return suffix** (scanner presses Enter after scan)
   - This is usually enabled by default
   - Allows auto-processing in the app

2. **Set to USB-HID mode** (not serial)
   - This makes it act as a keyboard
   - Default mode for most models

3. **Enable continuous scan mode** (optional)
   - Hold button once, scan multiple codes
   - Useful for batch processing

4. **Set beep volume**
   - Confirmation beep when QR detected
   - Check scanner manual for config codes

### Alternative: Wireless Scanner

If using Bluetooth version:
```bash
# Enable Bluetooth
sudo systemctl start bluetooth
sudo systemctl enable bluetooth

# Pair scanner
bluetoothctl
> power on
> agent on
> default-agent
> scan on
# Wait for scanner to appear
> pair [MAC_ADDRESS]
> trust [MAC_ADDRESS]
> connect [MAC_ADDRESS]
> quit
```

### Performance Tips

- **Scanner works instantly** - faster than camera/image scanning
- **Keep QR codes clean** - dirt affects scanning
- **Good lighting helps** - scanner has built-in light but ambient light helps
- **Hold steady** - scanner needs <1 second to read
- **Distance**: 5-20cm from QR code works best

### Pi-Specific Advantages

✅ **Low power consumption** - Scanner uses <100mA
✅ **No driver installation** - Works instantly on Pi OS
✅ **No camera needed** - Save cost and USB port
✅ **Faster than camera** - Instant scan vs camera focus time
✅ **Works in any lighting** - Built-in LED illuminator
✅ **Rugged design** - Better for warehouse/outdoor use

### Multi-Scanner Setup

You can connect multiple scanners:
```bash
# Each scanner acts as separate keyboard
# They all work simultaneously
# Useful for multiple workstations

# Check all USB devices
lsusb
# Each scanner shows as separate device
```

## �🐛 Troubleshooting

### Camera Not Working
```bash
# Enable camera interface
sudo raspi-config
# → Interface Options → Camera → Enable

# Check camera modules
lsmod | grep bcm2835

# For USB cameras, check permissions
ls -l /dev/video0
# Should show: crw-rw---- 1 root video

# Add user to video group if needed
sudo usermod -a -G video pi
```

### Display Issues
```bash
# If GUI is too small/large
# Edit /boot/config.txt
sudo nano /boot/config.txt

# Adjust HDMI settings:
# hdmi_force_hotplug=1
# hdmi_group=2
# hdmi_mode=82  # 1080p 60Hz

# Reboot
sudo reboot
```

### Low Memory
```bash
# Check memory usage
free -h

# Increase swap space
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change CONF_SWAPSIZE to 1024 or 2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Slow Performance
```bash
# Close unnecessary programs
# Use lightweight desktop (LXDE instead of full Raspbian desktop)

# Disable Bluetooth if not needed
sudo systemctl disable bluetooth
sudo systemctl stop bluetooth

# Reduce graph refresh frequency in app
# (Graphs can be manually refreshed)
```

## 🚀 Auto-Start on Boot

### Method 1: Desktop Autostart
```bash
# Create autostart directory
mkdir -p ~/.config/autostart

# Create desktop entry
cat > ~/.config/autostart/inventory.desktop << EOF
[Desktop Entry]
Type=Application
Name=Water Gallon Inventory
Exec=python3 /home/pi/Inventory_System/main.py
X-GNOME-Autostart-enabled=true
EOF
```

### Method 2: systemd Service
```bash
# Create service file
sudo nano /etc/systemd/system/inventory.service

# Add content:
[Unit]
Description=Water Gallon Inventory System
After=graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
WorkingDirectory=/home/pi/Inventory_System
ExecStart=/usr/bin/python3 /home/pi/Inventory_System/main.py
Restart=on-failure

[Install]
WantedBy=graphical.target

# Enable service
sudo systemctl enable inventory.service
sudo systemctl start inventory.service
```

## 💡 Pi-Specific Features

### Touchscreen Support
- All buttons are sized for touch interaction (minimum 30x30 pixels)
- Large emoji icons for easy recognition
- Swipe scrolling support

### Portable Mode
If running on a battery-powered Pi:
1. Use auto-brightness settings
2. Disable WiFi/Bluetooth if not needed
3. Lower screen resolution
4. Use SSD instead of SD card for better power efficiency

### Remote Access
Access your inventory from another device:
```bash
# Enable VNC
sudo raspi-config
# → Interface Options → VNC → Enable

# Or use SSH
sudo raspi-config
# → Interface Options → SSH → Enable

# Connect from another computer
# VNC: raspberry_pi_ip:5900
# SSH: ssh pi@raspberry_pi_ip
```

## 📊 Database Backup

```bash
# Automatic backup to USB drive
# Insert USB drive, then:
sudo mkdir /mnt/usb
sudo mount /dev/sda1 /mnt/usb

# Copy database
cp inventory.db /mnt/usb/
cp -r qr_codes/ /mnt/usb/
cp -r logs/ /mnt/usb/

# Unmount
sudo umount /mnt/usb
```

## 🔧 Maintenance

### Update Application
```bash
cd Inventory_System
git pull origin main
pip3 install -r requirements.txt --upgrade
```

### Clear Cache
```bash
rm -rf __pycache__
python3 -m py_compile main.py
```

### Monitor Resource Usage
```bash
# Install htop
sudo apt-get install htop
htop

# Or use built-in tools
top
df -h
free -h
```

## 🎨 Customize for Your Pi

The application automatically adapts to your screen:
- Window size: 90% of screen or max 1200x700
- Minimum size: 800x500
- Fullscreen: F11 key
- Responsive tabs for small screens

## 📞 Support

For Raspberry Pi specific issues:
1. Check Raspberry Pi forums
2. Verify camera/display configuration
3. Check system logs: `journalctl -xe`
4. Monitor resources with `htop`

---

**Enjoy your Water Gallon Inventory System on Raspberry Pi! 🥧💧**
