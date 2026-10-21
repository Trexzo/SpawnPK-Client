# v311 — eight more authentic independent Java source rebuilds

**2026-10-21.** This records **real original-client bytecode ↔ privately reconstructed Java** results from the user's uploaded official v311 JAR, not synthetic hosted CI, the earlier R308 recovery binary, or a claim of complete v311 source parity.

## Exact authority and independent source build

- Private original: `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.
- Original project namespace contains **1,184 `rs/` classes**, all Java 9 bytecode (major 53).
- Independently reconstructed **eight additional actual original-v311 classes** as private Java. All **eight compile together in one `javac --release 9 -proc:none -g:none -encoding UTF-8` invocation** with explicitly empty compiler classpath and sourcepath, no `rs/` binary fallback, no original JAR on compilation classpath.
- Inspected `javap -c -p -s` for both original and rebuilt classes. Only numeric constant-pool slot indices were normalized; retained declarations, method signatures, exact ordered opcodes and byte offsets, branch targets and resolved JVM symbolic operands.

| Original class | Original class SHA-256 | Private source-built class SHA-256 | Ordered JVM instructions |
|---|---|---|---:|
| `rs/g/e.class` | `00c814f10b0ae596962c431b2b7b698d1c1c06419fb8de00155704017e588241` | `866a680786740c704c8a1e868f66a2fbcfb65a35d3ca2fcbf864eb0e6140d617` | 27/27 |
| `rs/l/e/b.class` | `6ba5d2d7141f0dc99ff3431ecbc9fe951cd6a6ce6412a266c2f77398cc994dbe` | `114b9ea4e1d6aad833def44db9a67ae6856c6866ee8e2602b3119182aca4218c` | 18/18 |
| `rs/l/e/d.class` | `dae2f2a146469286cd85036637e01e195f834682c4367b8e8067a69c507e5b04` | `453e43deb38daffa7f136d216bfc7880a7c22b28e315068395d30ddd4eb6aef3` | 20/20 |
| `rs/plugins/b/h.class` | `99fce84722d3dd5a5e7001fa80b310063fbe683284b9dc77d8e969caa8fec5c1` | `784dba77cbd04da24bea5fea3eeacfe9a5e7c4b46a9ea8caa1aaeb8d6b5a7d02` | 11/11 |
| `rs/runelite/events/ClientStartUp.class` | `a0cb56ad70c2b2cb2ab5996014f99e1e333e1d0896ac30d3cff446ea8a2edfea` | `432dad605fcde23906266830e1418e3301561675526c425f146fa7dbe093cf3d` | 33/33 |
| `rs/runelite/events/MenuOpened.class` | `013c20205d35dafa1619f9bc14c3140e02bc3b4dfadbd38f58dcff0e875f50a6` | `2afcab5887f549ce55a136d0879c60281d0bd423422ad23770aa2ff5f30b9b67` | 33/33 |
| `rs/t/f.class` | `7fb57ece8149dc73db5a898929649998f81a77543da89969405413d6bd3422fd` | `af79a718698ba9af9ac328efed8a6688e8470814f3dc9a58600b83bdc60c8324` | 14/14 |
| `rs/t/h.class` | `54f7a5523be70c0a9b857cd89e79597e1f59b32a190b3e0ec7a3b74b40b17399` | `e30bd7b6c3fb9dc51fe826dd80bd53a62d94f7840fed5ac878822c06abff6050` | 56/56 |
| **Total added** | | | **212/212** |

Combined with the prior [three independently rebuilt v311 classes](V311_FIRST_THREE_INDEPENDENT_SOURCE_REBUILDS.md), this establishes **eleven privately reconstructed, individually compiling original-v311 classes with 259/259 instruction parity**. Do **not** describe all eleven as one compiling source island; the obfuscated Java class/package naming collision below prevents compiling them all together without a reviewed namespace remap.

## Additional real original-vs-source behavior probes

All **eight of eight** classes were loaded separately via JDK reflection using isolated classloaders, once from the exact original JAR and once from the independent source-built class output. Outcomes matched for:

- Thread sleep helper: negative, zero, one, ten and eleven milliseconds (only completion behavior compared; elapsed timing was not equated);
- nullable string selection/data holder updates and integer-list initialization;
- Swing panel preferred size in headless rendering mode (not a live UI test);
- both RuneLite event classes: equality to self, equality to a distinct same-type instance, wrong-type inequality, hash and string representation;
- static float ULP constants and float polynomial evaluation/derivative across selected input cases.

**Exception-table parity:** original `rs/g/e.class` contains two `InterruptedException` handlers. The independently rebuilt class has the same exact two protected PC ranges, handler targets and catch type. This caught a gap in the previous reusable source-parity checker, which refused all exception tables. It now compares exact original/rebuilt handler rows and rejects malformed or changed handlers rather than ignoring them. It is **not** a claim of complete StackMapTable equality or all possible runtime behavior.

The methods with JDK-only implementations are recoverable from bytecode evidence; no original client game, login or server endpoint was executed.

## Real namespace obstacle to a complete source build

The exact original JAR has **1,489 class-path/ancestor-path collision relationships across 88 distinct existing ancestor-class names** within `rs/`. This is a path-level census, not 1,489 individually proven compiler errors. One relevant concrete example:

- Original `rs/t.class` means Java class `rs.t`;
- Original `rs/t/f.class` and `rs/t/h.class` require Java **package** `rs.t`.

These three cannot simply be included as unchanged Java source names in one `javac` build. The eight new classes do compile together because `rs/t.class` is not part of that selected island. Future complete source recovery requires a verified canonical naming and reference remap; compiling against the original JAR does **not** solve the collision and also violates the zero-original-game-binary fallback principle.

The new `require_compilable_source_namespace` preflight checks selected source names before writing outputs and fails on an unrenamed class/package collision. It does not rewrite names, silently exclude classes or declare the full-v311 build solved.

## GitHub verifier and scope

`src/spk_recovery/standalone_source_parity.py` accepts SHA-pinned private original JAR/class entries and privately maintained candidate Java. The verifier compiles selected source files with empty original game classpaths and checks original/rebuilt declarations, complete ordered JVM disassembly and exception-handler tables. It rejects malformed handlers, altered caught types/protected ranges, changed source bytecode, wrong hashes and output overwrites.

Hosted CI uses unrelated JDK-only synthetic Java source, including a real try/catch compiled by Java 9 `javac`. It **does not possess or recompile the eight proprietary Java candidates**; real original/source comparisons were carried out privately.

**Unproven:** complete v311 source compilation, exact complete original classfile bytes and attributes, StackMapTable frames, original source syntax/author provenance, all runtime inputs, original-v309/v310 method lineage, live 50-tile rendering and authenticated server gameplay.

**Next substantive engineering gate:** grow safe original-v311 Java source islands, then resolve class/package naming collisions through the existing reviewed class-identity/remapper pipeline without losing verifiable bytecode provenance.


## v311 compile-only temporary alias: all eleven as one source island

A follow-up **actual owner-private original-v311 replay** combined all 11
previously reconstructed Java files in **one** zero-original-game-classpath
`javac --release 9 -proc:none -g:none` compilation. The original Java
declarations `rs.t` and package `rs.t` cannot coexist in one unrenamed
Java source compilation. A separate, disposable source overlay changed
**only** the owning `rs/t.java` declaration, constructor and self-field
types to temporary `rs.RecoveredNodeV311` under the *same* `rs` package.
The private original `rs/t.java` and all ten other canonical sources were
not modified.

**Measured actual results (not a hosted synthetic fixture):**

- 11 distinct original `rs/` Java source files compiled together;
  exactly 11 JVM classfiles produced, all Java 9 bytecode;
- private compiled-class-path/SHA-256 manifest:
  `0afb856039e8370a8940d758f1610d544ebff261636c79f8afd0f3e47c9711ab`;
- 11/11 verified declarations and **259/259 original ordered JVM instructions**
  match after inverse-mapping the temporary class identity and normalizing
  numeric constant-pool indexes only; the two original exception handlers
  in the sleep helper also match;
- no client launch, server connection, game class binary fallback or GUI
  acceptance is represented by the result.

The recompiled binary class identities are **compile-only aliases**, not
accepted semantic deobfuscation names. The public repository's existing
`classfile_utf8_remap` is now reused by
`standalone_source_parity.verify_standalone_sources` to restore class
identities on **copied output classfiles** for comparison against original
`javap` output. `--compile-alias` makes the review explicit. The original
JAR, canonical source and any compiled/repaired class output remain private.
The tool must reject incorrect original SHA pins, missing/ambiguous references,
unrecognized source identifier uses, unsafe/colliding replacement class
identities, reflective string rewrites and any source-tree mutation.

Synthetic GitHub CI separately compiles two unrelated Java 9 classes with
the same class/package conflict (`rs.t` versus `rs.t.f`) and requires
full declaration, byte-offset and symbolic instruction parity after the
inverse bytecode alias. It also verifies negative paths. The actual private
11-source compilation is **not run in public GitHub CI**.

This solves a *bounded source-island compilation blocker*, not all the
original v311 namespace shadows, Windows path case collisions or full
1,184-class Java source reconstruction. The R125 namespace legalizer and
independent class/member lineage gates remain required for a full client.

