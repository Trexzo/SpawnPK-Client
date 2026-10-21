# v311: 25 original Java sources, first explicitly connected class island

**2026-10-21.** Local read-only original-binary investigation and privately reconstructed Java source replay. No original game binary, JDK-disassembled method transcript, generated client classfile, private Java source, credentials or game cache has been committed to public GitHub.

## Exact original authority and real source compilation

Original uploaded `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.

The [previous 23-source compilation island](V311_TWENTYTHREE_INDEPENDENT_SOURCE_ISLAND.md) has been extended by **two real, original v311 dependency-connected Java implementations**:

| Original class | Original class SHA-256 | Privately rebuilt class SHA-256 | Ordered JVM instructions |
|---|---|---|---:|
| `rs/w/d.class` | `de7c2515805f151bbc9379ccdc7cbf2c0539c527b4bcae0f3d43a9006e3788ce` | `7030fd2c937058ed2df0524b8a5f687f9d432f1ae88ec165e09f51a58724dc64` | **120/120** |
| `rs/g/c.class` | `0564e5a197ffeb894f8bd0e4facdad9927485d93eaf1025ebf40b38327202410` | `036b757df9165e8048a513e3ad13ff21df90733399cdc883dac33706d483feb7` | **232/232** |
| **This batch** | | | **352/352** |
| **Combined 25-class island** | | | **734/734** |

In contrast to prior independent data holders, these implementations **reference other recovered original game classes**:

- `rs/w/d` references `rs/w/c`: maintains an `ArrayList`-backed set of timestamped entries, prunes expired entries and counts/sums them;
- `rs/g/c` extends `rs/g/b` and calls `rs/g/e`: the timestamp-adjusted pacing/clock algorithm, its rolling 10-slot history and its sleep helper;
- the three explicit original `rs/` cross-class dependency edges are exactly `rs/w/d → rs/w/c`, `rs/g/c → rs/g/b`, and `rs/g/c → rs/g/e`.

All **25 privately reconstructed Java sources compiled together** via one Java 9 `javac --release 9 -proc:none -g:none -encoding UTF-8` invocation with empty original game binary classpath/sourcepath, using the already reviewed disposable `rs/t` alias. Exactly **25 Java 9 classfiles** were emitted. The original-vs-recompiled declarations, ordered JVM opcodes, exact byte offsets and symbolic operands/branch targets matched after normalizing only numeric constant-pool slots. The previously established two `rs/g/e` original exception-handler entries remained matched. The private compiled class-path/byte-hash manifest digest is `3e9956d028419a3fe6ace78bdf78175aadafe24b05898e2a91f9a604df58feb8`. The four previously compiled dependency/alias class SHA-256s are unchanged from the 23-class run.

The private `twentyfive-source-authority-private.json` records the complete 25-class SHA pins and stays outside GitHub.

## Bounded offline original-versus-rebuilt behavior

A JDK reflection probe loaded the **exact original v311 JAR and the private 25-class build in isolated classloaders**. Two connected subsystem cases agreed:

1. `rs/w/d`: 2 initial entries with values 3 and 7, one ancient and one safely *future-dated*. Before pruning count=2/sum=10; after pruning with a nonzero 10ms expiry count=1/sum=7. An expiry-disabled instance retained both entries. The fixed future timestamp deliberately prevents the observation from depending on elapsed wall-clock milliseconds.
2. `rs/g/c`: monotonic adjusted timestamp, 10-slot rolling clock initialization, reset-to-zero behavior and positive pacing result on a small bounded input. These are **invariant checks**, not exact wall-clock or timing-performance parity.

Both original and rebuilt cases passed; no client game, graphics renderer or SpawnPK server was launched. These do not prove all algorithm branches, concurrent operation or server-facing correctness.

## New fail-closed dependency boundary

`src/spk_recovery/source_dependency_closure.py` parses original JVM constant-pool `CONSTANT_Class`, `NameAndType` and `MethodType` references (including array-class and method/field descriptors, with strict Modified UTF-8 decoding). For a selected source island, the existing `standalone_source_parity` verifier now checks that **each explicit original project `rs/` class dependency is also selected**, after verifying exact original whole-JAR and per-class hashes and **before** it creates output or starts compilation. On this 25-class original input, **25 selected project classes, 3 cross-project class edges, 0 unresolved explicit project references** were independently measured.

For regression purposes, a synthetic JDK-only Java 9 fixture includes a child subclass that directly references its own project base class. Both classes together compile with symbolic JVM parity; choosing the child but excluding its base now rejects the build **before creating an output folder**, even if a compiler might otherwise find a class on an incidental classpath. Additional regressions reject malformed constant pools and preserve the distinction between supported reference types and unresolved dynamic loading.

**Important scope:** this proves closure only for constant-pool-represented class references and descriptors. It does not prove no dynamic reflection, `ServiceLoader`, resource access, native dependency, invokedynamic bootstrap semantics or behavior requiring other game assets. It is stronger than class-count parity but **not** a complete standalone v311 release proof.

The original binary, reconstructed Java and all compiled classfiles are private; only redacted hash/count evidence, verifier code and synthetic CI tests are committed. No historical R308 native Windows game-launch or private ZIP test is needed to validate this source-island milestone.

## Forward recovery task

Find further verified dependency-closed sets around `rs/w/c`/ `rs/w/d`, pacing/clock abstractions or richer RuneLite event/GUI types. Extend the zero-original-game-binary Java source compilation incrementally and retain exact original class/bytecode evidence. Separately resolve the complete 1,184-class namespace graph, semantic class/member lineage and original game runtime only when there is an actionable gameplay or release-level change.
