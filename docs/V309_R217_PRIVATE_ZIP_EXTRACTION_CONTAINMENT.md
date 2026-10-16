# R217 — original v309 Java cache ZIP-extraction containment

R217 modifies actual **private** readable production v309 Java source from the SHA-pinned R216 build: `AssetUpdater.extractZip` and `CacheUpdater.extractCache` formerly constructed and used archive-entry paths directly, including deletes. Untrusted entries such as `../outside`, Windows separators, drive paths, or symlink exits could reach outside the asset extraction directory.

The **newly written** public production helper is [SafeZipPath.java](../tools/java/r217/SafeZipPath.java). The independently kept private R217 candidate changes these two original production source methods to resolve each ZIP-entry target through `SafeZipPath.resolveUnderRoot(root, entry)` **before delete/create/write**; the cache extractor imports the helper. The complete private original Java is not committed here.

## Real private-input evidence

- Baseline private R216 bundle SHA-256: `70b0f7e952db24dbaa116b10c4625a6128d34a3952c533c54ae686d87cae9286`.
- Rebuilt complete tree: **1,276 actual Java files**, `javac --release 11 -proc:none -g:none -encoding UTF-8`, **zero errors**, **1,377 production JVM classfiles**.
- The private original-version compile-only library contains **zero `rs/` game classfiles**, preventing a binary fallback from masquerading as source compilation.
- The regression invoked **both real production extraction paths**, rejecting malicious `../`, nested traversals, absolute paths, Windows separators/device paths, and an existing symlink leading outside the extraction root. Safe nested asset ZIP extraction passed.
- Existing R216 offline cache/version/download regression: **PASS**.
- Full private R217 source archive SHA-256: `3972e50956064bc4fcf9f41334ed67f0912d97b4514e3ed8084280634e9e2a28`.
- R217 source-built production JAR SHA-256: `627236e820c05bb60d59df927a8d98636c2ecfeb0d1b1da6d8e4b1e07adb8210`.

Public CI is limited to verifying the helper on synthetic ZIP entry names. It does **not** possess the private original source, Java dependencies, or the two real production extractors. Keep this PR in draft until independent private-input verification and Windows gameplay tests.

**Limits:** The guard checks path traversal and existing symlink escapes, not race-free filesystem extraction, oversized ZIP decompression, or all other archive extraction sites. Normal-version game network and startup behavior was not changed by this fix. No original-v309 instruction parity or playable-runtime acceptance is claimed. This R217 source tree is a separate lineage from the R221 original-symbol single-class parity research.
