# R148 — exact-v309 float bitcast call-edge witness

**Client-only** original Java source recovery, stacked on [R147 #1034](https://github.com/Trexzo/SpawnPK-Client/pull/1034), with final goal [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

R147 obtains 20 strictly unique access/erased-member-signature candidates within the 91 declared members of the original binary `rs/x/e` ↔ source `rs/io/Packet.java` owner. But 71 member names (especially **37** original public no-argument `int` methods) remain ambiguous on member shape alone. R148 adds an **actual body/callsite context constraint** to narrow ONE ambiguous integer callee via the R147-unique float caller.

## Evidence from original v309 and candidate Java

An independent private disassembly of the exact original-v309 `rs/x/e` owner and inspection of SHA-pinned decompiled candidate Java show the original's sole public `()F` method `s` has exactly these JVM instructions:

```text
aload_0
invokevirtual same-original-owner r:()I
invokestatic java/lang/Float.intBitsToFloat:(I)F
freturn
```

The corresponding candidate source's unique public `()F` method is `readFloat()`, whose entire method body consists of `return Float.intBitsToFloat(this.method2826());`. This produces a **context-grounded candidate** original `r:()I` ↔ source `method2826():int`, rather than guessing an identifier from method order among 37 same-shaped original methods. It does NOT mean the integer reader's underlying bytecode is equal: method call provenance, bytecode, dependencies, and complete source parity still require independent acceptance.

## Implementation

The pinned-private runner requires the full R146 original JVM+candidate Java owner shapes and RSA-literal corroboration, then R147's unique-member shape partition. Its own trusted Java 11 `JavacTask.parse()` helper accepts exactly **one** float zero-argument source method with one return expression consisting of `Float.intBitsToFloat(this.<single uniquely declared int() method>())`. No implicit receiver, arithmetic, additional source statements, overload guess or alternate method conversion is accepted. Independently decode original JVM classfile's original float method and require exact **four opcodes** `aload_0 invokevirtual invokestatic freturn`, exact bytecode length, no original field operations or exception handlers, first invocation target the same original owner `()I`, second `java/lang/Float.intBitsToFloat:(I)F`. Verify the target original `()I` method is uniquely declared by full descriptor/name and belongs to a shape-ambiguous original group (so this is genuinely NEW evidence, not a duplicate R147 unique seed).

The tool outputs a SHA-pinned **aggregate-only report** by default with one additional call-edge-correlated candidate, original shape-group size, opcode/AST booleans, witness digest and explicit rejection of source method-body or bytecode parity, name acceptance, full compilation or redistribution. Optional `--fresh-private-identifier-map` writes exact original/candidate method names to a new **private-only** file; never put it in public GitHub issues, PRs or hosted CI. No original client or candidate Java is executed.

### Private exact-input invocation

```text
python -m spk_recovery.private_v309_packet_float_call_anchor_r148 \
  PRIVATE_ORIGINAL_V309.jar PRIVATE_DECOMPILED_SOURCE.zip FRESH_PRIVATE_SUMMARY.json \
  --source-sha256 2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536
```

Full original-v309 JAR expected SHA-256 is `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Cross-platform synthetic tests compile original JVM Java classes with two same-shaped `()I` readers and one forwarding `()F` method, plus independent source Java with different names. Tests require the one anchored mapping and reject changed original float code, implicit/altered source call shape, RSA mismatch and hash mismatch. Hosted synthetic fixtures carry NO original private source/JAR/assets.

**Limits:** an independently inspected callsite shape is not full source compiled method parity; R148 must not add any guessed int readers, accept all original 37 method names, claim byte-identical recompilation, or change the independently measured **516** remaining v309 Java compiler errors. The next step is direct original `r` method body and source `method2826` method operand/field parity and then the matrix's separate `B:()I` decoder mapping.
