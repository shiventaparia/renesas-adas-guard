"""Portable, dependency-free Renesas ADAS guard core."""

from .evaluator import TrustEvaluator
from .protocol import decision_to_json, heartbeat_to_json
from .models import (
    Heartbeat,
    SensorSnapshot,
    TrustDecision,
    TrustLimits,
    TrustReason,
    TrustState,
)

__all__ = [
    "Heartbeat",
    "SensorSnapshot",
    "TrustDecision",
    "TrustEvaluator",
    "TrustLimits",
    "TrustReason",
    "TrustState",
    "decision_to_json",
    "heartbeat_to_json",
]
