# R123 — private multi-module SpawnPK source intake

## What the inspected external archive actually contributes

An externally supplied multi-module source ZIP was inspected **read-only** and compared by per-file SHA-256 against a separately preserved private v309 decompiled candidate. Do not mistake this for a new original v309 reconstruction.

Private uploaded ZIP SHA-256: `2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536`. Private earlier source-candidate ZIP SHA-256: `d3e75c0fcebb2026620cdf4d298f2d18eff83f5727e5221ed3b7f482d113aaf5`.

The current archive has **1,551 total Java files**. Its actual **1,271 client main-source Java files** share **1,270 paths** with the earlier candidate; **1,269 shared files are byte-identical**. One changed shared Java file is `rs/Configuration.java` (local host/port system-property overrides); one addition is `rs/tools/ClientServerTargetCheck.java`. The remaining **31 Java-looking files under client resources** are bundled `javax.annotation` classes, not additional client main-source units.

**New bounded packet evidence:** the external server's 257-value outgoing packet-length array is **257/257 equal** to the same ZIP's decompiled client `incomingLengths` assignments. R123 rechecks every ordinal, requires exactly 257 definitions on each side, and reports mismatches without accepting original-v309 parity. The original v309 JAR uses separate obfuscated type identities; this remains **internal source consistency only**.\n\nThe genuinely new separate server source area contains **197 main Java files** (server application 1, API 20, core 175, plugins package marker 1) and **52 test Java files** (server 1, core 51). Server domains include networking/ISAAC/framing, login and throttling, cache and definitions, tick phases, world/entity and map/path systems, player/NPC synchronization, event bus, account persistence, and plugin infrastructure. The ZIP also contains detailed client-side protocol and synchronization research and Kotlin scripting resources. These domains indicate useful *implementation candidates*, **not proof of parity with the original unavailable SpawnPK server**.

The client ZIP declares build number 309; that is source text, **not** exact original-v309 bytecode acceptance. The available source is a renamed/recompiled decompiler baseline; don't substitute this package for the independent original-derived `rs/f/a` work or mark any of R119/R120 accepted solely because this source tree exists.

## Build/behavior cautions

- The archive contains a Gradle launcher script but **no `gradle/wrapper/gradle-wrapper.jar`**, so the checked-in wrapper alone is not complete.
- The client Gradle project declares `client/libs/vendored-unidentified.jar`, but **that binary is absent**. Do not claim complete offline client buildability or silently use the original client JAR as a fallback.
- The client source module targets Java 11; the separate original-v309 owner recovery gates intentionally use `javac --release 9`. A successful Java11 build would not establish original Java9 classfile parity.
- The source supports command-line host and port overrides, but its default host selection still includes a live production hostname. Do **not** run this candidate without airgap/proxy policy review and local network controls.
- The server is an **independently written emulator/reimplementation**, not original server source. Its crypto/protocol assertions are hypotheses grounded in its decompiled client and docs and require comparison against the exact v309 original and the existing `Trexzo/SpawnPK-RE` server before adoption.
- The supplied ZIP contains native `.dll`, `.so`, `.dylib` resource files; **nothing in this intake executes or loads them**.
- The archive's Kotlin plugin scripts and Gradle tasks were neither executed nor imported into public GitHub.

## R123 gate

`spk_recovery.private_source_archive_delta_r123` requires two private ZIPs with a single root folder. It checks duplicate entries, path traversal, ZIP symlinks, size ceilings and archive counts. It compares SHA-256 of each Java source file, identifies only changed/new/removed paths, counts separately implemented server source and tests by Gradle module, and checks the presence of essential build files.

Private command:

```text
python -m spk_recovery.private_source_archive_delta_r123 UPLOADED_ARCHIVE.zip BASELINE_SOURCE.zip NEW_PRIVATE_REPORT.json
```

The destination must not exist. The output contains only aggregate counts, digest pins, and a short path-delta inventory. It does **not** copy source into the repository, run the application, execute untrusted build logic, compare complete original-v309 classfile semantics, or certify any original server implementation.

## Intended next use

Retain the uploaded server tree and protocol documents as **private read-only donor evidence**. First compare packet contracts, ownership and behavior tests with `Trexzo/SpawnPK-RE` and the pinned original-v309 client. Port only proven, nonconflicting subsystems via reviewed, narrowly scoped server PRs; preserve existing LocalLab behavior. For original client recovery, finish R122's large-method assembly then R120 source-witness and R119 exact-original parity.

**No supplied client/server Java, JAR, original client classfile or native binary is included in this public PR.**
