#!/bin/bash
# Launcher script with error handling

# Change to script directory
cd "$(dirname "$0")"

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    zenity --error --text="Python3 is not installed!\n\nPlease install it first:\nsudo apt-get install python3" 2>/dev/null || \
    xmessage -center "Python3 is not installed! Please install it first: sudo apt-get install python3"
    exit 1
fi

# Check if required packages are installed
if ! python3 -c "import tkinter" 2>/dev/null; then
    zenity --error --text="Python tkinter is not installed!\n\nPlease install it:\nsudo apt-get install python3-tk" 2>/dev/null || \
    xmessage -center "Python tkinter is not installed! Install: sudo apt-get install python3-tk"
    exit 1
fi

# Run the application
python3 main.py 2>&1

# If it fails, show error
if [ $? -ne 0 ]; then
    zenity --error --text="Application failed to start!\n\nCheck terminal for errors:\npython3 main.py" 2>/dev/null || \
    xmessage -center "Application failed to start! Run in terminal: python3 main.py"
    exit 1
fi
