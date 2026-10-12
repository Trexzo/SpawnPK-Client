# R74 — original v309 Boolean helper callback and static-field ordering

R73 restores the source form for the original indexed `Properties` int-array loop. R74 recovers **two** more original local `Exception`-protected Java source blocks, with 15 and 19 JVM instructions, whose important behavior is the precise ordering of helper callbacks and Boolean field updates.

## Original 15-op local protected source

The original 15 JVM opcodes check an exact `Properties.getProperty(String)` result for null. On null, the original method assigns a static Boolean field `false` and skips the other path. On non-null, it calls the *same lookup again*, converts via `Boolean.valueOf(String).booleanValue()`, stores the Boolean in JVM local3 and calls a declared static `(Z)V` helper on the owner—**without writing the original Boolean field** on that non-null path.

```java
try {
    if (originalLocalSlot1.getProperty("PRIVATE_KEY") == null) {
        originalBooleanField = false;
    } else {
        boolean originalParsedBoolean = Boolean.valueOf(
            originalLocalSlot1.getProperty("PRIVATE_KEY")
        ).booleanValue();
        originalOwnerHelper(originalParsedBoolean);
    }
} catch (java.lang.Exception ignored) {}
```

## Original 19-op local protected source

The original 19-op protected range also checks one property String twice along the non-null path. On null it invokes an **external original static `(Z)V` helper with false**, then assigns the original static Boolean field false. On non-null it parses and stores one Boolean JVM local3, calls the **same external helper** using that Boolean, and only afterward writes it to the static Boolean field. Reordering these side effects is not permitted.

```java
try {
    if (originalLocalSlot1.getProperty("PRIVATE_KEY") == null) {
        ExternalHelper.apply(false);
        originalBooleanField = false;
    } else {
        boolean originalParsedBoolean = Boolean.valueOf(
            originalLocalSlot1.getProperty("PRIVATE_KEY")
        ).booleanValue();
        ExternalHelper.apply(originalParsedBoolean);
        originalBooleanField = originalParsedBoolean;
    }
} catch (java.lang.Exception ignored) {}
```

Both catch bodies are verified empty. Source helper/class/field identifiers above are **illustrative**, not disclosed exact original identities.

## GitHub recovery

`spk_recovery.boolean_helper_protected_source` reads the exact complete original JAR under SHA pre/post, selects the private class/method, verifies original 15/19-opcode contiguous protected regions, matching typed `Properties` lookups and repeated key, boxed Boolean conversion/unboxing, original owner/external helper descriptors and exact helper ownership, declared owner Boolean static field, branch destinations, local3 stack use, and exact empty `Exception` catch. It rejects unaccounted incoming branch/handler targets. Private original source/operand graphs stay in a new private directory; public-safe output holds only counts/hashes.

Synthetic `javac --release 9` tests compile both kinds of protected Java blocks, extract original JVM-backed source, recompile the recovered source and compare candidate JVM branches, ordered exception tables and static-field write order through R66. Negative tests reject changed external helper descriptors, loss of original owner static method status, mismatched whole-JAR SHA and occupied output.

Private replay:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.boolean_helper_protected_source `
  'C:\private\original-v309.jar' 'example/OriginalOwner.class' `
  'privateMethod' '()V' 'C:\private\r74-new-output' `
  --sha256 '<whole original-v309 JAR SHA256>'
```

Bounded original protected source forms reach **40/42 local `Exception` regions** only when upstream R71–R74 pass their CI and original CLI replay. The last two local bodies have **23 and 36 JVM instructions**. R74 has not yet executed its generic CLI against the actual private original v309 JAR; evidence comes from independently inspected pinned JVM disassembly. A complete 697-instruction Java method, external helper implementation behavior, other complex sibling method, original nested enum identities and client runtime parity remain unverified.
