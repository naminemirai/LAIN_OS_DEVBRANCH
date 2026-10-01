package dev.lain.os

import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.TextView
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import dev.lain.os.databinding.ActivityMainBinding
import dev.lain.os.ui.WorkbenchState
import dev.lain.os.ui.WorkbenchViewModel

class MainActivity : AppCompatActivity() {
    private lateinit var ui: ActivityMainBinding
    private val model: WorkbenchViewModel by viewModels()
    private var lastHistory = ""
    private var lastResults: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ui = ActivityMainBinding.inflate(layoutInflater)
        setContentView(ui.root)
        ViewCompat.setOnApplyWindowInsetsListener(ui.root) { view, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
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
        ui.approvalText.text = approval?.let {
            "${it.optString("type")}\n${it.optJSONObject("arguments")?.toString(2)}\n\n${getString(R.string.approval_explanation)}"
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
                val text = "${action.optString("type")}\n" +
                    "Execution: ${action.optString("status")}  ·  Verification: ${action.optString("verification")}" +
                    if (detail != null && detail.length() > 0) "\n${detail.toString(2)}" else ""
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
                    text = "${entry.optString("label")}\n${entry.optString("status").replace('_', ' ')}"
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
