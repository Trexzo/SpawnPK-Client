# R63 — original v309 typed static write source-producer chains

The larger original-v309 owner method contains **697 JVM instructions, 78 static-field assignments, 120 explicit branches and 44 exception handlers** (R62). Independently reviewing the original pinned JAR now identifies **37** of its 78 assignments with an identical, strictly local typed operand chain:

```text
aload_1
ldc String                    // private original key
invokevirtual(String) -> reference
invokestatic(reference) -> reference
invokevirtual() -> Z or I
putstatic owner.boolean_or_int
```

All 37 JVM method return/argument descriptors align exactly. Of these, **32 produce booleans and five produce integers**. These are real local operand dataflow shapes, not claims that the field values are correct under all branches or exceptions. The original local slot one Java type and original exception handling are **not reconstructed**. The other 41 static writes follow other patterns.

[Original aggregate evidence](../research/v309-source-recovery/typed-static-write-chains-r63.json) includes only shape/type counts and SHA-256 original complete JAR identity, never member names or original String keys.

## GitHub module

`spk_recovery.typed_static_write_chains` operates read-only on a SHA-pinned exact original class and a privately named method. It finds adjacent six-op windows, verifies an actual String LDC, exact JVM lookup/conversion/extraction return and argument signatures, original owner static field declarations and exact primitive type, then vetoes branch targets or exception-handler entries into the *interior* of the chain. It records each accepted original target, source String and method member coordinates in a **private** JSON operand graph, with aggregate counts and private SHA only in stdout.

This is a stepping stone toward reconstructing the 697-instruction method's **field value producer expressions**, not generated compilable Java, helper-body recovery or a replay of the original method's 44 exception regions.

Run from a GitHub checkout with exact private original JAR and privately resolved JVM class/method identity:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.typed_static_write_chains `
  'C:\private\original-v309.jar' `
  'example/OriginalOwner.class' `
  'privateOriginalMethod' '()V' `
  'C:\private\r63-new-output' `
  --original-sha256 '<complete original JAR SHA256>'
```

The class/method coordinates above are **placeholders**, not an accepted canonical mapping. Outputs are `typed-write-chains.private.json` and `typed-write-chains.aggregate.json`, written only into a fresh private output directory. Do not publish the private JSON, original Java, literal keys or binaries.

Synthetic Java 9 tests cover typed boolean/int chains, altered intermediate method descriptors, an unexpected branch into the producer, SHA-256 mismatch and preservation of an occupied destination. The R63 GitHub CLI has **not yet been executed against the private original JAR**; its original evidence was independently measured from the pinned binary. The actual CFG veto may lower the 37-site accepted count; do not call them 37 recovered Java expressions or runtime-proven field assignments before replay.

Unresolved: recovered local1 type, source-level try/catch, 41 other static field producers, helper implementations, both large original method sources, nested enum metadata, and runtime equivalence.
