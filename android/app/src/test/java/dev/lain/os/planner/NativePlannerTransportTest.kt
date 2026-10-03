package dev.lain.os.planner

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.net.ConnectException
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownHostException
import javax.net.ssl.SSLException

class NativePlannerTransportTest {
    private class FakeSecretStore(private val secret: String? = "secret") : SecretStore {
        override fun create(secret: String) = error("unused")
        override fun replace(credentialRef: String, secret: String) = error("unused")
        override fun resolve(credentialRef: String): String =
            secret ?: throw SecretStoreException(AndroidKeystoreSecretStore.ERROR_CREDENTIAL_MISSING)
        override fun contains(credentialRef: String) = secret != null
        override fun remove(credentialRef: String) = error("unused")
    }

    private class FakeConnection(
        url: URL,
        private val status: Int = 200,
        private val response: ByteArray = "{\"choices\":[]}".toByteArray(),
        private val responseType: String? = "application/json",
        private val statusFailure: IOException? = null,
        private val responseStream: InputStream? = null,
    ) : HttpURLConnection(url) {
        val written = ByteArrayOutputStream()
        var disconnected = false

        override fun connect() = Unit
        override fun disconnect() { disconnected = true }
        override fun usingProxy() = false
        override fun getOutputStream() = written
        override fun getResponseCode(): Int {
            statusFailure?.let { throw it }
            return status
        }
        override fun getInputStream() = responseStream ?: ByteArrayInputStream(response)
        override fun getContentType(): String? = responseType
        override fun getContentLengthLong(): Long = response.size.toLong()
    }

    private fun binding(
        mode: String = "cloud",
        baseUrl: String = "https://example.invalid/v1",
        credentialRef: String? = "cred_" + "a".repeat(32),
        allowInsecureLanHttp: Boolean = false,
        maxResponseBytes: Int = 1024,
        timeoutSeconds: Double = 2.0,
    ) = PlannerBinding(
        profileId = "test",
        mode = mode,
        protocol = "openai_compatible_v1",
        baseUrl = baseUrl,
        model = "model-a",
        credentialRef = credentialRef,
        timeoutSeconds = timeoutSeconds,
        maxResponseBytes = maxResponseBytes,
        responseMode = "json_object",
        allowInsecureLanHttp = allowInsecureLanHttp,
    )

    @Test fun postsToChatCompletionsWithOptionalBearerCredential() {
        lateinit var connection: FakeConnection
        val transport = NativePlannerTransport(FakeSecretStore()) { url ->
            FakeConnection(url).also { connection = it }
        }

        val result = transport.newCall(binding(), "{\"hello\":\"world\"}").execute()

        assertTrue(result is PlannerTransportResult.Success)
        assertEquals("https://example.invalid/v1/chat/completions", connection.url.toString())
        assertEquals("Bearer secret", connection.getRequestProperty("Authorization"))
        assertEquals("application/json", connection.getRequestProperty("Content-Type"))
        assertEquals("{\"hello\":\"world\"}", connection.written.toString(Charsets.UTF_8.name()))
        assertTrue(connection.disconnected)
    }

    @Test fun mapsRequiredHttpFailures() {
        val cases = mapOf(
            401 to NativePlannerTransport.ERROR_AUTH_REJECTED,
            403 to NativePlannerTransport.ERROR_AUTH_REJECTED,
            404 to NativePlannerTransport.ERROR_MODEL_NOT_FOUND,
            408 to NativePlannerTransport.ERROR_TIMEOUT,
            429 to NativePlannerTransport.ERROR_RATE_LIMITED,
            500 to NativePlannerTransport.ERROR_SERVER,
            503 to NativePlannerTransport.ERROR_SERVER,
        )
        for ((status, expected) in cases) {
            val transport = NativePlannerTransport(FakeSecretStore()) { FakeConnection(it, status = status) }
            val result = transport.newCall(binding(), "{}").execute()
            assertEquals(expected, (result as PlannerTransportResult.Failure).code)
        }
    }

    @Test fun mapsRequiredNetworkFailures() {
        val cases = listOf(
            UnknownHostException() to NativePlannerTransport.ERROR_DNS_UNREACHABLE,
            ConnectException() to NativePlannerTransport.ERROR_CONNECTION_REFUSED,
            SSLException("tls") to NativePlannerTransport.ERROR_TLS,
            SocketTimeoutException() to NativePlannerTransport.ERROR_TIMEOUT,
            IOException("network") to NativePlannerTransport.ERROR_ENDPOINT_UNREACHABLE,
        )
        for ((failure, expected) in cases) {
            val transport = NativePlannerTransport(FakeSecretStore()) { throw failure }
            val result = transport.newCall(binding(), "{}").execute()
            assertEquals(expected, (result as PlannerTransportResult.Failure).code)
        }
    }

    @Test fun rejectsOversizedMalformedTrailingAndUnsupportedResponses() {
        val oversized = NativePlannerTransport(FakeSecretStore()) {
            FakeConnection(it, response = ByteArray(9) { 'x'.code.toByte() })
        }.newCall(binding(maxResponseBytes = 8), "{}").execute()
        assertEquals(
            NativePlannerTransport.ERROR_RESPONSE_TOO_LARGE,
            (oversized as PlannerTransportResult.Failure).code,
        )

        val invalidBodies = listOf(
            "not-json",
            "[]",
            "{\"choices\":[]}garbage",
        )
        for (body in invalidBodies) {
            val malformed = NativePlannerTransport(FakeSecretStore()) {
                FakeConnection(it, response = body.toByteArray())
            }.newCall(binding(), "{}").execute()
            assertEquals(
                NativePlannerTransport.ERROR_RESPONSE_MALFORMED,
                (malformed as PlannerTransportResult.Failure).code,
            )
        }

        val unsupported = NativePlannerTransport(FakeSecretStore()) {
            FakeConnection(it, responseType = "text/html")
        }.newCall(binding(), "{}").execute()
        assertEquals(
            NativePlannerTransport.ERROR_RESPONSE_UNSUPPORTED,
            (unsupported as PlannerTransportResult.Failure).code,
        )
    }

    @Test fun wholeRequestDeadlineBoundsTrickledResponse() {
        val response = "{\"choices\":[]}".toByteArray()
        val slowStream = object : InputStream() {
            var index = 0
            override fun read(): Int {
                if (index >= response.size) return -1
                Thread.sleep(20)
                return response[index++].toInt() and 0xff
            }
            override fun read(buffer: ByteArray, offset: Int, length: Int): Int {
                val next = read()
                if (next < 0) return -1
                buffer[offset] = next.toByte()
                return 1
            }
        }
        val transport = NativePlannerTransport(FakeSecretStore()) {
            FakeConnection(it, response = response, responseStream = slowStream)
        }

        val result = transport.newCall(binding(timeoutSeconds = 0.05), "{}").execute()

        assertEquals(
            NativePlannerTransport.ERROR_TIMEOUT,
            (result as PlannerTransportResult.Failure).code,
        )
    }

    @Test fun cancellationNeverReturnsAResponse() {
        val call = NativePlannerTransport(FakeSecretStore()) { FakeConnection(it) }
            .newCall(binding(), "{}")
        call.cancel()
        val result = call.execute()
        assertEquals(
            NativePlannerTransport.ERROR_CANCELLED,
            (result as PlannerTransportResult.Failure).code,
        )
    }

    @Test fun localModeNeverFallsBackToCloud() {
        val visited = mutableListOf<String>()
        val transport = NativePlannerTransport(FakeSecretStore()) { url ->
            visited += url.toString()
            throw UnknownHostException()
        }
        val result = transport.newCall(
            binding(
                mode = "local",
                baseUrl = "https://192.168.1.9:11434/v1",
                credentialRef = null,
            ),
            "{}",
        ).execute()

        assertEquals(
            NativePlannerTransport.ERROR_DNS_UNREACHABLE,
            (result as PlannerTransportResult.Failure).code,
        )
        assertEquals(listOf("https://192.168.1.9:11434/v1/chat/completions"), visited)
    }

    @Test fun rejectsCleartextEndpointsEvenWhenLocalPrivateLiteralIsOptedIn() {
        val rejected = listOf(
            { binding(mode = "local", baseUrl = "http://192.168.1.9:11434/v1", credentialRef = null, allowInsecureLanHttp = true) },
            { binding(mode = "cloud", baseUrl = "http://192.168.1.9/v1", allowInsecureLanHttp = true) },
            { binding(mode = "local", baseUrl = "http://192.168.1.9/v1", allowInsecureLanHttp = false) },
            { binding(mode = "local", baseUrl = "http://8.8.8.8/v1", allowInsecureLanHttp = true) },
            { binding(mode = "local", baseUrl = "http://example.com/v1", allowInsecureLanHttp = true) },
        )
        for (build in rejected) {
            var failed = false
            try { build() } catch (_: IllegalArgumentException) { failed = true }
            assertTrue(failed)
        }
    }
}
