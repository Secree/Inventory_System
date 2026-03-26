# System Timing Specifications

## Individual Stage Timings

| Stage | Timing | Details |
|-------|--------|---------|
| **QR code scan** | ~1 seconds | OpenCV/pyzbar QR code decode from camera |
| **Pneumatic sealing + pressurization** | ~2-3 seconds | Actuator lower + seal mechanics |
| **Pressure monitoring/hold** | ~15 seconds | `PRESSURE_TEST_TIME_MS = 15000ms` (leak detection) |
| **Actuator retraction / defect rejection OR conveyor transport to refilling station** | ~3-4 seconds | Actuator raise (~1s) + `REJECT_AFTER_RAISE_DELAY = 300ms` + `CONVEYOR_START_DELAY = 3000ms` |
| **Refilling (solenoid open to XKC cutoff)** | ~15-30 seconds | `FILL_START_DELAY_MS = 3000ms` (stable detection) + `MAX_FILL_TIME = 15000ms` (actual fill) |
| **Buzzer + gallon removal detection** | ~3-5 seconds | `REMOVAL_CONFIRM_MS = 500ms` confirmation + buzzer alert (~1s) + manual pickup time |

## Complete Cycle Breakdown

```
1. QR Scan & Intake:                       ~1s
   └─ Parse QR code, log gallon ID

2. Lower & Seal:                           ~2s
   └─ Extend primary actuator

3. Pre-Pressure Settle:                    ~2s
   └─ PRE_PRESSURE_POST_LOWER_DELAY = 2s

4. Leak Detection Test:                    ~15s
   └─ PRESSURE_TEST_TIME_MS = 15000ms
   └─ Apply pump pressure, monitor for leak

5. Post-Pressure Settle:                   ~2s
   └─ POST_PRESSURE_PRE_RAISE_DELAY = 2000ms

6. Raise & Clear:                          ~1.3s
   └─ Retract primary actuator
   └─ REJECT_AFTER_RAISE_DELAY = 300ms settle

7. Conveyor Start Delay:                   ~3s
   └─ CONVEYOR_START_DELAY = 3000ms
   └─ Move gallon to fill station

8. Gallon Detection:                       ~0.5s
   └─ Ultrasonic sensor triggers
   └─ Conveyor stops

9. Fill Start Delay:                       ~3s
   └─ FILL_START_DELAY_MS = 3000ms
   └─ Wait for stable ultrasonic detection

10. Water Filling:                         ~15-30s
    └─ Solenoid valve open
    └─ MAX_FILL_TIME = 15000ms (or until water level detected)

11. Removal Detection & Alert:             ~3-5s
    └─ REMOVAL_CONFIRM_MS = 500ms confirmation
    └─ Buzzer alarm (~1s for 3 tones)
    └─ Wait for gallon pickup

                                          ─────────
   **TOTAL CYCLE TIME:  ~45-50 seconds per gallon**
```

## Configurable Parameters (Arduino Code)

### Pressure Test (automated_refill_system.ino)
- `PRESSURE_TEST_TIME_MS = 15000` – How long to monitor for leaks
- `PUMP_ON_TIME_MS = 15000` – Keep pump active during test
- `PRE_PRESSURE_POST_LOWER_DELAY_SEC = 2` – Settle time before pressurization
- `POST_PRESSURE_PRE_RAISE_DELAY_MS = 2000` – Settle time after pressure test
- `REJECT_AFTER_RAISE_DELAY = 300` – Settle time after actuator raise

### Conveyor & Transport (automated_refill_system.ino)
- `CONVEYOR_START_DELAY = 3000` – Delay before conveyor starts (ms)
- `GALLON_STOP_DELAY_MS = 1000` – Keep conveyor running after first detect (ms)

### Fill Station (arduino2_fill_controller.ino)
- `FILL_START_DELAY_MS = 3000` – Wait after gallon detection before opening valve (ms)
- `MIN_FILL_TIME_MS = 1500` – Minimum fill duration (ms)
- `LEVEL_CONFIRM_MS = 400` – Water level confirmation delay (ms)
- `REMOVAL_CONFIRM_MS = 500` – Gallon removal confirmation delay (ms)
- `MAX_FILL_TIME = 15000` – Maximum fill timeout (ms)

### QR Scanner (main.py)
- ~500-1000ms decode time (camera frame capture + OpenCV processing)

## Performance Notes

- **Pressure test dominates**: 15 seconds is the single largest contributor to cycle time
- **Fill time variable**: Depends on container volume and water pressure (currently 15-30s)
- **Critical path**: Leak detection → Actuator cycle → Transport → Fill = ~45-50s per gallon
- **Throughput**: ~72-96 gallons per hour at full cycle time

## Optimization Opportunities

1. **Reduce pressure test time** – If leak detection threshold allows, reduce `PRESSURE_TEST_TIME_MS`
2. **Parallel conveyor movement** – Move gallon to fill station while pressure test runs (if hardware supports)
3. **Faster fill detection** – Optimize ultrasonic sensor for quicker gallon positioning
4. **Concurrent operations** – Implement background pressure monitoring while filling
