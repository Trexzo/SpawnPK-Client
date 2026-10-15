# R193 — actual original v309 macOS serial Java source and five-owner compiler frontier

Client original-source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004), stacked on [R192 PR #1086](https://github.com/Trexzo/SpawnPK-Client/pull/1086). This is recovery of a **real original JVM method implementation**, NOT another declaration-only stub.

## Original source and full class evidence

The exact original pinned v309 client binary SHA256 is:
`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

Recovered original Java owner: **rs/secure/b.java**, corresponding original classfile SHA256:
`e2c302760621fce745f13619ad7ac079d0bd9dac40444573c64ca45793f0a61b`.

This original class has exactly **one private static String field, three complete JVM methods and 112 decoded JVM instructions**. Private independently reconstructed Java preserves:
- exact original constructor and static initialization,
- the full macOS `/usr/sbin/system_profiler SPHardwareDataType` serial-number reading method `a():String`,
- original IO catches, return-null cases, finally-driven stream closure and caching, and original `MACOSX ` prefix,
- Java9 `javac --release 9 -g:none -proc:none -implicit:none` source-only compilation, with an EMPTY external/original compiled binary and sourcepath.

A local original-versus-rebuilt `javap -p -c -v` audit gives **112/112 symbolic instruction identities, including exact instruction byte offsets**, class owner/super/version/access, original private static field declaration, all three method modifiers, original exception handler table and matching count of StackMap frames. The `MACOSX ` StringConcatFactory recipe remains identical. The original system command was **never executed**. No source derived from this binary is committed publicly.

New private rs/secure/b.java source:
- exact one-source ZIP SHA256 **41470de78250b7a5bdf06aba9e77187ab4cec95fed422e0b05e630f6096e7282**,
- exact source text SHA256 **275eca944d4671d5c433478064e90670a90c2467e7ff912099dc9bc510c3dd34**.

## Real integrated source compiler progress

An additional private `javac --release 9` source-only build compiled **five original-semantic owners** together: rs/q/a (ISAAC), rs/v/a (Signlink), rs/v/a$a (direction enum), rs/k/j (platform enum), rs/secure/b (macOS identifier), plus FOUR separately marked NOT-ORIGINAL compiler declaration helpers for the still-unrecovered rs/f/a, rs/w/c and rs/secure/a/c. The original outer Signlink's 24/24 method semantics (870 original JVM instructions, documented 35 ldc→ldc_w width changes) remain intact. Compiler-only helpers are never counted as recovered original source or executed as a game runtime.

An entirely separate experiment added rs/secure/b.java to the SHA-pinned R192 **1,282-file** private source tree, retaining **all old 1,282 Java source bytes unchanged**, with no invented helper types inserted. The exact new source-tree ZIP contains **1,283 Java files**:

**SHA256: 7ec20525e1e2a51c78199102b46c54bd5b2ae9c0a9cd40783473d21a975e9eab**.

Same JDK21.0.12.1, same isolated `-J-Xmx4g --release 9 -g:none -proc:none -implicit:none -Xmaxerrs 10000 -classpath EMPTY -sourcepath EMPTY` compiler options. No original/client/external classfiles were loaded in either run.

| Private original-client source snapshot | Java files | Exact javac errors | Exit |
| --- | ---: | ---: | --- |
| Prior R192 overlay | 1,282 | 2,346 | Failed |
| R193 + original secure/b.java | **1,283** | **2,345** | Failed |
| **Change** | +1 | **−1** | Still failed |

The private candidate `javac` stderr SHA256 was **0e70deeda709b92cd1976d59e0beeb4db8db83d47710f6ad12aa2abbb7f30308**, and the source file count and diagnostic error summary were checked against the actual compiler output. This is a real error reduction for a strictly pinned source-tree comparison; it does **not** imply any other original classes are restored or that the full v309 client compiles.

## Public GitHub reproducibility

The R193 private-input verifier pins the original v309 JAR SHA, original classfile SHA and recovered original-name Java ZIP, independently recompiles the one real Java owner, and uses the repository's strict R150 bytecode comparator across all three methods, symbolic references, StackMapTable and exception handlers, method flags and field ABI. A separate wrapper builds a byte-preserving private five-owner overlay and compares actual JDK-only compiler diagnostics against its pinned R192 parent.

Hosted Ubuntu and Windows CI run unrelated invented Java9 three-method classes and synthetic ZIP overlay/compile tests only: wrong digest, wrong owner, changed JVM operation, changed method/field inventory, byte-preservation and diagnostic delta refusal. **No original client binary or original-derived Java enters hosted CI.**

## Outstanding acceptance

- Three of the original four other direct secure/config/audio support owners are still required: rs/secure/a, rs/secure/c, rs/f/a and rs/w/c (**four total**).
- Whole v309 original client still fails 2,345 JDK-only compiler diagnostics and has other external/library/source closure blockers.
- The original system_profiler command, client runtime/networking/audio behavior and JVM verifier StackMap acceptance outside the reconstructed class are not tested.
- Exact private-input GitHub runner replay, full Recovery CI, original file licensing and source redistribution rights remain unapproved. Keep PR DRAFT.
- Source file remains private and outside canonical published GitHub source tree until redistribution and full closure conditions are met.

Next restore rs/secure/a and rs/secure/c original Java, then actual rs/f/a and rs/w/c supporting implementations; measure new common source baseline, also combine original R179 Packet recovery without double-counting source compiler snapshots.
