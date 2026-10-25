# Original SpawnPK v311 R136 — PRIVATE 106-class common Java9 source-build certification

**Evidence date:** 2026-10-25. Owner-provided original v311 game client JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. This is owner-private source recovery, NOT a full original-client/gameplay build. **DO NOT upload owner-private reconstructed Java sources, original JAR, source-verification tools, original/rebuilt game/vendor binaries, device information, or private source ZIP to public GitHub.** This GitHub report is redacted aggregate verification evidence only.

## Genuine integration of 3 ALREADY privately accepted R125 callback original classes

R136 constructs exactly **ONE `javac --release 9 -g:none -proc:none` source compilation of 100 owner-private Java files**, emitting **106 selected original-named JVM classfiles and 10,960 accounted matching original JVM instructions in the largest ONE source build**. The preceding R135 common compilation had **103 selected original-named classfiles / 10,839 matching original JVM instructions**. Every single previous **103/103** R135 source-rebuilt classfile SHA256 fingerprint remains BYTE-FOR-BYTE UNCHANGED.

| Original-named class integrated now | Original instruction parity | SHA256 of original owner class | SHA256 of already R125-accepted rebuilt JVM class |
| --- | ---: | --- | --- |
| `rs/h/b.class` one-shot callback interface | **0/0** (declarations) | `a3a68a364e5c09d0c00c60816b3e92ed77517e801eee419664753933c837f578` | `bc2f52744886966d4ce8afae52dca63a4dd033b0f9fd38c975b6ea9e8348ce81` |
| `rs/h/c.class` CopyOnWrite / ConcurrentHashMap callback dispatch | **121/121** | `279754600b461d48869a31e882a80b781d83d302113b532c23684d4f4da1dd06` | `3be9f0e220b59d90057b1f95c070af8133d3ea23aa7b175245b6071a4cf6e943` |
| `rs/h/e.class` repeating callback interface | **0/0** (declarations) | `31c76d395cbc42e3146031208a4a4b1a8dfc4c9ec22b2a73d3f06a80fe6326e8` | `5175c1c3d591d31e4745fdc8f09ae4fd18cfb918ccf44cde9de98f7cf91eb1e9` |
| **Existing separately accepted R125 source-island integration, NOT NEW** | **121/121** | | **3/3 identical previously accepted rebuilt hashes** |

For all three newly integrated callback classfiles, exact original owner JAR vs private source-generated `javap -p -s -c` symbolic operand, method/field/descriptor/declaration, JVM instruction byte-offset and instruction sequence comparisons pass **0+121+0/121**. The original-vs-rebuilt callback probe matches **32/32** reflection and headless callback behavior observations with **NO original JAR as rebuilt runtime fallback**. `rs/h/b` and `rs/h/e` contain no Code instructions, but their complete interface signatures are independently certified. No original game `rs/` binary classfiles on javac compiler classpath, NO fabricated original-game implementation stubs. The R136 common compiler uses the previous authenticated original-owner-derived **vendor-only** Trove/Google/LWJGL/javax annotation compile inputs, excluded from the private ZIP and public GitHub.

### Twelve prior bounded original-vs-rebuilt behavior groups UNCHANGED

The new integration also reruns ALL **12 previous R135 original-vs-built bounded probe groups** from an isolated exact 103-class projection of the one-shot 106-class output:

| Existing bounded probe | Matching observation lines |
| --- | ---: |
| R111 overlay (+ original sentinel) | 66/66 |
| R120 callbacks/scene | 20/20 |
| R114 UI enums | 20/20 |
| R117 scene node | 24/24 |
| R116 renderer modes | 17/17 |
| R123 environment enums | 53/53 |
| R126 41-entry spellbook modes | 63/63 |
| R128 MIDI fake Receiver | 37/37 |
| R130 8 fake OS cases | 96/96 |
| R131 fake preseeded cached getter | 35/35 |
| R132 fake preseeded cached getter | 39/39 |
| R134 fake Process/date parser/cached getter | 38/38 |
| **Old 12 groups TOTAL** | **508/508** |
| **Plus R125 callback (newly integrated)** | **32/32** |
| **R136 total bounded observations** | **540/540** |

R116/R120/R123 remain **trailing owner JAR RUNTIME-ONLY metadata fallback**, NOT compiler input. R125/R130/R131/R132/R134 do **NOT** need original JAR as rebuilt-runtime fallback. Original R134 `rs/secure/c` StringConcatFactory BootstrapMethods `WINDOWS \\u0001\\u0001` recipe is still separately checked for original semantic fidelity. None of the probes invoke real OS/hardware/serial-number commands (`system_profiler`, `systeminfo`, PowerShell, `dmidecode`, `lshal`), external system process, game network, or real gameplay. All cached hardware paths use synthetic preseeded values and all date-parser processes use in-memory inputs.

### Owner-original outer `rs/u/a` BLOCKER AUDIT (not recovered)

An independent original-v311 `javap -p -s -c` audit now enforces:

- Authentic original outer `rs/u/a.class` SHA256 **`8e5de2d21852923e5837f5977f79e18c0033ffdf82d1fea4f5fb314bdaee461d`** contains exactly **870 original JVM instructions**.
- Excluding self, it directly references seven OTHER original project class identities: `rs/f/a`, `rs/k/j`, `rs/secure/a`, `rs/secure/b`, `rs/secure/c`, `rs/u/a$a`, `rs/v/c`.
- Six of those seven other identities are source-recovered in the common 106-class output: `rs/k/j`, `rs/secure/a`, `rs/secure/b`, `rs/secure/c`, `rs/u/a$a`, `rs/v/c`.
- **`rs/f/a` is still the missing seventh DIRECT original dependency**. Both `rs/u/a` itself and real outer `rs/f/a` are **UNRECOVERED**: compile-only donor owners are discarded, not counted.
- This is **DIRECT BYTECODE REFERENCE COVERAGE**, not full source/transitive closure, full behavioral matching or a runnable original client. The genuine original `rs/u/a` could start threads, create sockets and interact with local game/runtime; none of that was executed or certified.

### Strict negative testing — 24/24 FAIL CLOSED from CLEAN EXTRACTED R136 ZIP

The fully source-only private owner ZIP `SpawnPK-v311-R136-106-Class-Private-Integrated-Sources.zip` is **SHA256 `452ef13f486190e4534947d0fa155a7c23b13b26c79548f11a1e74cbf075d839`**, **407,301 bytes / 222 entries**. It was independently CLEAN-EXTRACTED and both verifiers replayed against the EXACT SHA-pinned original v311 JAR:

- Full positive pass: **100 Java sources → 106 original-named output classfiles in ONE Java9 build**, **103/103 old SHA pins preserved**, **3/3 previously accepted R125 class SHA pins preserved**, original ordered JVM **121/121**, all bounded probes **540/540**, missing original outer audit **6/7** with exactly `rs/f/a` missing.
- **24/24 negative failure tests pass**: all **13 older R135 deliberate-invalid cases** rerun unchanged; ten R136 original/source/compiler/probe/manifest/ledger/outer-audit tampering cases refused; and a REAL callback map-selection JVM code change, recompiled with **BOTH actual changed Java source SHA and newly generated classfile SHA repinned**, rejected on strict original symbolic JVM code mismatch, not simple source/hash preflight.
- Two previous changed-code checks also run under old R135 negatives: a real changed JVM branch AND a real changed StringConcatFactory BootstrapMethods recipe despite identical visible `javap` opcodes.
- ZIP contains reconstructed owner-private Java source, manifests, original-independent compiler/verifiers and safe probe sources only. **NO original client JAR, original or rebuilt compiled game/vendor classes, assets, hardware IDs, credentials or account material.** It is intentionally **NOT uploaded to GitHub**.

Public [fictional, owner-independent synthetic Java9 callback common-build regression](../tests/test_v311_synthetic_callback_common_build.py) is a separate original-free regression, NOT the private original-JAR comparison. Public hosted CI similarly CANNOT attest private owner-original bytecode parity.

### Accepted distinct original source recovery accounting

**Cumulative DISTINCT accepted original-v311 recovery remains UNCHANGED from R134: 134/1,184 original class identities and 12,156 original JVM instruction matches ACROSS separately certified source islands.** R135 and R136 add **ZERO new distinct classes**. Largest ONE private Java9 source compilation grows **R135 103 classes / 10,839 accounted matching instructions → R136 106 classes / 10,960 instructions**. Never label these as 134 jointly compiled classes.

Original `rs/f/a`, `rs/u/a`, `rs/n/c/ap`, scene model `rs/a/a`, renderer `rs/k/e`, provisional scene tiles, original nested enclosing-class/invalid `valueOf` reflection paths, full game/client/network/native GPU/gameplay and real machine-identifier behavior remain NOT CERTIFIED.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT AND UNMERGED**, no gameplay or hardware testing prompted.
