# R109 — eight exact original-v309 nonconstant-final field write recipes

## Independent pinned actual-original bytecode finding

The complete original v309 `client(7).jar` is SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Its unique settings-owner class has **126 fields, 41 public-static-final**, 33 JVM `ConstantValue` fields and exactly **eight additional public-static-final fields without `ConstantValue`**. Its original Java9 `<clinit>` has **213 decoded JVM instructions**, exactly **93 own-class `putstatic` writes**. Direct private read-only `javap` inspection verifies **all eight nonconstant final fields are assigned exactly once** by their own original JVM initializer field-reference names and descriptors.

All eight RHS bytecode sites are structurally recoverable without inventing an expression:

| Source-provenance category | Original sites | Exact original opcode window |
|---|---:|---|
| Direct enum constant | 1 | `getstatic,putstatic` |
| Enum identity comparison + two literal branches + invokedynamic String concat | 2 | `getstatic,getstatic,if_acmpne,ldc,goto,ldc,invokedynamic,putstatic` |
| Enum argument to a static String helper | 2 | `getstatic,invokestatic,putstatic` |
| Fixed-length `int[]` allocation | 1 | `bipush,newarray,putstatic` |
| Static String helper + invokedynamic String concat | 1 | `invokestatic,invokedynamic,putstatic` |
| Integer `valueOf` of an original constant | 1 | `ldc,invokestatic,putstatic` |
| **Total** | **8** | **Five non-indy sites, three indy sites** |

## R109 reusable private recovery tool

`spk_recovery.private_v309_eight_final_initializer_r109` operates only on an explicitly selected original owner class inside a complete SHA256-pinned original JAR. It checks the unique 126-field owner inventory, exactly 33 `ConstantValue` fields, eight uninitialized finals, 213 original initializer instructions, 93 own `putstatic` instructions and unambiguous, nonduplicate original assignments. It then identifies each RHS opcode window by **exact shape, field descriptor, JVM member operands**, contiguous bytecode offsets, branch destinations, literal pool types and invokedynamic bootstrap identity. Every String concatenation must resolve to the exact Java9 `StringConcatFactory.makeConcatWithConstants` bootstrap with precisely one `\u0001` variable slot and no `\u0002` constant slots; the two conditional writes must share one bootstrap index and the additional static-helper concatenation must use a different original bootstrap index.

The tool **does not silently guess Java source** for string concatenation or out-of-class helper calls. It emits a **private-only** detailed JSON of the eight actual field identities, decoded RHS instructions (with original literal contents and JVM names), original bytecode offsets and full symbolic invokedynamic bootstrap records. A separate public-safe aggregate carries counts and only the SHA256 of the private exact-operand map. Bad original hash, duplicate putstatic, missing write, altered branch/indy target, unsupported value type or different RHS pattern veto publication. Both files are promoted only on complete verification.

Hosted regression tests use **synthetic 126-field, 213-opcode/93-store initializer profiles** with all six RHS patterns and mutated branch, bootstrap, field, target and array operations. They are structure/provenance tests, not a replacement for private actual-original replay.

## Next step / no false equivalence

The **five direct non-invokedynamic sites** supply bounded source-expression seeds; the **three invokedynamic concatenation sites** still need exact original bootstrap recipes and control-flow/source synthesis. In all cases, **zero** complete owner source expressions have been accepted by `javac` and R58 in R109. R108 independently proves the *33* `ConstantValue` declarations, but the 8 nonconstant final source assignments and 93-write initializer are not yet certified. Nor are R107 full 126-field/ten-method owner source compilation, helper/callback/filesystem effects, or whole-client runtime equivalence.

All original member names, original literal values, source fragments and original JAR data stay outside the public repository.

Private CLI:

`python -m spk_recovery.private_v309_eight_final_initializer_r109 ORIGINAL_V309.jar ORIGINAL_OWNER.class NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA`
