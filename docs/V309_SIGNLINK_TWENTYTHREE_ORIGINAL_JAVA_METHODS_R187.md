# R187 — original v309 Signlink Java source: 23/24 JVM methods

**Client-only, partial original-class recovery.** Stacked on [R186 #1079](https://github.com/Trexzo/SpawnPK-Client/pull/1079), milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). The last original method, the large run() networking/audio service loop, remains deliberately UNRECOVERED. No canonical source-tree integration, whole-client build success, server emulation, game runtime or source redistribution is claimed.

## Measured, SHA-pinned private-original evidence

Original full client v309 JAR SHA256:
ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38

Original rs/v/a.class SHA256:
d0dc35deddc8016c3fdcaf2615810efa200c042120b83bed86cad5d04b1c0ddc

Private preceding R186 21-method partial Java source ZIP:
051b9f1a50e33422e1480aba3d6db6322894e9142b0cb08fb3e4bb6f88040798

Private R187 expanded original-name rs/v/a.java source text SHA256:
b878041371216339ba58d622e6390e5f51e4023f1e993db4af45027a474b4e58

Private R187 one-Java-source ZIP SHA256:
78d328edb230b5dd211b6f30b2d06f515221815ad1a801c01f3c6309d4acd59c

Compiler-only dependency declaration ZIP (SIX helpers, NOT original Java source):
25e8aa030b1c3f3a02a6148102a6337c16a3bc2f2b84595d825c92cd1c277448

All previous private stage ZIP hashes remain pinned by the verifier (6, 11, 16, 21, and 23 original method candidates).

## New actual original JVM Java-source method restorations

| JVM method | Matched decoded JVM instructions | Source behavior |
| --- | ---: | --- |
| g():String | 82/82 | Original file-store directory discovery over fourteen candidate paths, create/existence logic and exception boundaries |
| <clinit>():void | 23/23 | Exact original static initialization order and 79-byte Code stream for audio support, cache files, thread state, identity strings and flags |
| **New R187** | **105/105** | Java9 source-only independently compiled |
| Prior R186 21 methods | 469/469 | Independently recovered in earlier source stages |
| **Combined 23 of 24 methods** | **574/574** | Selected original JVM Code, not complete class source |

Local isolated Java9 compilation used JDK21 javac --release 9 -g:none -proc:none -implicit:none, no original game classfiles on classpath, and precisely six explicitly unverified declaration-only helper classes. The original and rebuilt javap instruction offsets, opcodes and symbolic operands matched for selected methods; the StringConcatFactory recipes for g() were checked against the original BootstrapMethods table.

**JVM constant-pool ordering:** placing g() after previously recovered methods caused Javac to widen original ldc to ldc_w for 13 short string constants, changing all method offsets. Moving g() earlier in the private Java declaration order restored its original exact 82-instruction / 206-byte Code stream; this also retained prior selected method code layouts. The new static initializer reproduces the original 79-byte Code stream in the original assignment order. CP slot numbers / invokedynamic *indices* themselves are not accepted as semantic identity; the repo's strict comparison resolves symbolic operands and bootstrap recipe content.

## GitHub verifier / test coverage

The new R187 verifier:
- pins the exact original JAR/class, all private prior source stages, expanded 23-method source and the six limited compiler-helper declarations;
- re-runs R186 original 21-method evidence before accepting g()/initializer;
- independently compiles source-only Java9 with empty original/external classpath, checks emitted original owner and exactly the six allowed invented declaration helpers;
- compares 23 original selected method Code streams, including initializer flags, bytecode offsets, symbolic method/field references, resolved invokedynamic recipes, exception handlers, max stack/locals and JVM method access flags.

Ubuntu/Windows hosted CI never receives original game classes or Java. It compiles entirely invented Java9 source fixtures and checks positive selected method/init equivalence, changed g() string literals, modified static initialization, all private SHA pins and explicitly unchanged rejection of the incomplete run() method.

## Acceptance boundary and next

**Original run():void is NOT reconstructed.** Its large original method coordinates sockets, worker threads, hostname lookups, sound clips, music and URL streams; it is original evidence, but publishing pseudocode or compiler-only placeholders would not constitute recovery. Partial original source remains in a privately pinned ZIP and MUST NOT be inserted into the canonical recovered-source/v309/src tree. Field q (original nested rs/v/a$a) and full field/member metadata are not yet accepted; six compiler-helper declarations are not recovered originals. Whole-client compiler errors, original runtime, dependency closure and publication rights remain unverified.

Next recover run() with exact original JVM control flow, try/finally, sound line exceptions and catch-table parity; recover nested dependency source; then independently verify full owner (all 24 methods plus field/method attribute ABI), consolidate privately with R179 Packet and R182 ISAAC, and remeasure one pinned full Java source compile.
