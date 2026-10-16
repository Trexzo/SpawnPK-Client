# R211 — full Java 11 source compilation of private v309 client: PASS

## Exact original dependency recovery

A Library-provided v309 client JAR, `client(20261015-104312).jar`, matched the original pinned SHA-256 **`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`**. Its ~9,334 non-game classfiles were isolated from all `rs/` game classes into a private runtime-only library JAR. Crucially this is **v309**, not the separate v382 test-distribution binary.

The original obfuscated Trove dependencies contain class/package collisions such as `gnu/trove/f.class` vs `gnu/trove/f/b/cc.class`; javac chooses a class name where a source import requires a package. Six ancestor classfiles plus one `com/google/c/c.class` were excluded from the **compile-only** binary classpath, while the complete non-game library JAR was kept for runtime. No game `rs/` binary is in either shared classpath.

## Actual source repairs and full compiler result

Starting with private R208 source (1,274 Java files), recovered these integrated changes:

- `rs/plugins/loottracker/LootHistoryStore.java`: mapped unrelocated Gson API to authenticated original v309 obfuscated `com.google.c.l/r` classes; isolated runtime probes verified `.f()` gives pretty printing and `.h()` disables HTML escaping; equivalent parse/write/annotation interfaces.
- `rs/plugins/configs/ConfigPanel.java`: replace missing Commons array index helper with equivalent Java `Arrays.asList(...).indexOf(...)`.
- `rs/model/anim/BonePoseTransform.java`: adapt original v309 quaternion/matrix constructor to the semantic `rs.io.Packet` interface via real source bridge `com.a.b.a.MatrixPacketAdapter.java`, without loading game binary `rs.x.e` in production.
- `rs/cache/osrs/util/OsrsMapDependencyScanner.java`: handle two real checked `IOException` paths explicitly and report unreadable OSRS cache payloads instead of compiler failure.

All **1,275** private Java files (original 1,274 plus one matrix bridge) compiled together under `javac --release 11 -proc:none -g:none -encoding UTF-8` with exit code **0**, **zero compiler errors**, generating **1,376 JVM .class files**. Generated source-built JAR SHA-256: `f138dc1f2ddeb7ba19c370f7ef1de6f578a90df4b11e8af8d44ef8b322612cdc`. This is genuine full-source build acceptance. It is **NOT** complete original-v309 classfile equivalence or a verified live GUI launch.

## Phase 4 verification

Against the self-contained source-built JAR plus **non-`rs/`** runtime dependency JAR:

- **9 of 10 headless offline client checks passed**: server-target configuration, packet capture, plugin discovery, inventory presets, inventory overrides, drop-table store, item search dialog, loot-history persistence, and loot-packet codec.
- **LootPanelCheck failed**, ultimately indicating UI visual/asset differences; the generated artifact intentionally excludes the original font and image resources.
- In a **separate parity-only test**, `MatrixPacketAdapter` was compared with the exact original v309 matrix constructor: **1,000 randomized samples, 16,000 float components and packet read cursors matched**.
- `jdeps --multi-release 11 --missing-deps` against the complete non-game runtime library yielded no missing-dependency output.
- The production GUI launcher was **not** run, to avoid unapproved live-server interaction and to keep original font files private.

## Private deliverable

`SpawnPK_v309_R211_INTEGRATED_SOURCE_BUILD_PRIVATE.zip` SHA-256 `6785b27c3dd7cd9658dc3adc43938ba919009a15907e1292e3f29d5001bd8841`. Contains full source, compiled source-built JAR, compile-only and runtime original-version non-game libraries, complete source checksums, Windows rebuild PowerShell, compiler log, and test evidence. No original full client binary, original `rs/` game classfiles as a fallback dependency, or font files are distributed in the bundle.

**Acceptance:** Full-source compilation YES; limited offline runtime checks YES with one failing UI check; complete GUI launch and original binary parity NOT YET.
