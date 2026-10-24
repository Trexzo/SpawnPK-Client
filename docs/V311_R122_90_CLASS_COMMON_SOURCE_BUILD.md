# Original SpawnPK v311 R122 — 90-class integrated Java9 source-build verification

**Owner-private original JAR:** SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Private reconstructed Java source, original JAR and source-verifier archive remain **off public GitHub**.

## R122 integrates five previously accepted R111 class identities, not new source discovery

**89 source inputs in ONE Java9 compilation produce 90 selected original-named JVM classfile outputs / 8,858 matching original JVM instructions accounted for**, versus R121 **85 / 8,585**. ALL **85/85 R121 rebuilt classfile SHA256 hashes are byte-for-byte unchanged**. The five added outputs each match their earlier privately accepted R111 rebuilt SHA256 fingerprints and original-v311 ordered symbolic JVM instructions:

| Existing accepted identity added to common build | Matching original JVM instructions |
| --- | ---: |
| `rs/l/f/l.class` — 10-position overlay enum | **120/120** |
| `rs/l/f/d.class` — compiler-generated enum switch lookup | **54/54** |
| `rs/l/f/h.class` — switch lookup | **26/26** |
| `rs/l/f/k.class` — switch lookup | **19/19** |
| `rs/l/f/n.class` — switch lookup | **54/54** |
| **Total previously accepted R111 identities newly integrated** | **273/273** |

The four temporary Java switch owner donor classes `DMap`, `HMap`, `KMap`, `NMap` are **discarded**; their real generated synthetic lookup classfiles are transformed by reviewed original-identity metadata-only rewrites. The enum field and helper names are also metadata-restored. **No executable JVM `Code` or handler tables modified**. Previously reviewed reversible Java compiler aliases and the discarded temporary `rs/k/e.class` renderer owner remain. There is still **no complete original renderer source** or whole-game compilation.

Compile classpath: SHA-authenticated owner-JAR-derived real vendor-only Trove, Google, LWJGL and `javax.inject.Singleton` annotation classes; **ZERO original `rs/` game class binary dependencies**, no unreviewed game implementation stubs.

### Owner-private clean-extracted verification

The owner-private `SpawnPK-v311-R122-90-Class-Private-Integrated-Sources.zip` SHA256 **`aa259e4147400e53d4cab5568d5c433caf87e71c27e6a60feb4be7e5fc683795`**, size **277,120 bytes / 166 ZIP entries** was clean-extracted then recompiled and independently checked against the exact owner-v311 original. It contains source/manifests/verifiers/probes, **NO original JAR, compiled game/vendor classes, assets or credentials**. It is **NOT uploaded to GitHub**.

- **90/90** selected original-named JVM output identities; **85/85** previous rebuilt SHA hashes unchanged; new five compiled output SHAs identical to R111 acceptance; original-vs-rebuilt `javap -p -s -c` parity **273/273** ordered instructions, declarations/offsets/symbolic operands.
- Original versus rebuilt headless behavioral observations: **R111 65/65**, **R120 20/20**, **R114 20/20**, **R117 24/24**, **R116 17/17**. R111/R114/R117 rebuilt runs require **no original JAR as a runtime fallback**. R120/R116 retain the previously disclosed original game JAR as **trailing RUNTIME-ONLY metadata fallback** for the unrecovered original scene-model and outer renderer types respectively; NEVER as javac compiler dependencies.
- **9/9 fail-closed negative cases** passed in the clean-extracted owner-private ZIP: unexpected source change, missing source, added fake game source, changed compile helper, changed switch-metadata transform, changed behavior probe, inflated distinct class ledger, incorrect original-JAR authority and **real changed enum JVM initialization order after BOTH Java source and rebuilt-class SHA pins were deliberately updated**. The last is rejected by actual original-vs-rebuilt JVM instruction comparison rather than superficial hash mismatch.
- Unchanged old class fingerprints re-attest build stability; R122 does **not** rerun every historical behavioral test beyond the five probes above.

[Public synthetic-only Java9 integration regression](../tests/test_v311_synthetic_overlay_enum_switch_common_build.py) uses completely unrelated invented toy classes and enum switch donors to test prior-class SHA preservation, discarded compiler donor owners and executable JVM enum-order mutation detection. Public hosted CI is separate; it **does not verify private original-JAR parity**.

### Distinct ledger vs largest integrated group

**Accepted original-v311 cumulative DISTINCT ledger remains 118/1,184 classes and 10,054 original matching JVM instructions ACROSS SEPARATE privately verified source islands**, unchanged from R121. R122 only increases the largest **single original-named source-generated group to 90/8,858**. Do not represent 118 recovered classes as jointly compiled. Original full classfile binary identity remains unclaimed.

### Blocked original scene-model dependencies (direct project-type references only)

Original `rs/a/a` scene model has **7/14 distinct accepted direct original project class references**. The seven unrecovered direct class references and their **uncompressed classfile byte counts in this exact owner JAR** are:

| Not source-recovered original type | Classfile bytes |
| --- | ---: |
| `rs/Client` | 290,805 |
| `rs/a/h` | 100,996 |
| `rs/a/j` | 3,715 |
| `rs/a/k` | 21,039 |
| `rs/d/d` | 42,313 |
| `rs/f/a` | 13,099 |
| `rs/l/f/e` | 7,749 |

`rs/a/j` has the smallest direct classfile, **but is not independently source-closed**: its bytecode references the unrecovered animation/scene dependencies and its original superclass `rs/a/c` is not in the accepted source group. Thus choosing it solely by byte size would understate its closure cost. No provisional replacement is counted. Original renderer `rs/k/e` remains **17/36** accepted direct dependencies; the seven provisional tile classes, full original client/native/GPU/gameplay integration are also unaccepted.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT / UNMERGED**. No manual game verification is required for this source-only milestone.
