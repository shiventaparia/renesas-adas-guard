"""Run scripted Renesas ADAS guard scenarios with only the Python stdlib."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .evaluator import TrustEvaluator
from .models import Heartbeat, SensorSnapshot, TrustState
from .protocol import decision_to_json


DEMO_SCENARIO: Dict[str, Any] = {
    "name": "guard-demo",
    "steps": [
        {"name": "normal", "now_s": 10.5, "heartbeat_at_s": 10.0},
        {"name": "hot", "now_s": 11.5, "heartbeat_at_s": 11.0, "ambient_temp_c": 80.0},
        {
            "name": "fog",
            "now_s": 12.5,
            "heartbeat_at_s": 12.0,
            "ambient_temp_c": 20.0,
            "relative_humidity_pct": 95.0,
        },
        {"name": "tilt", "now_s": 13.5, "heartbeat_at_s": 13.0, "mount_tilt_deg": 5.1},
        {"name": "vibration", "now_s": 14.5, "heartbeat_at_s": 14.0, "vibration_rms_g": 0.81},
        {
            "name": "sensor-fault",
            "now_s": 15.5,
            "heartbeat_at_s": 15.0,
            "sensor_faults": ["temperature"],
        },
        {"name": "heartbeat-loss", "now_s": 17.0, "heartbeat_at_s": None},
    ],
}

DEFAULTS = {
    "ambient_temp_c": 25.0,
    "relative_humidity_pct": 40.0,
    "mount_tilt_deg": 1.0,
    "vibration_rms_g": 0.2,
}


def _number(step: Dict[str, Any], name: str) -> float:
    value = step.get(name, DEFAULTS[name])
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("step field '{}' must be numeric".format(name))
    return float(value)


def _load_steps(document: Any) -> List[Dict[str, Any]]:
    steps = document.get("steps") if isinstance(document, dict) else document
    if not isinstance(steps, list) or not steps:
        raise ValueError("scenario must contain a non-empty 'steps' list")
    if any(not isinstance(step, dict) for step in steps):
        raise ValueError("each scenario step must be an object")
    return steps


def run_scenario(document: Any, json_output: bool = False) -> List[TrustState]:
    """Evaluate all steps and print either a readable report or JSON frames."""
    evaluator = TrustEvaluator()
    previous_state: Optional[TrustState] = None
    states: List[TrustState] = []
    for index, step in enumerate(_load_steps(document)):
        name = step.get("name", "step-{}".format(index + 1))
        if not isinstance(name, str) or not name:
            raise ValueError("step name must be a non-empty string")
        now_s = step.get("now_s")
        if isinstance(now_s, bool) or not isinstance(now_s, (int, float)):
            raise ValueError("step field 'now_s' must be numeric")
        heartbeat_at_s = step.get("heartbeat_at_s")
        if heartbeat_at_s is not None and (isinstance(heartbeat_at_s, bool) or not isinstance(heartbeat_at_s, (int, float))):
            raise ValueError("heartbeat_at_s must be numeric or null")
        heartbeat = None if heartbeat_at_s is None else Heartbeat(float(heartbeat_at_s))
        faults = step.get("sensor_faults", [])
        if not isinstance(faults, list) or any(not isinstance(item, str) or not item for item in faults):
            raise ValueError("sensor_faults must be a list of non-empty strings")
        snapshot = SensorSnapshot(
            ambient_temp_c=_number(step, "ambient_temp_c"),
            relative_humidity_pct=_number(step, "relative_humidity_pct"),
            mount_tilt_deg=_number(step, "mount_tilt_deg"),
            vibration_rms_g=_number(step, "vibration_rms_g"),
            sensor_faults=frozenset(faults),
        )
        decision = evaluator.evaluate(snapshot, heartbeat, float(now_s), previous_state)
        states.append(decision.state)
        if json_output:
            print(decision_to_json(decision, sequence=index, timestamp_ms=int(float(now_s) * 1000)))
        else:
            reasons = ",".join(reason.value for reason in decision.reasons) or "none"
            print("{:<16} {:<10} score={:>3} reasons={} heartbeat_age_s={:.3f}".format(
                name, decision.state.value, decision.score, reasons, decision.heartbeat_age_s
            ))
        previous_state = decision.state
    return states


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--demo", action="store_true", help="run the built-in seven-state demo")
    source.add_argument("--scenario", type=Path, help="read a JSON scenario file")
    parser.add_argument("--json", action="store_true", help="emit protocol guard_status JSON lines")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.scenario:
            document = json.loads(args.scenario.read_text(encoding="utf-8"))
        else:
            document = DEMO_SCENARIO
        run_scenario(document, json_output=args.json)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("scenario error: {}".format(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
