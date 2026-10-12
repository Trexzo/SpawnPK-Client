# R71 — five additional original-v309 empty-catch Java source regions

R67 recovered 29 conditional Boolean/integer protected source blocks. R68 added two direct Boolean blocks, and R69 proved the exact original lookup receiver is `java.util.Properties`. R71 reconstructs **five additional original JVM-backed Java protected source forms**, bringing the local Exception-source inventory to **36 of 42**. It does not establish complete method or runtime equivalence.

## Exact original private v309 observations

From a read-only, whole-SHA-256-pinned original v309 owner method disassembly, the remaining local exception bodies include exactly:

| Source form | Original sites | Original protected instructions per site |
| --- | ---: | ---: |
| Guarded `List.add(Object)` invocation, discard returned boolean | 3 | 8 |
| Guarded `Integer` conversion and static int assignment | 1 | 10 |
| String assignment with literal default and second lookup on non-null path | 1 | 11 |
| **New bounded protected Java source blocks** | **5** | — |

Each has a verified original `java.lang.Exception` handler with an empty catch (`goto` past exactly one `astore_3`). The guarded `List.add` regions check `Properties.getProperty(String)` for non-null, then load the original static `List` and original member reference and invoke `List.add(Object):boolean`, discarding that result. The integer region checks for non-null and evaluates the same property key again before calling the original static boxed-Integer conversion and `intValue`. The nullable String region assigns either its original default literal or the result of a second original property lookup. No lookup is incorrectly cached or removed.

## Private source form illustrations

```java
try {
    if (originalLocalSlot1.getProperty("PRIVATE_KEY") != null) {
        originalStaticList.add(originalStaticMember);
    }
} catch (java.lang.Exception ignored) { }

try {
    if (originalLocalSlot1.getProperty("PRIVATE_INT_KEY") != null) {
        originalInt = OriginalConverter.convert(
            originalLocalSlot1.getProperty("PRIVATE_INT_KEY")
        ).intValue();
    }
} catch (java.lang.Exception ignored) { }

try {
    if (originalLocalSlot1.getProperty("PRIVATE_TEXT_KEY") == null) {
        originalString = "PRIVATE_DEFAULT";
    } else {
        originalString = originalLocalSlot1.getProperty("PRIVATE_TEXT_KEY");
    }
} catch (java.lang.Exception ignored) { }
```

Identifiers and literal keys above are placeholders. The actual original member coordinates remain private. External field/member source names and nested enum references are **not promoted as canonical recovered Java identities**; a standalone fragment still depends on those missing Java types.

## GitHub implementation

`spk_recovery.other_protected_source_r71` validates the exact original JAR SHA pre/post, private exact class/method selection, original declared static fields, typed `getProperty(String)` resolution, exact contiguous eight-/ten-/eleven-op protected ranges, List.add and Integer conversion member descriptors, original String literal ConstantPool types and repeated key equality, original `ifnull`/`ifnonnull`/`goto` targets, and empty Exception catch bodies. Unexpected incoming branches or handler entries into a protected region are rejected.

It emits original-key-backed Java snippets and full operand graphs **privately**, with aggregate-only site counts, form counts and a private fragment SHA fingerprint. No original literal keys, proprietary source, obfuscated identifiers or JARs are publicly committed.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.other_protected_source_r71 `
  'C:\private\original-v309.jar' 'example/PrivateOwner.class' `
  'privateMethod' '()V' 'C:\private\r71-new-output' `
  --sha256 '<whole exact original-v309 JAR SHA256>'
```

Synthetic Java9 tests compile three actual guarded `List.add`, one guarded integer conversion and one nullable-String block, reconstruct private source from their classfile and recompile it against Java 9. The merged R66 verifier checks the original and compiled candidate's branch topology, exact ordered typed exception table and static-field write sequence. Tests also veto changed List method names, conflicting repeated String key literals, wrong whole-JAR pin and occupied private output.

## Remaining source and runtime work

Six more local `Exception` protected bodies have other original instruction patterns of lengths **11, 22, 15, 19, 23 and 36**. Source reconstruction of those six regions, integration of all 42 local catch scopes inside R70's two outer I/O regions, the separate 364-op method, original helper side effects, original nested-enum sources and complete 697-op runtime parity remain unaccepted.

The new generic R71 CLI is not claimed to have been run end-to-end against the actual private original v309 JAR; source-form counts were independently checked from its read-only disassembly. Never equate a bounded JVM source-form match with complete runtime equivalence.
