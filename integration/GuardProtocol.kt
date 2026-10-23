package com.example.adas.integration

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

/** JSON codec for the versioned Renesas ADAS trust-guard messages. */
object GuardProtocol {
    const val VERSION: String = GUARD_PROTOCOL_VERSION

    val json: Json = Json {
        encodeDefaults = true
        explicitNulls = false
        ignoreUnknownKeys = true
    }

    fun encodeHeartbeat(message: GuardHeartbeat): String {
        validateEnvelope(message.protocol, message.type, message.sequence, message.timestampMs, "heartbeat")
        return json.encodeToString(GuardHeartbeat.serializer(), message)
    }

    fun encodeStatus(message: GuardStatus): String {
        validateStatus(message)
        return json.encodeToString(GuardStatus.serializer(), message)
    }

    fun decodeHeartbeat(payload: String): GuardHeartbeat {
        val message = json.decodeFromString(GuardHeartbeat.serializer(), payload)
        validateEnvelope(message.protocol, message.type, message.sequence, message.timestampMs, "heartbeat")
        return message
    }

    fun decodeStatus(payload: String): GuardStatus {
        val message = json.decodeFromString(GuardStatus.serializer(), payload)
        validateStatus(message)
        return message
    }

    /** Decode either wire message when a transport needs to inspect its type. */
    fun decode(payload: String): GuardMessage {
        val type = json.parseToJsonElement(payload).jsonObject["type"]?.jsonPrimitive?.content
            ?: error("Message type is required")
        return when (type) {
            "heartbeat" -> GuardMessage.Heartbeat(decodeHeartbeat(payload))
            "guard_status" -> GuardMessage.Status(decodeStatus(payload))
            else -> error("Unsupported message type: $type")
        }
    }

    private fun validateStatus(message: GuardStatus) {
        validateEnvelope(message.protocol, message.type, message.sequence, message.timestampMs, "guard_status")
        require(message.score in 0..100) { "Guard score must be between 0 and 100" }
        require(message.heartbeatAgeS.isFinite() && message.heartbeatAgeS >= 0.0) {
            "Heartbeat age must be finite and non-negative"
        }
        require(message.dewPointMarginC.isFinite()) {
            "Dew-point margin must be finite"
        }
        val expectedOutputs = when (message.state) {
            GuardState.TRUSTED -> GuardOutputs(GuardLed.GREEN, buzzer = false)
            GuardState.DEGRADED -> GuardOutputs(GuardLed.AMBER, buzzer = false)
            GuardState.UNTRUSTED -> GuardOutputs(GuardLed.RED, buzzer = true)
        }
        require(message.outputs == expectedOutputs) {
            "Outputs do not match guard state"
        }
        require(message.reasons == message.reasons.distinct()) {
            "Guard reasons must not repeat"
        }
        val reasonOrder = listOf(
            GuardReason.HEARTBEAT_EXPIRED,
            GuardReason.SENSOR_FAULT,
            GuardReason.THERMAL_WARNING,
            GuardReason.FOG_RISK,
            GuardReason.MOUNT_TILT,
            GuardReason.VIBRATION,
        )
        require(message.reasons == message.reasons.sortedBy { reasonOrder.indexOf(it) }) {
            "Guard reasons are out of precedence order"
        }
    }

    private fun validateEnvelope(protocol: String, type: String, sequence: Long, timestampMs: Long, expectedType: String) {
        requireValidVersion(protocol)
        require(type == expectedType) { "Message type must be $expectedType" }
        require(sequence >= 0L) { "Sequence must be non-negative" }
        require(timestampMs >= 0L) { "Timestamp must be non-negative" }
    }

    private fun requireValidVersion(version: String) {
        require(version == VERSION) {
            "Unsupported guard protocol version: $version (expected $VERSION)"
        }
    }
}
