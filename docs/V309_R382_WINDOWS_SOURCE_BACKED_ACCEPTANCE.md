# R382 — actual Windows source-backed offline acceptance (R381 unchanged)

**Repository:** `Trexzo/SpawnPK-Client`. **Base:** draft R381 PR #1176. The private recovered v309 Java source is **not** committed to public GitHub. **No new Java client-source modification in R382**; this is a Windows test/fixture-portability milestone.

## Tested setup and provenance

- Owner-authorized Windows PC, NT `10.0.26300.0`, Java Temurin **21.0.12.1**, Python **3.12.10**. The default `java` on this PC is Java 8, so test runner explicitly prepended JDK 21.
- Transferred to an **isolated temporary folder** a SHA-pinned scratch fixture ZIP (`ee0a5349…c5eb0789`) containing **10 exact R381 Java sources** for model/store/serializer tests, the historical Java test fixtures, and a test runner; it does **not** include the full game JAR, original v309 binary, private dependencies or live cache.
- Verified the fixture's SHA-256 *on Windows before extraction*. All ten recovered Java files passed manifest SHA-256 checks.
- R381 full private source archive SHA-256 `c5350e964219a36f79584576ce60693d49eec0e5b0ee2138cfcab258aa47bca7`; unchanged full-source JAR SHA-256 `ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3` (the 1,277-file compile/reproducibility previously occurred on Linux, **not** Windows).
- Actual Windows result JSON SHA-256: `52e23870eb2139a56eb00050f5a5a1a7220d48bec518f6ff23cfe0be86dd806a`. The full result stays on the authorized Windows PC; public GitHub carries its hash, exact test inventory and limitations only.

## Test progression — failures retained

| Windows pass | Scripts | Interpretation |
|---|---:|---|
| Initial unmodified R381 harness | 9/15 | Path separator incorrectly rejected stubs in `test_r371_rename.py`; symlink privileges and fixed Linux-oriented assertion counts failed |
| After first fixture-only patch | 12/15 | R371 fixed, but R373 assertion count and R377 symlink probe still required conditional handling |
| Final Windows-only fixture-adjusted run | **15/15** | All offline contracts passed; restricted symlink-only cases are **explicit skips**, never silently counted as executed |

**Fixture-only portability repairs (no private `source/` changes):** replace `str(rel).startswith('rs/')` with `rel.as_posix().startswith('rs/')`; explicitly catch Windows `FileSystemException` where symbolic-link creation lacks privilege; preserve assertion counts for executed cases and accept the documented skip-specific reduced count. All other exceptions still fail tests. The final SHA-pinned report lists every script as PASS.

The 15 scripts cover R369 ordering, R370 version receipts, R371–R373 rename/recovery, R374–R378 staging/durability diagnostics, R379–R381 cooperative locks and session evidence, and isolated store/serializer tests. The R381 session contract reports **32 source-backed assertions**, and R380 folder-lock contract **22** in the final Windows environment. Some earlier counts were different because not all Linux symlink assertions could run here.

## What hosted CI does and does not do

GitHub's four-way Windows/Ubuntu Python 3.11/3.13 workflow validates this public witness, **synthetic-only** result-checking code, and a generic scratch-file Java path/lock/symlink probe under JDK 21. It **does not** have the 10 private Java sources or run the 15 source-backed tests; that evidence comes from the owner PC and is pinned by the Windows-results digest.

## Release gates remain closed

No authenticated game client launch, visual GUI check, reconnect, live v312 integration, original v309 bytecode parity, physical power cut, complete multi-file transaction, privileged Windows symlink acceptance, safe staged-file deletion, or full **1,277-source Windows compilation**. The R381 JAR and source baseline remain unchanged. **DRAFT / UNMERGED; private source publication not approved.** The original v309 JAR, v312 updater, live caches and servers were not modified.
