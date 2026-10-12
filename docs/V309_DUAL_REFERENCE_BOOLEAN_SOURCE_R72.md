# R72 — original v309 two-write reference and Boolean protected Java source

R67, R68 and R71 identify 36 of the original 697-instruction method's 42 local `Exception`-protected Java source regions. R72 recovers another **exact 11-instruction protected region** that writes **two distinct static fields** under the same empty exception catch.

## Original JVM evidence

The exact whole-SHA-256-pinned original v309 bytecode contains:

```text
aload_1; ldc original-first-key;
invokevirtual Properties.getProperty(String):String;
invokestatic original String-to-nested-reference converter;
putstatic original nested-reference field;
aload_1; ldc original-second-key;
invokevirtual Properties.getProperty(String):String;
invokestatic original String-to-Boolean converter;
invokevirtual Boolean.booleanValue():boolean;
putstatic original Boolean field;
goto over empty Exception handler (astore_3)
```

The first converter's original return descriptor equals the first field's original reference descriptor; the second converter returns `java.lang.Boolean`, unboxed to primitive `Z` before the second static-field write. The two original literal keys and all member coordinates remain **private**.

R72 stages this source form in an exclusive-create private output:

```java
try {
    originalReferenceField = OriginalReferenceConverter.fromString(
        originalLocalSlot1.getProperty("PRIVATE_REFERENCE_KEY")
    );
    originalBooleanField = Boolean.valueOf(
        originalLocalSlot1.getProperty("PRIVATE_BOOLEAN_KEY")
    ).booleanValue();
} catch (java.lang.Exception ignored) { }
```

The source here is illustrative; source fragments generated privately preserve original JVM names, descriptors and two separate lookup evaluations, and do not invent an enum lookup or default values.

## GitHub implementation

`spk_recovery.dual_reference_boolean_source_r72` verifies original whole-JAR SHA before and after, unique private owner/method, 11 exact contiguous opcodes, the original two field declarations and exact typed conversion descriptors, both original String LDC operands, no unexpected incoming branches or exception handler entries, and an original `goto` skipping the empty typed `Exception` handler. It refuses source forms that change the original reference type or Boolean converter signature.

Synthetic Java9 tests compile an original protected two-write Java block, extract private Java from the resulting JVM instructions, compile that source into a second class, and require the R66 original/candidate method comparator to pass exact branches, ordered typed exception handlers and mapped two-write order. Negative tests mutate converter descriptor, original static target type, JAR pin and destination collisions.

## Integration and limits

After R72's bounded **one** new source form, **37 of the original 42 local protected source regions** have a claimed JVM-backed Java pattern; the remaining five have original instruction counts **22, 15, 19, 23, 36** and are not reconstructed. The real nested enum class source naming and `InnerClasses` metadata collision remain unproven. R72 has **not** yet replayed the actual original JAR with the new generic CLI; independent read-only disassembly supplied the original evidence. Nor is the original whole 697-instruction method, helper behavior or runtime parity certified.

Actual original private names, literal strings, original binaries or source are never included in GitHub artifacts. The generated source is research-only and cannot be treated as a complete drop-in original class.
