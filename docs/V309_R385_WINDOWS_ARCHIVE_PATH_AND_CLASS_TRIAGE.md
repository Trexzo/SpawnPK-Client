# R385 — Windows archive path hardening and offline JAR drift triage

**Repository:** `Trexzo/SpawnPK-Client`; stacked on R384 draft PR #1179. **PRIVATE source release gate CLOSED. DRAFT and UNMERGED.**

## Why R385 exists

R383/R384 reproduced a Java ZIP creator-OS metadata mismatch and implemented a canonical classfile archive writer. The genuine owner Windows PC (`DESKTOP-LTXXO4K`) remains offline. It is not responsible to mark the full private-source Windows compilation as passing without running it on that machine.

An audit of the R384 source-verification runner found an additional *Windows portability risk*: a ZIP member can pass traversal / slash checks yet use a Windows device alias (`CON.java`, `COM1.*`, `LPT1.*`, `NUL`, etc.), a component with trailing spaces/dots, or an invalid Windows filename character. Python's normal ZIP extraction is host-dependent. The SHA-pinned private build kit contains none of those cases; this is preventive hardening, not a witnessed failure with the real kit.

## Bounded changes

1. Update **public-only** `tools/r383/verify_private_full_build.py` to reject those Windows-invalid path components before writing any extracted private-kit member. No private source or dependency bytes are committed. The existing per-member source/dependency SHA-256 checks, archive size budgets, case-collision refusal and `javac --release 11` options remain.
2. Add `tools/r385/compare_local_build_jars.py`, a read-only, local comparison that distinguishes exactly identical archives, equivalent class bytes with ZIP metadata/order differences, class byte differences, and class-set differences. JSON reports contain only counts and hashed class IDs (not filenames or class contents). A match is **not runtime parity**.
3. Add the optional `tools/r385/run_r385_windows_acceptance.ps1` wrapper for the connected owner PC, requiring explicit JDK 21 and a **new** output directory. It refuses to overwrite an existing output. It does not launch SpawnPK or touch any production runtime.

## Verification

- **50/50 local public synthetic tests PASS**: inherited R383 (26), R384 (6) and new R385 (18). Synthetic ZIP fixtures cover Windows reserved names, trailing dot/space and forbidden characters, plus class set/bytes/header/order/comment mismatch classification.
- Updated real private-kit verifier accepted the exact SHA-256 pinned R381 kit and checked **1,277** source pins and both binary dependency pins. Full JDK 21 Linux compilation produced **1,388** class files and the expected JAR SHA-256 `ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3`.
- The R385 local JAR comparison of the independently built R384/R385 JARs is `EXACT_HASH_MATCH`, with **0 changed class bytes**. Actual owner Windows compilation **not performed**; this private Linux repeat does not establish it.
- Public GitHub CI (Windows/Ubuntu, Python 3.11/3.13, JDK21) runs **synthetic tests only**. Hosted Windows success cannot substitute for compiling the private source on the owner Windows PC.

## Still not proven

Full private Windows compilation, original v309 JAR parity, actual GUI/game launch and login, v312 compatibility, physical power-cut durability, full multi-file atomicity, process ownership, and safe automatic staging-file cleanup. The original v309 JAR, live v312 runtime, updater, caches and server are unchanged.
