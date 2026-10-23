"""Typed data models for the portable ADAS trust guard core."""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import FrozenSet, Optional, Tuple


class TrustState(Enum):
    """Overall trust state reported by the guard."""

    TRUSTED = "trusted"
    DEGRADED = "degraded"
    UNTRUSTED = "untrusted"


class TrustReason(Enum):
    """Stable, machine-readable reasons for a trust decision."""

    HEARTBEAT_EXPIRED = "heartbeat_expired"
    SENSOR_FAULT = "sensor_fault"
    THERMAL_WARNING = "thermal_warning"
    FOG_RISK = "fog_risk"
    MOUNT_TILT = "mount_tilt"
    VIBRATION = "vibration"


@dataclass(frozen=True)
class SensorSnapshot:
    """One synchronized set of environmental and mount sensor readings."""

    ambient_temp_c: float
    relative_humidity_pct: float
    mount_tilt_deg: float
    vibration_rms_g: float
    sensor_faults: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        values = (
            ("ambient_temp_c", self.ambient_temp_c),
            ("relative_humidity_pct", self.relative_humidity_pct),
            ("mount_tilt_deg", self.mount_tilt_deg),
            ("vibration_rms_g", self.vibration_rms_g),
        )
        for name, value in values:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("{} must be a finite number".format(name))
        if not 0.0 <= self.relative_humidity_pct <= 100.0:
            raise ValueError("relative_humidity_pct must be between 0 and 100")
        if self.vibration_rms_g < 0.0:
            raise ValueError("vibration_rms_g must be non-negative")
        if isinstance(self.sensor_faults, (str, bytes)):
            raise ValueError("sensor_faults must be an iterable of fault names")
        faults = frozenset(self.sensor_faults)
        if any(not isinstance(fault, str) or not fault for fault in faults):
            raise ValueError("sensor_faults must contain non-empty strings")
        object.__setattr__(self, "sensor_faults", faults)


@dataclass(frozen=True)
class Heartbeat:
    """Timestamp of the most recently received ADAS heartbeat."""

    observed_at_s: float

    def __post_init__(self) -> None:
        if isinstance(self.observed_at_s, bool) or not isinstance(self.observed_at_s, (int, float)) or not math.isfinite(self.observed_at_s):
            raise ValueError("observed_at_s must be a finite number")


@dataclass(frozen=True)
class TrustLimits:
    """Thresholds and penalties used by :class:`TrustEvaluator`."""

    heartbeat_timeout_s: float = 1.0
    thermal_warning_c: float = 80.0
    dew_point_margin_warning_c: float = 2.0
    max_mount_tilt_deg: float = 5.0
    max_vibration_rms_g: float = 0.8
    thermal_penalty: int = 20
    fog_penalty: int = 25
    tilt_penalty: int = 25
    vibration_penalty: int = 20
    degraded_enter_score: int = 80
    degraded_recovery_score: int = 90

    def __post_init__(self) -> None:
        positive = (
            ("heartbeat_timeout_s", self.heartbeat_timeout_s),
            ("dew_point_margin_warning_c", self.dew_point_margin_warning_c),
            ("max_mount_tilt_deg", self.max_mount_tilt_deg),
            ("max_vibration_rms_g", self.max_vibration_rms_g),
        )
        for name, value in positive:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0.0:
                raise ValueError("{} must be positive and finite".format(name))
        if isinstance(self.thermal_warning_c, bool) or not isinstance(self.thermal_warning_c, (int, float)) or not math.isfinite(self.thermal_warning_c):
            raise ValueError("thermal_warning_c must be a finite number")
        for name, value in (
            ("thermal_penalty", self.thermal_penalty),
            ("fog_penalty", self.fog_penalty),
            ("tilt_penalty", self.tilt_penalty),
            ("vibration_penalty", self.vibration_penalty),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("{} must be a non-negative integer".format(name))
        if isinstance(self.degraded_enter_score, bool) or not isinstance(self.degraded_enter_score, int) or not 0 <= self.degraded_enter_score <= 100:
            raise ValueError("degraded_enter_score must be an integer between 0 and 100")
        if isinstance(self.degraded_recovery_score, bool) or not isinstance(self.degraded_recovery_score, int) or not 0 <= self.degraded_recovery_score <= 100:
            raise ValueError("degraded_recovery_score must be an integer between 0 and 100")
        if self.degraded_recovery_score < self.degraded_enter_score:
            raise ValueError("degraded_recovery_score must not be below degraded_enter_score")


@dataclass(frozen=True)
class TrustDecision:
    """Complete deterministic output from a trust evaluation."""

    state: TrustState
    score: int
    reasons: Tuple[TrustReason, ...]
    heartbeat_age_s: float
    dew_point_margin_c: float
    previous_state: Optional[TrustState] = None
