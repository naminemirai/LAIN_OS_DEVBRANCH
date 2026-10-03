package dev.lain.os

import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.TextView
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import dev.lain.os.databinding.ActivityMainBinding
import dev.lain.os.planner.PlannerConnectionStatus
import dev.lain.os.planner.PlannerProfileDraft
import dev.lain.os.planner.PlannerSettingsManager
import dev.lain.os.ui.WorkbenchState
import dev.lain.os.ui.WorkbenchViewModel

class MainActivity : AppCompatActivity() {
    private lateinit var ui: ActivityMainBinding
    private lateinit var plannerSettings: PlannerSettingsManager
    private val model: WorkbenchViewModel by viewModels()
    private var lastHistory = ""
    private var lastResults: String? = null
    private var plannerIds = emptyList<String>()
    private var plannerEditingId: String? = null
    private var renderingPlanner = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ui = ActivityMainBinding.inflate(layoutInflater)
        setContentView(ui.root)
        ViewCompat.setOnApplyWindowInsetsListener(ui.root) { view, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        plannerSettings = PlannerSettingsManager(this)
        setupPlannerSettings()
        ui.runButton.setOnClickListener { model.run(ui.commandInput.text.toString()) }
        ui.stopButton.setOnClickListener { model.stop() }
        ui.approveButton.setOnClickListener { model.approve() }
        ui.resumeButton.setOnClickListener { model.resume() }
        ui.reconnectButton.setOnClickListener { model.reconnect() }
        val demos = listOf("Create demo file", "Show battery", "Show demo toast", "Vibrate briefly", "Copy demo text", "Share demo text")
        demos.forEach { command ->
            val button = Button(this).apply {
                text = command
                isAllCaps = false
                setOnClickListener { ui.commandInput.setText(command); ui.commandInput.setSelection(command.length) }
            }
            ui.demoCommands.addView(button)
        }
        model.state.observe(this) { render(it) }
    }

    override fun onStart() { super.onStart(); model.attach() }
    override fun onStop() { model.detach(isChangingConfigurations); super.onStop() }

    private fun setupPlannerSettings() {
        ui.plannerModeSelector.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            listOf(getString(R.string.planner_mode_cloud), getString(R.string.planner_mode_local)),
        )
        ui.plannerProfileSelector.onItemSelectedListener =
            object : android.widget.AdapterView.OnItemSelectedListener {
                override fun onItemSelected(
                    parent: android.widget.AdapterView<*>?,
                    view: View?,
                    position: Int,
                    id: Long,
                ) {
                    if (!renderingPlanner && position in plannerIds.indices) {
                        plannerEditingId = plannerIds[position].takeUnless { value -> value == "offline-demo" }
                        renderPlannerForm(plannerIds[position])
                    }
                }
                override fun onNothingSelected(parent: android.widget.AdapterView<*>?) = Unit
            }
        ui.plannerNewButton.setOnClickListener {
            plannerEditingId = null
            ui.plannerNameInput.setText("")
            ui.plannerEndpointInput.setText("")
            ui.plannerModelInput.setText("")
            ui.plannerCredentialInput.setText("")
            ui.plannerModeSelector.setSelection(0)
            setPlannerEditorEnabled(true)
            ui.plannerStatus.text = getString(R.string.planner_new_ready)
        }
        ui.plannerSaveButton.setOnClickListener { savePlannerProfile() }
        ui.plannerSelectButton.setOnClickListener { selectedPlannerId()?.let(::selectPlannerProfile) }
        ui.plannerRemoveCredentialButton.setOnClickListener {
            plannerEditingId?.let { id ->
                runPlannerMutation {
                    plannerSettings.removeCredential(id)
                    refreshPlannerSettings(id)
                    getString(R.string.planner_credential_removed)
                }
            }
        }
        ui.plannerDeleteButton.setOnClickListener {
            plannerEditingId?.let { id ->
                runPlannerMutation {
                    plannerSettings.delete(id)
                    plannerEditingId = null
                    refreshPlannerSettings()
                    getString(R.string.planner_deleted)
                }
            }
        }
        ui.plannerTestButton.setOnClickListener {
            selectedPlannerId()?.let { id ->
                runPlannerMutation {
                    val status = plannerSettings.testConnection(id)
                    refreshPlannerSettings(id)
                    getString(R.string.planner_test_result, statusLabel(status))
                }
            }
        }
        refreshPlannerSettings()
    }

    private fun selectedPlannerId(): String? =
        ui.plannerProfileSelector.selectedItemPosition
            .takeIf { position -> position in plannerIds.indices }
            ?.let { position -> plannerIds[position] }

    private fun savePlannerProfile() {
        val mode = if (ui.plannerModeSelector.selectedItemPosition == 1) "local" else "cloud"
        runPlannerMutation {
            val id = plannerSettings.save(
                PlannerProfileDraft(
                    profileId = plannerEditingId,
                    name = ui.plannerNameInput.text.toString().trim(),
                    mode = mode,
                    baseUrl = ui.plannerEndpointInput.text.toString().trim(),
                    model = ui.plannerModelInput.text.toString().trim(),
                    credential = ui.plannerCredentialInput.text.toString().takeIf { value -> value.isNotBlank() },
                )
            )
            ui.plannerCredentialInput.setText("")
            plannerEditingId = id
            refreshPlannerSettings(id)
            getString(R.string.planner_saved)
        }
    }

    private fun selectPlannerProfile(id: String) {
        runPlannerMutation {
            plannerSettings.select(id)
            refreshPlannerSettings(id)
            getString(R.string.planner_selected)
        }
    }

    private fun runPlannerMutation(block: () -> String) {
        ui.plannerStatus.text = try {
            block()
        } catch (_: Exception) {
            getString(R.string.planner_invalid)
        }
    }

    private fun refreshPlannerSettings(preferredId: String? = null) {
        val snapshot = plannerSettings.snapshot()
        val active = snapshot.profiles.first { profile -> profile.id == snapshot.activeProfileId }
        ui.plannerIdentity.text = getString(
            R.string.planner_identity,
            active.mode.replaceFirstChar { char -> char.uppercase() },
            active.model,
        )
        plannerIds = snapshot.profiles.map { profile -> profile.id }
        val labels = snapshot.profiles.map { profile ->
            if (profile.id == snapshot.activeProfileId) "● " + profile.name else profile.name
        }
        renderingPlanner = true
        ui.plannerProfileSelector.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            labels,
        )
        val selected = preferredId?.takeIf { value -> value in plannerIds } ?: snapshot.activeProfileId
        val index = plannerIds.indexOf(selected).coerceAtLeast(0)
        ui.plannerProfileSelector.setSelection(index)
        renderingPlanner = false
        plannerEditingId = selected.takeUnless { value -> value == "offline-demo" }
        renderPlannerForm(selected)
    }

    private fun renderPlannerForm(profileId: String) {
        val profile = plannerSettings.snapshot().profiles.first { value -> value.id == profileId }
        val editable = profile.mode != "demo"
        ui.plannerNameInput.setText(profile.name)
        ui.plannerEndpointInput.setText(profile.baseUrl)
        ui.plannerModelInput.setText(profile.model)
        ui.plannerCredentialInput.setText("")
        ui.plannerCredentialInput.hint = if (profile.credentialSaved) {
            getString(R.string.planner_credential_saved)
        } else {
            getString(R.string.planner_credential_hint)
        }
        if (editable) ui.plannerModeSelector.setSelection(if (profile.mode == "local") 1 else 0)
        setPlannerEditorEnabled(editable)
        ui.plannerSelectButton.isEnabled = true
        ui.plannerTestButton.isEnabled = true
    }

    private fun setPlannerEditorEnabled(enabled: Boolean) {
        ui.plannerModeSelector.isEnabled = enabled
        ui.plannerNameInput.isEnabled = enabled
        ui.plannerEndpointInput.isEnabled = enabled
        ui.plannerModelInput.isEnabled = enabled
        ui.plannerCredentialInput.isEnabled = enabled
        ui.plannerSaveButton.isEnabled = enabled
        ui.plannerRemoveCredentialButton.isEnabled = enabled && plannerEditingId != null
        ui.plannerDeleteButton.isEnabled = enabled && plannerEditingId != null
    }

    private fun statusLabel(status: PlannerConnectionStatus): String = when (status) {
        PlannerConnectionStatus.OFFLINE_DEMO -> "Offline Demo"
        PlannerConnectionStatus.CONNECTED -> "Connected"
        PlannerConnectionStatus.AUTHENTICATION_REJECTED -> "Authentication rejected"
        PlannerConnectionStatus.MODEL_UNAVAILABLE -> "Model unavailable"
        PlannerConnectionStatus.ENDPOINT_UNREACHABLE -> "Endpoint unreachable"
        PlannerConnectionStatus.TLS_FAILURE -> "TLS failure"
        PlannerConnectionStatus.TIMED_OUT -> "Timed out"
        PlannerConnectionStatus.RESPONSE_UNSUPPORTED -> "Response unsupported"
        PlannerConnectionStatus.MISSING_CREDENTIAL -> "Missing credential"
        PlannerConnectionStatus.UNAVAILABLE -> "Unavailable"
    }

    private fun render(state: WorkbenchState) {
        val session = state.session
        val active = session?.optBoolean("active") == true
        val recovery = session?.optBoolean("recovery_required") == true
        ui.connection.text = getString(when {
            state.ready -> R.string.connected
            state.connected -> R.string.starting
            else -> R.string.disconnected
        })
        ui.reconnectButton.visibility = if (!state.connected || state.startupFailed) View.VISIBLE else View.GONE
        ui.message.text = state.message
        ui.runButton.isEnabled = state.ready && !state.pending && !active && !recovery
        ui.stopButton.isEnabled = state.connected && (active || recovery)
        ui.commandInput.isEnabled = !state.pending && !active
        for (i in 0 until ui.demoCommands.childCount) ui.demoCommands.getChildAt(i).isEnabled = !active && !state.pending
        ui.taskTitle.text = session?.optString("label") ?: getString(R.string.no_task)
        val status = session?.optString("status") ?: "idle"
        ui.taskStatus.text = if (session?.optBoolean("stop_requested") == true)
            getString(R.string.stopping) else status.replace('_', ' ').uppercase()
        ui.progress.visibility = if (active && status != "paused_confirmation" && !recovery) View.VISIBLE else View.GONE
        ui.resumeButton.visibility = if (recovery && status != "paused_confirmation") View.VISIBLE else View.GONE
        ui.resumeButton.isEnabled = state.ready && !state.pending
        val approval = session?.optJSONObject("approval")
        ui.approvalCard.visibility = if (approval != null) View.VISIBLE else View.GONE
        ui.approveButton.isEnabled = state.ready && !state.pending
        ui.approvalText.text = approval?.let { value ->
            value.optString("type") + "\n" + value.optJSONObject("arguments")?.toString(2) +
                "\n\n" + getString(R.string.approval_explanation)
        } ?: ""
        val actions = session?.optJSONArray("actions")
        val resultsKey = session?.optString("session_id") + actions?.toString()
        if (resultsKey != lastResults) {
            lastResults = resultsKey
            ui.results.removeAllViews()
            if (actions == null || actions.length() == 0) {
                ui.results.addView(resultText(getString(R.string.no_results)))
            } else for (i in 0 until actions.length()) {
                val action = actions.getJSONObject(i)
                val detail = action.optJSONObject("details")
                val text = action.optString("type") + "\n" +
                    "Execution: " + action.optString("status") + "  ·  Verification: " +
                    action.optString("verification") +
                    if (detail != null && detail.length() > 0) "\n" + detail.toString(2) else ""
                ui.results.addView(resultText(text))
            }
        }
        val historyKey = state.history.toString() + active
        if (historyKey != lastHistory) {
            lastHistory = historyKey
            ui.history.removeAllViews()
            if (state.history.length() == 0) ui.history.addView(resultText(getString(R.string.no_history)))
            for (i in 0 until state.history.length()) {
                val entry = state.history.getJSONObject(i)
                ui.history.addView(Button(this).apply {
                    text = entry.optString("label") + "\n" + entry.optString("status").replace('_', ' ')
                    isAllCaps = false
                    isEnabled = !active
                    setOnClickListener { model.select(entry.getString("session_id")) }
                })
            }
        }
    }

    private fun resultText(value: String) = TextView(this).apply {
        text = value
        setTextColor(getColor(R.color.text_secondary))
        setTextIsSelectable(true)
        setPadding(0, 12, 0, 20)
        textSize = 13f
    }
}
