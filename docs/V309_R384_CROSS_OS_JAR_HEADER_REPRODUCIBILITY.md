# R384 — deterministic Windows/Ubuntu JAR metadata

**Target:** `Trexzo/SpawnPK-Client`, stacked on R383 PR #1178; owner-private source release gate **CLOSED**. Keep this work **DRAFT / UNMERGED**.

## Reproduced defect

The R383 Python build runner produced a deterministic classfile archive on Linux, but used the host-dependent default `zipfile.ZipInfo.create_system` when generating the final JAR. That ZIP central-directory metadata defaults to **0 (Windows)** on `os.name == 'nt'` and **3 (Unix)** elsewhere. The same class bytes, compressed with the same settings, can therefore produce **different JAR SHA-256 values** solely because of the creator OS marker. An expected-hash check on Windows could incorrectly fail even if `javac` generated equivalent classfiles. This is a **packaging defect discovered by static audit and a synthetic reproduction**, not an observed failed private full-source Windows build.

## R384 bounded fix and evidence

- Updated only the *public-safe R383 verification runner* in `tools/r383/verify_private_full_build.py` to generate all classfile ZIP entries through `canonical_class_zipinfo`, explicitly fixing `create_system=3` (existing reference-JAR format), permissions, timestamp and compression.
- The original 24 synthetic contract tests and two new compatibility checks pass, plus six R384 cross-OS ZIP regression tests: **32/32 local synthetic tests**.
- A scratch-only `javac --release 11` classfile/JAR probe passes on Linux JDK21 and is available in the new Windows/Ubuntu CI workflow. All ZIP contents in these public tests are synthetic.
- Rebuilt all 1,277 private R381 Java source files from the SHA-verified private kit on Linux JDK21: **1,388 classes** and **exact original JAR SHA-256** `ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3`. No recovered Java source or binary dependency changes.
- Verified the reference JAR's 1,388 entries consistently specify ZIP creator OS **3**.

## Important outstanding acceptance gate

The owner Windows device `DESKTOP-LTXXO4K` remained **OFFLINE** when R384 was prepared. Thus full private-source Windows compilation and byte-for-byte Windows JAR reproduction are **NOT TESTED**, even if hosted Windows *synthetic* CI passes. The ZIP metadata fix removes one known discrepancy; actual Windows compiler output, JDK patch compatibility and filesystem behavior can still differ. Never infer full game runtime, v312 compatibility, safe staging cleanup, power-loss durability or production-readiness.

The recovered source, private kit, compiled candidate, updater, v312 installation, user caches and original v309 client remain untouched by this GitHub change.
