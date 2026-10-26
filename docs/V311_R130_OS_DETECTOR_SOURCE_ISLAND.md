# Original SpawnPK v311 R130 — one privately source-recovered OS detector

**Owner-original pinned v311 JAR:** SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Owner-original JAR, recovered private Java source, private original verifier, and private source ZIP are **NOT uploaded to public GitHub**.

## One genuinely NEW distinct original JVM class

`rs/secure/HardwareValidator.class` is a small JDK-only OS family detector. The original classfile SHA256 is **`71ab8133820198f4cf6d29a89931dbb84d0a36169b64618a6e27f7785c56106c`**; the privately Java9 source-generated classfile SHA256 is **`ac650cf92809da91def4e15e717a09a4bcff58ae889f9de9e8c1d21a7fc038b8`**. Private `javap -p -s -c` comparison demonstrates **79/79 EXACT ordered original JVM instructions**, declaration/descriptor identities, byte offsets and symbolic operands (numeric constant-pool indexes normalized only). The one original-named class is built from **one Java9 source** with `javac --release 9 -proc:none -g:none`, EMPTY compiler classpath/sourcepath, **ZERO game or vendor binaries**, ZERO invented source implementations, zero temporary compiler donors or post-build Code transformations. We do not claim full classfile byte-for-byte identity or the original author's exact Java source text.

### Bounded behavior, security and privacy

Original pinned owner-JAR vs rebuilt JVM comparison passes **96/96 original-compatible output observations**: twelve flags/reflection/main-output lines for each of **eight explicit test OS strings**, including Windows, macOS, Darwin, Linux, AIX, embedded-aix, SunOS and unknown. Both original and rebuilt JVM are launched with explicitly chosen `-Dos.name` strings. The rebuilt process runs **WITHOUT original game JAR runtime fallback**. No hardware serial, unique machine identifier, network access, real machine OS name collection or external system command is used in these tests. The unusual original `aix` index-of condition is preserved rather than silently corrected. This is **not** certification of unrelated original HWID-fingerprinting utilities `rs/secure/a`, `rs/secure/b` or `rs/secure/c`.

### Clean-extracted private acceptance and refusal checks

Owner-private archive `SpawnPK-v311-R130-OS-1-Class-Private-Sources.zip`, SHA256 **`fd9cb1a14a4e6315eb411efd7ccef1a12e9001371f81b2cf022d50fe2e33ce2b`**, **6,851 bytes / 6 entries**, contains the recovered Java source, pinned class/authority manifest, original-vs-rebuilt probe, source verifier, negative tests and README. It contains **NO original client JAR, compiled game/vendor binaries, game assets or credentials**. It remains owner-private and has **NOT** been placed on public GitHub.

Independent **clean ZIP extraction and full replay PASSED**: original pinned JAR/class SHA, source/tool/probe SHA, exactly one original-named rebuilt output with its pinned rebuilt class SHA, original symbolic JVM **79/79**, headless original-versus-rebuilt **96/96 synthetic OS/reflection observations**. **9/9 deliberately invalid candidates REFUSED**: changed source, missing source, extra fake Java source, modified probe, modified verifier, inflated cumulative ledger, wrong original JAR, falsified original-class SHA, and a **REAL mutated JVM OS test** after **repinning BOTH the Java-source and newly compiled class SHA256**. The last passes SHA preflight but fails the direct `ORIGINAL_JVM_PARITY_MISMATCH` check. This verifies that SHA repinning alone cannot falsely certify a changed JVM implementation.

The [public toy-only Java9 synthetic OS gate regression](../tests/test_v311_synthetic_os_gate_source_island.py) contains only fictional identifiers and OS fixture values. It checks deterministic source build, fake OS behavior and a real changed JVM instruction sequence despite rehashed source and class; **2/2 local tests PASSED**. Hosted CI is **independent** and **does not** execute the owner's original-JAR/source comparisons.

### Accurate counts and remaining real blockers

- **Prior accepted cumulative DISTINCT original v311:** R129 **130 / 1,184 original class identities and 11,467 matching JVM instructions across separate private source builds**.
- **R130 genuinely NEW:** `rs/secure/HardwareValidator.class`, **+1 original class / +79 original JVM instructions**.
- **R130 new distinct cumulative:** **131 / 1,184 original class identities / 11,546 exact original JVM instructions across separately accepted source islands**.
- **Largest ONE integrated Java9 original-named group remains R129: 99 classfiles / 10,150 original instructions.** R130 builds a **separate one-class island**, not a 131-class common compilation.
- **Critical dependency caveat:** `rs/secure/HardwareValidator` is **NOT** one of the still-missing direct dependencies of original `rs/u/a`. Its missing direct `rs/secure/a`, `rs/secure/b` and `rs/secure/c` original classes (plus the genuine original `rs/f/a` outer) remain unaccepted. The actual `rs/u/a`, `rs/n/c/ap`, `rs/f/a`, scene `rs/a/a`, renderer `rs/k/e`, whole client/native/GPU/gameplay and the previous nested enum outer-class reflection/invalid `valueOf` mismatch remain unresolved.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT AND UNMERGED**. No manual gameplay, network, sound-device or machine-identifier test is called for at this source-only milestone.
