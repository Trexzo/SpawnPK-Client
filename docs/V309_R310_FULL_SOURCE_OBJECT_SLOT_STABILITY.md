# R310 — v309 complete recovered source stability

Date: 2026-10-26. Owner-private Java source remains off public GitHub.

The R310 patch addresses counted-but-empty scene object slots during object lookup, removal, plane movement, object metadata lookup and wall-decoration setup. The patch is intentionally limited to seven public methods in the real Scene source. The original R309 crash paths were reproduced before modification. Normal non-null object lookup/removal remains covered.

## Verified evidence

- Original R309 Java sources: 1,277, all individually SHA-verified before changes.
- R310: 1,277 Java sources compiled to 1,386 class files, zero errors.
- Only rs/Scene.class differs from the accepted R309 output; 1,385 class files match.
- R310 JAR SHA-256: `ae8191810ad324b68495446e0da9f325157ccc719c1bc698a734643b8baba722`.
- Scene.java postimage SHA-256: `63b3bc9d7b01f5337ca859616196f08af635f28dbf119caa11f55dadec43d4bc`.
- Actual compiled-client headless tests: R310 15/15, inherited R309 38/38, inherited R308 256/256, total 309/309.
- Clean private archive extraction and rebuild reproduced the exact same R310 class-only JAR.
- A second source-only rebuild starting from the SHA-pinned owner R278/R265 archives and the pinned GitHub R302–R310 builder chain also matched that JAR byte for byte.

## Explicit limitations

Real authenticated SpawnPK login, sustained world gameplay, native Windows GPU/GUI and physical cache power-loss have NOT been certified by this work. Additional older scene tests requiring original external config.bin/assets were not executed. This is not v311 original-bytecode parity.

The full 1,277-source R310 ZIP remains private. Public [reproducible R310 patch recipe](../tools/recovery/r310/rebuild_r310_from_pinned.py) contains no full recovered game source or binary.

Keep the PR draft and unmerged. Coordinate with issue #1117.
