import io
import json
import math
import unittest
from contextlib import redirect_stdout

from core import Heartbeat, SensorSnapshot, TrustEvaluator, TrustLimits, TrustReason, TrustState
from core.protocol import decision_to_json, heartbeat_to_json
from core.scenario_runner import DEMO_SCENARIO, run_scenario


class InputAndProtocolTests(unittest.TestCase):
    def healthy(self):
        return SensorSnapshot(25.0, 40.0, 1.0, 0.2)

    def test_sensor_snapshot_rejects_non_finite_and_out_of_range_values(self):
        with self.assertRaises(ValueError):
            SensorSnapshot(math.nan, 40.0, 1.0, 0.2)
        with self.assertRaises(ValueError):
            SensorSnapshot(25.0, 101.0, 1.0, 0.2)
        with self.assertRaises(ValueError):
            SensorSnapshot(25.0, 40.0, 1.0, -0.1)

    def test_boolean_and_magnus_domain_inputs_are_rejected_or_failed_safe(self):
        with self.assertRaises(ValueError):
            SensorSnapshot(True, 40.0, 1.0, 0.2)
        with self.assertRaises(ValueError):
            TrustLimits(thermal_penalty=1.5)

        decision = TrustEvaluator().evaluate(
            SensorSnapshot(-243.12, 40.0, 1.0, 0.2), Heartbeat(10.0), now_s=10.1
        )
        self.assertEqual(TrustState.UNTRUSTED, decision.state)
        self.assertEqual((TrustReason.SENSOR_FAULT,), decision.reasons)
        self.assertEqual(0.0, decision.dew_point_margin_c)

    def test_zero_humidity_keeps_protocol_telemetry_finite(self):
        decision = TrustEvaluator().evaluate(
            SensorSnapshot(25.0, 0.0, 1.0, 0.2), Heartbeat(10.0), now_s=10.1
        )
        payload = json.loads(decision_to_json(decision, sequence=1, timestamp_ms=10100))
        self.assertEqual(TrustState.TRUSTED, decision.state)
        self.assertTrue(math.isfinite(payload["dew_point_margin_c"]))
        self.assertGreater(payload["dew_point_margin_c"], 2.0)

    def test_missing_heartbeat_is_untrusted_with_finite_timeout_age(self):
        decision = TrustEvaluator().evaluate(self.healthy(), None, now_s=10.0)

        self.assertEqual(TrustState.UNTRUSTED, decision.state)
        self.assertEqual((TrustReason.HEARTBEAT_EXPIRED,), decision.reasons)
        self.assertEqual(1.0, decision.heartbeat_age_s)

    def test_protocol_serialization_has_wire_names_and_stable_reason_order(self):
        decision = TrustEvaluator().evaluate(
            self.healthy(), Heartbeat(10.0), now_s=11.1
        )
        status = json.loads(decision_to_json(decision, sequence=7, timestamp_ms=11100))

        self.assertEqual("1.0", status["protocol"])
        self.assertEqual("guard_status", status["type"])
        self.assertEqual(
            ["heartbeat_expired"], status["reasons"]
        )
        self.assertEqual({"led": "red", "buzzer": True}, status["outputs"])
        self.assertTrue(math.isfinite(status["heartbeat_age_s"]))

    def test_protocol_serialization_rejects_invalid_envelope(self):
        with self.assertRaises(ValueError):
            heartbeat_to_json(Heartbeat(1.0), sequence=-1, timestamp_ms=1000)
        with self.assertRaises(ValueError):
            heartbeat_to_json(Heartbeat(1.0), sequence=1, timestamp_ms=1000, source="")

    def test_demo_script_covers_all_requested_states(self):
        output = io.StringIO()
        with redirect_stdout(output):
            states = run_scenario(DEMO_SCENARIO)

        self.assertEqual(
            [
                TrustState.TRUSTED,
                TrustState.DEGRADED,
                TrustState.DEGRADED,
                TrustState.DEGRADED,
                TrustState.DEGRADED,
                TrustState.UNTRUSTED,
                TrustState.UNTRUSTED,
            ],
            states,
        )
        self.assertIn("heartbeat-loss", output.getvalue())

    def test_scenario_input_requires_steps_and_numeric_time(self):
        with self.assertRaises(ValueError):
            run_scenario({"steps": []})
        with self.assertRaises(ValueError):
            run_scenario({"steps": [{"now_s": "later"}]})


if __name__ == "__main__":
    unittest.main()
