package dev.lain.os.planner

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import android.util.Base64
import org.json.JSONObject
import java.io.File
import java.io.RandomAccessFile
import java.security.KeyStore
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Native-only planner credential storage.
 *
 * Planner/session state stores only the opaque credential reference returned by [create].
 * Raw credential material is never exposed through Binder or Python-facing APIs.
 */
internal interface SecretStore {
    fun create(secret: String): String
    fun replace(credentialRef: String, secret: String)
    fun resolve(credentialRef: String): String
    fun contains(credentialRef: String): Boolean
    fun remove(credentialRef: String): Boolean
}

internal class SecretStoreException(
    val code: String,
    cause: Throwable? = null,
) : Exception(code, cause)

internal class AndroidKeystoreSecretStore(context: Context) : SecretStore {
    private val root = File(context.applicationContext.filesDir, STORE_DIRECTORY).apply {
        if (!exists() && !mkdirs()) throw SecretStoreException(ERROR_STORAGE_FAILED)
        if (!isDirectory) throw SecretStoreException(ERROR_STORAGE_FAILED)
    }

    override fun create(secret: String): String {
        validateSecret(secret)
        repeat(16) {
            val credentialRef = "cred_" + UUID.randomUUID().toString().replace("-", "")
            val target = secretFile(credentialRef)
            if (!target.exists()) {
                writeEncrypted(target, secret)
                return credentialRef
            }
        }
        throw SecretStoreException(ERROR_STORAGE_FAILED)
    }

    override fun replace(credentialRef: String, secret: String) {
        validateSecret(secret)
        val target = secretFile(credentialRef)
        if (!target.exists()) throw SecretStoreException(ERROR_CREDENTIAL_MISSING)
        writeEncrypted(target, secret)
    }

    override fun resolve(credentialRef: String): String {
        val target = secretFile(credentialRef)
        if (!target.exists()) throw SecretStoreException(ERROR_CREDENTIAL_MISSING)
        val length = target.length()
        if (length <= 0L || length > MAX_RECORD_BYTES) {
            throw SecretStoreException(ERROR_CREDENTIAL_INVALID)
        }
        val payload = try {
            AtomicFile(target).readFully()
        } catch (exc: Exception) {
            throw SecretStoreException(ERROR_CREDENTIAL_INVALID, exc)
        }
        return decrypt(payload)
    }

    override fun contains(credentialRef: String): Boolean = secretFile(credentialRef).exists()

    override fun remove(credentialRef: String): Boolean {
        val target = secretFile(credentialRef)
        if (!target.exists()) return false
        return try {
            AtomicFile(target).delete()
            !target.exists()
        } catch (exc: Exception) {
            throw SecretStoreException(ERROR_STORAGE_FAILED, exc)
        }
    }

    private fun secretFile(credentialRef: String): File {
        if (!CREDENTIAL_REF.matches(credentialRef)) {
            throw SecretStoreException(ERROR_CREDENTIAL_INVALID)
        }
        return File(root, "$credentialRef.secret")
    }

    private fun validateSecret(secret: String) {
        val bytes = secret.toByteArray(Charsets.UTF_8)
        try {
            if (bytes.isEmpty() || bytes.size > MAX_SECRET_BYTES) {
                throw SecretStoreException(ERROR_CREDENTIAL_INVALID)
            }
        } finally {
            bytes.fill(0)
        }
    }

    private fun writeEncrypted(target: File, secret: String) {
        val plaintext = secret.toByteArray(Charsets.UTF_8)
        val record = try {
            val cipher = Cipher.getInstance(CIPHER)
            cipher.init(Cipher.ENCRYPT_MODE, secretKey())
            val ciphertext = cipher.doFinal(plaintext)
            JSONObject()
                .put("v", RECORD_VERSION)
                .put("iv", Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
                .put("ciphertext", Base64.encodeToString(ciphertext, Base64.NO_WRAP))
                .toString()
                .toByteArray(Charsets.UTF_8)
        } catch (exc: SecretStoreException) {
            throw exc
        } catch (exc: Exception) {
            throw SecretStoreException(ERROR_STORAGE_FAILED, exc)
        } finally {
            plaintext.fill(0)
        }

        if (record.size > MAX_RECORD_BYTES) throw SecretStoreException(ERROR_STORAGE_FAILED)
        val atomic = AtomicFile(target)
        val stream = try {
            atomic.startWrite()
        } catch (exc: Exception) {
            throw SecretStoreException(ERROR_STORAGE_FAILED, exc)
        }
        try {
            stream.write(record)
            stream.fd.sync()
            atomic.finishWrite(stream)
        } catch (exc: Exception) {
            atomic.failWrite(stream)
            throw SecretStoreException(ERROR_STORAGE_FAILED, exc)
        } finally {
            record.fill(0)
        }
    }

    private fun decrypt(payload: ByteArray): String {
        val plaintext = try {
            val raw = JSONObject(payload.toString(Charsets.UTF_8))
            if (raw.length() != 3 || raw.optInt("v", -1) != RECORD_VERSION ||
                !raw.has("iv") || !raw.has("ciphertext")) {
                throw SecretStoreException(ERROR_CREDENTIAL_INVALID)
            }
            val iv = Base64.decode(raw.getString("iv"), Base64.NO_WRAP)
            val ciphertext = Base64.decode(raw.getString("ciphertext"), Base64.NO_WRAP)
            if (iv.size != GCM_IV_BYTES || ciphertext.isEmpty()) {
                throw SecretStoreException(ERROR_CREDENTIAL_INVALID)
            }
            val cipher = Cipher.getInstance(CIPHER)
            cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(GCM_TAG_BITS, iv))
            cipher.doFinal(ciphertext)
        } catch (exc: SecretStoreException) {
            throw exc
        } catch (exc: Exception) {
            throw SecretStoreException(ERROR_CREDENTIAL_INVALID, exc)
        }
        return try {
            plaintext.toString(Charsets.UTF_8)
        } finally {
            plaintext.fill(0)
        }
    }

    private fun secretKey(): SecretKey {
        val lockFile = File(root, KEY_LOCK_FILE)
        try {
            RandomAccessFile(lockFile, "rw").channel.use { channel ->
                val lock = channel.lock()
                try {
                    val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
                    val existing = keyStore.getKey(KEY_ALIAS, null)
                    if (existing is SecretKey) return existing
                    val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE)
                    generator.init(
                        KeyGenParameterSpec.Builder(
                            KEY_ALIAS,
                            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
                        )
                            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                            .setRandomizedEncryptionRequired(true)
                            .setKeySize(256)
                            .build()
                    )
                    return generator.generateKey()
                } finally {
                    lock.release()
                }
            }
        } catch (exc: Exception) {
            throw SecretStoreException(ERROR_STORAGE_FAILED, exc)
        }
    }

    companion object {
        const val ERROR_CREDENTIAL_MISSING = "PLANNER_CREDENTIAL_MISSING"
        const val ERROR_CREDENTIAL_INVALID = "PLANNER_CREDENTIAL_INVALID"
        const val ERROR_STORAGE_FAILED = "PLANNER_CREDENTIAL_STORAGE_FAILED"

        private const val STORE_DIRECTORY = "planner-secrets"
        private const val KEY_LOCK_FILE = ".keystore.lock"
        private const val KEYSTORE = "AndroidKeyStore"
        private const val KEY_ALIAS = "dev.lain.os.planner.credentials.v1"
        private const val CIPHER = "AES/GCM/NoPadding"
        private const val RECORD_VERSION = 1
        private const val GCM_TAG_BITS = 128
        private const val GCM_IV_BYTES = 12
        private const val MAX_SECRET_BYTES = 16 * 1024
        private const val MAX_RECORD_BYTES = 32 * 1024
        private val CREDENTIAL_REF = Regex("^cred_[0-9a-f]{32}$")
    }
}
