package dev.lain.os.runtime

import android.os.Binder
import android.os.Process
import org.json.JSONObject

object RuntimeProtocol {
    const val DESCRIPTOR = "dev.lain.os.runtime.Control.v1"
    const val REQUEST = android.os.IBinder.FIRST_CALL_TRANSACTION
    const val MAX_BYTES = 65536
    val readCommands = setOf("inspect", "sessions", "stop")
    val writeCommands = setOf("start", "approve", "resume")

    fun enforceCaller(callingUid: Int = Binder.getCallingUid(), ownUid: Int = Process.myUid()) {
        if (callingUid != ownUid) throw SecurityException("Private application control")
    }

    fun request(command: String, arguments: JSONObject): String =
        JSONObject().put("version", 1).put("command", command).put("arguments", arguments).toString()

    fun failure(code: String): String = JSONObject().put("version", 1).put("ok", false)
        .put("error", code).put("message", "Runtime unavailable; inspect session state before retrying.").toString()
}
