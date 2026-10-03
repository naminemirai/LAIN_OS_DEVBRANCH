package dev.lain.os.planner

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class NativePlannerBridgeTest {
    @Test fun bridgeReturnsBoundedSuccessWithoutCredentialMaterial() {
        val secrets = object : SecretStore {
            override fun create(secret: String) = error("unused")
            override fun replace(credentialRef: String, secret: String) = error("unused")
            override fun resolve(credentialRef: String) = "raw-secret-must-not-return"
            override fun contains(credentialRef: String) = true
            override fun remove(credentialRef: String) = false
        }
        val transport = NativePlannerTransport(secrets) { url ->
            FakeConnection(
                url,
                """{"choices":[{"message":{"content":"{\"status\":\"complete\",\"reason\":\"done\",\"actions\":[]}"},"finish_reason":"stop"}]}"""
            )
        }
        val bridge = NativePlannerBridge(transport)

        val result = bridge.execute(bindingJson(), """{"model":"model-a"}""")

        val envelope = org.json.JSONObject(result)
        assertTrue(envelope.getBoolean("ok"))
        assertTrue(envelope.getString("body").contains("\"choices\""))
        assertFalse(result.contains("raw-secret-must-not-return"))
    }

    @Test fun bridgeRejectsMalformedOrOversizedBindings() {
        val transport = NativePlannerTransport(NoopSecretStore) { url ->
            FakeConnection(url, "{}")
        }
        val bridge = NativePlannerBridge(transport)

        assertEquals(
            "PLANNER_TRANSPORT_FAILED",
            org.json.JSONObject(bridge.execute("{}", "{}")).getString("error"),
        )
        assertEquals(
            "PLANNER_TRANSPORT_FAILED",
            org.json.JSONObject(bridge.execute("x".repeat(9000), "{}")).getString("error"),
        )
    }

    private fun bindingJson() = """
        {
          "profile_id":"cloud-primary",
          "mode":"cloud",
          "protocol":"openai_compatible_v1",
          "base_url":"https://api.example.invalid/v1",
          "model":"model-a",
          "credential_ref":"cred_0123456789abcdef0123456789abcdef",
          "timeout_seconds":30.0,
          "max_response_bytes":1048576,
          "response_mode":"json_schema",
          "allow_insecure_lan_http":false
        }
    """.trimIndent()

    private object NoopSecretStore : SecretStore {
        override fun create(secret: String) = error("unused")
        override fun replace(credentialRef: String, secret: String) = error("unused")
        override fun resolve(credentialRef: String) = error("unused")
        override fun contains(credentialRef: String) = false
        override fun remove(credentialRef: String) = false
    }

    private class FakeConnection(
        url: URL,
        private val response: String,
    ) : HttpURLConnection(url) {
        private val request = ByteArrayOutputStream()

        override fun connect() = Unit
        override fun disconnect() = Unit
        override fun usingProxy() = false
        override fun getResponseCode() = 200
        override fun getContentType() = "application/json"
        override fun getContentLengthLong() = response.toByteArray().size.toLong()
        override fun getInputStream() = ByteArrayInputStream(response.toByteArray())
        override fun getOutputStream() = request
    }
}
