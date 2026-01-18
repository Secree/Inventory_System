"""
Pressure Sensor Module for Leak Detection
Monitors pressure in water gallons and detects leaks automatically
For Raspberry Pi with pressure sensor integration
"""

import time
import threading
from datetime import datetime


class PressureSensor:
    """
    Handles pressure sensor readings for leak detection
    Supports multiple sensor types compatible with Raspberry Pi
    """
    
    def __init__(self, sensor_type='analog', pin=None, threshold=5.0, monitoring_duration=30):
        """
        Initialize pressure sensor
        
        Args:
            sensor_type: 'analog' (via ADC) or 'i2c' (digital sensor)
            pin: GPIO pin number or I2C address
            threshold: Pressure drop percentage to trigger leak detection (default 5%)
            monitoring_duration: Seconds to monitor before declaring leak (default 30s)
        """
        self.sensor_type = sensor_type
        self.pin = pin
        self.threshold = threshold  # Percentage drop
        self.monitoring_duration = monitoring_duration
        
        self.current_pressure = 0.0
        self.baseline_pressure = 0.0
        self.is_monitoring = False
        self.monitoring_thread = None
        self.leak_detected = False
        self.leak_callback = None
        
        # Pressure reading history for smoothing
        self.pressure_history = []
        self.max_history = 10
        
        self.setup_sensor()
    
    def setup_sensor(self):
        """Initialize the pressure sensor hardware"""
        try:
            if self.sensor_type == 'analog':
                # For analog sensors using MCP3008 ADC
                try:
                    import busio
                    import digitalio
                    import board
                    import adafruit_mcp3xxx.mcp3008 as MCP
                    from adafruit_mcp3xxx.analog_in import AnalogIn
                    
                    # Create SPI bus
                    spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
                    cs = digitalio.DigitalInOut(board.D5)  # Chip select on D5
                    mcp = MCP.MCP3008(spi, cs)
                    
                    # Create analog input on specified channel (default CH0)
                    channel = self.pin if self.pin is not None else 0
                    self.sensor = AnalogIn(mcp, getattr(MCP, f'P{channel}'))
                    print(f"✅ Analog pressure sensor initialized on MCP3008 CH{channel}")
                    
                except ImportError:
                    print("⚠️ Adafruit MCP3008 library not installed. Using simulation mode.")
                    self.sensor = None
                    
            elif self.sensor_type == 'i2c':
                # For I2C digital pressure sensors (BMP280, BME280, etc.)
                try:
                    import board
                    import adafruit_bmp280
                    
                    i2c = board.I2C()
                    self.sensor = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
                    print("✅ I2C pressure sensor (BMP280) initialized")
                    
                except ImportError:
                    print("⚠️ Adafruit BMP280 library not installed. Using simulation mode.")
                    self.sensor = None
            
            else:
                print("⚠️ Unknown sensor type. Using simulation mode.")
                self.sensor = None
                
        except Exception as e:
            print(f"⚠️ Sensor initialization error: {e}. Using simulation mode.")
            self.sensor = None
    
    def read_pressure(self):
        """
        Read current pressure from sensor
        Returns pressure value in PSI or kPa depending on sensor
        """
        try:
            if self.sensor is None:
                # Simulation mode for testing without hardware
                import random
                base = 30.0  # Base pressure in PSI
                if self.is_monitoring and self.leak_detected:
                    # Simulate pressure drop
                    elapsed = time.time() - self.monitoring_start_time
                    drop = (elapsed / self.monitoring_duration) * (self.threshold + 5)
                    return max(0, base - drop + random.uniform(-0.5, 0.5))
                return base + random.uniform(-1, 1)
            
            elif self.sensor_type == 'analog':
                # Read analog voltage and convert to pressure
                voltage = self.sensor.voltage
                # Typical pressure sensor: 0.5V = 0 PSI, 4.5V = 100 PSI
                pressure = ((voltage - 0.5) / 4.0) * 100.0
                return max(0, pressure)
            
            elif self.sensor_type == 'i2c':
                # Read from I2C sensor (returns kPa or hPa)
                pressure_kpa = self.sensor.pressure / 10.0  # Convert hPa to kPa
                return pressure_kpa
            
        except Exception as e:
            print(f"❌ Error reading pressure: {e}")
            return 0.0
    
    def get_average_pressure(self, samples=5):
        """Get average pressure over multiple samples for accuracy"""
        readings = []
        for _ in range(samples):
            readings.append(self.read_pressure())
            time.sleep(0.1)
        return sum(readings) / len(readings)
    
    def start_monitoring(self, inventory_id, callback=None):
        """
        Start monitoring pressure for leak detection
        
        Args:
            inventory_id: The gallon ID being monitored
            callback: Function to call when leak is detected (receives inventory_id, pressure_drop)
        """
        if self.is_monitoring:
            print("⚠️ Already monitoring another gallon")
            return False
        
        self.inventory_id = inventory_id
        self.leak_callback = callback
        self.is_monitoring = True
        self.leak_detected = False
        
        # Record baseline pressure
        self.baseline_pressure = self.get_average_pressure()
        self.monitoring_start_time = time.time()
        
        print(f"🔍 Started monitoring {inventory_id} - Baseline: {self.baseline_pressure:.2f} PSI")
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitoring_thread.start()
        
        return True
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.is_monitoring:
            # Read current pressure
            current = self.read_pressure()
            self.current_pressure = current
            
            # Add to history for smoothing
            self.pressure_history.append(current)
            if len(self.pressure_history) > self.max_history:
                self.pressure_history.pop(0)
            
            # Calculate average from history
            avg_pressure = sum(self.pressure_history) / len(self.pressure_history)
            
            # Calculate pressure drop percentage
            if self.baseline_pressure > 0:
                pressure_drop = ((self.baseline_pressure - avg_pressure) / self.baseline_pressure) * 100
            else:
                pressure_drop = 0
            
            # Check for leak
            elapsed_time = time.time() - self.monitoring_start_time
            
            if pressure_drop >= self.threshold and elapsed_time >= self.monitoring_duration:
                if not self.leak_detected:
                    self.leak_detected = True
                    print(f"🚨 LEAK DETECTED! Pressure drop: {pressure_drop:.2f}%")
                    print(f"   Baseline: {self.baseline_pressure:.2f} PSI → Current: {avg_pressure:.2f} PSI")
                    
                    # Call callback function
                    if self.leak_callback:
                        self.leak_callback(self.inventory_id, pressure_drop, self.baseline_pressure, avg_pressure)
                    
                    # Stop monitoring after leak detected
                    self.stop_monitoring()
                    break
            
            time.sleep(1)  # Check every second
    
    def stop_monitoring(self):
        """Stop pressure monitoring"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)
        print(f"⏹️ Stopped monitoring {getattr(self, 'inventory_id', 'unknown')}")
    
    def get_status(self):
        """Get current monitoring status"""
        if not self.is_monitoring:
            return {
                'monitoring': False,
                'inventory_id': None,
                'current_pressure': 0,
                'baseline_pressure': 0,
                'pressure_drop': 0,
                'elapsed_time': 0,
                'leak_detected': False
            }
        
        elapsed = time.time() - self.monitoring_start_time
        pressure_drop = 0
        if self.baseline_pressure > 0:
            pressure_drop = ((self.baseline_pressure - self.current_pressure) / self.baseline_pressure) * 100
        
        return {
            'monitoring': True,
            'inventory_id': self.inventory_id,
            'current_pressure': self.current_pressure,
            'baseline_pressure': self.baseline_pressure,
            'pressure_drop': pressure_drop,
            'elapsed_time': elapsed,
            'leak_detected': self.leak_detected
        }


# Test function for development
if __name__ == '__main__':
    print("🧪 Testing Pressure Sensor Module\n")
    
    def leak_callback(inventory_id, drop_pct, baseline, current):
        print(f"\n🚨 CALLBACK: Leak detected in {inventory_id}")
        print(f"   Drop: {drop_pct:.2f}%")
        print(f"   Baseline: {baseline:.2f} PSI → Current: {current:.2f} PSI")
    
    # Create sensor (simulation mode)
    sensor = PressureSensor(sensor_type='analog', threshold=5.0, monitoring_duration=10)
    
    print("Starting leak detection test...")
    sensor.start_monitoring('WG-0001', callback=leak_callback)
    
    # Simulate monitoring
    try:
        while sensor.is_monitoring:
            status = sensor.get_status()
            print(f"⏱️ {status['elapsed_time']:.1f}s | "
                  f"Pressure: {status['current_pressure']:.2f} PSI | "
                  f"Drop: {status['pressure_drop']:.2f}%")
            time.sleep(2)
    except KeyboardInterrupt:
        sensor.stop_monitoring()
    
    print("\n✅ Test completed")
