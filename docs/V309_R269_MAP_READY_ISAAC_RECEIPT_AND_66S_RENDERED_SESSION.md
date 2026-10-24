# v309 R269 — actual localhost map-ready and sustained rendering

**Sole active SpawnPK-Client integration. Draft PR #1142; no production source changed.** Continuation of R268 and the verified private R265 Java11-target source-built client with cache R246.

## Two independent authentic-client Linux/Xvfb replays

### 1. Long observation: 66.05 seconds after login

A **fresh, isolated home** was reconstructed from SHA-pinned owner archives (10,772 authentic .spawnpk cache files and non-class UI resources from the original JAR). Client host was explicitly `127.0.0.1:43594`, with synthetic login only—never a real account or server. The actual diagnostic client GUI repeatedly rendered ground/structures, avatar, minimap and HUD. Screenshots captured at +12, +26, +45 and +60 seconds each showed more than 98% of the tested 3D viewport nonblack.

A source-derived fake server sent 26 periodic, valid, no-mask three-byte opcode-81 syncs, plus three authentic IdentityKit appearance and local-position packets (initial **48,48**, then **50,49** and **52,51**). Actual `Client.method1850` diagnostic logs confirmed all three positions with `appearance=true` and `packetCaret=68/68`. The server received **128 post-login bytes**, SHA256 `99e3ec8329f82f96a8545836c9ea476c2daa7ed0cb4f4c0662f45d43079a4daa`. No premature client disconnect was observed during the 66-second window. Closing the mock server ends the test; this is not indefinite gameplay.

### 2. Independent outbound wire / ISAAC test: 22.47 seconds

With `-Dspk.capture=true`, the actual client's opt-in `PacketCapture` logged outbound **opcode 121 (zero payload)** after the first region build. The separate localhost listener received **57 ciphertext post-login bytes**, SHA256 `a7c39391723e1c4dec9489860eda6b7f72c209865431db3c5e89029562ca66fb`. It independently derived the outgoing ISAAC stream from its **dummy local login** (keys used in memory, not retained), decoded the first three client packets using source-backed framing—`185` with 2 payload bytes, then two `103` variable-byte frames—and decoded all intervening zero-length keepalive packets.

The real server-received ISAAC-decoded sequence and opcode offsets:

```text
opcodes: 185, 103, 103, 0, 0, 0, 0, 0, 121
offsets:   0,   3,  21,31,32,33,34,35, 36
```

**Map-ready opcode 121 conclusively received at offset 36.** Earlier R268 falsely reported failure because it assumed offset 35; an additional outgoing zero-length opcode 0 shifted 121 one byte. The wire parser now derives positions from the actual framing instead of relying on a single hardcoded offset.

## Tests and evidence

- The actual previously compiled R265 production `Client.method1850` 63-assertion direct teleport/appearance regression was rerun: **63/63 PASS**.
- The R269 early outbound ISAAC parsing self-test, including three truncated-stream rejection cases, passed **7 checks**.
- Both graphical replay runners completed; the longer test validated three full appearances, 26 heartbeats and four screenshot frame gates; the wire test verified independent receipt of 121.
- Deterministic source-free evidence ZIP: `SpawnPK_v309_R269_MAPREADY_AND_66S_WORLD_EVIDENCE.zip`, SHA256 **`0390a2dcefc1efa6fc2b46e0231d4b18c3428aab22eaeb87c018bfee14746584`**, 1,377,605 bytes, 36 entries including MANIFEST.json; nested entry hashes and ZIP CRC validated. Includes screenshots, original test logs, Python synthetic loopback probes, Java RobotLogin keyboard fix, checksum-pinned cache staging and replay drivers, ISAAC implementation, login-seed parser, frame decoder, offline tests.
- Private R265 source ZIP SHA256 `9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb`; original client JAR **non-class resources only** SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`; asset ZIP `8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565`; R230 mappings `5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125`.

## Strict acceptance boundaries

1. **Not real user-controlled walking:** position changes were *server-directed teleports*, not clicks/pathfinding/movement acknowledgements. No NPC, object interaction or combat acceptance.
2. **Not genuine authentication:** dummy login + localhost-only server; no real/live connections.
3. **Not a new full-source build:** R269 used the checksum-pinned actual R265 source-built Java11 diagnostic JAR, not a newly compiled R269 production JAR.
4. No Windows GUI or full client session acceptance, long-lived live-game session, original v309 binary equivalence, broad cache compatibility, or power-cut recovery proof.
5. Private client classes/cache/assets were not published to GitHub or bundled in the R269 evidence archive. Keep PR #1142 DRAFT, historical PRs intact, do not merge `main` without acceptance.

**Next R270:** prove actual player-controlled click-to-walk outbound frame, then world-authoritative movement/interaction acknowledgment in the same isolated server. Test owner Windows GUI separately after this protocol milestone.
