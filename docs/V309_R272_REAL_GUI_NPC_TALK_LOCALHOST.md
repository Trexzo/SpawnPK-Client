# SpawnPK v309 R272 — cache-backed NPC Talk-to GUI loopback

**2026-10-18 / Sole-owner integration draft #1142.** No production client source modified. Prior R265 source-built Java11-target client integrated R246 cache, with isolated original cache and original-JAR non-class resources.

## Source-derived test and results

Authenticated only to an isolated mock server at `127.0.0.1:43594` with dummy credentials. Original `rs` client parsed the actual owner cache config archive, loaded NPC definition **ID 1, Man, model 53**, and parsed inbound 7-byte opcode **65**, spawning NPC slot **47** near local tile 48,48. A 1400x900 Xvfb graphical client showed the NPC; genuine AWT right-click at **(392,265)** opened the client menu with Attack, Talk-to, Pickpocket and other actions. Genuine AWT left-click **(345,310)** selected **Talk-to Man**.

Real `Client.handleMenuAction(20)` sent **opcode 98** approach/walk plus **opcode 155** with NPC slot 47. An independent localhost server ISAAC-decoded the opcode-155 2-byte payload, accepted the slot and returned source-framed inbound **opcode 253**, 44 bytes of character-terminated test chat. Real client drew `Man: Welcome to the isolated local session!` in chat.

Two independent completed graphical replays, each with actual client original decoder and mouse handling:
- Replay 1: **34.11s**, 94 post-login C>S bytes, NPC155 at raw offset **49**, response 253 and rendered chat confirmed.
- Replay 2: **34.15s**, 94 post-login C>S bytes, NPC155 at raw offset **50**, response 253 and rendered chat confirmed.
- Earlier attempted separate home disconnected after **3.45s**, **NOT counted**.
- Outbound map-ready opcode **121** independently observed in both successful sessions.

## Actual Java and wire regressions

- **64/64** actual compiled Java assertions: NPC menu actions 20→155, 225→17, 965→21, 478→18, 412→72, 413→131, movement requests where applicable, absent-target refusal.
- **19/19** actual compiled Java assertions: genuine cache-backed NPC definition, real inbound opcode65 spawn/retain and subsequent `handleMenuAction(20)`.
- **22/22** independent Python ISAAC and packet framing assertions.
- Exactly pinned input / clean temporary Linux runner **105/105**, followed by independent source-free archive replay validator **155/155**.

## Evidence and restrictions

`SpawnPK_v309_R272_VISIBLE_NPC_TALK_LOOPBACK_EVIDENCE.zip` SHA256 **`499205453796d9edd26bb8197180218d1ecba2f3fdf1b231d83d41dbd3516757`**. All 47 ZIP entries passed CRC; manifest lists hashes and sizes. Screenshots of context menu and chat, socket ciphertext and server decoder report for each run, client packet captures, synthetic loopback source, actual-client Java regressions, SHA-guarded Linux runner and archive validator included. Game classes, owner assets and proprietary JARs are NOT distributed.

**Not verified:** real production authentication, original dialogue/quest logic, combat, click-to-object interactions, native Windows GUI or full source parity. All server-side interaction responses here are fabricated testing fixtures. No new full private client-source build done in R272. Keep PR draft, no merge to main. Next: source-backed object actions and/or owner-local Windows GUI verification.
