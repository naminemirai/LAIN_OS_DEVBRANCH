package dev.lain.os.planner

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.io.File
import java.util.UUID
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.CountDownLatch
import kotlin.concurrent.thread
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PlannerProfileStoreAndroidTest {
    private val context = ApplicationProvider.getApplicationContext<android.content.Context>()
    private val root = File(context.cacheDir, "planner-profile-test-" + UUID.randomUUID())

    @After fun cleanup() {
        root.deleteRecursively()
    }

    @Test fun restartPreservesProfilesAndActiveSelection() {
        val first = PlannerProfileStore(root)
        val profile = cloudProfile("cloud-primary", "model-a")

        first.upsert(profile)
        first.select(profile.id)

        val afterRestart = PlannerProfileStore(root)
        assertEquals(profile, afterRestart.get(profile.id))
        assertEquals(profile, afterRestart.active())
        assertEquals(profile.toTrustedBindingJson().toString(), afterRestart.activeBindingJson())
    }

    @Test fun noSelectionDefaultsToOfflineDemo() {
        val store = PlannerProfileStore(root)

        assertEquals(PlannerProfile.offlineDemo(), store.active())
        assertEquals(listOf("offline-demo"), store.list().map { it.id })
    }

    @Test fun activeRemovalFallsBackToOfflineDemo() {
        val store = PlannerProfileStore(root)
        val profile = cloudProfile("cloud-primary", "model-a")
        store.upsert(profile)
        store.select(profile.id)

        assertEquals(true, store.remove(profile.id))
        assertNull(store.get(profile.id))
        assertEquals("offline-demo", store.active().id)
    }


    @Test fun twoInstancesSerializeConcurrentUpdatesInProcess() {
        val first = PlannerProfileStore(root)
        val second = PlannerProfileStore(root)
        val start = CountDownLatch(1)
        val failures = ConcurrentLinkedQueue<Throwable>()

        val workers = listOf(
            thread(start = true) {
                start.await()
                repeat(50) { index ->
                    try {
                        first.upsert(cloudProfile("cloud-a", "model-a-$index"))
                    } catch (exc: Throwable) {
                        failures.add(exc)
                    }
                }
            },
            thread(start = true) {
                start.await()
                repeat(50) { index ->
                    try {
                        second.upsert(cloudProfile("cloud-b", "model-b-$index"))
                    } catch (exc: Throwable) {
                        failures.add(exc)
                    }
                }
            },
        )
        start.countDown()
        workers.forEach { it.join() }

        assertTrue(failures.toString(), failures.isEmpty())
        val after = PlannerProfileStore(root)
        assertNotNull(after.get("cloud-a"))
        assertNotNull(after.get("cloud-b"))
    }

    @Test fun rejectedRawCredentialNeverReachesPersistentState() {
        val store = PlannerProfileStore(root)
        val valid = cloudProfile("cloud-primary", "model-a")
        store.upsert(valid)

        assertThrows(IllegalArgumentException::class.java) {
            store.upsert(valid.copy(id = "bad", credentialRef = "sk-raw-secret"))
        }

        val state = File(root, "profiles.json").readText()
        assertFalse(state.contains("sk-raw-secret"))
    }

    private fun cloudProfile(id: String, model: String) = PlannerProfile(
        id = id,
        name = "Cloud",
        mode = "cloud",
        protocol = "openai_compatible_v1",
        baseUrl = "https://api.example.invalid/v1",
        model = model,
        credentialRef = "cred_0123456789abcdef0123456789abcdef",
        timeoutSeconds = 30.0,
        maxResponseBytes = 1_048_576,
        responseMode = "json_schema",
        allowInsecureLanHttp = false,
    )
}
