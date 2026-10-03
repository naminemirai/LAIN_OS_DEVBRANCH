package dev.lain.os.planner

import org.json.JSONException
import org.json.JSONObject
import org.json.JSONTokener
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.net.ConnectException
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URI
import java.net.URL
import java.net.UnknownHostException
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.util.concurrent.CancellationException
import java.util.concurrent.ExecutionException
import java.util.concurrent.FutureTask
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
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
        require(
            !uri.host.isNullOrBlank() &&
                uri.userInfo == null &&
                uri.query == null &&
                uri.fragment == null
        )
        require(uri.scheme?.lowercase() == "https") {
            "Android planner transport requires HTTPS"
        }
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

private enum class PlannerCallTerminalState {
    ACTIVE,
    CANCELLED,
    TIMED_OUT,
    FINISHED,
}

internal class PlannerTransportCall(
    private val binding: PlannerBinding,
    private val requestBody: String,
    private val secretStore: SecretStore,
    private val connectionFactory: (URL) -> HttpURLConnection,
) {
    private val started = AtomicBoolean(false)
    private val terminalState = AtomicReference(PlannerCallTerminalState.ACTIVE)
    @Volatile private var activeConnection: HttpURLConnection? = null
    @Volatile private var activeTask: FutureTask<PlannerTransportResult>? = null

    fun cancel() {
        if (terminalState.compareAndSet(
                PlannerCallTerminalState.ACTIVE,
                PlannerCallTerminalState.CANCELLED,
            )
        ) {
            activeConnection?.disconnect()
            activeTask?.cancel(true)
        }
    }

    fun execute(): PlannerTransportResult {
        if (!started.compareAndSet(false, true)) {
            return PlannerTransportResult.Failure(NativePlannerTransport.ERROR_TRANSPORT_FAILED)
        }
        terminalFailureOrNull()?.let { return it }

        val task = FutureTask { executeBlocking() }
        activeTask = task
        terminalFailureOrNull()?.let {
            task.cancel(true)
            activeTask = null
            return it
        }

        Thread(task, "lain-planner-transport").apply {
            isDaemon = true
            start()
        }

        return try {
            task.get(timeoutMillis().toLong(), TimeUnit.MILLISECONDS)
        } catch (_: TimeoutException) {
            if (terminalState.compareAndSet(
                    PlannerCallTerminalState.ACTIVE,
                    PlannerCallTerminalState.TIMED_OUT,
                )
            ) {
                activeConnection?.disconnect()
                task.cancel(true)
                timeout()
            } else if (terminalState.get() == PlannerCallTerminalState.FINISHED) {
                try {
                    task.get()
                } catch (_: Exception) {
                    terminalResult(NativePlannerTransport.ERROR_TIMEOUT)
                }
            } else {
                terminalResult(NativePlannerTransport.ERROR_TIMEOUT)
            }
        } catch (_: CancellationException) {
            terminalResult(NativePlannerTransport.ERROR_TRANSPORT_FAILED)
        } catch (_: InterruptedException) {
            Thread.currentThread().interrupt()
            if (terminalState.compareAndSet(
                    PlannerCallTerminalState.ACTIVE,
                    PlannerCallTerminalState.CANCELLED,
                )
            ) {
                activeConnection?.disconnect()
                task.cancel(true)
            }
            cancelled()
        } catch (_: ExecutionException) {
            finishFailure(NativePlannerTransport.ERROR_TRANSPORT_FAILED)
        } finally {
            activeTask = null
        }
    }

    private fun executeBlocking(): PlannerTransportResult {
        terminalFailureOrNull()?.let { return it }

        var connection: HttpURLConnection? = null
        return try {
            val endpoint = URL(chatCompletionsUrl(binding.baseUrl))
            connection = connectionFactory(endpoint)
            activeConnection = connection
            terminalFailureOrNull()?.let { return it }

            configure(connection)
            connection.outputStream.use { it.write(requestBody.toByteArray(Charsets.UTF_8)) }
            terminalFailureOrNull()?.let { return it }

            val status = connection.responseCode
            terminalFailureOrNull()?.let { return it }
            statusFailure(status)?.let { return finishFailure(it) }

            val declared = connection.contentLengthLong
            if (declared > binding.maxResponseBytes) {
                return finishFailure(NativePlannerTransport.ERROR_RESPONSE_TOO_LARGE)
            }
            if (!isSupportedJsonType(connection.contentType)) {
                return finishFailure(NativePlannerTransport.ERROR_RESPONSE_UNSUPPORTED)
            }

            val bytes = readBounded(connection)
            terminalFailureOrNull()?.let { return it }
            val body = decodeUtf8(bytes)
                ?: return finishFailure(NativePlannerTransport.ERROR_RESPONSE_MALFORMED)
            if (!isCompleteJsonObject(body)) {
                return finishFailure(NativePlannerTransport.ERROR_RESPONSE_MALFORMED)
            }
            finishSuccess(body)
        } catch (_: ResponseTooLarge) {
            finishFailure(NativePlannerTransport.ERROR_RESPONSE_TOO_LARGE)
        } catch (exc: SecretStoreException) {
            finishFailure(exc.code)
        } catch (_: UnknownHostException) {
            finishFailure(NativePlannerTransport.ERROR_DNS_UNREACHABLE)
        } catch (_: ConnectException) {
            finishFailure(NativePlannerTransport.ERROR_CONNECTION_REFUSED)
        } catch (_: SSLException) {
            finishFailure(NativePlannerTransport.ERROR_TLS)
        } catch (_: SocketTimeoutException) {
            finishFailure(NativePlannerTransport.ERROR_TIMEOUT)
        } catch (exc: IOException) {
            if (exc.message.orEmpty().contains("cleartext", ignoreCase = true)) {
                finishFailure(NativePlannerTransport.ERROR_CLEARTEXT_BLOCKED)
            } else {
                finishFailure(NativePlannerTransport.ERROR_ENDPOINT_UNREACHABLE)
            }
        } catch (_: Exception) {
            finishFailure(NativePlannerTransport.ERROR_TRANSPORT_FAILED)
        } finally {
            activeConnection = null
            connection?.disconnect()
        }
    }

    private fun configure(connection: HttpURLConnection) {
        val timeoutMillis = timeoutMillis()
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

    private fun timeoutMillis(): Int =
        ceil(binding.timeoutSeconds * 1000.0)
            .coerceAtMost(Int.MAX_VALUE.toDouble())
            .toInt()
            .coerceAtLeast(1)

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
                terminalFailureOrNull()?.let { throw IOException(it.code) }
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

    private fun isCompleteJsonObject(body: String): Boolean = try {
        val tokener = JSONTokener(body)
        val value = tokener.nextValue()
        value is JSONObject && tokener.nextClean() == '\u0000'
    } catch (_: JSONException) {
        false
    }

    private fun isSupportedJsonType(contentType: String?): Boolean {
        if (contentType == null) return true
        val mediaType = contentType.substringBefore(';').trim().lowercase()
        return mediaType == "application/json" || mediaType.endsWith("+json")
    }

    private fun finishSuccess(body: String): PlannerTransportResult {
        return if (terminalState.compareAndSet(
                PlannerCallTerminalState.ACTIVE,
                PlannerCallTerminalState.FINISHED,
            )
        ) {
            PlannerTransportResult.Success(body)
        } else {
            terminalResult(NativePlannerTransport.ERROR_TRANSPORT_FAILED)
        }
    }

    private fun finishFailure(code: String): PlannerTransportResult {
        return if (terminalState.compareAndSet(
                PlannerCallTerminalState.ACTIVE,
                PlannerCallTerminalState.FINISHED,
            )
        ) {
            PlannerTransportResult.Failure(code)
        } else {
            terminalResult(code)
        }
    }

    private fun terminalFailureOrNull(): PlannerTransportResult.Failure? = when (terminalState.get()) {
        PlannerCallTerminalState.CANCELLED -> cancelled()
        PlannerCallTerminalState.TIMED_OUT -> timeout()
        PlannerCallTerminalState.ACTIVE,
        PlannerCallTerminalState.FINISHED -> null
    }

    private fun terminalResult(fallbackCode: String): PlannerTransportResult.Failure = when (
        terminalState.get()
    ) {
        PlannerCallTerminalState.CANCELLED -> cancelled()
        PlannerCallTerminalState.TIMED_OUT -> timeout()
        PlannerCallTerminalState.ACTIVE,
        PlannerCallTerminalState.FINISHED -> PlannerTransportResult.Failure(fallbackCode)
    }

    private fun cancelled() =
        PlannerTransportResult.Failure(NativePlannerTransport.ERROR_CANCELLED)

    private fun timeout() =
        PlannerTransportResult.Failure(NativePlannerTransport.ERROR_TIMEOUT)

    private class ResponseTooLarge : IOException()

    private fun chatCompletionsUrl(baseUrl: String): String =
        if (baseUrl.trimEnd('/').endsWith("/chat/completions")) baseUrl.trimEnd('/')
        else baseUrl.trimEnd('/') + "/chat/completions"
}
