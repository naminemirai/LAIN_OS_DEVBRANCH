# Native APK physical acceptance

This checklist validates the new standalone APK. Prior Termux acceptance and
emulator results do not establish physical toast, vibration, clipboard, or
chooser behavior for these native adapters.

Install the current debug APK, package `dev.lain.os`, version `0.1.4-interface`
(code 5). Record the APK SHA-256, Android version, device model, and date.
The APK uses an offline demo planner and needs no provider credentials.

1. Open LAIN_OS. Wait for “Local runtime ready”; Run must remain disabled until
   initialization and saved-state inspection finish.
2. Select **Show battery**, then Run. Expect execution success, verification
   PASSED, and structured approved fields including percentage.
3. Run **Show demo toast**. Observe the toast physically. Expect execution
   success and LIMITED verification; LIMITED alone is not evidence of the toast.
4. Run **Vibrate briefly**. Observe vibration physically on supported hardware.
   Expect execution success and LIMITED; a device without a vibrator should
   safely report unsupported.
5. Run **Copy demo text**. Expect success and PASSED when Android permits the
   immediate private comparison. Restricted clipboard access may produce a
   limited result; record it rather than claiming a match. No clipboard getter
   or private observed clipboard value should appear in results/history.
6. Run **Share demo text**. Before approval, expect PAUSED CONFIRMATION, redacted
   content, and no chooser. Approve exactly that stored action. Observe the
   chooser, then dismiss it without selecting a destination or sending anything.
   Expect LIMITED, not independent proof of delivery.
7. Start another share task, leave it unapproved, and tap Stop. Expect CANCELLED
   with no chooser. Also repeat several times, tapping Stop as the task reaches
   its confirmation pause; cancellation must settle without a second Stop or
   reconnect. Rotate the app and confirm no duplicate task is submitted.
8. Start a share task and leave it paused. Terminate only this app's processes
   through Android's app controls (or `adb shell am force-stop dev.lain.os`).
   Reopen LAIN_OS. No chooser or automatic execution should occur. Inspect the
   durable task, then Stop it or explicitly approve its fresh stored action;
   dismiss any chooser without sending. Record recovery behavior.

Report each step as pass/fail/unsupported with actual displayed execution and
verification states. Include any startup, disconnect, or crash symptoms. Never
paste private clipboard contents, credentials, or sensitive logs into the report.

The debug build and portable tests are separate evidence. Physical acceptance
remains open until physical observations are recorded for the final APK.
