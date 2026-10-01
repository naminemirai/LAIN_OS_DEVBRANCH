package dev.lain.os.runtime

import android.content.ComponentName
import android.content.ServiceConnection
import android.os.Binder
import android.os.Parcel
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.filters.SdkSuppress
import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject
import java.util.Collections
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/** Authored connection regressions; device execution is deferred by the owner. */
class RuntimeConnectionTest {
    private class FakeBinding : RuntimeBinding {
        val connections = mutableListOf<ServiceConnection>()
        var unbound = 0
        override fun bind(connection: ServiceConnection): Boolean {
            connections += connection
            return true
        }
        override fun unbind(connection: ServiceConnection) { unbound++ }
    }

    @Test fun staleConnectionCannotReplaceNewBinding() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        instrumentation.runOnMainSync {
            val binding = FakeBinding()
            val client = RuntimeClient(instrumentation.targetContext, binding)
            val states = mutableListOf<Boolean>()
            client.onConnection = { states += it }
            client.connect()
            val old = binding.connections.single()
            client.disconnect()
            client.connect()
            old.onServiceConnected(ComponentName("dev.lain.os", "Old"), Binder())
            assertEquals(false, states.last())
            binding.connections.last().onServiceConnected(null, Binder())
            assertEquals(true, states.last())
            client.close()
        }
    }

    @Test
    @SdkSuppress(minSdkVersion = 26) // ServiceConnection.onBindingDied was added in API 26.
    fun bindingDeathAllowsExplicitReconnect() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        instrumentation.runOnMainSync {
            val binding = FakeBinding()
            val client = RuntimeClient(instrumentation.targetContext, binding)
            client.connect()
            binding.connections.single().onBindingDied(null)
            client.connect()
            assertEquals(2, binding.connections.size)
            assertEquals(1, binding.unbound)
            client.close()
            client.connect()
            assertEquals(2, binding.connections.size)
        }
    }

    @Test fun queuedWriteAndOldReplyDoNotCrossReconnect() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val binding = FakeBinding()
        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val settled = CountDownLatch(1)
        val staleCallbacks = AtomicInteger()
        val oldCommands = Collections.synchronizedList(mutableListOf<String>())
        val newCommands = Collections.synchronizedList(mutableListOf<String>())
        fun endpoint(commands: MutableList<String>, block: Boolean) = object : Binder() {
            override fun onTransact(code: Int, data: Parcel, reply: Parcel?, flags: Int): Boolean {
                data.enforceInterface(RuntimeProtocol.DESCRIPTOR)
                commands += JSONObject(data.readString()!!).getString("command")
                if (block) {
                    entered.countDown()
                    check(release.await(5, TimeUnit.SECONDS))
                }
                reply!!.writeNoException()
                reply.writeString(RuntimeProtocol.failure("APP_BUSY"))
                return true
            }
        }
        lateinit var client: RuntimeClient
        try {
            instrumentation.runOnMainSync {
                client = RuntimeClient(instrumentation.targetContext, binding)
                client.connect()
                binding.connections.last().onServiceConnected(null, endpoint(oldCommands, true))
                client.request("sessions", JSONObject()) { staleCallbacks.incrementAndGet() }
            }
            assertTrue(entered.await(5, TimeUnit.SECONDS))
            instrumentation.runOnMainSync {
                client.request("start", JSONObject().put("goal", "Show battery")) { staleCallbacks.incrementAndGet() }
                client.reconnect()
                binding.connections.last().onServiceConnected(null, endpoint(newCommands, false))
                client.request("sessions", JSONObject()) { settled.countDown() }
            }
            release.countDown()
            assertTrue(settled.await(5, TimeUnit.SECONDS))
            assertEquals(listOf("sessions"), oldCommands)
            assertEquals(listOf("sessions"), newCommands)
            assertEquals(0, staleCallbacks.get())
        } finally {
            release.countDown()
            instrumentation.runOnMainSync { client.close() }
        }
    }
}
