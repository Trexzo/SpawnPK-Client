# R173 — original v309 Packet Java writer method recovery

This work is client-only, stacked on R172 PR #1063. It advances privately recovered original Java Packet source, not the reconstructed server and not a complete original Packet class.

The exact original SHA-pinned `rs/x/e.class` contains twelve additional original byte-writing methods independently reconstructed from JVM Code and recompiled with `javac --release 9 -g:none -proc:none` (no original/game binary classpath):

| Original method | Function | Original JVM instructions |
| --- | --- | ---: |
| `b(int)` | one byte | 13 |
| `d(int)`, `e(int)` | two byte orders | 27 + 27 |
| `f(int)` | 3-byte integer | 41 |
| `h(int)` | 4-byte little-endian integer | 55 |
| `i(int)` | one byte (second original identity) | 13 |
| `j(int)` | indexed byte update with no cursor movement | 12 |
| `l(int)`, `m(int)` | transformed one-byte writes | 14 + 15 |
| `n(int)`, `o(int)`, `p(int)` | two-byte variants | 27 + 29 + 29 |
| **New original body set** | **12 methods** | **302/302** |

The source preserves individual original shift ordering, byte conversions, array indexes and cursor increment semantics. Every original-vs-rebuilt `javap -p -s -c` instruction offset/opcode/resolved field reference matches. The private source contains all 22 R172 verified read/cursor bodies and these 12 writers: **34 original selected methods / 611 matching JVM instructions** in one independently compilable original-named partial class.

Original SHA anchors: complete v309 client JAR `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`; original Packet class `b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2`.

Private source ZIP SHA256: **`0409b9ad3ce72b4b4c7c03c144e16326e39b746de1b3d395375e9480ebeff29e`**. Java text SHA256: **`2bd45ced5180fd2dec43e16fb27f144b76c63c150651006a935e9338ac3fc3ad`**. Original-derived Java remains private.

GitHub R173 adds SHA-pinned source-only Java9 recompilation that requires the SAME verified R172 22-method source, then checks twelve additional original selected JVM methods and 611 total original JVM instructions, rejecting mutation/hash/instruction drift. Independent Ubuntu/Windows tests use synthetic different write algorithms. Hosted CI never receives original client source or game class binaries.

**Not complete:** The original `rs/x/e` Packet superclass `rs/a`, constructors, other methods, pool/networking and class-level attributes remain unverified. No partial Packet source added to canonical recovered-source/v309/src, which remains 1276 files. The last JDK-only full-source javac diagnostic is 2339 errors, not rerun for the partial Packet. Complete original client compilation and original-derived source redistribution remain unresolved.
