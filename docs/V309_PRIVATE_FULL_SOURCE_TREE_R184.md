# R184 — private full-source assembly and source-repair frontier

This research lane is **about the actual Java tree**. It makes a new private source directory from a complete client-source ZIP, optionally applying independently reviewed Java replacements. It does not publish private Java code into the public repository.

## Evidence measured in this session

Uploaded third-party decompilation archive: `SpawnPk-Decompiled-main (4).zip`; its `client/src/main/java` subtree contained **1,274 Java files**. On JDK 21.0.12.1, `javac -proc:none -g:none -encoding UTF-8 -Xmaxerrs 3000` without third-party dependencies returned **2,391 errors and 9 warnings**. These numbers are for the uploaded decompilation, **not** the pinned, separately recovered private v309 tree. JDK-only missing dependencies account for many errors; this is not a vetted 2,391-item source repair backlog.

Observed first-pass compiler reasons:
- `cannot find symbol`: 1,711 diagnostic occurrences
- `package org.slf4j does not exist`: 136
- `package javax.inject does not exist`: 95
- `package com.google.inject does not exist`: 59
- `package lombok does not exist`: 54
- `LootTrackerItem` constructor argument mismatch: 32
- `package gnu.trove.f.b does not exist`: 30

The previous private subset R3 compiled **312 Java sources** from that third-party decompilation; it did not establish v309-original binary parity.

## Assembler

`tools/private_source_tree_r184.py` accepts a full private source ZIP and a separate private Java overlay ZIP. It refuses any overlay entry without a sidecar per-file reviewed approval pinned to BOTH the old Java file hash (or null for new files) and replacement Java file hash.

```powershell
python tools/private_source_tree_r184.py `
  --baseline-zip 'C:\private\SpawnPk-Decompiled-main.zip' `
  --baseline-prefix 'SpawnPk-Decompiled-main/client/src/main/java/' `
  --overlay-zip 'C:\private\verified-recovered-java.zip' `
  --overlay-prefix 'src/' `
  --approvals 'C:\private\approved-overlays.json' `
  --private-output 'C:\private\v309-r184-new-source-tree'
```

The approval JSON object maps Java-relative paths to objects containing `status: reviewed-private-recovery`, `baseline_sha256` and `replacement_sha256`. The output must not exist already, and must remain private. A sidecar manifest records the exact Java tree. No full-client compile or exact original JVM parity is asserted merely by assembling files.

The source ZIP is a **candidate** input; evidence from a decompiler is not equal to recovered original-source parity. Source files in the repository stay restricted until publication rights are settled. Use R31/R32/R33 strict bytecode gates and complete-source javac checks before replacing authoritative classes.

## Remaining full-source work

1. Replay on the actual pinned original v309 binary and authoritative private 1,279-file candidate, rather than substituting this 1,274-file third-party archive.
2. Identify genuine source failures separate from missing approved dependencies, Lombok-generated elements and related cascades.
3. Reconstruct original class and method bodies with strict JVM Code and ABI parity; make reviewed per-class source overlays.
4. Run whole-tree Java 9 build without original-JAR fallback and validate runtime entry path.
5. Confirm redistribution rights before committing original-derived full Java source to the public GitHub repository.
