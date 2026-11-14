# R389 — native Windows ZIP class-order reproducibility repair

**Repo:** Trexzo/SpawnPK-Client. **Base:** R388 draft PR #1182.
**Keep DRAFT/UNMERGED and Source-M1 private-source release gate CLOSED.**

## What was found on the authorized Windows PC

The original R386 one-layer owner-private bundle was already present in an isolated TEMP workspace. SHA-256 verified:
- One-layer private archive: 4bd59b939a27c6aa4a8a4111201dbfb8e188bdd4636a96e593c7bba59d524741
- Private R381 kit: 902e3b583840073c095ea51c5fe5bee4034340ab92bd19dc7c36f3173f092f96
- Linux reference JAR: ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3

The first native Windows full-source build compiled all 1,277 Java sources to 1,388 class files, whose bytes matched the Linux reference, but the generated JAR SHA-256 was different: e80076437e630c649a761ce5810b9fa355348da065dc003c8bb06780f12d7054. The class comparator classified the failure as CLASS_BYTES_EQUAL_ARCHIVE_DRIFT with zero missing, added or changed classes; ZIP entry metadata differed.

## Root cause and verified fix

The R383 builder used native Path object sorting of compiled class files, creating a host-dependent ZIP entry order. R384 already canonicalized each entry's ZIP metadata, but did not ensure deterministic ordering. R389 changes the single ordering expression to sort by p.relative_to(classes).as_posix(). The R386 orchestrator updates its exact runner SHA pin to d09947d5863fc361e7f8362fbcabe5e100452d160ee69fee089f5fb6106944af.

On the owner Windows device, the patched copy ran a **new, isolated native JDK21 full-source rebuild**. Its generated class count and both output JAR and reference hashes matched exactly:
- Generated classes: 1,388
- Native Windows status: R386_WINDOWS_FULL_BUILD_PASS
- Class comparison: EXACT_HASH_MATCH; zero missing/added/changed classes
- Built JAR SHA-256: ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3

This is **reference rebuild reproducibility**; not proof of parity to the original v309 binary, client behavior, GUI/login or runtime compatibility.

## Public changes and CI

Only public-safe tooling changes and tiny synthetic tests, Windows/Ubuntu CI and this report. Nine new tests pin both exact source scripts, assert explicit portable sort order and deterministic ZIP creation, and exercise unsafe entry refusal. Inherited R386 synthetic checks remain in CI. Hosted workflows never receive the reconstructed Java sources, private dependency JARs, original client or resource companion.

No private owner bundle, original-v309 binary, compiled JAR, cache, credential or production client content has been committed. No source release, staging cleanup, live v312 modification or updater change is authorized.
