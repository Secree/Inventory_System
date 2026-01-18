#!/bin/bash
# Test if the application can run

echo "🔍 Testing Water Gallon Inventory System"
echo "========================================="
echo ""

# Test 1: Python3
echo "1️⃣  Testing Python3..."
if command -v python3 &> /dev/null; then
    echo "   ✅ Python3 found: $(python3 --version)"
else
    echo "   ❌ Python3 NOT found"
    echo "   Install: sudo apt-get install python3"
    exit 1
fi

# Test 2: Tkinter
echo ""
echo "2️⃣  Testing Tkinter (GUI library)..."
if python3 -c "import tkinter" 2>/dev/null; then
    echo "   ✅ Tkinter is installed"
else
    echo "   ❌ Tkinter NOT installed"
    echo "   Install: sudo apt-get install python3-tk"
    exit 1
fi

# Test 3: Display
echo ""
echo "3️⃣  Testing Display..."
if [ -z "$DISPLAY" ]; then
    echo "   ⚠️  Warning: DISPLAY variable not set"
    echo "   This might cause issues on headless systems"
else
    echo "   ✅ DISPLAY is set: $DISPLAY"
fi

# Test 4: Required packages
echo ""
echo "4️⃣  Testing Python packages..."
MISSING=""

for pkg in PIL qrcode numpy cv2 matplotlib pyzbar; do
    if python3 -c "import $pkg" 2>/dev/null; then
        echo "   ✅ $pkg"
    else
        echo "   ❌ $pkg NOT installed"
        MISSING="$MISSING $pkg"
    fi
done

if [ -n "$MISSING" ]; then
    echo ""
    echo "   Missing packages:$MISSING"
    echo "   Install: pip3 install -r requirements.txt"
fi

# Test 5: Camera
echo ""
echo "5️⃣  Testing Camera (optional)..."
if [ -e /dev/video0 ]; then
    echo "   ✅ Camera found at /dev/video0"
else
    echo "   ⚠️  No camera at /dev/video0"
    echo "   Camera scanning won't work (optional feature)"
fi

# Test 6: Directories
echo ""
echo "6️⃣  Testing Directories..."
if [ -d "qr_codes" ]; then
    echo "   ✅ qr_codes/ exists"
else
    echo "   ⚠️  Creating qr_codes/"
    mkdir -p qr_codes
fi

if [ -d "logs" ]; then
    echo "   ✅ logs/ exists"
else
    echo "   ⚠️  Creating logs/"
    mkdir -p logs
fi

# Test 7: Database
echo ""
echo "7️⃣  Testing Database access..."
if python3 -c "import sqlite3; conn = sqlite3.connect('test.db'); conn.close()" 2>/dev/null; then
    echo "   ✅ SQLite works"
    rm -f test.db
else
    echo "   ❌ SQLite problem"
fi

# Test 8: File permissions
echo ""
echo "8️⃣  Testing File Permissions..."
if [ -x "main.py" ]; then
    echo "   ✅ main.py is executable"
else
    echo "   ⚠️  main.py is not executable"
    echo "   Fixing: chmod +x main.py"
    chmod +x main.py
fi

if [ -x "launch.sh" ]; then
    echo "   ✅ launch.sh is executable"
else
    echo "   ⚠️  launch.sh is not executable"
    echo "   Fixing: chmod +x launch.sh"
    chmod +x launch.sh
fi

# Summary
echo ""
echo "========================================="
echo "✅ READY TO RUN!"
echo ""
echo "Run with:"
echo "  ./launch.sh"
echo "  OR"
echo "  python3 main.py"
echo ""
echo "Or double-click the desktop icon!"
echo "========================================="
