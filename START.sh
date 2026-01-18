#!/bin/bash
# Simple one-command runner with error messages

cd "$(dirname "$0")"

echo "🚰 Starting Water Gallon Inventory System..."
echo ""

# Check Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python3 not found!"
    echo "Install with: sudo apt-get install python3"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check tkinter
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "❌ ERROR: Python tkinter not installed!"
    echo "Install with: sudo apt-get install python3-tk"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ ERROR: main.py not found!"
    echo "Make sure you're in the correct directory."
    read -p "Press Enter to exit..."
    exit 1
fi

# Run it
echo "✅ Launching application..."
python3 main.py

# If it exits, pause to see errors
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Application exited with errors."
    read -p "Press Enter to close..."
fi
