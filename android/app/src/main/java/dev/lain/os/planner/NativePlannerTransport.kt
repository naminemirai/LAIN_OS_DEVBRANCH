package dev.lain.os.planner

import org.json.JSONException
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.net.ConnectException
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.SocketTimeoutException
import java.net.URI
import java.net.URL
import java.net.UnknownHostException
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.util.concurrent.atomic.AtomicBoolean
import javax.net.ssl.SSLException
import kotlin.math.ceil

internal data class PlannerBinding(
    val profileId: String,
    val mode: String,
    val protocol: String,
    val baseUrl: String,
    val model: String,
    val credentialRef: String?,
    val timeoutSeconds: Double,
    val maxResponseBytes: Int,
    val responseMode: String,
    val allowInsecureLanHttp: Boolean,
) {
    init {
        require(profileId.isNotBlank())
        require(mode == "cloud" || mode == "local")
        require(protocol == "openai_compatible_v1")
        require(baseUrl.isNotBlank() && model.isNotBlank())
        require(credentialRef == null || credentialRef.isNotBlank())
        require(timeoutSeconds.isFinite() && timeoutSeconds > 0)
        require(maxResponseBytes > 0)
        require(responseMode == "json_schema" || responseMode == "json_object")
        require(mode != "cloud" || !allowInsecureLanHttp)
        validateEndpoint()
    }

    private fun validateEndpoint() {
        val uri = try { URI(baseUrl) } catch (exc: Exception) {
            throw IllegalArgumentException("invalid planner endpoint", exc)
        }
        val host = uri.host?.removePrefix("[")?.removeSuffix("]")
        require(
            !host.isNullOrBlank() &&
                uri.userInfo == null &&
                uri.query == null &&
                uri.fragment == null
        )
        when (uri.scheme?.lowercase()) {
            "https" -> Unit
            "http" -> require(
                mode == "local" &&
                    allowInsecureLanHttp &&
                    isAllowedPrivateLiteral(host)
            )
            else -> throw IllegalArgumentException("planner endpoint must use HTTP(S)")
        }
    }

    private fun isAllowedPrivateLiteral(host: String): Boolean {
        parseIpv4(host)?.let { octets ->
            return octets[0] == 127 ||
                octets[0] == 10 ||
                (octets[0] == 172 && octets[1] in 16..31) ||
                (octets[0] == 192 && octets[1] == 168)
        }
        if (!host.contains(':') || host.contains('%')) return false
        val address = try { InetAddress.getByName(host).address } catch (_: Exception) { return false }
        if (address.size != 16) return false
        val first = address[0].toInt() and 0xff
        val second = address[1].toInt() and 0xff
        val loopback = address.dropLast(1).all { it.toInt() == 0 } && address.last().toInt() == 1
        return loopback || first in 0xfc..0xfd || (first == 0xfe && second in 0x80..0xbf)
    }

    private fun parseIpv4(host: String): IntArray? {
        val parts = host.split('.')
        if (parts.size != 4) return null
        val values = IntArray(4)
        for ((index, part) in parts.withIndex()) {
            if (part.isEmpty() || !part.all(Char::isDigit) || (part.length > 1 && part[0] == '0')) {
                return null
            }
            val value = part.toIntOrNull() ?: return null
            if (value !in 0..255) return null
            values[index] = value
        }
        return values
    }
}

internal sealed interface PlannerTransportResult {
    data class Success(val body: String) : PlannerTransportResult
    data class Failure(val code: String) : PlannerTransportResult
}

internal class NativePlannerTransport(
    private val secretStore: SecretStore,
    private val connectionFactory: (URL) -> HttpURLConnection = {
        it.openConnection() as HttpURLConnection
    },
) {
    fun newCall(binding: PlannerBinding, requestBody: String) =
        PlannerTransportCall(binding, requestBody, secretStore, connectionFactory)

    companion object {
        const val ERROR_DNS_UNREACHABLE = "PLANNER_DNS_UNREACHABLE"
        const val ERROR_CONNECTION_REFUSED = "PLANNER_CONNECTION_REFUSED"
        const val ERROR_ENDPOINT_UNREACHABLE = "PLANNER_ENDPOINT_UNREACHABLE"
        const val ERROR_TLS = "PLANNER_TLS_FAILURE"
        const val ERROR_AUTH_REJECTED = "PLANNER_AUTH_REJECTED"
        const val ERROR_MODEL_NOT_FOUND = "PLANNER_MODEL_NOT_FOUND"
        const val ERROR_TIMEOUT = "PLANNER_TIMEOUT"
        const val ERROR_RATE_LIMITED = "PLANNER_RATE_LIMITED"
        const val ERROR_SERVER = "PLANNER_SERVER_ERROR"
        const val ERROR_CANCELLED = "PLANNER_CANCELLED"
        const val ERROR_RESPONSE_TOO_LARGE = "PLANNER_RESPONSE_TOO_LARGE"
        const val ERROR_RESPONSE_MALFORMED = "PLANNER_RESPONSE_MALFORMED"
        const val ERROR_RESPONSE_UNSUPPORTED = "PLANNER_RESPONSE_UNSUPPORTED"
        const val ERROR_HTTP_REJECTED = "PLANNER_HTTP_REJECTED"
        const val ERROR_CLEARTEXT_BLOCKED = "PLANNER_CLEARTEXT_BLOCKED"
        const val ERROR_TRANSPORT_FAILED = "PLANNER_TRANSPORT_FAILED"
    }
}

internal class PlannerTransportCall(
    private val binding: PlannerBinding,
    private val requestBody: String,
    private val secretStore: SecretStore,
    private val connectionFactory: (URL) -> HttpURLConnection,
) {
    private val started = AtomicBoolean(false)
    private val cancelled = AtomicBoolean(false)
    @Volatile private var activeConnection: HttpURLConnection? = null

    fun cancel() {
        cancelled.set(true)
        activeConnection?.disconnect()
    }

    fun execute(): PlannerTransportResult {
        if (!started.compareAndSet(false, true)) {
            return PlannerTransportResult.Failure(NativePlannerTransport.ERROR_TRANSPORT_FAILED)
        }
        if (cancelled.get()) return cancelled()

        var connection: HttpURLConnection? = null
        return try {
            val endpoint = URL(chatCompletionsUrl(binding.baseUrl))
            connection = connectionFactory(endpoint)
            activeConnection = connection
            if (cancelled.get()) return cancelled()

            configure(connection)
            connection.outputStream.use { it.write(requestBody.toByteArray(Charsets.UTF_8)) }
            if (cancelled.get()) return cancelled()

            val status = connection.responseCode
            if (cancelled.get()) return cancelled()
            statusFailure(status)?.let { return PlannerTransportResult.Failure(it) }

            val declared = connection.contentLengthLong
            if (declared > binding.maxResponseBytes) {
                return PlannerTransportResult.Failure(NativePlannerTransport.ERROR_RESPONSE_TOO_LARGE)
            }
            if (!isSupportedJsonType(connection.contentType)) {
                return PlannerTransportResult.Failure(NativePlannerTransport.ERROR_RESPONSE_UNSUPPORTED)
            }

            val bytes = readBounded(connection)
            if (cancelled.get()) return cancelled()
            val body = decodeUtf8(bytes)
                ?: return PlannerTransportResult.Failure(NativePlannerTransport.ERROR_RESPONSE_MALFORMED)
            try {
                JSONObject(body)
            } catch (_: JSONException) {
                return PlannerTransportResult.Failure(NativePlannerTransport.ERROR_RESPONSE_MALFORMED)
            }
            if (cancelled.get()) cancelled() else PlannerTransportResult.Success(body)
        } catch (_: ResponseTooLarge) {
            if (cancelled.get()) cancelled() else PlannerTransportResult.Failure(
                NativePlannerTransport.ERROR_RESPONSE_TOO_LARGE
            )
        } catch (exc: SecretStoreException) {
            if (cancelled.get()) cancelled() else PlannerTransportResult.Failure(exc.code)
        } catch (_: UnknownHostException) {
            if (cancelled.get()) cancelled() else PlannerTransportResult.Failure(
                NativePlannerTransport.ERROR_DNS_UNREACHABLE
            )
        } catch (_: ConnectException) {
            if (cancelled.get()) cancelled() else PlannerTransportResult.Failure(
                NativePlannerTransport.ERROR_CONNECTION_REFUSED
            )
        } catch (_: SSLException) {
            if (cancelled.get()) cancelled() else PlannerTransportResult.Failure(
                NativePlannerTransport.ERROR_TLS
            )
        } catch (_: SocketTimeoutException) {
            if (cancelled.get()) cancelled() else PlannerTransportResult.Failure(
                NativePlannerTransport.ERROR_TIMEOUT
            )
        } catch (exc: IOException) {
            if (cancelled.get()) cancelled()
            else if (exc.message.orEmpty().contains("cleartext", ignoreCase = true)) {
                PlannerTransportResult.Failure(NativePlannerTransport.ERROR_CLEARTEXT_BLOCKED)
            } else PlannerTransportResult.Failure(NativePlannerTransport.ERROR_ENDPOINT_UNREACHABLE)
        } catch (_: Exception) {
            if (cancelled.get()) cancelled() else PlannerTransportResult.Failure(
                NativePlannerTransport.ERROR_TRANSPORT_FAILED
            )
        } finally {
            activeConnection = null
            connection?.disconnect()
        }
    }

    private fun configure(connection: HttpURLConnection) {
        val timeoutMillis = ceil(binding.timeoutSeconds * 1000.0)
            .coerceAtMost(Int.MAX_VALUE.toDouble())
            .toInt()
            .coerceAtLeast(1)
        connection.requestMethod = "POST"
        connection.instanceFollowRedirects = false
        connection.doOutput = true
        connection.connectTimeout = timeoutMillis
        connection.readTimeout = timeoutMillis
        connection.setRequestProperty("Content-Type", "application/json")
        connection.setRequestProperty("Accept", "application/json")
        binding.credentialRef?.let { ref ->
            connection.setRequestProperty("Authorization", "Bearer ${secretStore.resolve(ref)}")
        }
    }

    private fun statusFailure(status: Int): String? = when {
        status in 200..299 -> null
        status == 401 || status == 403 -> NativePlannerTransport.ERROR_AUTH_REJECTED
        status == 404 -> NativePlannerTransport.ERROR_MODEL_NOT_FOUND
        status == 408 -> NativePlannerTransport.ERROR_TIMEOUT
        status == 429 -> NativePlannerTransport.ERROR_RATE_LIMITED
        status in 500..599 -> NativePlannerTransport.ERROR_SERVER
        status in 300..399 -> NativePlannerTransport.ERROR_RESPONSE_UNSUPPORTED
        else -> NativePlannerTransport.ERROR_HTTP_REJECTED
    }

    private fun readBounded(connection: HttpURLConnection): ByteArray {
        val output = ByteArrayOutputStream(minOf(binding.maxResponseBytes, 8192))
        val buffer = ByteArray(8192)
        connection.inputStream.use { input ->
            while (true) {
                if (cancelled.get()) throw IOException("cancelled")
                val read = input.read(buffer)
                if (read < 0) break
                if (output.size() + read > binding.maxResponseBytes) {
                    throw ResponseTooLarge()
                }
                output.write(buffer, 0, read)
            }
        }
        return output.toByteArray()
    }

    private fun decodeUtf8(bytes: ByteArray): String? = try {
        Charsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
            .decode(ByteBuffer.wrap(bytes))
            .toString()
    } catch (_: Exception) {
        null
    }

    private fun isSupportedJsonType(contentType: String?): Boolean {
        if (contentType == null) return true
        val mediaType = contentType.substringBefore(';').trim().lowercase()
        return mediaType == "application/json" || mediaType.endsWith("+json")
    }

    private fun cancelled() = PlannerTransportResult.Failure(NativePlannerTransport.ERROR_CANCELLED)

    private class ResponseTooLarge : IOException()

    private fun chatCompletionsUrl(baseUrl: String): String =
        if (baseUrl.trimEnd('/').endsWith("/chat/completions")) baseUrl.trimEnd('/')
        else baseUrl.trimEnd('/') + "/chat/completions"
}
