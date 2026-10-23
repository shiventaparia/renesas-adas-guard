# Renesas ADAS guard integration scaffold

This directory is a board-neutral integration seam between the upstream
`com.example.adas` Android application and the portable Python/C++ ADAS trust
evaluator. It contains no Android Gradle project and no Renesas SDK headers,
so the files can be copied into an existing application or host-side SDK
sample.

## Files

| File | Purpose |
| --- | --- |
| `guard-protocol.md` | Versioned heartbeat/status contract, reason codes, thresholds, and examples. |
| `GuardModels.kt` | `kotlinx.serialization` trust status, reasons, score, freshness, dew-point, and outputs. |
| `GuardProtocol.kt` | JSON encoding/decoding and status validation. |
| `GuardController.kt` | Android heartbeat publisher, stale-status rejection, and `StateFlow` status exposure. |
| `GuardEvaluator.h/.cpp` | Board-agnostic C++17 evaluator matching the Python core's penalties and precedence. |
| `main.cpp` | Host demo for healthy, thermal/fog/tilt warning, and heartbeat-expiry paths. |
| `../core/scenario_runner.py` | Dependency-free scripted Python simulator for normal, hot, fog, tilt, vibration, sensor-fault, and heartbeat-loss states. |

## Android placement in the upstream app

Copy the three Kotlin files into the existing Android module at a package path
matching `com.example.adas`, for example:

```text
app/src/main/java/com/example/adas/integration/
  GuardModels.kt
  GuardProtocol.kt
  GuardController.kt
```

The files use package `com.example.adas.integration` and do not reference an
`Activity`, `Service`, Android hardware API, timer, socket, or transport. The
upstream app owns its lifecycle-aware coroutine scope and calls
`publishHeartbeat()` from its existing periodic transport task. Feed each board
`guard_status` frame to `receiveGuardStatus()` and collect `status` as a
`StateFlow<GuardStatus>` for the app's warning UI.

Add the serialization and coroutines dependencies already selected by the
upstream app. For a Kotlin DSL module, the required capabilities are
equivalent to:

```kotlin
plugins {
    kotlin("plugin.serialization")
}

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:<version>")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:<version>")
}
```

## C++ placement and Renesas adaptation

Compile `GuardEvaluator.cpp` into the board-side or host-side target and
include `GuardEvaluator.h`. Translate the exact Renesas SDK readings into
`GuardInput`, including the latest heartbeat timestamp and any sensor-fault
codes. Call `evaluate(input, now_ms, previous_state)` once per synchronized
sample and serialize or transport the returned `GuardStatus`.

The included `LocalLedBuzzerOutput` logs changes to `stdout`. On the Renesas
target, replace it with an adapter mapping:

* `setLed(LedColor)` to the board's GPIO, RGB LED, or vehicle HMI driver;
* `setBuzzer(bool)` to the board's buzzer or audio-alert driver.

The exact Renesas SDK integration remains board-specific: camera/ISP capture,
neural-network inference, SDK event types, clock/timestamp source, transport,
GPIO pin assignments, watchdog policy, sensor-fault taxonomy, and production
actuator behavior. The reusable evaluator has no Renesas SDK headers.

The C++ demo can be checked with:

```bash
g++ -std=c++17 -Wall -Wextra -Wpedantic GuardEvaluator.cpp main.cpp -o guard_demo
./guard_demo
```

The demo is an integration smoke test, not evidence that a specific Renesas
board SDK or Android transport is configured.

## Scripted scenario simulator

From this directory's parent, run the standard-library-only demo:

```bash
PYTHONPATH=renesas-adas-guard python3 -m core.scenario_runner --scenario renesas-adas-guard/scenarios/demo.json
```

Use `--json` to emit one protocol-compatible `guard_status` frame per step.
A custom JSON file may contain either a `{"steps": [...]}` object or a bare
step array. Each step requires `now_s`; set `heartbeat_at_s` to `null` to
exercise the missing-heartbeat path.
