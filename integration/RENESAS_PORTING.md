# Renesas porting checklist

The evaluator is board-neutral. The final firmware port should keep the policy
in `GuardEvaluator.cpp` and put all Renesas SDK calls behind small adapters.

## Required adapters

### Clock

Provide a monotonic millisecond clock for `now_ms`. Do not use wall-clock time
for watchdog decisions.

### Heartbeat transport

Decode one complete `heartbeat` frame at a time, validate protocol version and
sequence, then update `heartbeat_observed_at_ms`. Treat malformed, stale, or
replayed messages as transport faults rather than healthy input.

### Sensors

Convert readings into the exact units expected by `GuardInput`:

- temperature: degrees Celsius;
- humidity: relative humidity percentage `[0, 100]`;
- mount tilt: signed degrees;
- vibration: RMS acceleration in `g`;
- faults: non-empty diagnostic codes.

If a sensor is disconnected, stale, out of range, or returns a non-finite
number, add a fault code. The evaluator intentionally fails safe.

### Output

Replace `LocalLedBuzzerOutput` with a GPIO/HMI adapter. Verify power-on output,
reset output, and communication-loss output on the real board.

### Hardware watchdog

The software evaluator is not a substitute for the Renesas hardware watchdog.
Configure the watchdog independently for task stalls, sensor-bus deadlocks, and
firmware lockups. Record the reset reason and expose it in diagnostics.

## Timing targets for the MVP

| Activity | Target |
|---|---:|
| Sensor sample | 100 ms |
| Android heartbeat | 250 ms |
| Watchdog timeout | 1000 ms |
| Status publication | At least 10 Hz |

Measure actual values on the board and include the evidence in the hackathon
demo notes. Do not claim the target timing until it has been measured.

## Hardware validation matrix

- phone heartbeat present / absent;
- BLE disconnect and reconnect;
- temperature threshold crossing and recovery;
- humidity/dew-point margin crossing;
- mount tilt on both signs;
- vibration above and below threshold;
- sensor unplugged during trusted operation;
- board reset while Android remains alive;
- Android freeze while board remains powered;
- power cycle and startup self-test.
