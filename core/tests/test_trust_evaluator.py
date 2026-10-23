import unittest

from core import Heartbeat, SensorSnapshot, TrustEvaluator, TrustReason, TrustState


class TrustEvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = TrustEvaluator()
        self.heartbeat = Heartbeat(observed_at_s=10.0)

    def snapshot(self, **overrides):
        values = {
            "ambient_temp_c": 25.0,
            "relative_humidity_pct": 40.0,
            "mount_tilt_deg": 1.0,
            "vibration_rms_g": 0.2,
        }
        values.update(overrides)
        return SensorSnapshot(**values)

    def test_healthy_snapshot_is_trusted(self):
        decision = self.evaluator.evaluate(self.snapshot(), self.heartbeat, now_s=10.5)

        self.assertEqual(TrustState.TRUSTED, decision.state)
        self.assertEqual(100, decision.score)
        self.assertEqual((), decision.reasons)
        self.assertAlmostEqual(0.5, decision.heartbeat_age_s)

    def test_heartbeat_loss_is_untrusted_and_has_precedence(self):
        decision = self.evaluator.evaluate(
            self.snapshot(ambient_temp_c=90.0, mount_tilt_deg=9.0),
            self.heartbeat,
            now_s=11.01,
        )

        self.assertEqual(TrustState.UNTRUSTED, decision.state)
        self.assertEqual(0, decision.score)
        self.assertEqual(
            (TrustReason.HEARTBEAT_EXPIRED, TrustReason.THERMAL_WARNING, TrustReason.MOUNT_TILT),
            decision.reasons,
        )

    def test_thermal_warning_degrades_trust(self):
        decision = self.evaluator.evaluate(
            self.snapshot(ambient_temp_c=80.0), self.heartbeat, now_s=10.1
        )

        self.assertEqual(TrustState.DEGRADED, decision.state)
        self.assertEqual(80, decision.score)
        self.assertEqual((TrustReason.THERMAL_WARNING,), decision.reasons)

    def test_dew_point_margin_detects_fog_risk(self):
        decision = self.evaluator.evaluate(
            self.snapshot(ambient_temp_c=20.0, relative_humidity_pct=95.0),
            self.heartbeat,
            now_s=10.1,
        )

        self.assertEqual(TrustState.DEGRADED, decision.state)
        self.assertEqual(75, decision.score)
        self.assertEqual((TrustReason.FOG_RISK,), decision.reasons)
        self.assertLess(decision.dew_point_margin_c, 2.0)

    def test_mount_tilt_degrades_trust(self):
        decision = self.evaluator.evaluate(
            self.snapshot(mount_tilt_deg=-5.1), self.heartbeat, now_s=10.1
        )

        self.assertEqual(TrustState.DEGRADED, decision.state)
        self.assertEqual((TrustReason.MOUNT_TILT,), decision.reasons)

    def test_vibration_degrades_trust(self):
        decision = self.evaluator.evaluate(
            self.snapshot(vibration_rms_g=0.81), self.heartbeat, now_s=10.1
        )

        self.assertEqual(TrustState.DEGRADED, decision.state)
        self.assertEqual((TrustReason.VIBRATION,), decision.reasons)

    def test_sensor_fault_is_untrusted(self):
        decision = self.evaluator.evaluate(
            self.snapshot(sensor_faults={"temperature"}),
            self.heartbeat,
            now_s=10.1,
        )

        self.assertEqual(TrustState.UNTRUSTED, decision.state)
        self.assertEqual(0, decision.score)
        self.assertEqual((TrustReason.SENSOR_FAULT,), decision.reasons)

    def test_degraded_state_requires_recovery_score_with_hysteresis(self):
        degraded = self.evaluator.evaluate(
            self.snapshot(ambient_temp_c=80.0, relative_humidity_pct=95.0),
            self.heartbeat,
            now_s=10.1,
        )
        still_degraded = self.evaluator.evaluate(
            self.snapshot(ambient_temp_c=80.0),
            self.heartbeat,
            now_s=10.2,
            previous_state=degraded.state,
        )
        recovered = self.evaluator.evaluate(
            self.snapshot(),
            self.heartbeat,
            now_s=10.3,
            previous_state=still_degraded.state,
        )

        self.assertEqual(55, degraded.score)
        self.assertEqual(TrustState.DEGRADED, degraded.state)
        self.assertEqual(TrustState.DEGRADED, still_degraded.state)
        self.assertEqual(TrustState.TRUSTED, recovered.state)


if __name__ == "__main__":
    unittest.main()
