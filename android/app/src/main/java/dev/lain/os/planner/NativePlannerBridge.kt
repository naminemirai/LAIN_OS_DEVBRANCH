package dev.lain.os.planner

import android.content.Context
import org.json.JSONObject
import org.json.JSONTokener
import java.util.concurrent.atomic.AtomicReference

/**
 * Small Python-facing boundary over the native bounded planner transport.
 * Raw credentials remain inside [NativePlannerTransport]/[SecretStore].
 */
internal class NativePlannerBridge(
    private val transport: NativePlannerTransport,
) {
    constructor(context: Context) : this(
        NativePlannerTransport(AndroidKeystoreSecretStore(context))
    )

    private val activeCall = AtomicReference<PlannerTransportCall?>(null)

    fun execute(bindingJson: String, requestBody: String): String {
        if (
            bindingJson.toByteArray(Charsets.UTF_8).size > MAX_BINDING_BYTES ||
            requestBody.toByteArray(Charsets.UTF_8).size > MAX_REQUEST_BYTES
        ) {
            return failure(NativePlannerTransport.ERROR_TRANSPORT_FAILED)
        }
        val binding = try {
            parseBinding(bindingJson)
        } catch (_: Exception) {
            return failure(NativePlannerTransport.ERROR_TRANSPORT_FAILED)
        }
        val call = transport.newCall(binding, requestBody)
        if (!activeCall.compareAndSet(null, call)) {
            return failure(NativePlannerTransport.ERROR_TRANSPORT_FAILED)
        }
        return try {
            when (val result = call.execute()) {
                is PlannerTransportResult.Success -> JSONObject()
                    .put("ok", true)
                    .put("body", result.body)
                    .toString()
                is PlannerTransportResult.Failure -> failure(result.code)
            }
        } finally {
            activeCall.compareAndSet(call, null)
        }
    }

    fun cancel() {
        activeCall.get()?.cancel()
    }

    private fun failure(code: String): String = JSONObject()
        .put("ok", false)
        .put("error", code)
        .toString()

    private fun parseBinding(payload: String): PlannerBinding {
        val tokener = JSONTokener(payload)
        val raw = tokener.nextValue()
        require(raw is JSONObject && tokener.nextClean() == '\u0000')
        require(raw.keys().asSequence().toSet() == BINDING_FIELDS)

        val credential = raw.get("credential_ref")
        return PlannerBinding(
            profileId = strictString(raw, "profile_id"),
            mode = strictString(raw, "mode"),
            protocol = strictString(raw, "protocol"),
            baseUrl = strictString(raw, "base_url"),
            model = strictString(raw, "model"),
            credentialRef = if (credential === JSONObject.NULL) null else credential as? String
                ?: throw IllegalArgumentException("invalid credential ref"),
            timeoutSeconds = strictNumber(raw, "timeout_seconds").toDouble(),
            maxResponseBytes = strictInt(raw, "max_response_bytes"),
            responseMode = strictString(raw, "response_mode"),
            allowInsecureLanHttp = raw.get("allow_insecure_lan_http") as? Boolean
                ?: throw IllegalArgumentException("invalid planner binding"),
        )
    }

    private fun strictString(raw: JSONObject, key: String): String =
        raw.get(key) as? String ?: throw IllegalArgumentException("invalid planner binding")

    private fun strictNumber(raw: JSONObject, key: String): Number =
        raw.get(key) as? Number ?: throw IllegalArgumentException("invalid planner binding")

    private fun strictInt(raw: JSONObject, key: String): Int {
        val value = strictNumber(raw, key).toDouble()
        require(
            value.isFinite() &&
                value % 1.0 == 0.0 &&
                value >= Int.MIN_VALUE.toDouble() &&
                value <= Int.MAX_VALUE.toDouble()
        )
        return value.toInt()
    }

    companion object {
        private const val MAX_BINDING_BYTES = 8 * 1024
        private const val MAX_REQUEST_BYTES = 1024 * 1024
        private val BINDING_FIELDS = setOf(
            "profile_id",
            "mode",
            "protocol",
            "base_url",
            "model",
            "credential_ref",
            "timeout_seconds",
            "max_response_bytes",
            "response_mode",
            "allow_insecure_lan_http",
        )
    }
}
