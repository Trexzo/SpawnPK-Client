# R73 — exact original v309 indexed Properties / integer-array Java source loop

After R67/R68/R71/R72, 37 of the exact original settings method's 42 local `Exception`-protected regions have bounded JVM-backed Java source forms. R73 reconstructs the next: a **22-JVM-instruction `for` loop** that reads numbered properties and conditionally writes elements of one original static integer array.

## Grounded original JVM disassembly

The original protected sequence is exactly:

```text
iconst_0; istore_3; iload_3; getstatic [I; arraylength; if_icmpge;
aload_1; iload_3; invokedynamic StringConcatFactory; invokevirtual getProperty;
ifnull; getstatic [I; iload_3; aload_1; iload_3;
invokedynamic SAME StringConcatFactory; invokevirtual getProperty;
invokestatic Integer.valueOf(String); invokevirtual Integer.intValue();
iastore; iinc local3,+1; goto loop-test
```

The original JVM `getstatic` references match exactly and resolve to an original declared static `int[]` field. Both `invokedynamic` instructions target **the same original bootstrap entry** with descriptor `(I)Ljava/lang/String;`. Its `java/lang/invoke/StringConcatFactory.makeConcatWithConstants` method-handle is reference kind 6, and the original bootstrap recipe is a private ASCII prefix followed by exactly one dynamic `\u0001` integer marker, with no other dynamic or constant substitution marker. Both property lookups use `java.util.Properties.getProperty(String)`, and the original array value conversion uses `java.lang.Integer.valueOf(String).intValue()`.

The JVM branch targets point to the loop exit and index increment, with a single typed empty Exception catch outside the 22-op protected range. The Java source form preserves **both original property lookups** on the non-null path, their dynamic indexed key and every array element assignment.

## Actual private reconstructed source shape

```java
try {
    for (int originalArrayIndex = 0;
         originalArrayIndex < originalIntArray.length;
         originalArrayIndex++) {
        if (originalLocalSlot1.getProperty("PRIVATE_PREFIX" + originalArrayIndex) != null) {
            originalIntArray[originalArrayIndex] = Integer.valueOf(
                originalLocalSlot1.getProperty("PRIVATE_PREFIX" + originalArrayIndex)
            ).intValue();
        }
    }
} catch (java.lang.Exception ignored) {
}
```

Private input names/keys here are intentionally placeholders; actual bytecode-proved original values are only written to fresh **private** outputs, never committed. This does not grant canonical semantic identities or prove original runtime parity.

## GitHub source recovery and synthetic acceptance

`spk_recovery.indexed_properties_array_source` requires exact complete-original-JAR SHA-256 before and after reading, unique original owner/method, exact 22-op contiguous protected region, verified two identical int-array static reads, exact branch destinations and local3 increment, matching virtual Properties lookups, matching original two `invokedynamic` bootstrap indices and signatures, exact private bootstrap recipe and integer conversion/unboxing, and empty typed Exception catch. Any altered recipe, concatenation constant, field metadata, branch or handler structure fails closed. Source fragments and full operands are private; aggregate-only SHA/count evidence is public-safe.

Synthetic Java 9 tests compile the real `for` loop into an original test class, extract the private source, **recompile it** into a candidate class and apply R66's exact branch ordinal and exception-table comparison. They also check that changing the original recipe, second bootstrap index, loop-exit branch, SHA pin or output destination is refused.

Run privately from a GitHub checkout:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.indexed_properties_array_source `
  'C:\private\original-v309.jar' 'example/OriginalOwner.class' `
  'privateMethod' '()V' 'C:\private\r73-new-output' `
  --complete-jar-sha256 '<whole original-v309 JAR SHA256>'
```

The R73 generic CLI has not yet been executed against the actual private original client; the original 22-op source and bootstrap facts are independently measured with SHA-pinned read-only JVM disassembly. After this bounded region, **four original local Exception regions remain** (15, 19, 23 and 36 JVM instructions). Source-assembly into the actual 697-instruction Java method, full original `StringConcatFactory` runtime results, helper side effects and complete client equivalence are not certified.
