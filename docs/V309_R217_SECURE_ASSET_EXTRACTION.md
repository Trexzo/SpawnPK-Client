# R217 — secure archive extraction in two production paths

Fixed real ZIP path traversal in `rs/cache/updater/AssetUpdater.java` (`extractZip`) and `rs/cache/updater/assets/CacheUpdater.java` (`extractCache`). Both now resolve entries through a canonical destination-boundary check rejecting `../`, rooted paths, Windows drive paths and backslash traversal before destination file operations. No original asset bytes distributed.

**Java 11 complete-source compiler:** all 1,275 source files PASS, 1,376 generated classfiles and zero errors. Additional regressions PASS: 7 disallowed paths rejected, normal nested zip entries extracted, malicious archive rejected without escaping destination; offline no-download/version check PASS.

**Application checks:** eight non-UI tests PASS on rebuilt JAR. Two UI checks **not accepted** in this run because this execution environment lacks the authenticated original resource overlay/display; do not report 10/10 for R217.

Private complete source/JAR/dependency ZIP: `SpawnPK_v309_R217_SECURE_ASSET_EXTRACTION_PRIVATE.zip`, SHA256 `1dc65efd76f66ce405414baad6fe87a666a9ebb9326fa6e4dbddcc8dbb0db335`. Source-built JAR SHA256 `c3b5153d83d8ac4bb80bc32137b882563c0a4f69471670ccf32882d78550ce84`. Includes SHA-checked Windows rebuild, optional owner-local original resource overlay, and regression evidence.

Startup and gameplay parity remain unverified. Keep PR draft.
