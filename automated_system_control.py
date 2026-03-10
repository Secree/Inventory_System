#!/usr/bin/env python3
"""
Automated Gallon Refill System - Python Controller
Controls and monitors the Arduino-based automated refill system
"""

import serial
import serial.tools.list_ports
import time
import sys
from datetime import datetime


class AutomatedRefillSystem:
    """Control interface for automated gallon refill system"""
    
    def __init__(self, port=None, baudrate=9600):
        """
        Initialize connection to Arduino
        
        Args:
            port: Serial port (e.g., 'COM3' or '/dev/ttyUSB0')
            baudrate: Serial baud rate (default 9600)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        
        # Statistics
        self.gallons_processed = 0
        self.leaks_detected = 0
        self.errors_occurred = 0
        self.start_time = None
        
    def find_arduino(self):
        """Auto-detect Arduino port"""
        print("Searching for Arduino...")
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            # Check for Arduino VID/PID or CH340 (common USB-Serial chip)
            if 'Arduino' in port.description or 'CH340' in port.description or \
               '2341' in str(port.vid) or '1A86' in str(port.vid):
                print(f"✓ Found Arduino on {port.device}: {port.description}")
                return port.device
        
        # Fallback: list all available ports
        if ports:
            print("\nAvailable ports:")
            for i, port in enumerate(ports):
                print(f"  {i+1}. {port.device} - {port.description}")
            
            choice = input("\nSelect port number (or press Enter to skip): ").strip()
            if choice.isdigit() and 0 < int(choice) <= len(ports):
                return ports[int(choice)-1].device
        
        return None
    
    def connect(self):
        """Connect to Arduino"""
        if not self.port:
            self.port = self.find_arduino()
        
        if not self.port:
            print("❌ No Arduino found. Please specify port manually.")
            return False
        
        try:
            print(f"Connecting to {self.port}...")
            self.serial = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(2)  # Wait for Arduino to reset
            
            # Wait for READY message
            start = time.time()
            while time.time() - start < 5:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    print(line)
                    if 'READY' in line:
                        print("✓ Connected to Arduino")
                        return True
            
            print("⚠ Connected but no READY signal received")
            return True
            
        except serial.SerialException as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Arduino"""
        if self.serial and self.serial.is_open:
            self.send_command('STOP')
            time.sleep(0.5)
            self.serial.close()
            print("Disconnected")
    
    def send_command(self, command):
        """Send command to Arduino"""
        if not self.serial or not self.serial.is_open:
            print("❌ Not connected to Arduino")
            return False
        
        try:
            self.serial.write(f"{command}\n".encode())
            self.serial.flush()
            return True
        except Exception as e:
            print(f"❌ Send failed: {e}")
            return False
    
    def read_response(self, timeout=1):
        """Read response from Arduino"""
        if not self.serial or not self.serial.is_open:
            return None
        
        end_time = time.time() + timeout
        while time.time() < end_time:
            if self.serial.in_waiting:
                try:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    return line
                except Exception as e:
                    print(f"Read error: {e}")
                    return None
        return None
    
    def start_system(self):
        """Start automated refill system"""
        print("\n" + "="*50)
        print("Starting Automated Refill System")
        print("="*50)
        
        if self.send_command('START'):
            self.running = True
            self.start_time = datetime.now()
            print("✓ System started")
            return True
        return False
    
    def stop_system(self):
        """Stop automated refill system"""
        print("\nStopping system...")
        if self.send_command('STOP'):
            self.running = False
            print("✓ System stopped")
            self.print_statistics()
            return True
        return False
    
    def get_status(self):
        """Get current system status"""
        if self.send_command('STATUS'):
            time.sleep(0.1)
            # Read multiple lines of status
            status = []
            for _ in range(10):
                line = self.read_response(timeout=0.5)
                if line:
                    status.append(line)
                else:
                    break
            return status
        return []
    
    def reset_system(self):
        """Reset system to idle state"""
        print("\nResetting system...")
        if self.send_command('RESET'):
            self.running = False
            print("✓ System reset")
            return True
        return False
    
    def monitor(self):
        """Monitor system in real-time"""
        print("\n" + "="*50)
        print("Monitoring System (Ctrl+C to stop)")
        print("="*50)
        
        try:
            while True:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line:
                        # Add timestamp
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] {line}")
                        
                        # Update statistics
                        if 'CYCLE:COMPLETE' in line:
                            self.gallons_processed += 1
                        elif 'LEAK:DETECTED' in line:
                            self.leaks_detected += 1
                        elif 'ERROR' in line:
                            self.errors_occurred += 1
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped")
    
    def print_statistics(self):
        """Print system statistics"""
        print("\n" + "="*50)
        print("SYSTEM STATISTICS")
        print("="*50)
        print(f"Gallons Processed: {self.gallons_processed}")
        print(f"Leaks Detected: {self.leaks_detected}")
        print(f"Errors: {self.errors_occurred}")
        
        if self.start_time:
            runtime = datetime.now() - self.start_time
            hours = runtime.total_seconds() / 3600
            if self.gallons_processed > 0:
                rate = self.gallons_processed / hours
                print(f"Runtime: {runtime}")
                print(f"Processing Rate: {rate:.2f} gallons/hour")
        print("="*50)
    
    def interactive_mode(self):
        """Interactive control mode"""
        print("\n" + "="*50)
        print("INTERACTIVE CONTROL MODE")
        print("="*50)
        print("Commands:")
        print("  start   - Start automated system")
        print("  stop    - Stop system")
        print("  status  - Get current status")
        print("  reset   - Reset system")
        print("  monitor - Monitor real-time (Ctrl+C to exit)")
        print("  stats   - Show statistics")
        print("  quit    - Exit program")
        print("="*50 + "\n")
        
        try:
            while True:
                cmd = input(">>> ").strip().lower()
                
                if cmd == 'start':
                    self.start_system()
                    
                elif cmd == 'stop':
                    self.stop_system()
                    
                elif cmd == 'status':
                    status = self.get_status()
                    print("\n--- Status ---")
                    for line in status:
                        print(line)
                    print("-" * 14)
                    
                elif cmd == 'reset':
                    self.reset_system()
                    
                elif cmd == 'monitor':
                    self.monitor()
                    
                elif cmd == 'stats':
                    self.print_statistics()
                    
                elif cmd == 'quit' or cmd == 'exit':
                    break
                    
                elif cmd == 'help':
                    print("Available commands: start, stop, status, reset, monitor, stats, quit")
                    
                elif cmd == '':
                    continue
                    
                else:
                    print(f"Unknown command: {cmd}")
                    print("Type 'help' for available commands")
                    
        except KeyboardInterrupt:
            print("\n\nExiting...")


def main():
    """Main program"""
    print("="*60)
    print(" AUTOMATED GALLON REFILL SYSTEM - Control Software")
    print("="*60)
    
    # Parse command line arguments
    port = None
    if len(sys.argv) > 1:
        port = sys.argv[1]
    
    # Create system controller
    system = AutomatedRefillSystem(port=port)
    
    # Connect to Arduino
    if not system.connect():
        print("\nPlease specify port manually:")
        print("  Windows: python automated_system_control.py COM3")
        print("  Linux:   python3 automated_system_control.py /dev/ttyUSB0")
        sys.exit(1)
    
    try:
        # Run interactive mode
        system.interactive_mode()
    finally:
        # Cleanup
        system.disconnect()
        print("\nGoodbye!")


if __name__ == '__main__':
    main()
