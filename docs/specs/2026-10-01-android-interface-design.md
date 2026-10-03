# LAIN_OS Android interface — approved scope

This specification defines the first standalone APK interface for the existing LAIN_OS runtime. Voice, media, workflow graphs, and YouTube integration are later product stages.

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

Verification must distinguish source-level tests, APK assembly, emulator/instrumentation results, and physical-device acceptance. A successful build alone is not installed-device acceptance. Production release requires release signing, current security verification, and the documented device acceptance gates. Provider credentials are never bundled into the application.
