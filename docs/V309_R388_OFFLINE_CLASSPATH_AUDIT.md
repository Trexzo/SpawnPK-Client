# v309 R388 — reproducible offline classpath and runtime-linkage audit

This draft is stacked on R386 in Trexzo/SpawnPK-Client. **Do not merge or release Source-M1.**

## Why this work was needed

The 1,277 recovered Java sources compile into a reproducible 1,388-class JAR, but compilation does **not** prove that the reconstructed client launches or matches the original binary. Bundled third-party classes, original runtime resources, and legacy method descriptors require separate analysis.

## Public-safe verification

The tool `tools/r388/audit_offline_classpath.py` reads local JARs, checks optional SHA pins, parses constant-pool Class references, compares dependency class-path overlap, and reports missing references and a conservatively overestimated entrypoint dependency graph. It **does not** run the client, upload code, open network connections, inspect owner caches, or alter JARs.

The accompanying Python test suite contains **15 source-free synthetic cases**. The generic Java no-initialization linkage probe is compiled under JDK 21. GitHub's Windows/Ubuntu CI **never receives owner-private source or binaries**.

## Privately observed, advisory only

- The SHA-verified original v309 JAR contains **10,502 class files and 419 non-class resources**.
- The reconstructed candidate has **1,388 class files**. With the preferred dependency, the classpath has **10,715 unique class paths**; counting names is not binary equivalence.
- The preferred dependency contains all **9,326** files in the filtered alternative with byte-identical class contents and **one additional class**.
- Static entrypoint graph analysis leaves **two missing non-platform class references**. Both are present in the original v309 JAR, but one legacy class references other obfuscated classes not present under their original names in the reconstruction.
- A JDK 21 **no-initialization** probe loads and reflects all **1,388 reconstructed classes** successfully. The older matrix dependency still raises a missing-type failure during reflection, which does not itself prove it is invoked in gameplay.
- Six synthetic matrix-decoder comparisons were bit-for-bit equal between a reconstructed adapter and legacy decoder code under controlled fixture inputs.
- The original resource companion contains all **419 original non-class resource entries** with verified per-entry SHA hashes, saved privately and only in an isolated directory on the owner's Windows PC.

## Open acceptance gates

The full 1,277-source native Windows build is **still pending** because the private R386 kit is not in the owner's Downloads folder. Also unproven: original binary remapping parity, real GUI/launch/login/reconnect, v312 compatibility, power-cut durability, and safe staging cleanup.

**Keep this PR DRAFT/UNMERGED.** Never commit private recovered source, original/resolved JARs, cached user data, or the resource companion.
