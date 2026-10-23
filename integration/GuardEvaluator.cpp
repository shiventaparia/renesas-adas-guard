#include "GuardEvaluator.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>

namespace renesas::adas {
namespace {

constexpr double kDewPointA = 17.62;
constexpr double kDewPointB = 243.12;

bool finiteSnapshot(const GuardInput& input) {
    return std::isfinite(input.ambient_temp_c) &&
           std::isfinite(input.relative_humidity_pct) &&
           std::isfinite(input.mount_tilt_deg) &&
           std::isfinite(input.vibration_rms_g) &&
           input.ambient_temp_c > -kDewPointB &&
           input.relative_humidity_pct >= 0.0 &&
           input.relative_humidity_pct <= 100.0 &&
           input.vibration_rms_g >= 0.0;
}

double dewPointC(double temperature_c, double humidity_pct) {
    if (humidity_pct <= 0.0) {
        // Keep the protocol telemetry finite at the dry-air limit.
        return -273.15;
    }
    const double alpha = kDewPointA * temperature_c / (kDewPointB + temperature_c) +
                         std::log(humidity_pct / 100.0);
    return kDewPointB * alpha / (kDewPointA - alpha);
}

GuardOutputs outputsFor(GuardState state) {
    switch (state) {
    case GuardState::Trusted:
        return {LedColor::Green, false};
    case GuardState::Degraded:
        return {LedColor::Amber, false};
    case GuardState::Untrusted:
        return {LedColor::Red, true};
    }
    return {LedColor::Red, true};
}

bool contains(const std::vector<GuardReason>& reasons, GuardReason reason) {
    return std::find(reasons.begin(), reasons.end(), reason) != reasons.end();
}

}  // namespace

const char* toString(GuardState state) noexcept {
    switch (state) {
    case GuardState::Trusted: return "trusted";
    case GuardState::Degraded: return "degraded";
    case GuardState::Untrusted: return "untrusted";
    }
    return "untrusted";
}

const char* toString(GuardReason reason) noexcept {
    switch (reason) {
    case GuardReason::HeartbeatExpired: return "heartbeat_expired";
    case GuardReason::SensorFault: return "sensor_fault";
    case GuardReason::ThermalWarning: return "thermal_warning";
    case GuardReason::FogRisk: return "fog_risk";
    case GuardReason::MountTilt: return "mount_tilt";
    case GuardReason::Vibration: return "vibration";
    }
    return "sensor_fault";
}

const char* toString(LedColor color) noexcept {
    switch (color) {
    case LedColor::Green: return "green";
    case LedColor::Amber: return "amber";
    case LedColor::Red: return "red";
    }
    return "red";
}

std::string GuardStatus::toJson() const {
    std::ostringstream out;
    out << std::fixed << std::setprecision(3)
        << "{\"protocol\":\"1.0\",\"type\":\"guard_status\","
        << "\"sequence\":" << sequence << ","
        << "\"timestamp_ms\":" << timestamp_ms << ","
        << "\"state\":\"" << toString(state) << "\","
        << "\"score\":" << score << ",\"reasons\":[";
    for (std::size_t i = 0; i < reasons.size(); ++i) {
        if (i != 0) {
            out << ',';
        }
        out << "\"" << toString(reasons[i]) << "\"";
    }
    out << "],\"heartbeat_age_s\":" << heartbeat_age_s
        << ",\"dew_point_margin_c\":" << dew_point_margin_c
        << ",\"outputs\":{\"led\":\"" << toString(outputs.led)
        << "\",\"buzzer\":" << (outputs.buzzer ? "true" : "false") << '}';
    if (previous_state.has_value()) {
        out << ",\"previous_state\":\"" << toString(*previous_state) << "\"";
    }
    out << '}';
    return out.str();
}

void LocalLedBuzzerOutput::setLed(LedColor color) {
    if (color == led_) {
        return;
    }
    led_ = color;
    std::cout << "[local-output] LED=" << toString(led_) << '\n';
}

void LocalLedBuzzerOutput::setBuzzer(bool enabled) {
    if (enabled == buzzer_) {
        return;
    }
    buzzer_ = enabled;
    std::cout << "[local-output] buzzer=" << (buzzer_ ? "on" : "off") << '\n';
}

GuardEvaluator::GuardEvaluator(GuardOutputSink& output, GuardLimits limits)
    : output_(output), limits_(limits) {
    if (limits_.heartbeat_timeout_ms == 0 ||
        !std::isfinite(limits_.thermal_warning_c) ||
        !std::isfinite(limits_.dew_point_margin_warning_c) ||
        limits_.dew_point_margin_warning_c <= 0.0 ||
        !std::isfinite(limits_.max_mount_tilt_deg) ||
        limits_.max_mount_tilt_deg <= 0.0 ||
        !std::isfinite(limits_.max_vibration_rms_g) ||
        limits_.max_vibration_rms_g <= 0.0 ||
        limits_.thermal_penalty < 0 || limits_.fog_penalty < 0 ||
        limits_.tilt_penalty < 0 || limits_.vibration_penalty < 0 ||
        limits_.degraded_enter_score < 0 || limits_.degraded_enter_score > 100 ||
        limits_.degraded_recovery_score < 0 || limits_.degraded_recovery_score > 100 ||
        limits_.degraded_recovery_score < limits_.degraded_enter_score) {
        throw std::invalid_argument("invalid guard limits");
    }
}

GuardStatus GuardEvaluator::evaluate(
    const GuardInput& input,
    std::uint64_t now_ms,
    std::optional<GuardState> previous_state) {
    GuardStatus status;
    status.sequence = sequence_++;
    status.timestamp_ms = now_ms;
    status.previous_state = previous_state;

    const std::uint64_t age_ms =
        input.heartbeat_received && now_ms >= input.heartbeat_observed_at_ms
            ? now_ms - input.heartbeat_observed_at_ms
            : 0;
    status.heartbeat_age_s = input.heartbeat_received
        ? static_cast<double>(age_ms) / 1000.0
        : static_cast<double>(limits_.heartbeat_timeout_ms) / 1000.0;
    const bool heartbeat_expired =
        !input.heartbeat_received || status.heartbeat_age_s * 1000.0 > limits_.heartbeat_timeout_ms;

    const bool invalid_snapshot = !finiteSnapshot(input);
    const bool sensor_fault = invalid_snapshot || !input.sensor_faults.empty();
    if (!invalid_snapshot) {
        const double dew_point_c = dewPointC(input.ambient_temp_c, input.relative_humidity_pct);
        status.dew_point_margin_c = input.ambient_temp_c - dew_point_c;
    } else {
        // Keep the wire output finite while the sensor-fault reason carries the
        // critical failure. The Python evaluator uses the same fail-safe path.
        status.dew_point_margin_c = 0.0;
    }

    // This order matches TrustEvaluator._REASON_PRECEDENCE in the Python core.
    if (heartbeat_expired) {
        status.reasons.push_back(GuardReason::HeartbeatExpired);
    }
    if (sensor_fault) {
        status.reasons.push_back(GuardReason::SensorFault);
    }
    if (!invalid_snapshot && input.ambient_temp_c >= limits_.thermal_warning_c) {
        status.reasons.push_back(GuardReason::ThermalWarning);
    }
    if (!invalid_snapshot && status.dew_point_margin_c < limits_.dew_point_margin_warning_c) {
        status.reasons.push_back(GuardReason::FogRisk);
    }
    if (!invalid_snapshot && std::abs(input.mount_tilt_deg) > limits_.max_mount_tilt_deg) {
        status.reasons.push_back(GuardReason::MountTilt);
    }
    if (!invalid_snapshot && input.vibration_rms_g > limits_.max_vibration_rms_g) {
        status.reasons.push_back(GuardReason::Vibration);
    }

    const bool hard_failure = heartbeat_expired || sensor_fault;
    if (hard_failure) {
        status.score = 0;
    } else {
        int penalty = 0;
        if (contains(status.reasons, GuardReason::ThermalWarning)) {
            penalty += limits_.thermal_penalty;
        }
        if (contains(status.reasons, GuardReason::FogRisk)) {
            penalty += limits_.fog_penalty;
        }
        if (contains(status.reasons, GuardReason::MountTilt)) {
            penalty += limits_.tilt_penalty;
        }
        if (contains(status.reasons, GuardReason::Vibration)) {
            penalty += limits_.vibration_penalty;
        }
        status.score = std::max(0, 100 - penalty);
    }

    if (hard_failure) {
        status.state = GuardState::Untrusted;
    } else if (!status.reasons.empty() && status.score <= limits_.degraded_enter_score) {
        status.state = GuardState::Degraded;
    } else if (previous_state == GuardState::Degraded &&
               status.score < limits_.degraded_recovery_score) {
        status.state = GuardState::Degraded;
    } else {
        status.state = GuardState::Trusted;
    }

    status.outputs = outputsFor(status.state);
    output_.setLed(status.outputs.led);
    output_.setBuzzer(status.outputs.buzzer);
    return status;
}

}  // namespace renesas::adas
