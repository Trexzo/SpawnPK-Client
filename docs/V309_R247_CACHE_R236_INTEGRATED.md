# R247 Chat A canonical cache R235/R236 integration — independently executed

Date: 2026-10-17. Based on actual private R242 canonical source, not donor whole-tree replacement.

## SHA-pinned one-file merge
- Full R235 donor archive SHA-256: `fac5e4019f140ddcf870dbca1adb8515cc0ebce231a2b67860aed7ca0180e57f`.
- Full R236 donor archive SHA-256: `374ea0ef81da56fa82b6eb9f247e53bb08ff8ccb2133c533d8a4f6bad91b8ad0`.
- Exact `src/rs/cache/updater/assets/CacheUpdateTransaction.java` chain:
  - Canonical R242/R234 `bc08aff2ddd3948f5ea8c248100234a39ee03cafd66b24e27b48c85e91aa2cad`
  - R235 `39ae628442d65e6813f85322d126356f3e8bc1dc8d881c5a7a4247a6ff430d0a`
  - R236 `d63d0cc78f27af4452307646c098cd35ceac2584283f0f612b862cd18a306b72`
- Both donor ZIP CRC checks passed. Each changed-only embedded donor source and backup match the exact required SHA values. Replaced ONLY the canonical helper, kept all 1,276 other Java sources unchanged; old source tree remains intact.

## Actual independent build and regression
- Actual javac `--release 11 -proc:none -g:none -encoding UTF-8`, exact compile-only dependency set: **1,277 Java → 1,386 classfiles, zero errors**.
- **21 compatible Java regression programs exit 0**, including new R235 rollback-origin witness and R236 origin-consistency programs. **20 execute substantive checks on Linux**, Windows-specific R228 case-alias reports NOT_APPLICABLE. Two incompatible donor downloader programs continue excluded (not passes).
- Newly rebuilt class-only JAR SHA256 `72d8c76df780b3f9f00751fefd1be3ab5ca45c468b0ae7792cf78c1cec6711fc`.
- Complete private source, rebuilt JAR, dependencies, 21 test logs and test sources packaged under SHA256 `c7b4a64aa464a53b516cabe1322071ff40ab7ba20743ffad4c7d69b76ed7299f` (outer ZIP CRC PASS).

## Still pending
New R247 production JAR has **NOT** had GUI Xvfb replay, localhost login challenge, Windows launch, successfully authenticated world entry, or real power-cut testing. Previous GUI/rejection evidence is on R242, not R247. The R244 login-success-path static audit remains static only. Source-only original-v309 milestone #1004 remains separate from runtime reconstruction. Proprietary complete Java is retained privately, not in this public GitHub commit. Keep #1084 DRAFT and do not merge donor PR #1129/#1130 blindly.
