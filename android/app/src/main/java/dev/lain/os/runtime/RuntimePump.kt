package dev.lain.os.runtime

import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit
import java.util.concurrent.RejectedExecutionException

/** Schedules bounded runtime steps on the service's single worker. */
internal class RuntimePump(
    private val worker: ScheduledExecutorService,
    private val advance: () -> Boolean,
) {
    // Accessed only on the single worker, including transitions back to idle.
    private var pumping = false

    fun kick() {
        try {
            // Queue every wake-up before deciding whether a pump is active.
            // A Stop arriving during the last step runs after its idle transition.
            worker.execute {
                if (!pumping) {
                    pumping = true
                    advanceOnce()
                }
            }
        } catch (_: RejectedExecutionException) {
            // A destroyed service cannot start another pump or replay work.
        }
    }

    private fun advanceOnce() {
        try {
            if (advance() && !worker.isShutdown) {
                worker.schedule({ advanceOnce() }, 25, TimeUnit.MILLISECONDS)
            } else pumping = false
        } catch (_: Exception) {
            pumping = false
            // Preserve durable state for explicit inspection/recovery. No retry loop.
        }
    }
}
