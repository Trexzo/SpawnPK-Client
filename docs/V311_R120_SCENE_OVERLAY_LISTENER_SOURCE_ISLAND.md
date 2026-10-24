# Original SpawnPK v311 R120 — overlay listener registry, two-class private source island

**Date:** 2026-10-24. Owner-provided original v311 JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. **No original JAR, reconstructed original Java, compiled game/vendor binaries or credentials were committed to GitHub.**

## Two genuinely NEW distinct original JVM class identities

| Owner-original class | Function | Original class SHA256 | Source-generated, inverse-restored class SHA256 | Exact JVM instructions |
| --- | --- | --- | --- | ---: |
| `rs/runelite/b/a.class` | Independent static CopyOnWriteArrayList callback registries | `73d0c8b08a81ea73e7718711df64696cb9933c8c27350db4f1a2bb8af905acf5` | `0a8b7fd7b139d099977f9b18d67fb9c6f2c1e1c8a551e7bdcf75917b7a4c709b` | **16/16** |
| `rs/runelite/b/a$a.class` | Nested functional scene drawing callback interface | `958c6bd33b8fc177ae6612f5cc92804efe46e3a995ed237c62f1c9aae53ce028` | `2ace01bb6f5c33bf881c06f3b718e48f107b58ec3a5a0be4ff029ce3c99bd6ed` | **0/0** (declarations/descriptors, no executable code) |
| **NEW R120 accepted** | | | | **2 original classes / 16 matching JVM instructions** |

The interface has **no executable JVM instructions**. Its meaningful evidence is the exact original abstract method `draw(rs.a.a,boolean):boolean`, generic list signatures, nested class and functional-interface metadata. The container class's original ordered JVM instructions, declarations, symbolic field/method operands and instruction offsets all match under original-vs-rebuilt `javap -p -s -c` comparison with numeric constant-pool indexes normalized only.

### Compile-only source alias and explicit limits

Java source cannot declare a nested member with the **same simple name** as its enclosing class (`a$a` inside `a`). The one owner-private Java9 source therefore declares temporary nested `Listener`, and the interface's compile-only parameter type is `Object` because the genuine `rs/a/a` scene model is **not** source-recovered and no original game class binaries are allowed on the compiler classpath. A bounded, reviewed inverse transformation replaces exactly the generated nested interface identity, simple name and **one method-descriptor metadata string** on a *copy* of the generated classfiles. **No executable JVM `Code` or exception-handler instructions are edited.** The final JVM signatures are exact. This is source-generated original JVM parity using explicitly disclosed compile aliases; it is **not a claim of identical original authored Java source**, a standalone complete original scene model, or full original-classfile byte identity.

**`javac --release 9 -proc:none -g:none` compiles exactly one private Java source into two original-named classes**, using only one authenticated real `javax/inject/Singleton.class` vendor binary extracted from the SHA-pinned original JAR. No original game `rs/` class binaries enter the compiler classpath, and no fake implementation source stubs are added.

### Owner-private verifier and mutation coverage

Private archive: `SpawnPK-v311-R120-Scene-Overlay-2-Class-Private-Sources.zip`, SHA256 **`5ed1eb53a3b92515208859c8d6f6cc00b1f07e59634b8bace29aefa05acc087a`**, size **8,685 bytes**, eight source/probe/tool/manifest/readme entries. The ZIP was independently **fresh-extracted** and then recompiled against the exact owner-original JAR. Its content includes **no original game JAR, compiled game/vendor classfiles, vendor JAR or account data**; the complete source ZIP remains owner-private and off GitHub.

All checks passed:
- Exact full original JAR SHA, original class SHA, source/tool SHA, only the two expected compiled outputs, 16/16 original symbolic ordered JVM instructions and interface declaration/signature identity.
- **20/20 owner-original-versus-rebuilt headless Java behavioral/reflection observations**: registry identity, independence, CopyOnWriteArrayList snapshot behavior, generic parameter types and functional method/reflection shapes. The original v311 JAR is only a **trailing RUNTIME metadata fallback** for the still-unrecovered `rs/a/a` interface parameter class; it is **never on the Java compiler classpath**. No isolated complete scene-runtime closure is claimed.
- **8/8 deliberate invalid cases refused from a clean-extracted ZIP**: modified source, missing source, extra source stub, modified constant-pool restorer, modified probe, inflated cumulative ledger, wrong original-JAR authority, and altered **real JVM list getter instruction** with both the candidate's Java-source and compiled-class SHA fingerprints deliberately repinned. The last case fails **original JVM bytecode parity** rather than a SHA guard.

[Public synthetic-only Java9 regression](../tests/test_v311_synthetic_overlay_registry_source_island.py) uses entirely unrelated toy class names, method types and source code. It checks two-class compiler output, deterministic restored metadata and actual source-generated JVM mutation rejection. Public hosted CI is an independent regression test; it **cannot certify owner-private original v311 binary/source comparisons**.

### Recovery accounting

**Prior R119 accepted distinct ledger:** 116 / 1,184 original classes and 10,038 original JVM instructions, across separately verified source builds.

**New R120 distinct class contribution:** +2 original classes / +16 matching JVM instructions.

**R120 accepted distinct ledger:** **118 / 1,184 classes and 10,054 matching original JVM instructions ACROSS SEPARATE private source islands**. Largest ONE source-generated common group remains **R119: 83 original-named classfiles / 8,569 original JVM instructions**. R120 does NOT claim a single compiled 118-class group.

The still-blocked original scene model `rs/a/a` now has **7/14** distinct accepted original direct project-class dependencies (previously 5/14); its own original Java source remains unrecovered. The original `rs/k/e` renderer still has **17/36** accepted direct dependencies. Seven provisional tile classes and full original client, native/GPU renderer and gameplay runtime remain **unaccepted**.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**. No manual gameplay acceptance is required for this source-only milestone.
