# R67 — original-v309 protected Boolean assignments reconstructed as private Java

R62–R66 recovered original JVM control flow and bounded all 78 field-write sites but did not recover source-level exception handling. R67 is a concrete source-reconstruction step: **28 exact conditional Boolean assignment regions and their empty `catch(Exception)` bodies** are staged as *private Java source blocks* from the SHA-256-pinned original client.

## Independently measured original-JAR evidence

The original 697-instruction method has 44 exception handlers: 42 catch `java.lang.Exception` around local protected ranges and two catch `java.io.IOException` around the outer loading flow. **All 42 local Exception handlers** have the exact original `goto` past an `astore_3` instruction, followed by fallthrough into the next region. There is no JVM instruction in the catch body after the caught exception is stored.

**28 of the 42 local protected ranges** share exactly this 13-opcode body:

```text
aload_1, ldc, invokevirtual, ifnonnull,
iconst_0 or iconst_1, putstatic, goto,
aload_1, ldc, invokevirtual, invokestatic,
invokevirtual, putstatic
```

Across all 28, the two branches write the **same original Boolean field**, use **the same original lookup String** and the **same original lookup method**, with `ifnonnull` targeting the non-null branch and `goto` jumping past that branch. Fifteen assign `false` for a null lookup; thirteen assign `true`. Original bytecode **calls the lookup twice** on the non-null path. R67 intentionally preserves both invocations instead of deduplicating them (which could alter side effects).

The verified private Java source form is structurally:

```java
try {
    if (originalLocalSlot1.lookup("PRIVATE_KEY") == null) {
        originalBooleanField = false;
    } else {
        originalBooleanField = OriginalConverter.convert(
            originalLocalSlot1.lookup("PRIVATE_KEY")
        ).booleanValue();
    }
} catch (java.lang.Exception ignored) {
}
```

This is a structural illustration, not literal recovered original class/member identities. Private source blocks contain actual original JVM-linked String/member operands; GitHub artifacts do **not**. `originalLocalSlot1` is a placeholder: its Java type and enclosing method scope remain unrecovered.

## GitHub implementation and replay

`spk_recovery.local_exception_boolean_source` reads the exact original full JAR SHA-256 before/after profiling, verifies unique private owner/method identity, original field metadata, original String LDC kind/equality, matching virtual lookup descriptors, exact static Boolean conversion and primitive extraction, correct branch destinations, exact 13-op contiguous protected range, and the empty typed catch's `goto; astore_3; fallthrough` structure. It vetoes unexpected branch/handler entries into the protected body's interior.

Private replay example (method/class identities illustrative):

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.local_exception_boolean_source `
  'C:\private\original-v309.jar' 'example/Owner.class' `
  'privateMethodName' '()V' 'C:\private\r67-new-output' `
  --original-sha256 '<complete original-JAR SHA256>'
```

Outputs are an exclusive-create private graph, private Java source blocks, and aggregate-safe count/source SHA evidence. No original field names, method names, network endpoints, literal keys, source or client JAR are published.

## Recompilation and actual acceptance boundaries

The R67 synthetic Java 9 test compiles two actual `try/catch(Exception)` Boolean regions, runs the R67 source extractor, recompiles those **generated private Java blocks** into a second class, and applies the **R66 original-vs-candidate verifier** to check ordered writes, branches and exception table source structure. It also rejects a changed repeated lookup key, changed branch, nonempty/altered handler, incorrect whole JAR pin and occupied private output.

The original v309 **42 local handler / 28 Boolean region evidence** was separately measured using read-only disassembly. **The new R67 CLI has not yet been end-to-end replayed against the actual private v309 JAR**, and no original full-method candidate exists or has passed R66. Fourteen other local protected ranges, both outer I/O handlers, the original source local-variable type, source method body, helper side effects and full runtime equivalence remain unrecovered.

Do not promote source names from a compiled placeholder, or claim completed method/class runtime parity.
