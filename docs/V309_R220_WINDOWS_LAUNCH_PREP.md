# R220 — correct Windows rebuild / local launch handoff

The verified R219 full source package has working Java 11 bytecode but its shipped PowerShell wrappers erroneously refer to **R218** input filenames. R220 corrects the file references and output labels; this is a **packaging/script-only release, not a production Java source edit**.

Independent replay in this environment: `javac --release 11` of 1,275 actual Java files passed, producing 1,376 JVM classfiles, zero errors. Controlled 14-second virtual-display startup of the existing R219 source-built JAR with exact original-v309 local resource overlay, `spk.offlineProbe=true` and localhost game server exited by deliberate timeout, no Java exception in captured log. This is not a verified Windows login session, full network isolation or original bytecode parity.

Private ZIP `SpawnPK_v309_R220_WINDOWS_LAUNCH_PREP_PRIVATE.zip` SHA256 `21658df8be95a12b261d4f29294d6c345f470b76c29ead7c0937eb1ed619fc78`. Includes unchanged complete R219 Java source snapshot under corrected R220 filenames, source-built JAR, compile-only and runtime original non-game dependency candidates, corrected pinned Windows rebuild and local-owner resource scripts, input hashes and logs. Original font/image bytes are not shipped.

Next acceptance: run the corrected launcher with owner-local resources on Windows, capture screenshot plus stderr, verify login / local-server-only behavior; do not claim success on the basis of this virtual-display timeout.
