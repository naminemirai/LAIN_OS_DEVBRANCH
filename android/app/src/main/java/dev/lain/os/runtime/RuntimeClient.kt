package dev.lain.os.runtime

import android.content.ComponentName
import android.content.Context
import android.content.ServiceConnection
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Parcel
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.RejectedExecutionException

class RuntimeClient(context: Context, private val binding: RuntimeBinding = AndroidRuntimeBinding(context)) {
    private val main = Handler(Looper.getMainLooper())
    private val requests = Executors.newSingleThreadExecutor()
    private val stopRequests = Executors.newSingleThreadExecutor()
    @Volatile private var remote: IBinder? = null
    @Volatile private var epoch = 0L
    @Volatile private var closed = false
    private var connection: ServiceConnection? = null
    private var deathLink: Pair<IBinder, IBinder.DeathRecipient>? = null
    var onConnection: ((Boolean) -> Unit)? = null

    // Binding and callback state belongs to the main thread. Each binding has
    // its own identity so late callbacks cannot overwrite a newer connection.
    fun connect() {
        if (closed || connection != null) return
        epoch++
        val candidate = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
                if (closed || connection !== this) return
                epoch++
                clearRemote()
                if (binder == null) { disconnect(); return }
                val slot = this
                val death = IBinder.DeathRecipient {
                    main.post {
                        if (!closed && connection === slot && remote === binder) disconnect()
                    }
                }
                try {
                    binder.linkToDeath(death, 0)
                    deathLink = binder to death
                    remote = binder
                    onConnection?.invoke(true)
                } catch (_: Exception) { disconnect() }
            }
            override fun onServiceDisconnected(name: ComponentName?) {
                if (closed || connection !== this) return
                epoch++
                clearRemote()
                onConnection?.invoke(false)
            }
            override fun onBindingDied(name: ComponentName?) {
                if (connection === this) disconnect()
            }
            override fun onNullBinding(name: ComponentName?) {
                if (connection === this) disconnect()
            }
        }
        connection = candidate
        try {
            if (!binding.bind(candidate)) {
                connection = null
                epoch++
                onConnection?.invoke(false)
            }
        } catch (_: Exception) {
            connection = null
            epoch++
            onConnection?.invoke(false)
        }
    }

    fun reconnect() { disconnect(); connect() }

    fun request(command: String, arguments: JSONObject, callback: (JSONObject) -> Unit) {
        if (closed) return
        val payload = RuntimeProtocol.request(command, arguments)
        val requestEpoch = epoch
        val target = remote
        // Capture the binding at submission: a queued write must never migrate
        // to a new service connection or get replayed after reconnection.
        val channel = if (command == "stop") stopRequests else requests
        try {
            channel.execute {
                if (closed || epoch != requestEpoch) return@execute
                val result = try {
                    require(payload.toByteArray(Charsets.UTF_8).size <= RuntimeProtocol.MAX_BYTES)
                    val binder = target ?: throw IllegalStateException()
                    val data = Parcel.obtain()
                    val reply = Parcel.obtain()
                    try {
                        data.writeInterfaceToken(RuntimeProtocol.DESCRIPTOR)
                        data.writeString(payload)
                        check(binder.transact(RuntimeProtocol.REQUEST, data, reply, 0))
                        reply.readException()
                        val value = reply.readString() ?: throw IllegalStateException()
                        require(value.toByteArray(Charsets.UTF_8).size <= RuntimeProtocol.MAX_BYTES)
                        JSONObject(value)
                    } finally { data.recycle(); reply.recycle() }
                } catch (_: Exception) { JSONObject(RuntimeProtocol.failure("APP_DISCONNECTED")) }
                main.post {
                    if (!closed && epoch == requestEpoch) callback(result)
                }
            }
        } catch (_: RejectedExecutionException) {
            // Lifecycle closure does not submit or replay work.
        }
    }

    private fun clearRemote() {
        deathLink?.let { (binder, recipient) ->
            try { binder.unlinkToDeath(recipient, 0) } catch (_: Exception) { }
        }
        deathLink = null
        remote = null
    }

    fun disconnect() {
        epoch++
        clearRemote()
        val previous = connection
        connection = null
        if (previous != null) try { binding.unbind(previous) } catch (_: Exception) { }
        onConnection?.invoke(false)
    }

    fun close() {
        closed = true
        disconnect()
        requests.shutdown()
        stopRequests.shutdown()
        main.removeCallbacksAndMessages(null)
        onConnection = null
    }
}
