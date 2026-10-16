# R212 — complete v309 source rebuild plus resource-aware offline UI acceptance

The exact v309 reference JAR is available privately and its SHA-256 is pinned (`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`). R212 changes only the candidate Java regression test `rs/plugins/loottracker/LootPanelCheck.java`. Its raid-wing icon test previously asserted two different icons even when both specialized sprite files were unavailable, contradicting the production fallback rule. R212 requires distinct icons only when both specialized sprites are actually loaded; otherwise a generic raid mark is permitted. No production gameplay, protocol or UI source class was changed.

A private, local-only resource overlay was generated from the exact original v309 JAR and used solely for offline test execution; none of its font or image bytes are in the delivered ZIP. With source-built JAR, authentic non-game v309 libraries, and local resources on the Java classpath, **all ten offline application checks passed** (previously 9/10). Note that optional loot-specific icon files still generate fallback warnings; this is not proof of visual pixel parity.

A full clean `javac --release 11 -proc:none -g:none` replay over all **1,275** private Java sources succeeded with **zero compilation errors**, generating **1,376** classfiles. This is source compile acceptance, not full GUI launch or original bytecode equivalence.

Private artifact: `SpawnPK_v309_R212_COMPLETE_BUILD_AND_TESTS_PRIVATE.zip`, SHA-256 `cca00626e9609de79ec2c4949c2f3e2284cbb6b499c278f80f99edee9c84237f`. Contains all sources, source-built JAR, approved non-game dependency libraries, revised hash-checked PowerShell rebuild and optional owner-local resource overlay scripts, compiler output, tests and manifests. Exact original proprietary font files are deliberately excluded.

Remaining acceptance: user-machine graphical launch with resources and strictly local-only network destination, inspection of real sprite cache, complete source-to-original v309 binary/API parity and end-to-end gameplay/network verification.
