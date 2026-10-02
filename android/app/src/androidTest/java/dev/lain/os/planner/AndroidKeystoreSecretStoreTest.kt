package dev.lain.os.planner

import android.content.Context
import android.content.pm.ApplicationInfo
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import dev.lain.os.runtime.RuntimeProtocol
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

@RunWith(AndroidJUnit4::class)
class AndroidKeystoreSecretStoreTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()

    @Test fun credentialSurvivesFreshStoreInstance() {
        val secret = "sk-test-" + UUID.randomUUID()
        val first = AndroidKeystoreSecretStore(context)
        val ref = first.create(secret)
        try {
            val afterRestartBoundary = AndroidKeystoreSecretStore(context)
            assertEquals(secret, afterRestartBoundary.resolve(ref))
            assertTrue(ref.matches(Regex("^cred_[0-9a-f]{32}$")))
            assertFalse(ref.contains(secret))
        } finally {
            first.remove(ref)
        }
    }

    @Test fun replaceAndRemoveAreExplicit() {
        val store = AndroidKeystoreSecretStore(context)
        val ref = store.create("first-" + UUID.randomUUID())
        assertTrue(store.contains(ref))
        store.replace(ref, "second-" + UUID.randomUUID())
        val replacement = store.resolve(ref)
        assertTrue(replacement.startsWith("second-"))
        assertTrue(store.remove(ref))
        assertFalse(store.contains(ref))
        try {
            store.resolve(ref)
            fail("missing credential resolved")
        } catch (exc: SecretStoreException) {
            assertEquals(AndroidKeystoreSecretStore.ERROR_CREDENTIAL_MISSING, exc.code)
        }
    }

    @Test fun encryptedRecordDoesNotContainRawCredential() {
        val secret = "visible-marker-" + UUID.randomUUID()
        val store = AndroidKeystoreSecretStore(context)
        val ref = store.create(secret)
        try {
            val record = File(context.filesDir, "planner-secrets/$ref.secret").readText()
            assertFalse(record.contains(secret))
            assertTrue(record.contains("\"ciphertext\""))
            assertEquals(secret, store.resolve(ref))
        } finally {
            store.remove(ref)
        }
    }

    @Test fun swappedCredentialRecordsFailClosed() {
        val store = AndroidKeystoreSecretStore(context)
        val firstRef = store.create("first-" + UUID.randomUUID())
        val secondRef = store.create("second-" + UUID.randomUUID())
        val root = File(context.filesDir, "planner-secrets")
        val firstFile = File(root, "$firstRef.secret")
        val secondFile = File(root, "$secondRef.secret")
        val firstRecord = firstFile.readBytes()
        val secondRecord = secondFile.readBytes()
        try {
            firstFile.writeBytes(secondRecord)
            secondFile.writeBytes(firstRecord)

            for (ref in listOf(firstRef, secondRef)) {
                try {
                    store.resolve(ref)
                    fail("credential record swap was accepted for $ref")
                } catch (exc: SecretStoreException) {
                    assertEquals(AndroidKeystoreSecretStore.ERROR_CREDENTIAL_INVALID, exc.code)
                }
            }
        } finally {
            store.remove(firstRef)
            store.remove(secondRef)
        }
    }

    @Test fun concurrentStoreInitializationDoesNotFail() {
        val root = File(context.filesDir, "planner-secrets")
        assertTrue(root.deleteRecursively() || !root.exists())

        val workers = 8
        val ready = CountDownLatch(workers)
        val start = CountDownLatch(1)
        val done = CountDownLatch(workers)
        val failures = mutableListOf<Throwable>()
        val executor = Executors.newFixedThreadPool(workers)
        try {
            repeat(workers) {
                executor.execute {
                    ready.countDown()
                    try {
                        assertTrue(start.await(5, TimeUnit.SECONDS))
                        AndroidKeystoreSecretStore(context)
                    } catch (exc: Throwable) {
                        synchronized(failures) { failures += exc }
                    } finally {
                        done.countDown()
                    }
                }
            }
            assertTrue(ready.await(5, TimeUnit.SECONDS))
            start.countDown()
            assertTrue(done.await(10, TimeUnit.SECONDS))
            assertTrue("concurrent initialization failures: $failures", failures.isEmpty())
        } finally {
            executor.shutdownNow()
        }
    }

    @Test fun missingAndMalformedReferencesFailClosed() {
        val store = AndroidKeystoreSecretStore(context)
        try {
            store.resolve("cred_" + "0".repeat(32))
            fail("missing credential resolved")
        } catch (exc: SecretStoreException) {
            assertEquals(AndroidKeystoreSecretStore.ERROR_CREDENTIAL_MISSING, exc.code)
        }
        try {
            store.resolve("../secret")
            fail("malformed credential reference accepted")
        } catch (exc: SecretStoreException) {
            assertEquals(AndroidKeystoreSecretStore.ERROR_CREDENTIAL_INVALID, exc.code)
        }
    }

    @Test fun runtimeControlDoesNotExposeSecretOperations() {
        val commands = RuntimeProtocol.readCommands + RuntimeProtocol.writeCommands
        assertTrue(commands.none { it.contains("secret", ignoreCase = true) })
        assertTrue(commands.none { it.contains("credential", ignoreCase = true) })
    }

    @Test fun appBackupRemainsDisabled() {
        val info = context.packageManager.getApplicationInfo(context.packageName, 0)
        assertEquals(0, info.flags and ApplicationInfo.FLAG_ALLOW_BACKUP)
    }
}
