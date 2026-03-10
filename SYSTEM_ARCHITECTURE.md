# System Architecture - Automated Gallon Refill

## Complete System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI / PC                               │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Python Control Software (automated_system_control.py)       │ │
│  │  - Start/Stop control                                        │ │
│  │  - Real-time monitoring                                      │ │
│  │  - Statistics & logging                                      │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
│                           │                                         │
│                           │ USB Serial (9600 baud)                  │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ARDUINO UNO/MEGA                                 │
│                    (Master Controller)                              │
│                                                                     │
│  Sketch: automated_refill_system.ino                               │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              STATE MACHINE CONTROL                           │ │
│  │                                                              │ │
│  │  IDLE → CHECK_PRESSURE → MOVE → DETECT → FILL → MOVE_NEXT  │ │
│  │           ↓ Leak           ↓      ↓        ↓                │ │
│  │        ERROR_LEAK        Timeout OK     Full                │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  Pin Assignments:                                                  │
│  - A0: Pressure Sensor                                             │
│  - Pin 5: Solenoid Valve Relay                                     │
│  - Pin 6, 7, 8: Conveyor Motor Driver                              │
│  - Pin 9, 10: Ultrasonic Sensor                                    │
└───┬─────────────┬──────────────────┬──────────────────┬────────────┘
    │             │                  │                  │
    │             │                  │                  │
    ▼             ▼                  ▼                  ▼
┌────────┐   ┌─────────┐      ┌──────────┐      ┌──────────────┐
│PRESSURE│   │CONVEYOR │      │ULTRASONIC│      │  SOLENOID    │
│ SENSOR │   │  MOTOR  │      │  SENSOR  │      │    VALVE     │
│        │   │         │      │          │      │              │
│MPX5700 │   │ + L298N │      │ HC-SR04  │      │ + 5V Relay   │
│        │   │ Driver  │      │          │      │   Module     │
└────────┘   └─────────┘      └──────────┘      └──────────────┘
    │             │                  │                  │
    │             │                  │                  │
    ▼             ▼                  ▼                  ▼
┌────────────────────────────────────────────────────────────────┐
│                       PHYSICAL PROCESS                         │
│                                                                │
│  [Gallon] ──→ Pressure Check ──→ Conveyor ──→ Fill Station   │
│                   (Leak?)           ↓            ↓             │
│                                  Position    Fill Level        │
│                                  Detection   Detection         │
│                                     ↓            ↓             │
│                                  STOP      Open Valve          │
│                                               ↓                │
│                                          Water Filling         │
│                                               ↓                │
│                                          Full Detected         │
│                                               ↓                │
│                                         Close Valve            │
│                                               ↓                │
│                                         Move Forward           │
│                                               ↓                │
│                                         Next Gallon            │
└────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌──────────────┐
│  START CMD   │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Check Pressure   │──── < LEAK_THRESHOLD ──→ STOP & ALERT
└──────┬───────────┘
       │ OK
       ▼
┌──────────────────┐
│ Start Conveyor   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐       ┌──────────────┐
│ Ultrasonic Scan  │──NO──→│   Timeout?   │──YES──→ ERROR
└──────┬───────────┘       └──────────────┘
       │ DETECTED
       ▼
┌──────────────────┐
│ Stop Conveyor    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Open Valve      │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐       ┌──────────────┐
│ Monitor Water    │──NO──→│   Timeout?   │──YES──→ Close & Continue
│    Level         │       └──────────────┘
└──────┬───────────┘
       │ FULL
       ▼
┌──────────────────┐
│  Close Valve     │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Move Conveyor    │
│  (Fixed Time)    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Cycle Complete   │
└──────┬───────────┘
       │
       └──────→ Loop back to Check Pressure
```

## Communication Protocol

### Python → Arduino (Commands)

| Command | Purpose |
|---------|---------|
| `START\n` | Begin automated cycle |
| `STOP\n` | Emergency stop all operations |
| `STATUS\n` | Request current state & sensor values |
| `RESET\n` | Reset to IDLE state |

### Arduino → Python (Responses)

| Message | Meaning |
|---------|---------|
| `READY` | System initialized |
| `SYSTEM:STARTED` | Automation started |
| `SYSTEM:STOPPED` | Automation stopped |
| `PRESSURE:XX.X PSI` | Pressure reading |
| `LEAK:DETECTED` | Pressure below threshold |
| `LEAK:OK` | Pressure normal |
| `CONVEYOR:MOVING` | Motor activated |
| `CONVEYOR:STOPPED` | Motor stopped |
| `GALLON:DETECTED` | Ultrasonic detected gallon |
| `FILLING:START` | Valve opened |
| `FILLING:COMPLETE` | Fill cycle done |
| `CYCLE:COMPLETE (Total: N)` | One gallon processed |
| `ERROR: <message>` | Error occurred |

## Timing Diagram

```
Time →
0s     1s     2s     3s     4s     5s     6s     7s     8s     9s    10s
│      │      │      │      │      │      │      │      │      │      │
│                                                                      
├─ Check Pressure [OK] ──────────────────────────►                    
│                                                  │                   
├─────────────────────────── Start Conveyor ──────┤                   
│                                                  │                   
├────────────────────────────────── Gallon Detected @ 3.2s            
│                                                  │                   
├─────────────────────────────────── Stop Conveyor│                   
│                                                  │                   
├────────────────────────────────────── Open Valve│                   
│                                                  ├─── Filling ───────►
│                                                  │                   
├─────────────────────────────────────────────────┼─ Water Level Rise 
│                                                  │                   
├─────────────────────────────────────────────────┼────── Full @ 10s  
│                                                  │                   
├─────────────────────────────────────────── Close Valve              
│                                                                      
├──────────────────────────────────────────── Move Forward ───────────►
│                                                                      
└──────────────────────────────────────────────── Next Cycle ─────────►
```

## Power Requirements

```
┌──────────────┐
│ 12V/3A PSU   │──────┐
└──────────────┘      │
                      ├──→ Conveyor Motor (12V)
                      │
                      └──→ Solenoid Valve (12V via Relay)

┌──────────────┐
│ 5V/2A PSU    │──────┐
└──────────────┘      │
                      ├──→ Arduino (5V via USB or barrel jack)
                      │
                      ├──→ Sensors (HC-SR04, MPX5700)
                      │
                      └──→ Relay Module (5V logic)

⚠️ IMPORTANT: All ground connections must be common!
```

## Physical Layout Example

```
                    Water Supply
                         │
                         ▼
                    ┌─────────┐
                    │ SOLENOID│
                    │  VALVE  │
                    └────┬────┘
                         │
                         ▼
    Ultrasonic ──→  ┌─────────┐  ←── Pressure
     Sensor          │  FILL   │      Sensor
                     │ STATION │
                     └────┬────┘
                          │
         ┌────────────────┴────────────────┐
         │      CONVEYOR BELT               │
         │                                  │
    ┌────┴────┐    ┌─────────┐    ┌───────┴──┐
    │ Gallon  │───→│ Gallon  │───→│  Gallon  │
    │  (In)   │    │ (Fill)  │    │  (Out)   │
    └─────────┘    └─────────┘    └──────────┘
```

## Safety Interlocks

```
┌───────────────────────┐
│   Pressure Check      │
│   FAIL               │
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│  STOP ALL OPERATIONS  │
│  - Conveyor OFF       │
│  - Valve CLOSED       │
│  - Alert User         │
└───────────────────────┘

┌───────────────────────┐
│   Fill Timeout        │
│   > MAX_FILL_TIME     │
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│  Close Valve          │
│  Continue Cycle       │
│  Log Warning          │
└───────────────────────┘

┌───────────────────────┐
│  Gallon Not Detected  │
│  > 10 seconds         │
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│  STOP & ERROR         │
│  Alert: Check Belt    │
└───────────────────────┘
```
