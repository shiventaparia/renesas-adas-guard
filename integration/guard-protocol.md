# Renesas ADAS guard protocol

**Protocol name:** `renesas-adas-guard`

**Current version:** `1.0`

This protocol is the JSON seam between the Android `com.example.adas`
application and the board-side ADAS trust evaluator. Messages are UTF-8 JSON
objects, one message per transport frame. Unknown fields may be ignored for
forward compatibility, but an unsupported `protocol` value must be rejected.

## Common fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `protocol` | string | yes | Protocol version, currently `"1.0"`. |
| `type` | string | yes | `"heartbeat"` or `"guard_status"`. |
| `sequence` | integer | yes | Monotonically increasing sender sequence number. |
| `timestamp_ms` | integer | yes | Sender timestamp in Unix milliseconds. |

## Heartbeat (`heartbeat`)

A heartbeat proves that the sender is alive and gives the evaluator a clock
sample. Heartbeats do not change guard state.

```json
{
  "protocol": "1.0",
  "type": "heartbeat",
  "sequence": 42,
  "timestamp_ms": 1761000000123,
  "source": "android-adas"
}
```

The evaluator marks a status `untrusted` with reason `heartbeat_expired` when
no heartbeat has been received or its age is greater than `1.0` second by
default. When no heartbeat has ever been received, `heartbeat_age_s` is the
configured timeout (`1.0` by default) so the wire field remains finite and
protocol-valid; the `heartbeat_expired` reason identifies the missing sample.

## Guard status (`guard_status`)

A board-side evaluator publishes the latest trust decision. Reason order is
stable and matches the Python core:

1. `heartbeat_expired`
2. `sensor_fault`
3. `thermal_warning`
4. `fog_risk`
5. `mount_tilt`
6. `vibration`

```json
{
  "protocol": "1.0",
  "type": "guard_status",
  "sequence": 43,
  "timestamp_ms": 1761000000456,
  "state": "degraded",
  "score": 75,
  "reasons": ["fog_risk"],
  "heartbeat_age_s": 0.2,
  "dew_point_margin_c": 1.4,
  "outputs": {
    "led": "amber",
    "buzzer": false
  },
  "previous_state": "trusted"
}
```

`state` is one of `trusted`, `degraded`, or `untrusted`. `score` is an integer
from `0` to `100`. `heartbeat_age_s` and `dew_point_margin_c` are finite numeric
telemetry fields. `reasons` contains zero or more stable reason codes. At the
0% relative-humidity limit, the dew-point calculation uses `-273.15 C` as a
finite dry-air clamp so the wire field remains valid and fog risk is inactive.
`outputs.led` is `green` for trusted, `amber` for degraded, and `red` for
untrusted. `outputs.buzzer` is true for untrusted and false otherwise.
`previous_state` is optional and records the state supplied for hysteresis.
For an `untrusted` status, `outputs.led` must be `red` and `outputs.buzzer`
must be `true`; for `degraded` it must be `amber`/`false`; for `trusted` it
must be `green`/`false`.

A healthy baseline is:

```json
{
  "protocol": "1.0",
  "type": "guard_status",
  "sequence": 44,
  "timestamp_ms": 1761000000789,
  "state": "trusted",
  "score": 100,
  "reasons": [],
  "heartbeat_age_s": 0.5,
  "dew_point_margin_c": 14.5,
  "outputs": {
    "led": "green",
    "buzzer": false
  }
}
```

## Deterministic evaluation

The reference thresholds and penalties are:

| Condition | Default threshold | Score penalty |
| --- | --- | ---: |
| Ambient thermal warning | `ambient_temp_c >= 80.0` | 20 |
| Fog risk | `dew_point_margin_c < 2.0` | 25 |
| Mount tilt | `abs(mount_tilt_deg) > 5.0` | 25 |
| Vibration | `vibration_rms_g > 0.8` | 20 |

The score starts at `100` and applies all active warning penalties. Heartbeat
expiry and any sensor fault are critical failures: they force score `0` and
state `untrusted`, while all active reason codes remain present in the stable
order above. Warning results enter `degraded` at score `80` or below. A prior
`degraded` state recovers only when score reaches `90`.

JSON parsing or validation failure must not be treated as `trusted`. This
scaffold does not define authentication, encryption, framing, retry, clock
synchronization, or a vehicle safety case.
