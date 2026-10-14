# R151 — original matrix constructors, identity and zero operations recovered as Java

Client-only, continuation of [R150 #1037](https://github.com/Trexzo/SpawnPK-Client/pull/1037). The target is still the complete original-evidenced v309 recovered-source tree, milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## New original-v309 partial source evidence

The initial R150 private Java recovery independently compiled six method bodies matching 95 of the original matrix JVM instructions, but required a clearly unverified reset-method placeholder. R151 **removes that placeholder from the private candidate** by independently reconstructing the actual 4x4 identity-matrix reset implementation. It also reconstructs the 4x4 all-zero reset plus two constructors that have no original Packet dependency.

A private isolated Java9 recompilation using the exact original class owner and method descriptors, with no original v309 game binaries on the compiler classpath, now yields:

| Original matrix implementation (private Java) | Exact matching JVM instructions |
| --- | ---: |
| Previously recovered six methods (copy, uniform scale, three-axis scale, add, hash, equals) | 95 / 95 |
| Public zero-argument constructor (allocate 16 floats; reset identity) | 9 / 9 |
| Public copy constructor (allocate 16 floats; invoke copy) | 10 / 10 |
| Internal identity-matrix reset (16 explicit float assignments) | 81 / 81 |
| Public zero-matrix reset (16 explicit zero assignments) | 81 / 81 |
| **Total across 10 real recovered method bodies** | **276 / 276** |

The private original-v309 class SHA-256 is 52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030. This 276-instruction claim is an independent real private `javap -p -c` comparison, with original and Java9 recompilation separated from the game runtime. It does not assert full Code attributes, unselected original methods, static pool semantics, or class equivalence. Actual original-source binary parity needs the official R150/R151 strict normalized-bytecode runner applied privately as its distinct acceptance gate.

This stage improves real recoverable Java **behavior**, not just audits or mapping speculation. The original matrix has a game-Packet-dependent constructor/loader and other transformation/math routines that remain to be restored. Original source is deliberately kept in private storage; public GitHub contains only verification code, synthetic tests, aggregate evidence and SHA pins.

## Code and CI changes

R151 extends the R150 explicit method allowlist with an **opt-in** for constructor identity `<init>`, while continuing to reject class initializer `<clinit>` unconditionally. Users must supply a private selection of exact constructor descriptors and explicitly pass `--allow-constructor-methods`. Without that option, earlier R150 constructor veto remains enforced. Methods/constructors not explicitly selected are never considered recovered; any synthetic build-only scaffolding is rejected as original behavior.

The strict original-vs-source checks remain all decoded opcodes, offsets, resolved member/constant operands, branch targets, code length, max stack/locals, exception handlers and method access. StackMapTable equality is tracked separately to avoid the R149 mistake of equating instruction identity with full metadata identity. The original rs game linked matrix .class is never a dependency or an executed program.

Hosted Ubuntu and Windows tests independently build synthetic Java9 original rs.Game and non-rs ext.Matrix and prove an original-linked matrix constructor/identity/zero owner is recompilable using only independently reconstructed Java. The tests veto constructor acceptance without explicit opt-in, altered reset constants, class-initializer acceptance and SHA mismatches. R150 six-method regression must remain green.

Private invocation is R150's normal CLI with `--allow-constructor-methods` added. The private selection JSON must contain only the four newly verified method identities plus any other separately verified ones; do not put original names or recovered Java in public GitHub.

## Remaining source-tree blockers

Now **ten** original matrix Java method bodies have independent bytecode instruction matches. The original source owner is **still partial**: static pool management, original Packet-dependent constructor/reader, transformation composition and other math methods are missing. The two same-body signed-short Packet methods remain ambiguous as names even though their original B instructions matched. The prior private normalized full 1,271-Java compilation has **516 remaining errors**; no new full-client count is claimed until these partial source pieces are integrated into the whole client and compiled against source-only game-linked dependencies. Rights/provenance checks still apply before public source publication.
