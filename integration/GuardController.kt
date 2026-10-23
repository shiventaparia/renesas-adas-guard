package com.example.adas.integration

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Transport- and lifecycle-neutral controller for an Android ADAS component.
 * The app owns scheduling, coroutine scope, transport, and UI collection.
 */
class GuardController(
    private val send: (String) -> Unit,
    private val nowMs: () -> Long = { System.currentTimeMillis() },
    source: String = "android-adas",
) {
    private val sourceName = source
    private var nextSequence = 0L
    private var lastAcceptedSequence = -1L

    private val _status = MutableStateFlow(initialStatus(timestampMs = nowMs()))
    val status: StateFlow<GuardStatus> = _status.asStateFlow()

    private val _lastHeartbeat = MutableStateFlow<GuardHeartbeat?>(null)
    val lastHeartbeat: StateFlow<GuardHeartbeat?> = _lastHeartbeat.asStateFlow()

    /** Encode and send a heartbeat. Call this from the app's existing scheduler. */
    fun publishHeartbeat(): GuardHeartbeat {
        val heartbeat = GuardHeartbeat(
            sequence = nextSequence++,
            timestampMs = nowMs(),
            source = sourceName,
        )
        _lastHeartbeat.value = heartbeat
        send(GuardProtocol.encodeHeartbeat(heartbeat))
        return heartbeat
    }

    /** Decode and accept a board-produced guard_status message. */
    fun receiveGuardStatus(payload: String): GuardStatus {
        val message = GuardProtocol.decodeStatus(payload)
        require(message.sequence > lastAcceptedSequence) {
            "Stale guard status sequence ${message.sequence}; last is $lastAcceptedSequence"
        }
        lastAcceptedSequence = message.sequence
        _status.value = message
        return message
    }

    /** Compatibility name for transport callbacks that deliver one payload. */
    fun receive(payload: String): GuardStatus = receiveGuardStatus(payload)

    companion object {
        fun outputsFor(state: GuardState): GuardOutputs = when (state) {
            GuardState.TRUSTED -> GuardOutputs(GuardLed.GREEN, buzzer = false)
            GuardState.DEGRADED -> GuardOutputs(GuardLed.AMBER, buzzer = false)
            GuardState.UNTRUSTED -> GuardOutputs(GuardLed.RED, buzzer = true)
        }

        fun initialStatus(timestampMs: Long = System.currentTimeMillis()): GuardStatus = GuardStatus(
            sequence = 0L,
            timestampMs = timestampMs,
            state = GuardState.TRUSTED,
            score = 100,
            reasons = emptyList(),
            heartbeatAgeS = 0.0,
            dewPointMarginC = 0.0,
            outputs = outputsFor(GuardState.TRUSTED),
        )
    }
}
