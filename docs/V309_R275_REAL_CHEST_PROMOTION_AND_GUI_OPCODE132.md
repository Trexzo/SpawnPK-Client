# v309 R275 — actual pending-scene chest promotion and GUI Search opcode 132

**Status (2026-10-18): authentic cache-backed chest interaction confirmed twice on isolated localhost, production client unchanged.** Sole-owner integration PR #1142 remains draft.

## New source-backed scene promotion (real compiled R274 client)
Using the **exact** owner-private R274 rebuilt Java11-target 1386-class JAR and original .spawnpk asset ZIP, independently authored test `R275PendingObjectPromotionRegression.java` drives original `Client.method2310(Packet,151)` followed by original `Client.method1808` tick:
- A spawn for chest **object104** at local tile **(50,49)** queues, but is not immediately in `Scene`.
- Graphics mode 1 and absent **OSRS** model1226 do not promote the pending chest.
- Loads real OSRS model1226 into the OSRS model-header bank (**152 vertices, 286 faces**); the original `ObjectDefinition.method197(10)` then returns ready.
- Next real `Client.method1808` inserts object into real `Scene` at (50,49), packed hash **1075452082**, resolvable via `Scene.getHashAtTile`.
- Incoming removal subpacket **101** is queued and the next real tick removes it. No source modifications.
- **37/37 source-backed Java assertions PASS.** Independent Python framing checks for actual opcode60/u16 and nested subpacket151 **12/12 PASS**.
- The clean, SHA-256-pinned Linux script using only original owner inputs `R274_PRIVATE.zip`, `R265_PRIVATE.zip`, and `.spawnpk (4).zip` ran **49/49 PASS** after staging original `loc.dat`, `loc.idx`, and OSRS location config into a disposable test home. Earlier initial fresh-input NPE was test setup, not production source. Prior R274 compiled-JAR eight-suite **316/316** results retained as regression baseline.

## Two real graphical object interactions

Original isolated Linux/Xvfb client reached populated rendered scene and displayed a pickable chest. Genuine AWT right-click brought up the chest menu; genuine AWT selection **Search** generated the client-originated object-action packet **132**. A separate mock listener on `127.0.0.1:43594` decoded actual received outgoing ciphertext with session-derived ISAAC: opcode132, 6-byte packet, object **104**, world target **(3202,3201)**, raw offset **42**. It returned synthetic source-framed incoming opcode253 chat **"Chest: The lid creaks open."**

| | Replay 1 | Replay 2 |
|---|---:|---:|
| Connected observation | 6.61 seconds | 6.37 seconds |
| Outgoing postlogin bytes | 49 | 49 |
| Outgoing wire SHA256 | `7a7440cdca89602c8baa2658f0b240b26bbb6c47e47b656cb538bce2ba732649` | `124a28865374df10f2954332e1b47ed2f6ee4f07977e85e4a7442358b37662ed` |
| Object opcode132 | ID104, offset42 | ID104, offset42 |
| Synthetic response opcode253 | Observed | Observed |
| Map-ready opcode121 | Observed | Observed |

Two separately captured before/after GUI screenshots and listener receipts are archived. These **short** tests do not establish prolonged gameplay, original chest-loot logic or production server integration.

## Public-source-free verification package

`SpawnPK_v309_R275_REAL_CHEST_GUI_OPCODE132_AND_PROMOTION.zip`

**SHA256 `9ccc37c9d82af57ac682cdb37492770cd102cb8b03fea30f0571902d774991c2`**, **967,518 bytes**, **32 ZIP entries**, all CRC and SHA256 manifest verified. Independent `R275EvidenceVerifier.py` **106/106 assertions PASS**; two independent deterministic package builds produced identical ZIP bytes.

Contains source-backed **standalone tests**, Python/PowerShell/Linux read-only SHA-guarded runner, real screen captures, two localhost ciphertext receipts, synthetic server harness, and previous R274 compatibility log. Does **not** contain private client Java, original assets, owner JARs or login secrets. PowerShell runner authored but **not native-Windows tested**.

**Remaining:** actual original chest inventory/loot is absent (synthetic chat only). Java/native Windows GUI and sustained real server play not verified. The prior R274 stale-object lookup guard remains the last production client change; R275 changes no client production source. PR stays **DRAFT**, no main merge. Next R276 should focus on multi-object collision/interaction consistency and a longer local session, followed by native Windows owner acceptance.
