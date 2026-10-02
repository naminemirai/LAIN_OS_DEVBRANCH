package dev.lain.os.runtime

import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.ScheduledThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

class RuntimePumpTest {
    @Test fun stopDuringTransitionToIdleStillSettlesCancellation() {
        val worker = ScheduledThreadPoolExecutor(1)
        val idleDecision = CountDownLatch(1)
        val releaseIdle = CountDownLatch(1)
        val cancelled = CountDownLatch(1)
        val stopRequested = AtomicBoolean(false)
        val pump = RuntimePump(worker) {
            if (stopRequested.get()) {
                cancelled.countDown()
                false
            } else {
                // The step has decided to pause. Stop arrives before it returns
                // and before the pump publishes its idle state.
                idleDecision.countDown()
                check(releaseIdle.await(5, TimeUnit.SECONDS))
                false
            }
        }
        try {
            pump.kick()
            assertTrue("Worker must reach the idle transition", idleDecision.await(5, TimeUnit.SECONDS))
            stopRequested.set(true)
            pump.kick()
            releaseIdle.countDown()
            assertTrue("Stop must settle without another request or rebind", cancelled.await(2, TimeUnit.SECONDS))
        } finally {
            releaseIdle.countDown()
            worker.shutdownNow()
            assertTrue(worker.awaitTermination(5, TimeUnit.SECONDS))
        }
    }
}
