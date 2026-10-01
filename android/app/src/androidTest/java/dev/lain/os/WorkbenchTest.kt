package dev.lain.os

import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.click
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.*
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Test
import org.junit.runner.RunWith

/** UI acceptance cases are authored but not executed in this coding pass. */
@RunWith(AndroidJUnit4::class)
class WorkbenchTest {
    @Test fun rotationDoesNotSubmitAnotherTask() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            onView(withId(R.id.command_input)).check(matches(withText("")))
            scenario.recreate()
            onView(withId(R.id.task_title)).check(matches(withText(R.string.no_task)))
        }
    }

    @Test fun demoChoiceRequiresSeparateRunTap() {
        ActivityScenario.launch(MainActivity::class.java).use {
            onView(withText("Show battery")).perform(click())
            onView(withId(R.id.command_input)).check(matches(withText("Show battery")))
            onView(withId(R.id.task_title)).check(matches(withText(R.string.no_task)))
        }
    }

    @Test fun showsPlannerAndVerificationLimitations() {
        ActivityScenario.launch(MainActivity::class.java).use {
            onView(withText(R.string.demo_notice)).check(matches(isDisplayed()))
            onView(withText(R.string.limited_notice)).check(matches(withEffectiveVisibility(Visibility.VISIBLE)))
        }
    }
}
