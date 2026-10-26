# v309 R270 — real walk encoder and authoritative movement handler

**Draft-only integrated client evidence, 2026-10-18.** No original-derived client source published and no production/client cache modifications.

## Verified

* Authoritative private input R265 full client ZIP SHA256 `9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb`, actual Java11-source-built production JAR SHA256 `dc42ce52380d51bbc6162589d66e7226e5c86541ab84869f710b38ceffd7a503`.
* Actual `Client.method3573(0)` was invoked on an explicitly *empty interior* 104x104 collision grid. Actual `Packet` and ISAAC wrote **opcode 164**, 9 wire bytes with two waypoints and a declared 7-byte payload.
* With a disposable cipher seed [13,22,37,41], actual Java output was hex **70 07 01 0C 01 01 80 0C 00**. Decoded first world waypoint (3201,3200), final world target (3202,3201), local target (50,49), run=0.
* The outgoing walk did not change the player's local tile. Independently constructed 5-byte authoritative movement sync was passed to real `Client.method1850`, which placed the actor at (50,49). **This is an offline direct-method test, not a real socket acknowledgment.**
* Alternate real `method3573(2)` action route encoded opcode **98** and correct length. Blocking the entire test-only collision interior and disabling fallback causes method3573 to refuse the route and leave the outbound packet untouched.
* **23/23 real compiled Java assertions PASS**; separately authored Python ISAAC/walk decoder validated the exact Java bytes, malformed/truncated streams and composite framing: **23/23 PASS**. Packaged checksum-guarded Linux runner repeated **46/46** in a disposable compilation environment.
* One evidence ZIP `SpawnPK_v309_R270_WALK_PACKET_AND_SERVER_ACK_EVIDENCE.zip` SHA256 **260e97549c1fad0a1a3b8ba78182ff734c4fedf8f56e32cce884510764838231**, 25,861 bytes, 19 entries, deterministic two builds, entry hashes/ZIP CRC verified. Original client source, built JAR and user cache not bundled. Windows PowerShell runner included but not executed under Windows.

## Actual GUI click experiment: **not accepted**

Three isolated Linux/Xvfb GUI explorations attempted to reach a stable render and mouse click. Initially the window size shifted the synthetic login controls; one subsequently corrected attempt completed localhost login and appearance, with outbound opcode 121 independently observed at raw wire offset 36. However it was still black/loading at click time and the mock socket closed ~10.29 seconds post-login **without a captured opcode 164**. A subsequent replay was interrupted. Do NOT infer user-controlled walking, a server-received 164, or client-originated movement/response from these attempts. Neither real click handling nor real scene collision is cleared. Keep an explicit acceptance failure for the GUI phase.

## Next

Use the known-good fully rendered R269 GUI home and verify nonblack frames *before* sending a real AWT mouse click; capture both client's outbound opcode and independently ISAAC-decoded server receipt of 164; only then return a server-authoritative 81 acknowledgment. Record path target, click coordinates, collision data and runtime errors. Native Windows still pending. Preserve sole-owner integration draft PR #1142; no main merge.
