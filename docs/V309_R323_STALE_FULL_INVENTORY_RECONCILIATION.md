# R323 — stale inventory opcode53 and authoritative reconciliation

28 October 2026 · Source-safe, redacted results from **real owner-cache-backed recovered v309 client** GUI tests. Original game source and binaries remain private.

R322 demonstrated two independent Java logins and a saved synthetic-server inventory order. R323 extended the same isolated localhost-only environment with two additional **fresh Java client/server sessions**, using the same unchanged source-built game JAR SHA-256 `b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721`, authentic 10,772-file cache and Linux/Xvfb GUI.

**Session C — 21.95s, exit0:** client first displayed durable server inventory (Logs slot0, Coins slot1). Local synthetic server intentionally sent a stale incoming full-inventory opcode **53** with the prior ordering. The real client visibly displayed it (original inventory region **1,131 changed pixels**). Server then sent the saved authoritative state again with another opcode53; client displayed the correct order (zero pixel difference from initial). This is **server correction**, not client-side stale-packet filtering.

**Session D — 24.20s, exit0:** an independently launched client restored the durable state (zero changed pixels versus C's corrected inventory). Actual GUI drag emitted a genuine ISAAC-decoded client opcode **214**, local server rejected the action and reasserted the saved ordering with opcode53. Final item ROI difference: **0 pixels**. Captured real 51-byte client wire SHA-256 `8dea107dfb1fc1eed88e100c112e2032ca43d6a96854297736c496b43a00f923`. The durable state file remained SHA-256 `d0240cfd5d72dc44f3206a16156335a91fa38f6ed78569a5c1f33b1d812c1a48`.

The source review finds **no revision/epoch field on existing opcode53**. It follows that a robust server must serialize inventory snapshots and reject stale writes before encoding; it cannot rely on the client discovering an old packet. This finding does **not** justify a speculative production client edit. The live production service's implementation has not been audited.

[Private draft PR #4](https://github.com/Trexzo/fullspkclient-private/pull/4) contains the R323 source-safe SHA-locked fixture generator, replay receipt verifier and server-side revision *reference model*, plus Windows/Linux unit tests. The owner-only supplemental replay evidence package (1,116,877 bytes) SHA-256 `cac1b695ae21b8a05e93cd97f8222e2b86745476401fd42af730f3c3284fbbc6` passed clean-extraction verification.

**Release boundaries:** localhost-only synthetic game server, not authenticated SpawnPK inventory persistence, real database transaction order, Windows GPU or long-running public-server gameplay. Actual private **1,277 recovered Java files and 3 pinned JARs still NOT on GitHub**; [private issue #3](https://github.com/Trexzo/fullspkclient-private/issues/3) remains open. Keep both PRs draft/unmerged and original-v311 bytecode-parity lane separate.
