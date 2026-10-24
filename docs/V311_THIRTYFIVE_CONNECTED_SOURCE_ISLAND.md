# Official v311 — 35 independently compiled Java classes and repeatable next-class frontier

**2026-10-21.** This is privately verified original-client recovery, not a claim that all 1,184 project classes are reconstructed. Exact original `client(20261021-111920).jar` SHA-256: `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original JAR, recovered Java, original-vs-rebuilt behavior probes and compiled classes remain **outside public GitHub**.

## 35-class connected source compilation

Extended the previous [32-class linked-collection source island](V311_THIRTYTWO_LINKED_COLLECTION_SOURCE_ISLAND.md) with **three original classes**, each of which has a verified direct dependency on already recovered `rs/a.class`:

| Original class | Original exact class SHA-256 | Rebuilt private class SHA-256 | JVM instruction parity |
|---|---|---|---:|
| `rs/B.class` | `f9500103cca433c577da5429305923f2c22a077e1b256bbace161ae580a980e9` | `d779a78b2ab900b1896616a923df33b202bd369909246c2b81402149fd3e612b` | **109/109** |
| `rs/cache/d.class` | `b4876f0a27155338f11226f6d36f72055c87162518e9ab5801ce302017d62cf3` | `fd9b10712dba71d25c61f74b2cc603319e141c204e5a318b8096d8f26274b5d9` | **9/9** |
| `rs/runelite/a/d.class` | `f9c6328d2620b2843de6c83b4f68f343da16ebe12cd11c021225965050dbbdc8` | `5e02c1f478f4213234387fe92e8c0fd8091b7b08ac872a691fa4b03830cd5bd4` | **3/3** |
| **Additional 3** | | | **121/121** |
| **Combined 35** | | | **1,059/1,059** |

All **35 real Java sources** were compiled together by `javac --release 9 -proc:none -g:none` with **no original client/game binary on the compilation classpath**, and only the previously reviewed temporary `rs/t.class` compile-only alias. Exactly **35 Java 9 classfiles** were produced. All 32 previously source-built classfiles match their previous privately verified compiled **SHA-256 byte-for-byte**; all 35 original class declarations and 1,059 original `javap -c -p -s` ordered JVM opcodes, byte offsets, branches, resolved symbolic operands and exception handlers were compared in a fresh **35-way** parallel replay. Only numeric constant-pool indexes were normalized. Source-built binary classfile hashes differ from the original hashes; complete attributes/StackMapTable parity is unproven.

Private compiled class pathname + SHA-256 digest uses sorted lines `class_path + NUL + class_sha256 + newline`, SHA-256: `4710e5c58ab3026db69020cea94bd4886d0b88e1da70d055d934f46564a82c0d`.

### Bounded original-versus-rebuilt Java behavior

A private isolated-classloader test compared `rs/B` ring collection insertion, size, removal, iteration and exhausted-state behavior for the original and rebuilt types. It additionally checked default boolean/zero fields in `rs/cache/d` and the eight default-initialized integer fields and expected `rs/a` inheritance for `rs/runelite/a/d`. Both classloaders produced the **same exact** result:

```
0,2,true,1,true,true,true,true,0|true,true,0|0,true
```

This is real JDK-only original-versus-source-built behavior, **not** game-launch, authenticated client/server, graphical or exhaustive state-space acceptance.

### Explicitly excluded near match

`rs/y/a.class`, a next timer candidate referring to recovered `rs/y/b`, was also reconstructed and compiled, and its method instruction **count** agreed. However, its `c()` boolean branch ordering differed in the source-rebuilt output, so it is **NOT included** in these 35 accepted original-bytecode-parity classes. Mere semantic similarity or successful javac does not qualify for accepted source parity.

## Automating the next connected original-source target

The existing `source_dependency_closure.py` verifies one selected source set. New `source_island_frontier.py` scans a **privately owned, exact SHA-256 pinned original client JAR** and the actual selected original-class SHA manifest, refuses a stale/wrong JAR or incomplete base source dependency selection and proposes only project classes whose explicit original JVM class/descriptor references are **all already selected**. It prioritizes source-name-safe smaller classes and marks original class/package conflicts.

```powershell
spk-recovery original-source-frontier `
  C:\private\client-v311.jar `
  --source-authority C:\private\thirtyfive-source-authority-private.json `
  --max-candidates 30 `
  --out C:\private\v311-next-source-frontier.json
```

The public CLI produces a **private local JSON report**, never changes a JAR, refuses overwrites, records only paths, hashes, dependencies and size estimates (not bytecode/source), and never promotes a candidate to `source_reconstructed`. In the bounded private v311 inventory, the next observed original candidate areas after the 35-class group are the timer `rs/y/a` (parity **not** yet solved) and UI component `rs/ui/components/x` (source **not** reconstructed).

This is **explicit constant-pool dependency closure only**, not dynamic class loading, reflection, ServiceLoader, runtime assets/native dependencies, cross-version semantic class identity, source correctness or full original classfile identity.

Hosted Recovery CI exercises the new original-frontier discovery with small **synthetic Java9 subclass chains**, wrong hash/missing dependency/overwrite refusal checks. It does not access the user's private v311 JAR or reconstructed Java sources.

**Next engineering step:** recover additional dependency-connected original classes with exact source-to-instruction verification, then apply the existing reviewed namespace and class/member lineage tools to larger scene and client subsystems.
