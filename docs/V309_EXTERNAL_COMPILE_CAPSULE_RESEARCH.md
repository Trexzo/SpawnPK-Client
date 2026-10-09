# v309 external namespace compile capsule (research only)

The independent candidate v309 Java tree has **1,270** Java sources but is not a certified clean-source rebuild. Its original build.gradle refers to the missing vendored-unidentified.jar. The exact original v309 client embeds **9,333 candidate external-namespace class entries** under com/, org/, gnu/, javax/, and net/. The private local tool derives a filtered compile-only JAR from these, explicitly excluding rs/, tools/, a/, and source-owned com/apple/eawt/ classes. It also extracts SHA-pinned Lombok 1.18.32 from the independent deobfuscation tool archive.

**Critical limit:** Namespace is not definitive third-party provenance. Some non-rs classes might be project-owned. The output is provisional dependency research, NOT full verified zero-project-binary fallback or Source M1 dependency authority. The binary JARs MUST stay outside GitHub.

## Local invocation

Use exact uploaded private files, Python 3.11+ and a fresh nonexistent output directory outside the repo:

    $env:PYTHONPATH = (Join-Path (Get-Location) 'src')
    python -m spk_recovery.v309_external_compile_capsule --original-v309 'C:\private\v309.jar' --source-zip 'C:\private\source.zip' --deob-tool-zip 'C:\private\deob.zip' --out-dir 'C:\private\v309-capsule-new'

Defaults pin all three original ZIP/JAR SHA256s and exactly 9,333 qualifying class entries. The tool refuses changed inputs, unsafe archive paths, missing Lombok, unexpected class counts and existing outputs. Result JAR ordering and timestamps are deterministic; the sanitized report contains no proprietary class names or CP contents.

## Actual source compile results (2026-10-09)

Using a private filtered compile-only namespace capsule without original rs project bytecode, the isolated Java 11 source preflight advanced from **18/26 to 20/26** by compiling ClientShutdown and PluginChanged.

The Lombok annotation processor will not necessarily process Java files that javac implicitly loads through sourcepath. Explicitly including the relevant annotated source companions produced another **3 passes**, bringing the total to **23/26**:

- EventBus.java: explicitly include Class87.java and rs/util/Class85.java.
- DeferredEventBus.java: explicitly include Class87.java and rs/util/Class85.java.
- TextPopupWindow.java: explicitly include PlainLogHandler.java and LoginLogHandler.java.

The remaining blocked roots are OsrsMapDependencyScanner, EntityInteraction and NpcSpawned. Their source closure enters unresolved project Java references; no placeholder stubs, source rewrites or original rs project-class fallback were used.

Among five newly compiling anchors, ClientShutdown and DeferredEventBus have identical raw JVM field+method descriptor multisets versus the original v309 classfiles. PluginChanged, EventBus and TextPopupWindow compile but still show renamed/relocated type descriptors needing independent source-to-original proof before any normalization or acceptance.

The candidate workspace holds private SOURCE-NONPROJECT-DEPENDENCY-PREFLIGHT.json and SOURCE-DEPENDENCY-RESTORATION-PROVENANCE.json. The original source files remain unchanged. There is NO entire-project compilation PASS, no full class-set proof, and no new accepted class/member/field identity.

Canonical v309 stays ACCEPTED_INCOMPLETE (143 unresolved/26 descriptor-blocked); exact v308 Source Milestone 1 is separately not yet published under recovered-source/v308/.
