# R316 — genuine movement chain audited; mock-server fixture corrected

**27 October 2026.** Verified from owner-private 1,277-source reconstructed SpawnPK v309 client; original R311 production JAR untouched. Full original-v311 JVM bytecode recovery is a separate workstream.

## R315 movement failure was two distinct fixture conditions

1. The original R315 real AWT click at desktop (449,438) traversed **menu opcode516 → Scene.requestPick → rendered tile hit → Client.method3573**. Tile **(49,46)**, start **(48,48)**, original synthetic collision flags **start 0x200000 / target 0x200100**. Pathfinding reported an unreachable route; no movement packet was encoded for that click.
2. A later R316 GUI click sweep showed the client **could emit real ISAAC-encoded opcode164** for other tiles. The historical local test server successfully decoded three walk packets but computed the wrong local target: it subtracted hard-coded **(3152,3152)** although it had sent region `normal_region(420,596)`. Correct scene base is **(3312,4720)**. Therefore world packet target **(3360,4768)** mapped to **(48,48)**, not erroneous **(208,1616)**. The three old packets were to the starting tile (no displacement) and remain **NOT ACCEPTED** as real movement.

No speculative patch to the production client's movement algorithm was necessary.

## R316 controlled authentic client movement result

The real recovered source-built v309 client, owner-original 10,772-file cache and resource JAR ran in an isolated Linux/Xvfb GUI with a **127.0.0.1-only** ISAAC test server. A *diagnostic-only* Java overlay was compiled with Java11-target from the exact pinned R315 client/scene source, without modifying the actual production JAR.

The overlay has explicit OFF-by-default properties `spk.offlineProbeR316=true` for stage logs and `spk.syntheticClearSceneCollisionR316=true` for a synthetic local 45–51 tile corridor that clears the **0x200000** test collision flag. The locally corrected mock server computed base (3312,4720) and **refused to count no-op movement to (48,48)**.

A real Java Robot click at desktop **(388,408)** selected tile **(48,47)** after the client loaded the original graphical world. The real game implementation emitted an outbound **opcode164** from Client.method3573; the isolated local server **ISAAC-decoded** it and returned an **opcode81 player-position acknowledgment for (48,47)**. The initial player tile was **(48,48)**, so this was a nonzero tile delta. Authentic **61-byte wire and server acknowledgment receipt** SHA-256 `c240c16733ed69e9bcd245e7009eb14f7648cc2f91d01a101e420cec4b339f7b`. The fixture's top-level test exited **0 at 32.64 seconds** and cleaned up its children. Cook object action 114/opcode132 and local response253 were also confirmed in the same run.

**What this proves:** GUI selection, game pathfinder, original opcode164 encoder, ISAAC network wire and isolated authoritative opcode81 movement response can work together when the synthetic collision assumptions are correct.

**What it does not prove:** ordinary unmodified original collision loading, long-running position reconciliation, native Windows GPU acceptance, actual authenticated SpawnPK service, or a production movement repair. The diagnostic overlay is **NOT** to be used in a shipping client; production source/JAR SHA `b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721` remains unchanged.

## GitHub-only development / private code

Owner source-safe R316 diagnostics, fixture repair, classifier, AWT walk robot, unit tests and Windows/Linux CI are committed in the [PRIVATE fullspkclient-private recovery branch](https://github.com/Trexzo/fullspkclient-private/tree/recovery/v309-r315-world-acceptance/recovery/v309-r316). Public [Draft PR #1143](https://github.com/Trexzo/SpawnPK-Client/pull/1143) remains unmerged. Original game source and full client binaries are not uploaded to this public repository.

The actual **1,277-source complete GitHub import remains PENDING** on [private issue #3](https://github.com/Trexzo/fullspkclient-private/issues/3), because the remote owner's computer is currently offline. The previous importer has been fixed to force-stage only the three pinned private JARs ignored by `*.jar`, and to verify all 1,277 staged Java paths plus the remote GitHub HEAD/tree before declaring success.

Keep both PRs draft and do not conflate GitHub synthetic CI with the separate original-client local GUI evidence.
