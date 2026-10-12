# R70 — recover the original v309 outer IOException catch source envelope

R69 proves the original 24-op Java File/Properties load prefix and its local1 `java.util.Properties` type. R70 independently recovers the **outer typed IOException catch body** and demonstrates that the original two-handler-table split is produced by ordinary Java 9 source with an early return inside a `try` block.

## Read-only exact-original JVM evidence

The original 697-op v309 method has two `java/io/IOException` entries sharing a single exception handler:

| Protected JVM byte offset range | Handler byte offset |
| --- | ---: |
| `[3,21)` | `1608` |
| `[22,1605)` | `1608` |

At the end of the method, the exact original JVM opcodes are: `goto` over catch; `astore_0`; `aload_0`; `invokevirtual java/io/IOException.printStackTrace:()V`; `return`. The normal path jumps past the handler. Source-level exception handling must retain the `IOException.printStackTrace()` call, not silently ignore or replace it.

## Concrete Java9 reproducibility

An independent `javac --release 9 -g:none -proc:none` experiment compiled this source skeleton:

```java
preflight();
try {
    File originalLocalSlot0 = new File(originalStaticFilePath);
    if (!originalLocalSlot0.exists()) return;
    Properties originalLocalSlot1 = new Properties();
    FileInputStream originalLocalSlot2 =
        new FileInputStream(originalLocalSlot0);
    originalLocalSlot1.load(originalLocalSlot2);
    originalLocalSlot2.close();
    // Remaining original properties assignments go here
} catch (IOException originalIOException) {
    originalIOException.printStackTrace();
}
```

This produced exactly **two** `IOException` protected ranges, split around the early `return`—the same original JVM layout. It is not necessary to mutate the compiled exception table to explain that split. The snippet shows source structure, not publicly released original member identities.

## GitHub source generator and test

`spk_recovery.outer_io_exception_envelope` reuses R69's exact private original JVM prefix evidence and validates the original method's last five instructions, shared typed catch handler, both exact protected ranges, normal `goto` and `IOException.printStackTrace()` invocation. It emits a private Java *method body envelope* consisting of the exact original preflight and prefix, a clearly marked **unreconstructed middle**, and a source-level outer catch. No original file path String, class/member name, JAR or executable original code is committed.

Synthetic Java9 tests compile the original-style File/Properties prefix within a real `try/catch IOException`, extract its private Java envelope, **recompile** the emitted source, then apply R66 to compare the entire synthetic method's ordered exception tables, branch ordinal topology and static-write sequence. Changed catch side effects, protected offsets, invalid SHA and existing output are rejected.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.outer_io_exception_envelope `
  'C:\private\original-v309.jar' 'example/PrivateOwner.class' `
  'privateMethodName' '()V' 'C:\private\r70-new-output' `
  --sha256 '<whole original-v309 SHA256>'
```

The original v309 measurements are independently grounded, but the new R70 tool has **not** yet executed against the private original binary. The actual 697-op method's **middle** is still incomplete, including the remaining 11 local protected regions. The generated Java snippet must not be treated as a finished original method; no helper side-effect or runtime equivalence has been verified. Read the truthful flags in [R70 evidence](../research/v309-source-recovery/outer-io-exception-envelope-r70.json).
