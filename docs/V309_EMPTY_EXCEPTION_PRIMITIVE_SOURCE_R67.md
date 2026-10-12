# R67 — original v309 protected Boolean and integer Java source forms

R67 reconstructs private Java source statements for **29 original protected assignment regions** under exactly empty typed `catch (Exception)` handlers. This is original-JVM-driven **source recovery**, not a complete recompiled owner method or runtime equivalence.

## Corrected original-v309 inventory

Independent read-only inspection of the complete SHA-256-pinned original v309 owner class showed 44 exception handlers: **42 local `java.lang.Exception`** and two outer `java.io.IOException`. Every local Exception handler consists of the original `goto` past a single `astore_3` followed immediately by the next region, proving an empty catch body (no executable exception-response statements).

**29 local regions** follow the same exact 13-instruction conditional-value pattern:

```text
aload_1; ldc original String; invokevirtual lookup; ifnonnull;
iconst_0 / iconst_1 / bipush; putstatic owner; goto;
aload_1; ldc same String; invokevirtual same lookup;
invokestatic typed conversion; invokevirtual primitive extraction;
putstatic same owner field
```

| Reconstructed local protected source kind | Original regions |
| --- | ---: |
| Boolean false on null | 13 |
| Boolean true on null | 13 |
| Integer zero on null | 2 |
| Integer immediate (`bipush`) on null | 1 |
| **Total matching protected regions** | **29** |

All 29 have identical original lookup literal, virtual lookup method and static destination field between branches. The original Boolean conversions produce a boxed `java.lang.Boolean` and call `booleanValue():Z`; the three integer conversions produce a boxed `java.lang.Integer` and call `intValue():I`. Their JVM branch destinations and typed empty handlers have been checked independently.

The original method **invokes lookup twice** along a non-null path. R67 deliberately preserves both calls rather than caching a single lookup result, because doing so could change side effects.

## Actual private reconstructed source shape

```java
try {
    if (originalLocalSlot1.lookup("PRIVATE_KEY") == null) {
        originalPrimitiveField = false; // or true, 0, or proven integer
    } else {
        originalPrimitiveField = OriginalConverter.convert(
            originalLocalSlot1.lookup("PRIVATE_KEY")
        ).booleanValue(); // or intValue() for original integer field
    }
} catch (java.lang.Exception ignored) {
}
```

`originalLocalSlot1` is an explicitly unresolved local variable type. The source emitted privately uses original JVM field and helper coordinates and original string literals. GitHub output does not publish them. No claim is made that a standalone fragment can compile into the original complete owner without its original surrounding local initialization and dependency sources.

## Implementation and replay

`spk_recovery.local_exception_primitive_source` rejects all patterns except the exact original 13-instruction protected range, matching original field names/descriptors, exact type-aligned String read, boxed static conversion and Boolean/Integer extraction, the exact `ifnonnull` and `goto` destinations, an empty `astore_3` catch, and no unexpected branch/handler entry into the expression interior. Complete original JAR SHA-256 is checked before and after reading. Inputs and outputs remain private.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.local_exception_primitive_source `
  'C:\private\original-v309.jar' 'example/Owner.class' `
  'privateMethodName' '()V' 'C:\private\r67-new-output' `
  --original-sha256 '<whole exact original JAR SHA256>'
```

Public-safe outputs contain only count/hash evidence. Original names/literal keys/source are in separately created **private** files; never commit those to GitHub.

## Verification and hard boundaries

Synthetic Java 9 tests exercise two Boolean and three integer protected regions, extract their source, **recompile the generated Java** and compare the resulting method against the synthetic original using R66's exact JVM branch ordinal, typed exception range and field-write order gate. Negative tests reject changed repeated literal keys, mutated catch handlers, wrong complete JAR SHA-256 and occupied output directories.

The observed **29 source forms were independently counted from original-v309 disassembly**. The GitHub R67 CLI has **not yet been executed end-to-end on the private original v309 JAR**; that is a separate replay gate. **13 other local protected regions**, both outer I/O handlers, local1 source type, the complete 697-instruction method, helper side effects and all runtime behavior remain unverified. The corrected original evidence and truthful noncertification flags are in [`empty-exception-primitive-regions-r67.json`](../research/v309-source-recovery/empty-exception-primitive-regions-r67.json).

Do not mistake exact JVM source-form reconstruction for complete original source authorship or runtime parity.
