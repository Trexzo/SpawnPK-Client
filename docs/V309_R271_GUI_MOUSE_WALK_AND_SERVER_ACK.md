# v309 R271 — actual GUI click → walk164 → local server acknowledgement

**Status: isolated graphical gameplay milestone verified, 2026-10-18.** Sole-client ownership per coordination issue #1117. Continuation of the R269 fully rendered client and R270 source-backed offline walk packet. Production Java unchanged; no original-derived private source or cache published; PR stays **DRAFT**.

## Source-built runtime / valid scene gate

The exact R265 diagnostic Java11-target source-built client was launched with original non-class resources and real .spawnpk cache in an entirely separate Linux/Xvfb home (the hash-pinned R269 verified staging). Its initial local tile was (48,48), cache-R246 remained integrated. Repaired R270's test automation by returning to **1400×900 Xvfb**, the previously verified username → Tab → password → Enter keyboard procedure, and requiring >90% nonblack pixels in the 504×335 scene region on three consecutive frames **before clicking**.

Four actual `java.awt.Robot` left mouse clicks in the **rendered game viewport**: (310,306), (290,327), (448,278), (360,300). The live **original `Client.method3573(0)`** (not a substitute codec) pathfinding/scene picker generated ISAAC-obfuscated, variable-byte opcode **164** packets. The local TCP listener bound to **127.0.0.1:43594** independently decrypted, framed and decoded the requests with login-specific disposable ISAAC cipher state (never persisted).

| Actual AWT click | World target parsed from received opcode164 | Corresponding server opcode81 acknowledgement | Wire offsets (replays 1/2/3) |
|---|---|---|---|
| 310,306 | (3198,3204) | Local (46,52) | 40/40/40 |
| 290,327 | (3196,3205) | Local (44,53) | 55/56/55 |
| 448,278 | (3198,3215) | Local (46,63) | 70/71/70 |
| 360,300 | (3197,3219) | Local (45,67) | 87/88/87 |

Actual client diagnostic log independently confirms `R265_SELF_MASK_AFTER mask=16 appearance=true position=X,Y packetCaret=68` for all four replies. The mouse requests alone do not place the player. The *synthetic localhost server* makes a **type-3 teleport-style position acknowledgement** to the decoded walk destination; the client accepts it. This is **real user-input-driven request/response on loopback**, NOT proof of stepwise movement server logic.

## Three complete graphical replays

- First session **85.19 seconds**, 182 post-login ciphertext bytes, 34 periodic player-sync heartbeats; four genuine AWT walks/four acknowledgements and map-ready121.
- Second independently cloned test home **48.07 seconds**, 134 post-login bytes, four walks/four acknowledgements, map-ready121, final 3D scene **98.82% nonblack**.
- Third isolated test home **48.17 seconds**, 134 post-login bytes SHA256 `8d42e0d2a8352c48dd8e45f99bd987de85dde8508db04d71cdf491530b042914`, 19 heartbeats, four walks/four acknowledgements, map-ready121 and **98.51%** nonblack at end. Server recorded no runtime error or premature disconnect.

### Late outbound opcode77 framing corrected

The prior decoder rejected a later packet at byte 103, **after** successfully confirming all four walks. Source inspection established outbound opcode **77** is a variable-byte framed packet (`outgoingPacket.a(77)`, length placeholder, and `method1209` backfill). The final replay's independent decoder now handles its **framing only**, and consumed **all 134/134** post-login bytes without an error. R271 self-contained synthetic framing regression **11/11 PASS**. Replay 3's client/server evidence validator **34/34 PASS**; previous R270 real Java walk regression + Python test independently rerun **46/46 PASS**. A separate portable **standard-library archive verification test passed 133 checks** including entry hashes, reports, frames, four click logs, request/ack pairs and packet121.

## Provenance + artifact

Source-free reproducible evidence ZIP **`SpawnPK_v309_R271_REAL_GUI_WALK_SERVER_ACK_EVIDENCE.zip`**, **SHA256 `fe609d5443902de1e411ae8a3bcfc47dc5601f67c888ba523ec70c7980c87028`**, **1,488,639 bytes**, manifest for **35 files** plus MANIFEST.json; deterministic two builds identical, all CRC and manifest hashes pass. Contains original three-run screenshots (before/after), log and server receipt/ISAAC evidence, mock postlogin ciphertext, separately-authored read-only Linux GUI harness, Java AWT click helper, tests and setup instructions. **No original or reconstructed game Java, cache content, client JARs or dependency binaries included.** SHA-verified original inputs used only when reproducing from the owner's own archives.

## Remaining acceptance

Not genuine external server login, production multiplayer or continuous server-side walking simulation; fake server **teleports to requested target**. NPCs, object interactions, combat, path collision across multiple regions, native Windows graphical execution, original v309 parity and physical power-cut recovery **NOT verified**. No complete source rebuild repeated in R271: it reuses the independently source-built R265 compiled JAR with the diagnostic overlay. No merge into main; preserve historic stacked PRs. Next: source-backed real object/NPC interaction and server response on localhost, plus native Windows GUI acceptance.
