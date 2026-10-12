# R68 — two original v309 direct Boolean Java sources with empty Exception catches

R67 reconstructs private Java statements for 29 original v309 protected source regions (26 Boolean, three integer). Independent read-only inspection of the same whole-SHA-pinned JAR identifies two additional local `java.lang.Exception` protected ranges that are *simpler*: each contains exactly six JVM instructions followed by a `goto` over a single `astore_3` exception handler.

```text
aload_1
ldc original private String key
invokevirtual original lookup(String):reference
invokestatic exact converter(reference):java.lang.Boolean
invokevirtual java.lang.Boolean.booleanValue():boolean
putstatic original Boolean field
goto past astore_3 empty Exception catch
```

The recovered private Java source form (names and values here illustrative) is:

```java
try {
    originalBooleanField = OriginalConverter.convert(
        originalLocalSlot1.lookup("ORIGINAL_PRIVATE_KEY")
    ).booleanValue();
} catch (java.lang.Exception ignored) {
}
```

`originalLocalSlot1` is an unresolved source parameter/local type, not a declared recovered original Java identity. Unlike R67's conditional source forms, each R68 direct block invokes its lookup **once**, and no alternative/default value is fabricated.

Together R67 and R68 recognize **31 of the 42 local Exception-protected source regions**. The remaining **11 local regions**, and the outer two `IOException` exception handlers, remain unreconstructed. Counts reflect exact original JVM bytecode observations, not complete source parity.

## GitHub implementation

`spk_recovery.direct_empty_catch_source` requires exact original JAR SHA-256 before and after, a unique privately selected class/method, exact six-op contiguous JVM shape, declared original static Boolean destination, original String LDC literal, typed virtual lookup/static Boolean conversion/primitive extraction descriptors, original `goto`/`astore_3` empty catch body, and zero unexpected branch/handler targets into the protected source interior.

It generates private original JVM operand evidence and actual original-key/member-backed Java `try/catch` statements in exclusive-create private outputs. The public report contains counts and cryptographic fingerprints only; never commit the private original source, JAR, keys or member names.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.direct_empty_catch_source `
  'C:\private\original-v309.jar' 'example/OriginalOwner.class' `
  'privateOriginalMethod' '()V' 'C:\private\r68-new-output' `
  --sha256 '<whole original-v309 SHA256>'
```

Private class/member inputs are placeholders, not canonical recovered identities.

Synthetic Java9 tests compile two direct protected Boolean assignments, reconstruct private Java from their classfile, recompile the generated source, and compare both methods using R66's exact branch, typed-exception and static-write order verifier. Changed call descriptor, mutated empty catch, bad original JAR SHA and destination collision fail closed.

**Unmet acceptance gates:** R68's new generic CLI has not yet been privately replayed against the actual original v309 client. The original local type, eleven remaining protected source forms, two outer I/O handlers, helper implementations, complete 697-instruction Java method, cross-class source consistency and runtime behavior are not certified.
