package dev.lain.os.runtime

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.IBinder
import android.os.Parcel
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Device tests authored with the interface; execution is deferred. */
@RunWith(AndroidJUnit4::class)
class RuntimeServiceTest {
    @Test fun rejectsForeignUid() {
        try { RuntimeProtocol.enforceCaller(1002, 1001); fail("foreign UID accepted") }
        catch (_: SecurityException) { }
        RuntimeProtocol.enforceCaller(1001, 1001)
    }

    @Test fun malformedPayloadFailsClosed() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val connected = CountDownLatch(1)
        var remote: IBinder? = null
        val connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
                remote = binder; connected.countDown()
            }
            override fun onServiceDisconnected(name: ComponentName?) { remote = null }
        }
        assertTrue(context.bindService(Intent(context, RuntimeService::class.java), connection, Context.BIND_AUTO_CREATE))
        try {
            assertTrue(connected.await(10, TimeUnit.SECONDS))
            val data = Parcel.obtain()
            val reply = Parcel.obtain()
            try {
                data.writeInterfaceToken(RuntimeProtocol.DESCRIPTOR)
                data.writeString("not json")
                assertTrue(remote!!.transact(RuntimeProtocol.REQUEST, data, reply, 0))
                reply.readException()
                assertFalse(JSONObject(reply.readString()!!).getBoolean("ok"))
            } finally { data.recycle(); reply.recycle() }
        } finally { context.unbindService(connection) }
    }
}
