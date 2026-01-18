#!/bin/bash

# Water Gallon Inventory System - Raspberry Pi Setup Script
# This script sets up the application on Raspberry Pi OS

echo "🚰 Water Gallon Inventory System - Raspberry Pi Setup"
echo "======================================================"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    echo "   Continuing anyway..."
else
    echo "✅ Detected: $(cat /proc/device-tree/model)"
fi
echo ""

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update

# Install Python3 and pip if not installed
echo "🐍 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Installing Python3..."
    sudo apt-get install -y python3 python3-pip
else
    echo "✅ Python3 is already installed: $(python3 --version)"
fi

# Install system dependencies for OpenCV and GUI
echo "📦 Installing system dependencies..."
sudo apt-get install -y \
    python3-tk \
    python3-pil \
    python3-pil.imagetk \
    libzbar0 \
    libopencv-dev \
    python3-opencv \
    libatlas-base-dev \
    libjasper-dev \
    libqtgui4 \
    libqt4-test \
    libhdf5-dev \
    libhdf5-serial-dev \
    libilmbase-dev \
    libopenexr-dev \
    libgstreamer1.0-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev

# Install Python packages
echo "🐍 Installing Python packages..."
pip3 install --upgrade pip

# Install requirements
if [ -f requirements.txt ]; then
    echo "Installing from requirements.txt..."
    pip3 install -r requirements.txt
else
    echo "Installing packages individually..."
    pip3 install qrcode[pil] Pillow opencv-python numpy matplotlib pyzbar
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p qr_codes
mkdir -p logs

# Set permissions
echo "🔒 Setting permissions..."
chmod +x setup_raspberry_pi.sh
chmod +x main.py 2>/dev/null || true

# Test camera (if available)
echo ""
echo "📷 Testing camera access..."
if [ -e /dev/video0 ]; then
    echo "✅ Camera detected at /dev/video0"
    # Add user to video group if not already
    sudo usermod -a -G video $USER
    echo "✅ Added user to video group (logout/login required)"
else
    echo "⚠️  No camera detected at /dev/video0"
    echo "   QR scanning from camera may not work"
fi

# Create desktop shortcut
echo ""
echo "🖥️  Creating desktop shortcut..."
DESKTOP_DIR="$HOME/Desktop"
mkdir -p "$DESKTOP_DIR"
DESKTOP_FILE="$DESKTOP_DIR/WaterGallonInventory.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Water Gallon Inventory
Comment=Inventory Management System
Exec=$(pwd)/launch.sh
Icon=emblem-package
Path=$(pwd)
Terminal=false
StartupNotify=true
Categories=Utility;Application;
EOF

chmod +x "$DESKTOP_FILE"

# Make main files executable
chmod +x main.py
chmod +x launch.sh
chmod +x run_on_pi.sh

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 To run the application:"
echo "   1. From terminal: python3 main.py"
echo "   2. From desktop: Double-click 'Water Gallon Inventory' icon"
echo ""
echo "💡 Tips for Raspberry Pi:"
echo "   • Use a mouse for best experience"
echo "   • Press F11 for fullscreen mode"
echo "   • If camera doesn't work, you may need to enable it:"
echo "     sudo raspi-config → Interface Options → Camera"
echo ""
echo "⚠️  Note: If you added user to video group, logout and login"
echo "   for camera permissions to take effect."
echo ""
