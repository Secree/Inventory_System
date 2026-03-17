# Automated Refill System Hardware Schematic

This schematic is based on the active pin constants in:
- automated_refill_system.ino (Arduino1, master)
- solenoid_valve_arduino.ino (Arduino2, fill controller)

## 1) System Block Diagram

```mermaid
flowchart LR
    APP[Python App main.py] <-->|USB Serial 9600| A1[Arduino1 Master]
    APP <-->|USB Serial 9600| A2[Arduino2 Fill Controller]

    A1 <-->|OUT D2 and SCK D3| PS[Pressure Sensor Module OUT/SCK]
    A1 -->|D13 relay| PUMP[Air Pump]

    A1 -->|A1,A2, D11 PWM via Motor Driver| CONV[Conveyor Motor]
    A1 -->|D5,D6, D9 PWM via L298N| ACT1[Primary Actuator]
    A1 -->|D7,D8, D10 PWM via L298N| ACT2[Reject Actuator]

    A2 -->|D9 TRIG D10 ECHO| US2[Ultrasonic Sensor HC-SR04]
    A2 -->|D8 digital| LVL[Level Sensor]
    A2 -->|D7 relay| SOL[Solenoid Valve]

    PSU5[5V Logic Supply] --> A1
    PSU5 --> A2
    PSU5 --> PS
    PSU5 --> US2
    PSU5 --> LVL

    PSU12[12V Motor Supply] --> CONV
    PSU12 --> ACT1
    PSU12 --> ACT2

    GND[(Common Ground)] --- A1
    GND --- A2
    GND --- PSU5
    GND --- PSU12
```

## 2) Arduino1 Master Pin Map

| Function | Module | Arduino1 Pin |
|---|---|---|
| Pressure data | Pressure sensor OUT | D2 |
| Pressure clock | Pressure sensor SCK | D3 |
| Conveyor IN1 | Conveyor driver | A1 |
| Conveyor IN2 | Conveyor driver | A2 |
| Conveyor ENA PWM | Conveyor driver | D11 |
| Primary actuator IN1 | L298N | D5 |
| Primary actuator IN2 | L298N | D6 |
| Primary actuator ENA PWM | L298N | D9 |
| Reject actuator IN1 | L298N | D7 |
| Reject actuator IN2 | L298N | D8 |
| Reject actuator ENA PWM | L298N | D10 |
| Air pump relay control | Relay module | D13 |

## 3) Arduino2 Fill Controller Pin Map

| Function | Module | Arduino2 Pin |
|---|---|---|
| Ultrasonic TRIG | HC-SR04 | D9 |
| Ultrasonic ECHO | HC-SR04 | D10 |
| Solenoid relay control | Relay module | D7 |
| Level sensor input | Water level sensor | D8 |

## 4) Wiring Notes

- Keep all grounds common: Arduino1 GND, Arduino2 GND, relay GND, motor driver GND, sensor GND, and power supply GND must be tied together.
- Do not power motors from Arduino 5V. Use external 12V for conveyor/actuators through motor drivers.
- Relay modules for pump and solenoid are usually active LOW. Verify before live testing.
- Use flyback protection and proper relay/motor driver modules for inductive loads.
- Start with actuators disconnected from mechanical load during first firmware test.

## 5) Control Signal Flow

```mermaid
sequenceDiagram
    participant PC as Python App
    participant M as Arduino1 Master
    participant F as Arduino2 Fill

    PC->>M: STATUS
    M-->>PC: PRESSURE readings
    M-->>PC: LEAK:OK or LEAK:DETECTED

    alt No leak
        PC->>F: ENABLE
        PC->>M: CONVEYOR_START
        F-->>PC: GALLON:DETECTED
        M-->>PC: CONVEYOR:STOPPED
        F-->>PC: FILLING:START
        F-->>PC: FILLING:COMPLETE
        F-->>PC: GALLON:REMOVED_READY
    else Leak detected
        PC->>F: DISABLE
        PC->>M: REJECT
        M-->>PC: REJECT:DONE
    end
```
