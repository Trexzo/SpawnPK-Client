# Original SpawnPK v311 R131 — PRIVATE source recovery of original `rs/secure/b`

**Date:** 2026-10-25. Owner-provided original v311 client JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Neither the original game JAR, source-recovered private Java, compiled game/vendor classes, user/device identifiers nor the owner-private verifier are uploaded to public GitHub.

## ONE new, genuine direct dependency of blocked `rs/u/a`

New original JVM class identity **`rs/secure/b.class`**, a macOS hardware-serial lookup/cache support class. The original SHA256 of its owner-v311 JVM classfile is `e2c302760621fce745f13619ad7ac079d0bd9dac40444573c64ca45793f0a61b`. The independently source-generated Java9 JVM classfile has SHA256 `68a0347a384cd17418e0a281bf325f26c11f91622571cf2cdcc4451e7abc4e7d`.

**Original-vs-rebuilt strict `javap -p -s -c`: 111/111 EXACT original ordered symbolic JVM instructions**, identical method/field declarations, return and argument descriptors, numeric instruction byte offsets, symbolic referenced operands and exception-handler boundaries. Original constant-pool *numeric* indices are normalized, not operand semantics. The exact `try/catch/finally` control flow for the macOS lookup method is recreated using compiler-generated JVM code, NOT by editing classfile executable `Code` attributes. This is **not** a full original binary byte-for-byte identity or author-original Java text claim.

Single source `src/rs/secure/b.java` compiles with `javac --release 9 -proc:none -g:none` to exactly ONE original-named JVM class with EMPTY compiler classpath AND sourcepath. **ZERO original game or vendor binary classes, fake game source stubs, compiler aliases or temporary donor classfiles**. The owner-original class includes an uncached path that could execute `/usr/sbin/system_profiler SPHardwareDataType`; **THAT PATH WAS NOT EXECUTED**.

### Deliberately bounded original-vs-rebuilt behavior, no identifier collection

The original-vs-rebuilt **35/35 reflection and cached-getter observations match** using six explicit fake strings, injected into the private static cache `a` by reflection **BEFORE every getter invocation**. The probe also checks class/field/method descriptors, modifiers, private static initial cache and default public constructor. Both baseline and rebuilt processes are headless Java VMs. The rebuilt runtime uses **NO original JAR as trailing fallback**, no process execution, no real device identifier, no file/environment inspection, no network access or macOS profiler call.

This **does NOT** establish independent behavior parity for the **uncached external-command lookup**, which is intentionally out of behavioral test scope even though **all its original JVM instructions and exception table entries match**.

### Full private clean-ZIP replay and fail-closed checks

Owner-private source ZIP `SpawnPK-v311-R131-Secure-B-1-Class-Private-Sources.zip`, SHA256 **`9c134ca2b8fbb6894aed7c968831735355bba416da094e5d290af5fc6ea3e96c`**, **7,300 bytes / six entries** (private Java source, manifest, bounded cache-only Java reflection probe, verifier, negative tests, README). Contains NO original game JAR, generated game/vendor binaries, hardware identifiers, assets or credentials. **MUST NOT be uploaded to GitHub**.

Independently **freshly extracted** and checked against exact SHA-pinned owner-v311 JAR: **one original named rebuilt output, 111/111 instruction and original exception-handler table parity, 35/35 cached-only behaviors with NO runtime owner-JAR fallback**, exact SHA pins for original JAR, original class, rebuilt class, source and tooling.

**10/10 deliberate invalid cases rejected**: edited/missing/extra source, altered probe, altered verifier, altered README, forged prior recovery counts, wrong original JAR, wrong original class SHA pin, and **REAL altered getter JVM conditional after repinning BOTH Java source SHA and recompiled class SHA**. The last passes candidate hash preflight and fails **`ORIGINAL_JVM_PARITY_MISMATCH`**, not a superficial hash check. The non-cache path is NEVER executed by the verification harness.

The [public completely fictional cached-lookup Java9 regression](../tests/test_v311_synthetic_cached_lookup_source_island.py) uses only invented toy class names and no original game/serial retrieval code; **2/2 tests passed locally**, checking deterministic one-class compilation, mock-seeded cache lookup and actual JVM condition mutation after source/class hash refresh. Public hosted CI remains original-independent and does **not** reproduce owner-private bytecode certification.

### Recovery accounting / direct dependency scope

- Previous R130 **131/1,184 DISTINCT original identities and 11,546 original JVM instructions**, across separate privately verified source islands.
- R131 accepts **1 NEW original identity / 111 NEW original matching instructions**.
- New cumulative accepted **132/1,184 original class identities and 11,657 matching original JVM instructions ACROSS separately verified source islands**. Do not represent these as 132 files compiled together.
- Largest ONE common Java9 source-generated original-name group still **R129 99 classfiles / 10,150 previously verified original JVM instructions**. R131 is a *separate one-class build*.
- Unlike R130's `rs/secure/HardwareValidator`, original `rs/secure/b` is a **true previously missing direct dependency of original `rs/u/a`**. `rs/secure/a`, `rs/secure/c` and other game/outer dependencies remain missing. The genuine original outer `rs/u/a` is **NOT recovered**. Original `rs/n/c/ap`, `rs/f/a`, scene model `rs/a/a`, renderer `rs/k/e`, seven provisional tile types, full client/native/GPU/gameplay and R126 nested `getEnclosingClass()`/invalid `valueOf` reflection mismatch remain UNACCEPTED.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT AND UNMERGED**. Neither manual gameplay nor a real hardware-identifier test is warranted for this source-only recovery checkpoint.
