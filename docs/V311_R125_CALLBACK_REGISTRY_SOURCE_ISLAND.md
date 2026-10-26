# Original SpawnPK v311 R125 — privately source-recovered callback scheduling chain

**Evidence date:** 2026-10-24. Pinned owner-provided original v311 JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Original game JAR, owner-private reconstructed Java source, source verifier/archive, compiled game binaries and vendor assets are **not** uploaded to public GitHub.

## Three NEW authentic original JVM class identities

| Original classfile | Role | Owner-original SHA256 | Privately Java9 rebuilt SHA256 | Exact original JVM instructions |
| --- | --- | --- | --- | ---: |
| `rs/h/b.class` | No-argument one-shot `invoke():void` functional callback interface | `a3a68a364e5c09d0c00c60816b3e92ed77517e801eee419664753933c837f578` | `bc2f52744886966d4ce8afae52dca63a4dd033b0f9fd38c975b6ea9e8348ce81` | **0/0** (interface declarations) |
| `rs/h/e.class` | No-argument repeat-until-false `loop():boolean` functional callback interface | `31c76d395cbc42e3146031208a4a4b1a8dfc4c9ec22b2a73d3f06a80fe6326e8` | `5175c1c3d591d31e4745fdc8f09ae4fd18cfb918ccf44cde9de98f7cf91eb1e9` | **0/0** (interface declarations) |
| `rs/h/c.class` | Queue/registry with CopyOnWriteArrayList and separate one-shot / repeating ConcurrentHashMaps | `279754600b461d48869a31e882a80b781d83d302113b532c23684d4f4da1dd06` | `3be9f0e220b59d90057b1f95c070af8133d3ea23aa7b175245b6071a4cf6e943` | **121/121** |
| **NEW R125 acceptance** | | | | **3 original identities / 121 instructions** |

The **three original-named outputs** are compiled together from **exactly three private Java source files** using `javac --release 9 -proc:none -g:none` with an **EMPTY compiler classpath and sourcepath**, ZERO original game binary dependencies, ZERO vendor binaries, ZERO source implementation stubs, ZERO temporary outer donors and ZERO compiler aliases. The registry's full original declarations, method and field descriptors, operand symbols, bytecode offsets and instruction sequence match `javap -p -s -c` output with only numeric constant-pool indexes normalized. This does **not** claim original author-written source text or bitwise full classfile identity.

A 32-line original-vs-rebuilt Java reflection and behavior probe checks all three generic registry field signatures, public interface return types, queue invoke-once and clear semantics, keyed replacement, recurring callback removal when `loop()` returns false, CopyOnWrite snapshot behavior and reflection method shapes. **32/32 lines exactly match WITHOUT ANY original JAR as a fallback at rebuilt runtime**. Original JAR is used only on the separate original-baseline process. This is **genuine bounded source-island static/runtime closure**, not closure of the original full client.

## Private clean archive replay and fail-closed trials

Owner-private archive `SpawnPK-v311-R125-Callbacks-3-Class-Private-Sources.zip`, SHA256 **`8ceef1f569480abab9c7d68dd7f1c83bf8837bdfb7acbf0576c1dd8eb4795138`**, **9,049 bytes / 8 entries**, contains private Java source, original hash manifest, probe and verification tools. It contains **NO original client JAR, compiled game/vendor binaries, assets or credentials** and remains **off public GitHub**.

Independent **fresh extraction** was recompiled and checked against the same exact owner-v311 binary: **3/3 original named outputs, 121/121 authentic original JVM instructions, 32/32 reflection/behavior observations**, verified fixed original/compiled/source/tool/probe hashes. **8/8 negative cases refused**, including edited source, missing source, added fake source stub, modified probe, modified verifier, inflated cumulative class count, wrong original JAR and a **genuinely changed callback lookup JVM instruction** with **BOTH edited Java source SHA and newly built class SHA re-pinned**; original JVM parity still rejected it with `ORIGINAL_JVM_PARITY_MISMATCH`.

The [public fully synthetic Java9 callback source-island regression](../tests/test_v311_synthetic_callback_registry_source_island.py) uses **only unrelated fictional types and code**: two toy interfaces and one toy registry, repeatable deterministic Java9 outputs, real headless callback behavior, and rejection of a real changed JVM algorithm after valid newly computed candidate source and class hashes. Its two local tests passed. **Public hosted CI is independent and cannot certify private owner-JAR parity.**

## Verified recovery accounting and missing original parent

R124 accepted cumulative original-v311 **122 DISTINCT class identities / 10,349 authentic matching JVM instructions across multiple separate private source-island builds**. R125 adds **3 NEW class identities / 121 NEW instructions**:

- **New distinct accepted ledger: 125 / 1,184 original class identities, 10,470 original JVM instruction matches across SEPARATE source-island builds.**
- **Largest ONE previously integrated original-named Java9 build UNCHANGED at R124: 94 classfiles / 9,153 original JVM instructions.** R125 independently compiles only three classes. There is no 125-class common build.
- Original **`rs/f/a` outer** remains unaccepted: its current owner original binary contains **1,348 JVM instructions**, reads/writes game configuration and has **11 other direct original project-class references**. Before R125, only four nested environment enums were accepted among those direct dependencies. Accepting **`rs/h/b` and `rs/h/c`** improves this to **6/11 accepted direct original dependencies**. `rs/h/e` is a separately accepted **transitive prerequisite** to `rs/h/c`, not another direct outer dependency. Remaining direct originals for `rs/f/a`: `rs/V`, `rs/l/E`, `rs/n/c/ap`, `rs/n/c/ap$a`, `rs/u/a`. The parent `rs/f/a` is **not** recovered, so no direct closure improvement is claimed for scene model `rs/a/a`.
- The original scene model `rs/a/a` therefore remains **7/14** direct accepted dependencies, and the original renderer `rs/k/e` remains **17/36**. Seven provisional scene/tile types, complete original client, native/GPU graphics, gameplay and bitwise original classfile identity remain unaccepted.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT AND UNMERGED**. No manual game test required for a source-only island.
