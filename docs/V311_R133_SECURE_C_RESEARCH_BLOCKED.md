# Original SpawnPK v311 R133 — NOT-CERTIFIED `rs/secure/c` reconstruction audit

**Evidence date:** 2026-10-25. **Status: RESEARCH ONLY / BLOCKED, not accepted source recovery.** The original owner-provided v311 JAR SHA256 is `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. This report deliberately refuses to inflate the accepted class or instruction counts.

## A meaningful source-compiler advance, but strict original parity has NOT been reached

A privately held Java9 candidate `src/rs/secure/c.java` compiles from **one source with no game/vendor binary compiler inputs or implementation stubs** and emits one original-named classfile. The real original `rs/secure/c.class` SHA256 is `62b8bf45ecbdcc3bfa6ef1899b11fe398076588b718aad9478af030a5b5f9a79`, **334 original symbolic JVM instructions**. The current **NON-ACCEPTED** source-generated candidate has SHA256 `2a688b4f67711b5a2506e51c144c3602f17c2c8a800c7b274ee2e8cd75e8d13d`, **338 JVM instructions**, with explicit original/candidate bytecode, declaration, exception-table and operand mismatches. Rehashing the candidate is NOT certification.

Current exact instruction-count method audit:

| Method in owner original | Original JVM instruction count | Candidate count | Status |
| --- | ---: | ---: | --- |
| Public constructor | 3 | 3 | Full equivalent candidate instructions |
| Static cached/uncached getter `a()` | 69 | 69 | One important method owner mismatch (see below) |
| Process spawn/time limit `a(String,int)` | 21 | 21 | Instructions aligned, but candidate Exceptions attribute differs |
| Original-install-date stream parser `a(Process)` | 100 | 102 | Generated return/temp and `try-with-resources`/finally offset and exception-table mismatch |
| UTC-install-date parser `b(Process)` | 76 | 78 | Generated return/temp and close offset/exception-table mismatch |
| Fallback multi-locale date parser `a(String)` | 60 | 60 | Instructions aligned; candidate Exceptions attribute differs |
| Static initializer | 5 | 5 | Aligned |
| **Total** | **334** | **338** | **STRICT PARITY FAILED — DO NOT ACCEPT** |

The original uncached getter invokes **`rs/u/a.a:(Ljava/lang/String;)Z`**, an unrecovered game-owner method. To compile with **NO** original game classfiles or fake game implementation stub, the private research candidate calls JDK `Boolean.parseBoolean(String)` at the same invocation site. This is explicitly a **NON-PARITY placeholder**, NOT equivalent to the original method and NEVER exercised in safe behavior probes. It must be restored to the original method owner and proven safe before certification; changing constant-pool metadata can in principle retarget an otherwise unchanged instruction, but none has been certified at R133. The candidate also declares checked `throws` where the original's `Exceptions` method metadata does not. Correct original declarations, exception tables and **all 334 instructions** are mandatory before accepting this source.

### Reproducible, side-effect-free bounded evidence

The private research bundle `SpawnPK-v311-R133-Secure-C-Private-Research-Not-Certified.zip`, **SHA256 `2a014016c7e60bb4e15c004e41b8134caec7d2c06cd462ef3bf8c7b6b2f862a6`**, **6,102 bytes / five files**, contains one source candidate, a bounded independent Java reflection/cache/date-parsing probe, a strict original-vs-built audit script, a JSON difference snapshot, and README. It has **NO original client JAR, compiled original/rebuilt game/vendor binary, credentials, account or device identifiers, or game assets**. The research ZIP is **owner-private and NOT uploaded to public GitHub**.

The ZIP has been independently clean-extracted and the audit rerun against the exact SHA-pinned original v311 JAR. The result is **`RESEARCH_BLOCKED_NOT_ACCEPTED`** in both original and clean-replay runs, with **334 original versus 338 candidate instructions** and **14/14 matching safe observation lines**. The probe explicitly sets original and rebuilt cached state to **`b=true`** and `a` to fictional strings **before every public getter invocation**, and only exercises **JDK date parsing** with fixed timezone/locale and fictional test dates. **No `systeminfo`, PowerShell, hardware-identifier query, OS command, real environment inspection, network call or actual client/game runtime path was executed.** This is only a bounded behavior result, not a code or runtime certification.

### Correct accepted ledger / next actions

**The ACCEPTED distinct source-recovery baseline remains unchanged from R132: 133/1,184 real original-v311 JVM class identities and 11,822 original matching JVM instructions across accepted source-island builds.** The biggest one-shot compiled original-named source group remains **R129 99 classfiles / 10,150 original instructions**. **`rs/secure/c` is NOT counted**; the genuine original outer `rs/u/a` and its dependency closure remain unaccepted.

R133's concrete next work is to reproduce exact Javac9 resource close/return and `finally` lowering in both `a(Process)` and `b(Process)`, restore original method declaration metadata, and prove the original external static method owner `rs/u/a.a(String)` without adding original game binary compilation dependencies or a fake game implementation. Any prospective fix needs strict original symbolic JVM comparison, exact original exception table, fail-closed negatives including repinned changed JVM instructions, and independent source ZIP replay before increasing the accepted ledger.

[Draft PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) remains **DRAFT AND UNMERGED**, with private reconstructed Java code and original client JAR OFF public GitHub. No manual gameplay, process command or machine-identity test is warranted for this research-only step.
