# R108 — exact original v309 126 owner field declarations and 33 Java9 ConstantValue source literals

## Actual original-v309 evidence (private)

The complete SHA-pinned original client JAR (`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`) contains a uniquely verified owner with **126 fields and ten methods**. All 126 field names are distinct, Java-legal identifiers; all 126 fields have valid JVM descriptors with the original field declaration order. Access flags are exactly **85 public static** and **41 public static final**; JVM types are **100 boolean, 10 int, 15 object reference and one array**.

The 41 final fields divide into **33 JVM `ConstantValue` attributes** (28 booleans, four ints, one String) and **eight final object/array references** without `ConstantValue`. The latter require exact Java static initializer assignments and must not be assigned invented compile-time values.

An independent private script extracted all 126 declarations and the 33 source-level literal expressions, then invoked `javac --release 9 -g:none -proc:none` on an isolated 33-field declaration-only witness class. The resulting Java9 classfile exactly reproduces **33/33 original access flags, JVM descriptors, field identities and `ConstantValue` literals**. Real original-derived private fragment SHA-256: `4359973896659913e98fc9189ea640074354ade921eefeeb0706c0c392334b12`; independently compiled Java9 proof class SHA-256: `9afb9853955b1b0ae54392e1b3204086e14c6d1b4ea47f58fde3aa4d173f580d`.

## Reproducible private tooling

`spk_recovery.private_v309_owner_field_source_r108` does not hardcode any original class, field, string or configuration name. It requires a complete SHA-256-pinned original JAR and the explicit owner class entry. Fail-closed checks require original JVM classfile major 53, exactly 126 distinct valid Java field identities, no source-unrepresentable field signatures, exact original public/static/final and type distributions, exactly 33 allowable `ConstantValue` values (including printable-ASCII-safe private source literals), and exactly eight uninitialized final references.

It generates `<original owner>.fields.PRIVATE.java.inc` in original declaration order and a separate *compilable* `FieldConstantsProofR108.java` source with the 33 original constants, compiles it using Java9, and requires **exact 33-field name/access/descriptor/`ConstantValue` roundtrip**. Only after pinned original JAR re-verification and successful Java9 proof does it atomically promote a new private output folder with both private source fragments, compiled proof class, and sanitized aggregate JSON. Source strings and private original identifiers are never printed by the tool or committed to GitHub.

Synthetic real-`javac --release 9` regression tests validate the complete **126-field (85/41) + 33 constants + 8 uninitialized-final** inventory. Negative tests reject original hash mismatch, changed field count, missing original constant, unsafe String literal, wrong Java major, unavailable compiler and overwriting an occupied output.

## What R108 does not prove

R108 recovers **original field declarations and 33 JVM constant initializers**, not the owner's executable **ten method bodies** or the original **213-instruction/93-write static initializer**. The eight nonconstant final references still need original-derived initialization. R107's final-owner gate, complete owner source compilation, R95 full original four-enum acceptance, original client helper side effects and gameplay/runtime equivalence remain unverified. Hosted synthetic tests are not substituted for real original-private replay.

The original client JAR, field identifiers, source strings, compiled private witnesses and source fragments are private data and are not uploaded to public GitHub.

Private CLI:

`python -m spk_recovery.private_v309_owner_field_source_r108 ORIGINAL.jar ORIGINAL_OWNER.class FRESH_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --javac JAVAC9_OR_LATER`
