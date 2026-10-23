package com.example.adas.integration

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Version carried in every integration message. */
const val GUARD_PROTOCOL_VERSION: String = "1.0"

@Serializable
enum class GuardState {
    @SerialName("trusted") TRUSTED,
    @SerialName("degraded") DEGRADED,
    @SerialName("untrusted") UNTRUSTED,
}

/** Stable reason codes shared with the Python/C++ trust evaluators. */
@Serializable
enum class GuardReason {
    @SerialName("heartbeat_expired") HEARTBEAT_EXPIRED,
    @SerialName("sensor_fault") SENSOR_FAULT,
    @SerialName("thermal_warning") THERMAL_WARNING,
    @SerialName("fog_risk") FOG_RISK,
    @SerialName("mount_tilt") MOUNT_TILT,
    @SerialName("vibration") VIBRATION,
}

@Serializable
enum class GuardLed {
    @SerialName("green") GREEN,
    @SerialName("amber") AMBER,
    @SerialName("red") RED,
}

@Serializable
data class GuardOutputs(
    val led: GuardLed,
    val buzzer: Boolean,
)

@Serializable
data class GuardHeartbeat(
    val protocol: String = GUARD_PROTOCOL_VERSION,
    val type: String = "heartbeat",
    val sequence: Long,
    @SerialName("timestamp_ms") val timestampMs: Long,
    val source: String = "android-adas",
)

@Serializable
data class GuardStatus(
    val protocol: String = GUARD_PROTOCOL_VERSION,
    val type: String = "guard_status",
    val sequence: Long,
    @SerialName("timestamp_ms") val timestampMs: Long,
    val state: GuardState,
    val score: Int,
    val reasons: List<GuardReason> = emptyList(),
    @SerialName("heartbeat_age_s") val heartbeatAgeS: Double,
    @SerialName("dew_point_margin_c") val dewPointMarginC: Double,
    val outputs: GuardOutputs,
    @SerialName("previous_state") val previousState: GuardState? = null,
)

/** A parsed message without treating a heartbeat as a guard decision. */
sealed interface GuardMessage {
    val protocol: String
    val sequence: Long
    val timestampMs: Long

    data class Heartbeat(val value: GuardHeartbeat) : GuardMessage {
        override val protocol: String get() = value.protocol
        override val sequence: Long get() = value.sequence
        override val timestampMs: Long get() = value.timestampMs
    }

    data class Status(val value: GuardStatus) : GuardMessage {
        override val protocol: String get() = value.protocol
        override val sequence: Long get() = value.sequence
        override val timestampMs: Long get() = value.timestampMs
    }
}
