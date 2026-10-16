# R226 — six more genuine v309 Java sources + complete original packet-callback base parity

Stacked on [R225 #1112](https://github.com/Trexzo/SpawnPK-Client/pull/1112). This work moves beyond the individually recovered gambling widget/callbacks by compiling their **actual readable packet base class and real packet buffer implementation**, together with genuine intrusive-node, deque, and ISAAC-like support sources. These are **existing source files from the SHA-pinned recovered v309 Java tree**, not invented method bodies.

## Independently pinned original / real Java evidence

Original v309 client JAR SHA256:
`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

Original packet callback base: `rs/q/a/a/a.class`, SHA256:
`2bc61b580ec34dc8fde828b288f37dc9fef86637d830dc411b43d85b9f0e61bf`.

| Additional genuine readable Java source | SHA256 |
| --- | --- |
| `rs/scriptpacket/Class260.java` | `35c830443eceb92a3402ea2ab034bb50c613ed6543f91d86fe27d9322c9dd94e` |
| `rs/io/Packet.java` | `df4791701d6820b5ce41388be75d40364b2e8e20f08771d854e5fd62b9cf5030` |
| `rs/Node.java` | `dc62405cff406ef20c7c6bc1a33947a6b414246e47e5419fa4609c4ea76ee7b6` |
| `rs/DualNode.java` | `b7c63f2949f5fe7be716974d20a8bf96531b7814dd209de5ea822f15abfdfb0c` |
| `rs/NodeDeque.java` | `791f595d70e3c1500a190ece947a06c291ae30877fe6e2dca40fc2b7c0608dfd` |
| `rs/network/Class257.java` | `b41c145718684053a0820a4af0a45d7bc1e028b0167953e963cafa0fabe6b568` |

Authoritative recovered-source tree SHA256:
`cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.

R220–R221 original spellbook single-class evidence ZIP SHA256:
`4e39cdbf11e2ff5191778228a30da0208538f1cae93ff0730ea97dbd3d289658`.

## Independent source-only Java 9 compile

All **six exact genuine Java files** were compiled as real implementations, together with the existing ten genuine R225 readable owners (including the normalized complete Class179, gambling Class170, overlay Class169 and unchanged callback Class168). The temporary dependency declarations are separate, independently inventoried and are *not* counted as real.

`javac --release 9 -g:none -proc:none -implicit:none -classpath EMPTY -sourcepath EMPTY`

Result of actual private local replay:

| Measurement | R225 | R226 |
| --- | ---: | ---: |
| Genuine readable source owners | 10 | **16** |
| Clearly nonoriginal compiler-only owners | 8 | **11** |
| Total source files compiled | 18 | **27** |
| Isolated Java9 compiler errors | 0 | **0** |

The compiler-only declarations grow because the real `Class260` requires Guice Binder/Injector/Module, while the real Packet requires one retained Class307 signature, and the R225 configuration stub needs one additional `field1313:int` declaration. The synthetic `Class260` stub is gone. Four signature types are added; importantly, the new *Node*, *DualNode*, *NodeDeque* and *Class257* are **genuine Java source, not new stubs**. No full client source-tree improvement is claimed from the isolated 27-file build.

The produced binaries preserve all previously accepted complete class outputs:

- `Class179.class`: `b88820d9893b5a2d5b2ff05f5b88aa6d77dc5ee4a66f377db83758f1590c1c6e` — **identical to R221's 14-original-method / 4,314-op proof**;
- `Class170.class`: `4dddfefb8f688118c2b433ff0afd9c3834018b337ec8a6c255ad0b33b3e01aeb`;
- `Class168.class`: `0604158afc9475bdae752a0e2df7fd64483b2208dd7c571f709239416779db02`;
- `Class169.class`: `cae4619b7ffc5c653f38c22277ae0b6a3c5309f962033aabb2a200da74c16592`;
- `Class260.class`: `4032c94e90c9258a5094128e80c0648d8728128f8932a7b288f2b066e228b299`, now produced from REAL readable Java;
- `Packet.class`: `db27e7c735aa81b99af68b95aded101ba02038ca0929253cc955131`, produced from its REAL Java source.

## Original packet superclass method Code verification

The original `rs/q/a/a/a.class` implements `com.google.inject.Module`, extends `java/lang/Object`, has three instance fields and **13 declared JVM methods**, of which one is abstract `a():void`.

Readable `rs/scriptpacket/Class260.java` retains the matching abstract `handlePacket():void`. Its other **12 concrete method bodies** reproduce the original's **52/52 decoded JVM instructions** with identical byte offsets, operation kinds, constants and control flow after exactly 12 explicit original-to-readable field/method symbolic identity changes. This independently supports the new packet superclass deobfuscation rather than inferring it solely from class hierarchy.

Examples: original field `b:rs/x/e` → readable `packet:rs/io/Packet`, original `rs/x/e.A():int` → `Packet.method3348()`, original bit reads `J() / k(int) / K()` → `method3628() / getBits(int) / method480()`, and original Injector `a` → readable `field4122`.

The mapping SHA256 is `7a7282370e2b2e795675e5f7585dd474fff6d086d3b18a5c5b2e096d61e98973`. A public exact-input verifier enforces the original JAR SHA, class SHA, all six genuine source SHA pins, the full original vs rebuilt method declarations and Code, original class hierarchy/fields, and exact accepted compiled output hashes.

**Important:** While the actual `Packet.java` now compiles as a genuine existing source file, **its own complete original JVM method-Code parity is not established by R226**. The R179 original-named Packet research remains a separate independent workstream and should be reconciled before accepting a full Packet reconstruction.

## Evidence boundary and next step

The hosted Ubuntu+Windows CI uses wholly invented JVM disassembly fixtures and rejects wrong methods, offsets, symbols, aliases and source fingerprints. The actual original JAR and Java remain private and are only used by the independent local replay.

Original gameplay/runtime behavior is NOT executed; original classfile **byte identity** is not claimed. Eleven other compiler-only dependency sources remain. The full original v309 Java tree still has not passed source-only compilation; the last *comparable* R203 private JDK-only baseline was **1,295 Java / 2,358 compiler errors**, and the separate R211 Java11 1275-source candidate with dependencies uses different compiler conditions and must not be conflated with it.

Next investigate replacing the currently fake `rs/graphics/hud/Overlay` superclass with its genuine `Overlay.java`, along with the real GUI overlay family and Trove dependency, while preserving the original Class169 callback binary. Follow by independently auditing the real Packet owner against the R179 original-packet source and then updating a common full-client build frontier. Keep R226 **draft** until real dependency closure and runtime acceptance.
