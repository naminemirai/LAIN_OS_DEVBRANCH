package dev.lain.os

import android.os.SystemClock
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.util.UUID
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PlannerSettingsUiTest {
    private fun await(
        scenario: ActivityScenario<MainActivity>,
        condition: (MainActivity) -> Boolean,
    ) {
        val deadline = SystemClock.elapsedRealtime() + 60000
        while (SystemClock.elapsedRealtime() < deadline) {
            var matched = false
            scenario.onActivity { matched = condition(it) }
            if (matched) return
            SystemClock.sleep(100)
        }
        fail("Timed out waiting for planner settings state")
    }

    private fun click(scenario: ActivityScenario<MainActivity>, viewId: Int) {
        scenario.onActivity {
            check(it.findViewById<View>(viewId).performClick())
        }
    }

    private fun enter(scenario: ActivityScenario<MainActivity>, viewId: Int, value: String) {
        scenario.onActivity {
            it.findViewById<EditText>(viewId).setText(value)
        }
    }

    private fun sessions(activity: MainActivity): Set<String> =
        java.io.File(activity.filesDir, "lain/sessions").listFiles()
            ?.filter { it.isDirectory }
            ?.map { it.name }
            ?.toSet()
            ?: emptySet()

    private fun visibleText(view: View): String {
        val own = if (view is TextView) view.text?.toString().orEmpty() else ""
        if (view !is ViewGroup) return own
        return buildString {
            append(own)
            for (index in 0 until view.childCount) append(visibleText(view.getChildAt(index)))
        }
    }

    @Test fun plannerSettingsScreenPersistsSelectionAndNeverCreatesDiagnosticSession() {
        val suffix = UUID.randomUUID().toString().take(8)
        val name = "UI Cloud " + suffix
        val firstSecret = "ui-secret-one-" + suffix
        val secondSecret = "ui-secret-two-" + suffix

        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            click(scenario, R.id.planner_new)
            enter(scenario, R.id.planner_name, name)
            enter(scenario, R.id.planner_endpoint, "https://api.example.invalid/v1")
            enter(scenario, R.id.planner_model, "model-a")
            enter(scenario, R.id.planner_credential, firstSecret)
            click(scenario, R.id.planner_save)
            click(scenario, R.id.planner_select)

            await(scenario) {
                it.findViewById<TextView>(R.id.active_planner).text.toString()
                    .contains(name) &&
                    it.findViewById<TextView>(R.id.active_planner).text.toString().contains("model-a")
            }
            scenario.onActivity {
                val rendered = visibleText(it.findViewById(R.id.workbench_root))
                assertFalse(rendered.contains(firstSecret))
            }

            enter(scenario, R.id.planner_credential, secondSecret)
            click(scenario, R.id.planner_save)
            scenario.onActivity {
                val rendered = visibleText(it.findViewById(R.id.workbench_root))
                assertFalse(rendered.contains(secondSecret))
                assertEquals("", it.findViewById<TextView>(R.id.planner_credential).text.toString())
            }

            scenario.recreate()
            await(scenario) {
                it.findViewById<TextView>(R.id.active_planner).text.toString()
                    .contains(name) &&
                    it.findViewById<TextView>(R.id.active_planner).text.toString().contains("model-a")
            }

            var before = emptySet<String>()
            scenario.onActivity { before = sessions(it) }
            click(scenario, R.id.planner_remove_credential)
            click(scenario, R.id.planner_test)
            await(scenario) {
                it.findViewById<TextView>(R.id.planner_status).text.toString()
                    .contains("missing credential")
            }
            scenario.onActivity {
                assertEquals(before, sessions(it))
                assertTrue(
                    it.findViewById<TextView>(R.id.active_planner).text.toString()
                        .contains("model-a")
                )
            }

            click(scenario, R.id.planner_delete)
            await(scenario) {
                it.findViewById<TextView>(R.id.active_planner).text.toString()
                    .contains("Offline Demo · offline_demo")
            }
        }
    }
}
