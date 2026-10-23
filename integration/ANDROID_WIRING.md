# Android wiring guide

The upstream ADAS Android app is not vendored into this repository. This guide
shows the smallest safe integration once the app checkout and the exact BLE
transport are available.

## 1. Copy the domain files

Copy these files into the Android module:

```text
android_app/app/src/main/java/com/example/adas/integration/
  GuardModels.kt
  GuardProtocol.kt
  GuardController.kt
```

The app already needs Kotlin serialization and coroutines. Use the versions
already selected by the app's version catalog; do not add a second version.

## 2. Add a transport boundary

Keep Bluetooth code outside the trust logic:

```kotlin
interface GuardTransport {
    fun send(frame: String)
    fun setReceiver(receiver: (String) -> Unit)
}
```

The transport adapter should perform BLE framing, connection recovery, and
permission handling. `GuardController` should only see complete JSON frames.

## 3. Send a heartbeat at 250 ms

Use the app's existing lifecycle scope. The physical watchdog is on the board;
the Android scheduler is only responsible for attempting regular heartbeats.

```kotlin
val guard = GuardController(send = transport::send)

val heartbeatJob = lifecycleScope.launch {
    while (isActive) {
        guard.publishHeartbeat()
        delay(250)
    }
}

transport.setReceiver { payload ->
    guard.receiveGuardStatus(payload)
}
```

Cancel the job when the camera screen or service stops. Do not turn a missing
Android callback into a fake healthy status.

## 4. Expose trust state in the HUD

Collect `guard.status` using the existing lifecycle-aware Compose collection.
The UI should show:

| State | UI | Detector policy |
|---|---|---|
| `TRUSTED` | Green `AI TRUSTED` badge | Normal mode |
| `DEGRADED` | Amber reason and score | Explicit lighter mode or reduced-rate inference |
| `UNTRUSTED` | Red `AI NOT TRUSTED` warning | Stop claiming that detections are reliable |

The fallback policy must be deliberately implemented by the app team. This
scaffold does not silently change inference behavior because the correct action
depends on the detector and phone hardware.

## 5. Handle transport failure

If the BLE link disconnects, keep the last received status visible with a
staleness indicator. Never replace it with `TRUSTED`. The board must transition
to `UNTRUSTED` when its heartbeat watchdog expires, even if Android is no longer
able to update the screen.

## 6. Verify the integration

Before hardware testing:

1. Feed a valid `trusted` frame and verify the green badge.
2. Feed a valid `degraded` frame for each reason code.
3. Feed `untrusted` and verify the red warning persists.
4. Feed duplicate and out-of-order board sequences and verify rejection.
5. Disconnect BLE and confirm Android does not show a false healthy state.
6. Stop the heartbeat task and measure board alarm latency independently.
