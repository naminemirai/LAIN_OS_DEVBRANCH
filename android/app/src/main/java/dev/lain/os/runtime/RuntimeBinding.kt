package dev.lain.os.runtime

import android.content.Context
import android.content.Intent
import android.content.ServiceConnection

/** Trusted UI construction only; never selected through the action protocol. */
interface RuntimeBinding {
    fun bind(connection: ServiceConnection): Boolean
    fun unbind(connection: ServiceConnection)
}

internal class AndroidRuntimeBinding(context: Context) : RuntimeBinding {
    private val context = context.applicationContext
    override fun bind(connection: ServiceConnection): Boolean =
        context.bindService(Intent(context, RuntimeService::class.java), connection, Context.BIND_AUTO_CREATE)
    override fun unbind(connection: ServiceConnection) = context.unbindService(connection)
}
