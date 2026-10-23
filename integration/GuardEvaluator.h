#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace renesas::adas {

enum class GuardState { Trusted, Degraded, Untrusted };
enum class GuardReason {
    HeartbeatExpired,
    SensorFault,
    ThermalWarning,
    FogRisk,
    MountTilt,
    Vibration,
};
enum class LedColor { Green, Amber, Red };

struct GuardInput {
    double ambient_temp_c{25.0};
    double relative_humidity_pct{40.0};
    double mount_tilt_deg{0.0};
    double vibration_rms_g{0.0};
    bool heartbeat_received{false};
    std::uint64_t heartbeat_observed_at_ms{0};
    std::vector<std::string> sensor_faults;
};

struct GuardLimits {
    std::uint64_t heartbeat_timeout_ms{1000};
    double thermal_warning_c{80.0};
    double dew_point_margin_warning_c{2.0};
    double max_mount_tilt_deg{5.0};
    double max_vibration_rms_g{0.8};
    int thermal_penalty{20};
    int fog_penalty{25};
    int tilt_penalty{25};
    int vibration_penalty{20};
    int degraded_enter_score{80};
    int degraded_recovery_score{90};
};

struct GuardOutputs {
    LedColor led{LedColor::Red};
    bool buzzer{true};
};

struct GuardStatus {
    GuardState state{GuardState::Untrusted};
    int score{0};
    std::vector<GuardReason> reasons;
    double heartbeat_age_s{0.0};
    double dew_point_margin_c{0.0};
    std::optional<GuardState> previous_state;
    GuardOutputs outputs{};
    std::uint64_t sequence{0};
    std::uint64_t timestamp_ms{0};

    // Encodes the status fields used by the integration protocol. This is a
    // deliberately small encoder so the evaluator has no JSON dependency.
    std::string toJson() const;
};

/** Hardware boundary used by a board adapter or the host demo. */
class GuardOutputSink {
public:
    virtual ~GuardOutputSink() = default;
    virtual void setLed(LedColor color) = 0;
    virtual void setBuzzer(bool enabled) = 0;
};

/** Deterministic stdout implementation for local development and smoke tests. */
class LocalLedBuzzerOutput final : public GuardOutputSink {
public:
    void setLed(LedColor color) override;
    void setBuzzer(bool enabled) override;

private:
    LedColor led_{LedColor::Red};
    bool buzzer_{true};
};

class GuardEvaluator {
public:
    explicit GuardEvaluator(GuardOutputSink& output, GuardLimits limits = {});

    // Missing heartbeats use heartbeat_timeout_ms as a finite age marker while
    // heartbeat_expired remains the authoritative reason.
    GuardStatus evaluate(
        const GuardInput& input,
        std::uint64_t now_ms,
        std::optional<GuardState> previous_state = std::nullopt);
    std::uint64_t sequence() const noexcept { return sequence_; }

private:
    GuardOutputSink& output_;
    GuardLimits limits_;
    std::uint64_t sequence_{0};
};

const char* toString(GuardState state) noexcept;
const char* toString(GuardReason reason) noexcept;
const char* toString(LedColor color) noexcept;

}  // namespace renesas::adas
