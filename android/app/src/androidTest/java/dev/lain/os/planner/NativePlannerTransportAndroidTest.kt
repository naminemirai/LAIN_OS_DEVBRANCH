package dev.lain.os.planner

import android.Manifest
import android.content.Context
import android.security.NetworkSecurityPolicy
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL

@RunWith(AndroidJUnit4::class)
class NativePlannerTransportAndroidTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()

    private object NoCredentialSecretStore : SecretStore {
        override fun create(secret: String) = error("unused")
        override fun replace(credentialRef: String, secret: String) = error("unused")
        override fun resolve(credentialRef: String) = error("unused")
        override fun contains(credentialRef: String) = false
        override fun remove(credentialRef: String) = false
    }

    private class FakeConnection(url: URL, private val response: ByteArray) : HttpURLConnection(url) {
        private val written = ByteArrayOutputStream()

        override fun connect() = Unit
        override fun disconnect() = Unit
        override fun usingProxy() = false
        override fun getOutputStream() = written
        override fun getResponseCode() = 200
        override fun getInputStream() = ByteArrayInputStream(response)
        override fun getContentType() = "application/json"
        override fun getContentLengthLong() = response.size.toLong()
    }

    @Test fun appRequestsInternetPermissionForPlannerTransport() {
        val permissions = context.packageManager
            .getPackageInfo(context.packageName, 0x00001000)
            .requestedPermissions
            ?.toSet()
            .orEmpty()
        assertTrue(Manifest.permission.INTERNET in permissions)
    }

    @Test fun appDoesNotGloballyPermitCleartextTraffic() {
        assertFalse(NetworkSecurityPolicy.getInstance().isCleartextTrafficPermitted)
    }

    @Test fun malformedAndTrailingPlannerResponsesAreRejectedByAndroidJsonRuntime() {
        val binding = PlannerBinding(
            profileId = "instrumentation",
            mode = "local",
            protocol = "openai_compatible_v1",
            baseUrl = "https://127.0.0.1:11434/v1",
            model = "model-a",
            credentialRef = null,
            timeoutSeconds = 2.0,
            maxResponseBytes = 1024,
            responseMode = "json_object",
            allowInsecureLanHttp = false,
        )
        for (body in listOf("not-json", "[]", "{\"choices\":[]}garbage")) {
            val transport = NativePlannerTransport(NoCredentialSecretStore) { url ->
                FakeConnection(url, body.toByteArray())
            }

            val result = transport.newCall(binding, "{}").execute()

            assertEquals(
                NativePlannerTransport.ERROR_RESPONSE_MALFORMED,
                (result as PlannerTransportResult.Failure).code,
            )
        }
    }
}
