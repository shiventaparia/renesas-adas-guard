"""Deterministic trust evaluation for the Renesas ADAS guard."""

import math
from typing import Optional

from .models import (
    Heartbeat,
    SensorSnapshot,
    TrustDecision,
    TrustLimits,
    TrustReason,
    TrustState,
)


class TrustEvaluator:
    """Evaluate sensor and heartbeat inputs without external dependencies.

    The evaluator is intentionally stateless. Pass the previous decision's
    state to ``evaluate`` when carrying state across samples; this makes the
    hysteresis behavior explicit and reproducible in an embedded integration.
    A missing heartbeat is represented by ``None`` and uses the configured
    timeout as a finite wire-compatible age marker.
    """

    _DEW_POINT_A = 17.62
    _DEW_POINT_B = 243.12

    # Reasons are always emitted in this order, independent of input ordering.
    _REASON_PRECEDENCE = (
        TrustReason.HEARTBEAT_EXPIRED,
        TrustReason.SENSOR_FAULT,
        TrustReason.THERMAL_WARNING,
        TrustReason.FOG_RISK,
        TrustReason.MOUNT_TILT,
        TrustReason.VIBRATION,
    )

    def __init__(self, limits: Optional[TrustLimits] = None) -> None:
        self.limits = limits or TrustLimits()

    @classmethod
    def dew_point_c(cls, temperature_c: float, relative_humidity_pct: float) -> float:
        """Return dew point in Celsius using the Magnus approximation."""

        if temperature_c <= -cls._DEW_POINT_B:
            raise ValueError("temperature is outside the Magnus approximation domain")
        if relative_humidity_pct <= 0.0:
            # Keep the wire telemetry finite at the dry-air limit.
            return -273.15
        alpha = (
            cls._DEW_POINT_A * temperature_c / (cls._DEW_POINT_B + temperature_c)
            + math.log(relative_humidity_pct / 100.0)
        )
        return cls._DEW_POINT_B * alpha / (cls._DEW_POINT_A - alpha)

    def evaluate(
        self,
        snapshot: SensorSnapshot,
        heartbeat: Optional[Heartbeat],
        now_s: float,
        previous_state: Optional[TrustState] = None,
    ) -> TrustDecision:
        """Evaluate one sample and apply explicit state hysteresis."""

        if isinstance(now_s, bool) or not isinstance(now_s, (int, float)) or not math.isfinite(now_s):
            raise ValueError("now_s must be a finite number")

        heartbeat_age_s = (
            max(0.0, now_s - heartbeat.observed_at_s)
            if heartbeat is not None
            else self.limits.heartbeat_timeout_s
        )
        try:
            dew_point_c = self.dew_point_c(
                snapshot.ambient_temp_c, snapshot.relative_humidity_pct
            )
            dew_point_margin_c = snapshot.ambient_temp_c - dew_point_c
        except ValueError:
            dew_point_margin_c = 0.0

        active = set()
        if heartbeat is None or heartbeat_age_s > self.limits.heartbeat_timeout_s:
            active.add(TrustReason.HEARTBEAT_EXPIRED)
        if snapshot.sensor_faults or snapshot.ambient_temp_c <= -self._DEW_POINT_B:
            active.add(TrustReason.SENSOR_FAULT)
        if snapshot.ambient_temp_c >= self.limits.thermal_warning_c:
            active.add(TrustReason.THERMAL_WARNING)
        if snapshot.ambient_temp_c > -self._DEW_POINT_B and dew_point_margin_c < self.limits.dew_point_margin_warning_c:
            active.add(TrustReason.FOG_RISK)
        if abs(snapshot.mount_tilt_deg) > self.limits.max_mount_tilt_deg:
            active.add(TrustReason.MOUNT_TILT)
        if snapshot.vibration_rms_g > self.limits.max_vibration_rms_g:
            active.add(TrustReason.VIBRATION)

        reasons = tuple(reason for reason in self._REASON_PRECEDENCE if reason in active)
        score = 100
        if TrustReason.HEARTBEAT_EXPIRED in active or TrustReason.SENSOR_FAULT in active:
            score = 0
        else:
            penalties = {
                TrustReason.THERMAL_WARNING: self.limits.thermal_penalty,
                TrustReason.FOG_RISK: self.limits.fog_penalty,
                TrustReason.MOUNT_TILT: self.limits.tilt_penalty,
                TrustReason.VIBRATION: self.limits.vibration_penalty,
            }
            score = max(0, 100 - sum(penalties.get(reason, 0) for reason in reasons))

        hard_failure = any(
            reason in active
            for reason in (TrustReason.HEARTBEAT_EXPIRED, TrustReason.SENSOR_FAULT)
        )
        if hard_failure:
            state = TrustState.UNTRUSTED
        elif reasons and score <= self.limits.degraded_enter_score:
            state = TrustState.DEGRADED
        elif (
            previous_state == TrustState.DEGRADED
            and score < self.limits.degraded_recovery_score
        ):
            state = TrustState.DEGRADED
        else:
            state = TrustState.TRUSTED

        return TrustDecision(
            state=state,
            score=score,
            reasons=reasons,
            heartbeat_age_s=heartbeat_age_s,
            dew_point_margin_c=dew_point_margin_c,
            previous_state=previous_state,
        )
