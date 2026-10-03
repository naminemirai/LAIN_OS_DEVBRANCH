package dev.lain.os.planner

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Test

class PlannerProfileTest {
    @Test fun demoProfileProducesTrustedOfflineBinding() {
        val profile = PlannerProfile.offlineDemo()

        assertEquals("offline-demo", profile.id)
        assertEquals("demo", profile.mode)
        assertEquals("offline_demo", profile.model)
        assertEquals(
            setOf(
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
            ),
            profile.toTrustedBindingJson().keys().asSequence().toSet(),
        )
        assertFalse(profile.toTrustedBindingJson().toString().contains("sk-raw-secret"))
    }

    @Test fun cloudAndLocalProfilesShareOneStrictSchema() {
        val cloud = PlannerProfile(
            id = "cloud-primary",
            name = "Cloud primary",
            mode = "cloud",
            protocol = "openai_compatible_v1",
            baseUrl = "https://api.example.invalid/v1",
            model = "model-a",
            credentialRef = "cred_0123456789abcdef0123456789abcdef",
            timeoutSeconds = 30.0,
            maxResponseBytes = 1_048_576,
            responseMode = "json_schema",
            allowInsecureLanHttp = false,
        )
        val local = cloud.copy(
            id = "local-primary",
            name = "Local primary",
            mode = "local",
            baseUrl = "https://192.168.1.50:8443/v1",
            credentialRef = null,
        )

        assertEquals("cloud-primary", cloud.toTrustedBindingJson().getString("profile_id"))
        assertEquals("local", local.toTrustedBindingJson().getString("mode"))
    }

    @Test fun invalidEndpointsModelsAndCredentialValuesFailClosed() {
        val base = PlannerProfile(
            id = "cloud-primary",
            name = "Cloud primary",
            mode = "cloud",
            protocol = "openai_compatible_v1",
            baseUrl = "https://api.example.invalid/v1",
            model = "model-a",
            credentialRef = "cred_0123456789abcdef0123456789abcdef",
            timeoutSeconds = 30.0,
            maxResponseBytes = 1_048_576,
            responseMode = "json_schema",
            allowInsecureLanHttp = false,
        )

        val invalid = listOf(
            { base.copy(baseUrl = "http://api.example.invalid/v1") },
            { base.copy(baseUrl = "https://user:secret@api.example.invalid/v1") },
            { base.copy(baseUrl = "https://api.example.invalid/v1?token=secret") },
            { base.copy(model = " ") },
            { base.copy(credentialRef = "sk-raw-secret") },
            { base.copy(timeoutSeconds = Double.NaN) },
            { base.copy(maxResponseBytes = 0) },
            { base.copy(responseMode = "none") },
            { base.copy(mode = "local", allowInsecureLanHttp = true) },
        )

        invalid.forEach { candidate ->
            assertThrows(IllegalArgumentException::class.java) { candidate() }
        }
    }
}
