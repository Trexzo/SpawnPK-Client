# Cache R231 — authenticate the restored original after an interrupted rollback

Lane B cache-only reliability change, coordinated under issue #1117. Base: private cache R230, independent of Chat A source-runtime release numbering.

## Verified failure mode

In R230, a journal in `ROLLBACK_PREPARED` with `previous/` already missing and a live cache root present causes recovery to assume that the live root **is** the restored original. An unrelated process could have created/replaced that path during a crash window. The recovery then discards its journal and treats unrelated contents as trusted restored cache.

R231 writes `.rollback-witness` containing a deterministic SHA-256 digest of the genuine backup's relative names, directory markers and file contents **before moving that backup back to the cache root**. When replaying `ROLLBACK_PREPARED` with no backup left, or cleaning `ROLLBACK_RESTORED`, it checks that the active cache matches the recorded backup. Mismatch fails closed and preserves the root plus recovery evidence, rather than silently discarding the journal. Existing pre-R231 journals without witness remain readable as a backwards-compatibility exception.

## Real private Java11 source evidence

- Exactly one modified production path: `src/rs/cache/updater/assets/CacheUpdateTransaction.java`.
- R230 source preimage SHA256: `8ee21c114b98f7ece960b1347609edd8ffce300614f19d7f3103baaeaa715882`.
- R231 source postimage SHA256: `52f10e3b6cc69955bc5557aafc62af0f65d5558adcdbaf6287ac9d66258f1235`.
- Public original-independent `tools/java/r231/CacheUpdateTransaction.java` Git blob SHA1 `89ca523959fb84e70187a899ba5c73f9677b3946` is byte-for-byte identical to the private R231 production Java.
- Actual private full `javac --release 11` compilation: **1,277 Java sources, 1,388 .class files, zero compiler errors**; compared with R230 only that Java source and the matching `CacheUpdateTransaction.class` differ.
- New R231 private rollback witness regression **14 checks PASS**; all **17 inherited offline regression programs PASS**, including actual private CacheUpdater extractor, multi-JVM lock/hard-stop, journal/idempotent rollback, staged/active cache witnesses, HTTP failures and archive/path protections.
- Regression deliberately overwrites the supposed restored root with a **same-size, same-mtime change** and confirms failure preserves both live data and the witness; tests old-format journal compatibility, completed rollback, and after-promotion exception rollback.

## Private handoff

- Consolidated private archive `SpawnPK_v309_R231_ROLLBACK_WITNESS_PRIVATE.zip` SHA256 `2289fd31cfbe68404a85d9b82a7e0aa4b3c7a0b24aff07253747a4a3f46a5e6b`.
- One-file changed-only archive SHA256 `30ff702c521227fef49d1cec55480838a9b343b1de04bccf57e3a0a96cacaaaa`.
- Complete private source ZIP SHA256 `1f2c3911f78ec99f230afec17dc60373d31b16bf9e57c1c0a7c9d70389df5c97`.
- Compiled class-only private JAR SHA256 `08253521d839a53e58060748ef8c74d348bc21024bb9944664b7e7edf462cd72`.
- Includes full private sources, exact non-game dependency JARs, one-file overlay with R230 backup, checked no-extract PowerShell patch script, independent Windows Java11 rebuild + 18 test programs, manifests and local logs. No proprietary v309 source bytes are published on GitHub.

**Lane A:** Latest accepted full source is R238 with cache R230. Replace ONLY `CacheUpdateTransaction.java` after exact R230 preimage SHA check and back up the original; retain Lane A's CacheUpdater, downloader, login, GUI and network. Independently compile and test combined source. Full private Windows game and original bytecode parity have not been accepted. The public GitHub Windows/Ubuntu workflow tests only the independent helper and synthetic recovery case.

## Limits

The new fingerprint is content-based, not a cryptographic authentication token against a malicious actor who can edit the witness itself. Legacy pending journals with no witness retain prior compatibility behavior. Durability across hardware power loss, directory fsync and races after the final fingerprint check remain unproven. Keep draft.