# R75 — exact original v309 23-op external Boolean, enum and List fallback source

The original v309 settings method contains a local `Exception`-protected 23-instruction region with **two different control-flow paths and ordered external side effects**. R75 reconstructs its bounded private Java source form, leaving only the original 36-instruction protected region without a candidate source pattern.

## Exact JVM source facts

In the `Properties.getProperty(String) == null` branch, the original method executes *in this order*: (1) sets one external static Boolean field `true`, (2) adds a static enum reference to an original external `List`, (3) adds a second distinct static enum reference to the same `List`, discarding each returned Boolean, (4) sets a second external static Boolean field `false`, and (5) jumps past the alternative branch. In the non-null branch it re-evaluates the same String property key, converts it using `Boolean.valueOf(String).booleanValue()` and assigns that result to the **same first external Boolean field**.

Both original `getstatic` list reads have the exact same member owner/name/descriptor. Both enum reads come from the same class with the same reference descriptor but different constants. The two normal branches share an original typed `java.lang.Exception` handler with an empty catch body.

## Private Java form

```java
try {
    if (originalLocalSlot1.getProperty("PRIVATE_KEY") == null) {
        ExternalOptions.primaryFlag = true;
        ExternalOptions.values.add(OriginalEnum.FIRST);
        ExternalOptions.values.add(OriginalEnum.SECOND);
        ExternalOptions.secondaryFlag = false;
    } else {
        ExternalOptions.primaryFlag = Boolean.valueOf(
            originalLocalSlot1.getProperty("PRIVATE_KEY")
        ).booleanValue();
    }
} catch (java.lang.Exception ignored) {}
```

The names and String key above are illustrative, not canonical deobfuscations. The tool emits the real original binary member coordinates and key **only to private files**, never to GitHub source, aggregate evidence or output. The external enum's original recovered Java inner class name remains unresolved.

## Verifier and reproducibility

`spk_recovery.enum_list_fallback_source` validates the complete original JAR SHA before and after, unique original class and method, exact 23-op contiguous JVM body, original matching property literal and method descriptor, both Boolean field destinations and their call ordering, same external List reference on both list additions, distinct original enum constants, original typed `List.add(Object):Z` operations and discarded results, exact `ifnonnull` and `goto` targets, and a typed empty `Exception` handler. Unexpected branch/handler entry into a source window fails closed.

The Java9 synthetic test compiles the original branch with a real `List` and two distinct enum values, extracts JVM-backed private Java, recompiles it into a new class and applies merged R66 to compare exact branch topology, ordered typed exception ranges and **all three external static writes**. Wrong enum identity, altered List.add signature, bad JAR pin and existing output collision are vetoes.

Private replay:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.enum_list_fallback_source `
  'C:\private\original-v309.jar' 'example/PrivateOwner.class' `
  'privateMethodName' '()V' 'C:\private\r75-new-output' `
  --original-sha256 '<whole exact original-v309 JAR SHA256>'
```

The original 23-instruction site is based on read-only pinned original-JAR disassembly; **the new generic R75 CLI has not yet been replayed against actual private original-v309 input**. Even if all bounded local patterns pass synthetic tests, the complete 697-op original Java method, the last 36-op region, external enum source identity, original helper effects and runtime behavior remain unverified. Counted source windows are not equivalent to final runnable recovered source.
