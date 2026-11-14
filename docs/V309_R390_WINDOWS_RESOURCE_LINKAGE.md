# R390 — genuine Windows offline classloader and resource visibility

**Repository:** Trexzo/SpawnPK-Client. **Stack:** R388 draft PR #1182; R387 sibling draft PR #1183. **KEEP DRAFT/UNMERGED.** Source-M1 private source release gate CLOSED. No proprietary binary, recovered Java, dependency JAR or user cache committed.

## Actual owner Windows private acceptance

- Authorized Windows host: JDK21 scratch-only, without connecting to the game, initializing the launcher or touching the live v312 installation.
- Owner-private R386 one-layer archive found in an isolated TEMP workspace and SHA-verified: 4bd59b939a27c6aa4a8a4111201dbfb8e188bdd4636a96e593c7bba59d524741.
- SHA-verified unchanged R381 build-kit: 902e3b583840073c095ea51c5fe5bee4034340ab92bd19dc7c36f3173f092f96.
- R389-corrected Windows rebuild receipt reported R386_WINDOWS_FULL_BUILD_PASS: 1,277 Java sources, 1,388 compiled classes; independently verified rebuilt JAR exact SHA ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3. Initial R388 Windows trial had equal class bytes but JAR archive metadata drift; do not treat that first trial as an exact build pass.
- Scratch-extracted primary dependency R218.jar SHA 008feeece788788fbc61d0a2d7abec5213e3f8560eb39c69b92fa7e84e1ad6eb.
- R388 no-initialization reflection probe re-executed on this *native Windows-built* JAR with the primary dependency: TOTAL=1388, LINKED_WITH_REFLECTION=1388, FAILED=0.
- Class-free resource companion SHA 9a6a23750bedd39f49563c54bbbf89a0214f40e7f8fd8e0b1c08ba3da863fde4, matching the owner's original 419/419 archive entries per R387.
- R390 source-free Java URLClassLoader probe tested classpath [Windows-built candidate, R218.jar, resource companion]. It reported RESOURCE_ENTRIES=419, VISIBLE_IDENTICAL=419, MISSING=0, CHANGED=0, SHADOWED=0, COMPANION_CLASSES=0, LAUNCHER_NO_INIT=PASS.

## Public verification

The public Java R390ResourceProbe loads the launcher with Class.forName(name,false,...), does not initialize it, iterates resource entries, verifies each through URLClassLoader (including actual jar provider) and matches SHA-256 of the decompressed resource bytes. All input JARs were independently SHA-pinned before the genuine Windows run. Never invoke the actual game main method.

Ten source-free synthetic Python/JDK tests verify expected success, deliberate launcher static initializer not executing, missing launcher, altered expected count, duplicate/traversal resources, class contamination and resource shadowing by candidate or dependency. Hosted Windows/Ubuntu CI uses synthetic JARs only.

## Still NOT established

Original-v309 binary/runtime/GUI/login parity, correct behavior of all loaded methods, network behavior, v312 compatibility, automatic stage cleanup safety, power-loss durability and full multi-file transaction atomicity. No production client, updater, original JAR, owner cache or server modified.

The private R389 Windows ZIP-metadata fix is not included in this public R390 change. This PR records observed evidence rather than reimplementing or approving that separate fix.
