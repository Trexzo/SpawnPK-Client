# v309 R389 — exact Windows full-source build and JAR reproducibility

**Repository:** Trexzo/SpawnPK-Client · **Stack base:** R388 draft PR #1182 · **Source-M1 gate:** CLOSED. Keep DRAFT and UNMERGED.

## Verified defect and narrow correction

The genuine Windows build compiled all 1,277 private Java sources into 1,388 classes with **identical class bytes** to Linux, but archive SHA-256 initially differed (e80076437e630c649a761ce5810b9fa355348da065dc003c8bb06780f12d7054). The strict R386 runner correctly refused.

Raw ZIP inspection confirmed all 1,388 local header and compressed streams matched byte for byte, with the **member order different**: Python Path objects sort case-insensitively on Windows but Linux's relative POSIX strings sort case-sensitively.

The only change in the public build verifier is:

    classfiles=sorted(classes.rglob("*.class"), key=lambda p: p.relative_to(classes).as_posix())

The R386 orchestrator's verifier SHA-256 pin was updated to match. **No reconstructed Java source changed.**

## Actual source-backed Windows acceptance — separate from hosted CI

An isolated SHA-verified owner-private kit was rebuilt under Temurin JDK 21.0.12.1 on the connected owner's PC.

- All **1,277** recovered Java source SHA pins and **2** dependency SHA pins verified.
- Full compile generated **1,388** classfiles; class comparator: **0 added, missing or changed**.
- Windows JAR SHA-256 **ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3**, exactly the Linux reference.
- Strict runner verdict **R386_WINDOWS_FULL_BUILD_PASS** (exit 0), production_files_modified=false.
- Linux fresh rehearsal using corrected runner **R386_LINUX_REHEARSAL_PASS**.
- Separate no-initialization JDK 21 classpath fixture loaded/reflected **1,388/1,388** classes; accessed the original resource-only companion's bg.png, glow.png, LWJGL Windows DLL and manifest. Verdict **R389_WINDOWS_HEADLESS_CLASSPATH_AND_RESOURCES_PASS**. No game, GUI, login or network started.

## Public-only regression and release limits

Nine source-free synthetic tests cover case-sensitive canonical sorting, verifier SHA pin, deterministic archive member order and fail-closed statuses. Hosted Windows/Ubuntu CI executes public synthetic inputs only and must not be described as having compiled the private source.

Still unproven: original-v309 bytecode/behavior parity, full game launch and graphics, login/reconnect, v312 compatibility, physical power-loss durability and safe staging cleanup. **KEEP DRAFT, UNMERGED; Source-M1 release gate CLOSED.** Never commit recovered Java code, original binary, dependency JARs, owner caches or resource companion; no production files were modified.
