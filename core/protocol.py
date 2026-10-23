"""Dependency-free JSON helpers for the Renesas ADAS guard protocol."""

import json
import math
from typing import Any, Dict

from .models import Heartbeat, TrustDecision, TrustState


PROTOCOL_VERSION = "1.0"


def _require_non_negative_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("{} must be a non-negative integer".format(name))


def heartbeat_to_dict(heartbeat: Heartbeat, sequence: int, timestamp_ms: int, source: str = "android-adas") -> Dict[str, Any]:
    """Build a protocol heartbeat object after validating its envelope."""
    _require_non_negative_integer("sequence", sequence)
    _require_non_negative_integer("timestamp_ms", timestamp_ms)
    if not source:
        raise ValueError("source must not be empty")
    return {
        "protocol": PROTOCOL_VERSION,
        "type": "heartbeat",
        "sequence": sequence,
        "timestamp_ms": timestamp_ms,
        "source": source,
    }


def heartbeat_to_json(heartbeat: Heartbeat, sequence: int, timestamp_ms: int, source: str = "android-adas") -> str:
    """Serialize a heartbeat as one compact UTF-8 JSON frame."""
    return json.dumps(heartbeat_to_dict(heartbeat, sequence, timestamp_ms, source), separators=(",", ":"), allow_nan=False)


def decision_to_dict(decision: TrustDecision, sequence: int, timestamp_ms: int) -> Dict[str, Any]:
    """Build a protocol guard_status object from a core decision."""
    _require_non_negative_integer("sequence", sequence)
    _require_non_negative_integer("timestamp_ms", timestamp_ms)
    if not 0 <= decision.score <= 100:
        raise ValueError("decision score must be between 0 and 100")
    if not math.isfinite(decision.heartbeat_age_s) or decision.heartbeat_age_s < 0:
        raise ValueError("heartbeat age must be finite and non-negative")
    if not math.isfinite(decision.dew_point_margin_c):
        raise ValueError("dew-point margin must be finite")
    outputs = {
        TrustState.TRUSTED: {"led": "green", "buzzer": False},
        TrustState.DEGRADED: {"led": "amber", "buzzer": False},
        TrustState.UNTRUSTED: {"led": "red", "buzzer": True},
    }[decision.state]
    message: Dict[str, Any] = {
        "protocol": PROTOCOL_VERSION,
        "type": "guard_status",
        "sequence": sequence,
        "timestamp_ms": timestamp_ms,
        "state": decision.state.value,
        "score": decision.score,
        "reasons": [reason.value for reason in decision.reasons],
        "heartbeat_age_s": decision.heartbeat_age_s,
        "dew_point_margin_c": decision.dew_point_margin_c,
        "outputs": outputs,
    }
    if decision.previous_state is not None:
        message["previous_state"] = decision.previous_state.value
    return message


def decision_to_json(decision: TrustDecision, sequence: int, timestamp_ms: int) -> str:
    """Serialize a guard decision as one compact protocol JSON frame."""
    return json.dumps(decision_to_dict(decision, sequence, timestamp_ms), separators=(",", ":"), allow_nan=False)
