# R196 — original v309 MIDI/audio Java class completely reconstructed

CLIENT original-source restoration, stacked on [R195 #1089](https://github.com/Trexzo/SpawnPK-Client/pull/1089), milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## Entire original JVM owner, not declarations

SHA-pinned original v309 JAR:
`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

Exact original `rs/w/c.class` SHA256:
`5583878cbaa84b8a34013a19605d3e1cc53f840a35d711abdb64a2a31df85ff5`.

The original class contains **6 fields, 11 JVM methods, 263 decoded JVM instructions** and real Java Sound API behavior (Synthesizer, Sequencer, Mixer/FloatControl, MIDI channels, Receiver, ShortMessage, MetaMessage and a method-reference lambda). The private original-named `rs/w/c.java` has been reconstructed and independently compiled with `javac --release 9 -g:none -proc:none -implicit:none` and an EMPTY original/external classpath. It requires **no compiler-only helper classes** to compile.

The recovered source covers all original code:
- Constructor initializes the original volume field to zero.
- Two string getters and two setters.
- Overloaded volume/control setter `a(double)`, `a(double,boolean)` including gain control and both synthesized MIDI-channel fallback paths.
- MIDI ShortMessage receiver broadcast to 16 channels and original exception handler.
- Empty `c()` method.
- `d()` sequencer initialization, file loading, audio output routing and original `this::a` MetaEventListener invokedynamic method reference.
- MetaMessage handler `a(MetaMessage)` that resets volume on type 3.

A locally audited `javap -p -c -v` comparison matches **all 11 methods and all 263 original JVM instructions**, including original instruction offsets, resolved symbolic field/method operations, branch targets, all original catch-table entries and 18 StackMap frame entries. The initial reconstruction had two different backedges in MIDI channel loops (one null check skipped on subsequent iterations); those were corrected to reproduce original null-check-before-each-iteration semantics, yielding exact JVM Code.

Private one-source ZIP SHA256:
**48989772d86d2014aaa86179962a8d5c0d5fe8323476b46b0806797e511cc2dc**.

Source text SHA256:
**58a814d4346a02faba89d47a61505fb24171588677eeb00b637a6536f32cfa12**.

No original sequencer/synthesizer, audio hardware, client runtime, live-server connection or MIDI behavior was executed. All analysis is compile-only and disassembly-based. Do not claim classfile byte identity or runtime acceptance until explicitly separately established.

## Integrated original-source progress

An independent single JDK21 Java9 source-only build now compiles **eight real original-evidenced Java owners** (rs/q/a ISAAC, rs/v/a Signlink, rs/v/a$a direction enum, rs/k/j OS enum, rs/secure/a Linux, rs/secure/b macOS, rs/secure/c Windows, and rs/w/c MIDI) with only **one** remaining NONORIGINAL compiler-only declaration helper, `rs/f/a` configuration. This fake dependency is explicitly excluded from the recovered original source tree.

The original Signlink outer class still passes the existing semantic acceptance for **all 24 JVM method bodies, 870 original decoded JVM instructions**, modulo 35 known `ldc` vs `ldc_w` constant-pool index width differences. Non-byte-identical synthetic enum aliases and StackMap/non-Code metadata limitations remain separate.

## Real whole-client Java source compiler frontier

The SHA-pinned previous R195 private original Java overlay contains 1,285 files, ZIP SHA256
`99b852851b198d526596c9feb43a41572bf8519ad40245b2e7a221255c22a9a9`.

New experimental private R196 original MIDI overlay adds exactly `rs/w/c.java`, preserving ALL previous 1,285 source files byte-for-byte. Result: **1,286 Java files** in ZIP SHA256
**f248c92c9bea9047a2282b826b8003095935093680f4ba25c6d3dee435a5b00f**.

Both snapshots use identical isolated source-only JDK21.0.12.1 `javac -J-Xmx4g --release 9 -g:none -proc:none -implicit:none -Xmaxerrs 10000 -classpath EMPTY -sourcepath EMPTY` with no original client binary or invented helper source in the experimental tree.

| Private Java snapshot | Java files | Exact javac errors | Result |
| --- | ---: | ---: | --- |
| R195 seven-owner source | 1,285 | **2,343** | Failed |
| R196 eight-owner source | **1,286** | **2,341** | Failed |
| **Change** | +1 | **−2** | Still fails |

R196 complete JDK-only Javac stderr SHA256:
`28c7d389a95b66aa1d4460fe6591b8510a971585e340594d90d4283b67399ca4`.

This is a genuine two-error improvement for one exact SHA-pinned tree transition; not a fully source-compiled client. Do not compare it directly to similarly numbered R179 Packet candidates unless the original Packet Java is overlaid on the SAME exact source snapshot.

## Public GitHub verifier and boundary

The new R196 Python verifier runs the established exact-original-class `_strict_inspections` Java9 source-only proof across 11 methods and six fields, verifies original class/source SHA pins, forbids external/original compiled class fallback, and returns clear no-runtime/no-redistribution claims. Its private overlay wrapper preserves 1,285 existing Java file bytes and remeasures identical JDK-only full-source compiler error counts. Hosted CI uses only independently invented Java9 MIDI-shape test classes, mutation tests for channel loops and MetaMessage, wrong digest/owner/member counts, and synthetic source ZIP byte-preservation.

**Remaining direct original Signlink dependency:** `rs/f/a` configuration owner, with a large static field inventory and nested types. Other unrelated third-party/library source dependency errors still account for thousands of compiler diagnostics. Whole original v309 client compilation and safe, licensed release remain blocked; source-only tests do not validate audio runtime, user permissions, networking or game interoperability. Keep R196 PR DRAFT.
