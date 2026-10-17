# Cache R234 — versioned journals prevent silent missing-witness fallback

A new R233 transaction could lose its `.install-witness` file and be treated as an older witnessless journal. For a `PROMOTED` or `ROLLBACK_EMPTY` transaction, that removes its required content-provenance check.

R234 writes `SPK-CACHE-TRANSACTION-V2` for new journals. Recovery refuses V2 states later than `PREPARING` if the install witness is absent or malformed, **before** modifying live cache or backup. Historical V1 journals are still read and retain V1 when a recovery state is rewritten. The V2 marker is not a cryptographic authentication of arbitrary malicious rewrites.

**Actual local private validation:** complete Java11 target compilation of 1,277 source files into 1,388 classfiles, zero errors. 21/21 offline Java programs pass (including new 21-check R234 journal-version test), with original cache extract, downloader, hard-process-stop, cross-process lock and inherited witness recovery. Exactly one Java source and one production classfile differ from private R233. `javac --release 11` was used with locally available JDK21, not native Windows. No hosted R234 CI is claimed.

**Strict private overlay:** `src/rs/cache/updater/assets/CacheUpdateTransaction.java`.
R233 preimage SHA256: `5bd41aa1442642ce9b3ddc7a914cf0a98be98b6f3a85e763e7281b3dfe86aff6`.
R234 postimage SHA256: `bc08aff2ddd3948f5ea8c248100234a39ee03cafd66b24e27b48c85e91aa2cad`.

Private complete `SpawnPK_v309_R234_VERSIONED_JOURNAL_PRIVATE.zip` SHA256 `b88fa9565d048aac56683a27056852f8af08c2bbdaf225a993315cf15da5f199`.
Changed-only `R234_CHANGED_ONLY.zip` SHA256 `8c6f7d9cd06ac2f8cd5a263e70a9f91a6796fbbb190f8185206894eebd564762`.
Full source snapshot ZIP SHA256 `57b900ea9788cfae52ab19efeafd62940ced7f195b11aeda9585da8b7bddcde3`.
Built JAR SHA256 `a3a5e2eb8eacd052b27cd5ca2225070caff762fa0140ea86b006711e5c10593b`.

The private artifact contains exact one-file patch plus checked PowerShell backup/rollback, full Java source, dependency JARs, compiled JAR, 21 regression sources/logs and Windows rebuild scripts. Do not use donor source tree to overwrite Lane A canonical integrated files; only this helper file should be imported after SHA preflight.

This PR includes a review diff and documentation, not proprietary private game code or public R234 source-run acceptance. Unverified: actual native Windows client, hardware power loss, malicious rewriting V2 journal to V1, concurrent external writes, integrated source recompilation by Chat A. Keep draft.
