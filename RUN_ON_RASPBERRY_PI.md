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

## 🐛 Troubleshooting

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
