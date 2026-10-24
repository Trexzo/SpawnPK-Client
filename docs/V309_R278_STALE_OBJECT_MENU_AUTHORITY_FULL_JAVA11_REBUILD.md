# v309 R278 — object-menu authority hardening and deterministic Java 11 full rebuild

**Sole active client development chat, 2026-10-18.** Integration #1142 remains DRAFT. **Implemented privately, not publicly committed:** only the original-derived `source/rs/Client.java` changes; tests and this document are independently authored.

## Newly reproduced defect

R274 made `Client.handleObjectClick(...)` reject an absent authoritative `Scene.getHashAtTile(...)` result, so item-on-object (menu62 / wire192) and the already-conditional spell action were protected. But five ordinary menu handlers still called `handleObjectClick` and **ignored its boolean result**, then emitted an object packet anyway.

On the real compiled R274 production JAR, the new regression reached all 20 valid action cases but failed at the first stale-object attempt:

```text
AssertionError: STALE_SCENE_OBJECT_OPTION_EMITTED_PACKET action=1062
```

## Actual production change (private owner archive)

Exactly five R274 `Client.java` menu branches are now gated by successful `handleObjectClick` and call the helper **once**. The packet body and wire opcode remain unchanged for each valid scene object:

| Menu option | Actual outbound opcode |
|---:|---:|
| 1062 | 228 |
| 900 | 252 |
| 113 | 70 |
| 872 | 234 |
| 502 | 132 |

Menu62→192 and conditional spell action remain unchanged. Previous source preimage SHA256 **`1c3ca60ede6973d92eaf277471db2659dad024c19c15a85472fda90e63dd5201`**, private R278 postimage SHA256 **`319f893290473e6f144e04c89de6c7e48efaa03c8a10e6f2acd8a9e28c9aa959`**. No other 1,276 Java files modified.

## Independent actual-client compilation, red/green and compatibility

Original exact private R265 source archive was hash-verified SHA256 `9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb` and the previous R274 single-location guard reapplied with a pinned intermediate hash. Original dependencies were **not changed**. The existing eight conflicting third-party class names were excluded only from a disposable compile-only JAR, as in R274.

- Full `javac --release 11 -proc:none -g:none`: **1,277 original Java files → 1,386 production .class files; zero errors**.
- Two independent full builds produced **byte-identical deterministic class-only JARs**. A third exact SHA-guarded extraction/rebuild from the original R265 archive reproduced the same JAR.
- Private compiled JAR SHA256 **`dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd`**.
- **254/254 actual-client R278 regression assertions PASS** (four authentic cache objects 2,114,152,104; five valid menu choices each; exact per-choice outgoing opcode/ISAAC frame, including source-emitted 3-byte opcode183 diagnostic payload; stale scene hash rejects all five menu choices after cave deletion, plus inherited mixed-footprint collision/path checks).
- **Original R274 binary fails** the new stale-action assertion, patched R278 class directory and standalone compiled JAR both PASS. This is red/green proof, not only static code analysis.
- Ten existing/new direct Java regression suites **759/759 PASS**, including historical R274's eight suites (316 assertions), R277 mixed-object lifecycle/pathfinding (189), and R278 authority test (254).
- Additional standalone strict R277 packet framing **38/38 PASS**, for **797/797 clean-owner-input offline checks**, independently executed by the packaged Linux runner.
- Independent standard-library evidence-archive verification **103 checks PASS**, including complete JAR CRC, 1,386 entry count, five patch guards, expected old-version failure, Java suite counts, SHA manifests and reproducible input/build logs.

## Owner-only handoff

One package: `SpawnPK_v309_R278_FULL_SOURCE_OBJECT_AUTHORITY_GUARDS.zip`, SHA256 **`e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280`**, approximately 2.42 MB, **30 ZIP entries**, two byte-identical deterministic ZIP builds. Contains owner-private 1,386-class JAR, *short* R274→R278 one-file patch diff, exact hash-guarded Python rebuild script plus Windows PowerShell wrapper, source-backed standalone Java tests, read-only Linux test runner, past/present red-green logs and manifest. No original R265 full source archive or user cache data included. **Do not commit or merge this private package publicly.**

The public branch contains only this document and byte-identical independently authored Java regression `tests/java/r278/R278ObjectActionAuthorityRegression.java` (Git blob SHA `72f19eaeb3286b3552769e9ac5ec465ebcc52ecb`). The private JAR must be used together with pre-existing owner dependencies/non-class resources; it is not a standalone executable.

## Explicit remaining gates

The R278 compiled client **has not been newly launched in a full graphical scene** (Linux or native Windows); no new mouse-driven multi-object pick or prolonged loopback test was run using the R278 binary. The last limited R277 GUI only validated chest132 at offset42 and disconnected after 10.61 seconds. Production-world server login, actual loot, NPC dialogue logic, full interactive gameplay, original executable bytecode parity, native Windows acceptance and power-loss acceptance **NOT proven**.

**Next:** run GUI with actual rebuilt R278 JAR, confirm multiple real object IDs/menu choices and server-decoded receipts in one sustained isolated session; then request owner-local Windows acceptance at a meaningful milestone. Keep #1142 DRAFT, no main merge.
