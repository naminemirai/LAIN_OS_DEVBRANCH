# LAIN_OS Android interface — approved scope

The owner approved a GUI packaged as an APK for the existing LAIN_OS runtime on
2026-10-01. This is the first slice of the voice-agent brief; voice, media,
workflow graphs, and YouTube integration remain outside this slice.

Build a standalone Kotlin/AndroidX application embedding Python locally. It must
not depend on Termux, an external Python installation, or a separate server.
Provide command entry, progress/results, exact-action confirmation, session
history, and a Stop button. Preserve the portable Python CLI and existing trusted
validation → policy → deterministic execution → verification → audit path.

Use a non-exported runtime service in a private application process, same-UID
Binder authentication, bounded typed JSON control messages, app-private scoped
storage, and one active run. Models cannot invoke arbitrary Python functions,
grant approval, change policy, or select executors. Exact approvals refer to the
stored action and request identity, not text copied back from a UI or planner.

The initial offline demo planner must be visibly labeled and accept only its
documented demonstration commands. Arbitrary natural-language planning remains
unavailable until a reviewed embedded planner adapter is configured. Unsupported
Android operations fail closed until their native adapters are implemented.

Stop immediately acknowledges the request, prevents further actions, and records
the actual settled outcome of an action already in flight. It does not claim
rollback or guarantee that an external effect was prevented. Owner inspection
and Stop must remain available while the worker holds its execution lease.

The owner paused verification runs for this coding pass. Tests may be authored,
but tests, security verification, CI, and installed-device acceptance are deferred.
APK assembly is permitted to produce the requested artifact when tooling and
network access permit it. A successful build is not installed-device acceptance.
No public release, merge, deployment, upload, paid service, or provider credential
provisioning is authorized. Do not claim readiness from unrun acceptance checks.
