# R236 Lane A integration: cache R226 → R227 → R228

Canonical source: Lane A integrated R233/R235 (1277 Java). Inspected Issue #1117; fetched exact Lane B private R226, R227 and R228 donor bundles from owner's Library. Applied **only** `src/rs/cache/updater/assets/CacheUpdateTransaction.java` sequentially with SHA-256 preimage/postimage verification:
- cache R225 `9be38338d50c7a774d070e00ad6c426dc363180ef2c8d83c052b6baa41b78e43` → cache R226 `9def839b07b788431ae48444c7dcd98c1a03fce6951cbf16d9d7923cf99d228e`
- R226 → R227 `4b5234d09c74b491eaba18bfd2fb3ce70b736797154667cd5839299a62393311`
- R227 → R228 `198bd550540a5b9a2b52c3830be1e9178228f8b02b2a11a038d083516b8d99be`

**Actual integrated complete source compilation:** `javac --release 11` 1277 sources, **1386 .class**, **zero errors**, exit 0, using exact non-game compile-only dependency from canonical Lane A. Rebuilt JAR SHA256 `1500827b89daaa9325e228cb54cea8309bfa7de428f4cf6610bedc29a7c0d414`; complete source ZIP SHA256 `d4106fa2590baa3992f8433311be7b9a94a6bef89c38ed7f231a7bdd01a04e7c`.

**Actual merged production helper tests:** R226 post-rename witness 23 PASS; R227 staged mutation 24 PASS; R225 mutation/space 22 PASS; R224 rollback replay 21 PASS; R223 inventory 14 PASS; R222 isolation 8 PASS; R221 cross-process crash/lock 10 PASS; R220 transaction 8 PASS. R228 Windows-alias suite compiles but explicitly reports **NOT APPLICABLE on Linux**; hosted Windows CI on independent helper in PR #1122 is **not** private integrated Windows runtime proof.

**Private consolidated ZIP** `SpawnPK_v309_R236_CACHE_228_INTEGRATED_PRIVATE.zip` SHA256 `636f80c4791c2ef5428d1902bf700fbaad9bbe26bf579ab5ccf07654b86d6f0c`, ZIP CRC PASS, bundles full source, built JAR, precise libs, three donor overlays and test manifest. No GUI/server gameplay test run on R236 binary; R235 successful login request framing and invalid-password rejection belong to earlier binary. Windows and successful authenticated local session still pending; Lane B retains cache integrity ownership. Do not merge PR.