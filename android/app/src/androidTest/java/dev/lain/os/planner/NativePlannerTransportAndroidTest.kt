package dev.lain.os.planner

import android.Manifest
import android.content.Context
import android.security.NetworkSecurityPolicy
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class NativePlannerTransportAndroidTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()

    @Test fun appRequestsInternetPermissionForPlannerTransport() {
        val permissions = context.packageManager
            .getPackageInfo(context.packageName, 0x00001000)
            .requestedPermissions
            ?.toSet()
            .orEmpty()
        assertTrue(Manifest.permission.INTERNET in permissions)
    }

    @Test fun appDoesNotGloballyPermitCleartextTraffic() {
        assertFalse(NetworkSecurityPolicy.getInstance().isCleartextTrafficPermitted)
    }
}
