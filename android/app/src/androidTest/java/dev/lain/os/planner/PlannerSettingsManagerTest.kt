package dev.lain.os.planner

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.io.File
import java.util.UUID
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PlannerSettingsManagerTest {
    private val context = ApplicationProvider.getApplicationContext<android.content.Context>()

    private fun tempRoot(prefix: String): File =
        File(context.cacheDir, prefix + UUID.randomUUID()).apply { mkdirs() }
    private class FakeSecretStore : SecretStore {
        private val values = linkedMapOf<String, String>()
        var replacements = 0
        var removals = 0

        override fun create(secret: String): String {
            val ref = "cred_" + UUID.randomUUID().toString().replace("-", "")
            values[ref] = secret
            return ref
        }

        override fun replace(credentialRef: String, secret: String) {
            require(values.containsKey(credentialRef))
            replacements++
            values[credentialRef] = secret
        }

        override fun resolve(credentialRef: String): String =
            values[credentialRef] ?: throw SecretStoreException(AndroidKeystoreSecretStore.ERROR_CREDENTIAL_MISSING)

        override fun contains(credentialRef: String): Boolean = values.containsKey(credentialRef)

        override fun remove(credentialRef: String): Boolean {
            removals++
            return values.remove(credentialRef) != null
        }
    }

    @Test fun createSelectReplaceRemoveAndDeleteNeverExposeSecret() {
        val root = tempRoot("planner-settings-")
        try {
            val secrets = FakeSecretStore()
            val profiles = PlannerProfileStore(File(root, "profiles"))
            val manager = PlannerSettingsManager(profiles, secrets) { PlannerConnectionStatus.CONNECTED }

            val id = manager.save(
                PlannerProfileDraft(
                    name = "Cloud primary",
                    mode = "cloud",
                    baseUrl = "https://api.example.invalid/v1",
                    model = "model-a",
                    credential = "raw-secret-one",
                )
            )
            val created = manager.snapshot()
            val summary = created.profiles.single { it.id == id }
            assertTrue(summary.credentialSaved)
            assertFalse(created.toString().contains("raw-secret-one"))
            assertFalse(created.toString().contains("cred_"))

            manager.select(id)
            assertEquals(id, manager.snapshot().activeProfileId)

            manager.save(
                PlannerProfileDraft(
                    profileId = id,
                    name = "Cloud renamed",
                    mode = "cloud",
                    baseUrl = "https://api.example.invalid/v1",
                    model = "model-b",
                    credential = "raw-secret-two",
                )
            )
            assertEquals(1, secrets.replacements)
            assertFalse(manager.snapshot().toString().contains("raw-secret-two"))

            manager.removeCredential(id)
            assertFalse(manager.snapshot().profiles.single { it.id == id }.credentialSaved)
            assertEquals(1, secrets.removals)

            manager.delete(id)
            assertNull(manager.snapshot().profiles.firstOrNull { it.id == id })
            assertEquals(PlannerProfile.DEMO_ID, manager.snapshot().activeProfileId)
        } finally {
            root.deleteRecursively()
        }
    }

    @Test fun testConnectionIsReadOnlyWithRespectToProfileState() {
        val root = tempRoot("planner-settings-diagnostic-")
        try {
            val secrets = FakeSecretStore()
            val profiles = PlannerProfileStore(File(root, "profiles"))
            val seen = mutableListOf<String>()
            val manager = PlannerSettingsManager(profiles, secrets) { profile ->
                seen += profile.id
                PlannerConnectionStatus.CONNECTED
            }
            val id = manager.save(
                PlannerProfileDraft(
                    name = "Local",
                    mode = "local",
                    baseUrl = "https://192.168.1.50:8443/v1",
                    model = "model-a",
                )
            )
            manager.select(id)
            val before = manager.snapshot()

            assertEquals(PlannerConnectionStatus.CONNECTED, manager.testConnection(id))

            assertEquals(listOf(id), seen)
            assertEquals(before, manager.snapshot())
        } finally {
            root.deleteRecursively()
        }
    }

    @Test fun demoIsBuiltInAndCannotBeDeletedOrEdited() {
        val root = tempRoot("planner-settings-demo-")
        try {
            val manager = PlannerSettingsManager(
                PlannerProfileStore(File(root, "profiles")),
                FakeSecretStore(),
            ) { PlannerConnectionStatus.CONNECTED }

            assertFalse(manager.delete(PlannerProfile.DEMO_ID))
            manager.select(PlannerProfile.DEMO_ID)
            assertEquals(PlannerProfile.DEMO_ID, manager.snapshot().activeProfileId)
            assertEquals(
                PlannerConnectionStatus.OFFLINE_DEMO,
                manager.testConnection(PlannerProfile.DEMO_ID),
            )
        } finally {
            root.deleteRecursively()
        }
    }
}
