#include "GuardEvaluator.h"

#include <iostream>

namespace {

renesas::adas::GuardInput healthyInput() {
    renesas::adas::GuardInput input;
    input.ambient_temp_c = 25.0;
    input.relative_humidity_pct = 40.0;
    input.mount_tilt_deg = 1.0;
    input.vibration_rms_g = 0.2;
    input.heartbeat_received = true;
    input.heartbeat_observed_at_ms = 10000;
    return input;
}

void printStatus(const char* label, const renesas::adas::GuardStatus& status) {
    std::cout << label << ": " << status.toJson() << '\n';
}

}  // namespace

int main() {
    renesas::adas::LocalLedBuzzerOutput output;
    renesas::adas::GuardEvaluator evaluator(output);

    const auto healthy = evaluator.evaluate(healthyInput(), 10500);
    printStatus("healthy", healthy);

    auto thermal = healthyInput();
    thermal.ambient_temp_c = 80.0;
    const auto thermalStatus = evaluator.evaluate(thermal, 10600, healthy.state);
    printStatus("thermal-warning", thermalStatus);

    auto fog = healthyInput();
    fog.ambient_temp_c = 20.0;
    fog.relative_humidity_pct = 95.0;
    const auto fogStatus = evaluator.evaluate(fog, 10700, thermalStatus.state);
    printStatus("fog-warning", fogStatus);

    auto tilt = healthyInput();
    tilt.mount_tilt_deg = -5.1;
    const auto tiltStatus = evaluator.evaluate(tilt, 10800, fogStatus.state);
    printStatus("tilt-warning", tiltStatus);

    auto expired = healthyInput();
    expired.heartbeat_observed_at_ms = 10000;
    const auto expiredStatus = evaluator.evaluate(expired, 12001, tiltStatus.state);
    printStatus("heartbeat-expired", expiredStatus);

    renesas::adas::GuardInput missingHeartbeat;
    missingHeartbeat.heartbeat_received = false;
    const auto missingHeartbeatStatus = evaluator.evaluate(missingHeartbeat, 13000);
    printStatus("heartbeat-missing", missingHeartbeatStatus);

    auto sensorFault = healthyInput();
    sensorFault.ambient_temp_c = 90.0;
    sensorFault.mount_tilt_deg = 9.0;
    sensorFault.sensor_faults.push_back("temperature");
    const auto sensorFaultStatus = evaluator.evaluate(sensorFault, 11000);
    printStatus("sensor-fault-precedence", sensorFaultStatus);

    return (healthy.state == renesas::adas::GuardState::Trusted &&
            thermalStatus.state == renesas::adas::GuardState::Degraded &&
            fogStatus.state == renesas::adas::GuardState::Degraded &&
            tiltStatus.state == renesas::adas::GuardState::Degraded &&
            expiredStatus.state == renesas::adas::GuardState::Untrusted &&
            expiredStatus.outputs.led == renesas::adas::LedColor::Red &&
            expiredStatus.outputs.buzzer &&
            missingHeartbeatStatus.state == renesas::adas::GuardState::Untrusted &&
            missingHeartbeatStatus.heartbeat_age_s == 1.0 &&
            sensorFaultStatus.state == renesas::adas::GuardState::Untrusted &&
            sensorFaultStatus.score == 0 &&
            sensorFaultStatus.reasons.size() == 3 &&
            sensorFaultStatus.reasons[0] == renesas::adas::GuardReason::SensorFault &&
            sensorFaultStatus.reasons[1] == renesas::adas::GuardReason::ThermalWarning &&
            sensorFaultStatus.reasons[2] == renesas::adas::GuardReason::MountTilt)
               ? 0
               : 1;
}
