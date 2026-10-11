# R51 — private source forms for the two original v309 boolean predicates

R48 withheld two control-flow-joined boolean initializer stores. R50's
independent, SHA-pinned original-v309 analysis showed that both have exact
boolean literal/branch/goto diamonds.

R51 recovers two **JVM-equivalent candidate Java expression forms**, using
only the original conditional's immediate, exact `getstatic` operands:

1. Two contiguous reference `getstatic` operands with the **same JVM
   descriptor**, followed by `if_acmpne`, a true fallthrough and false
   taken branch: `target = (referenceA == referenceB);`
2. One contiguous boolean `getstatic` operand followed by `ifne`, a
   true fallthrough and false taken branch:
   `target = (!sourceBoolean);`

The exact original field references and target identifiers are emitted
**only** into the new private text fragment. The tracked
[aggregate evidence](../research/v309-source-recovery/boolean-predicate-source-r51.json)
contains the two semantic patterns, a SHA-256 of that private fragment,
and non-certification flags, but no original field/class names or source.

A read-only independent original-v309 `javap` inspection found both
patterns. A separate synthetic Java 9 compilation produced their same
JVM opcode shapes. This is **not** a compilation of the private fragment
against actual original dependencies, nor the complete initializer.

## GitHub-first private workflow

This PR extends R50 and **must not be merged ahead of R50**. From the
repository checkout and two exact SHA-pinned private complete JARs:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.boolean_predicate_source `
  'C:\private\original-v309.jar' `
  'C:\private\candidate-before-r51.jar' `
  'example/Owner.class' `
  'C:\private\new-r51-output' `
  --original-sha256 '<measured original complete-JAR SHA256>' `
  --candidate-sha256 '<measured candidate complete-JAR SHA256>'
```

The exact class entry and SHA placeholders above are not mappings.
The tool checks whole JAR hashes twice, original/candidate JVM owner and
field metadata, the R31/R32/R35/R36 method-field matrix, and R50's strict
local branch-join witness before attempting source text emission.

Extra vetoes include nonstatic producers, class/member names not
representable as Java tokens, different reference descriptors, any
additional branch entering the producer instructions, exception coverage,
unsupported condition opcodes, and output directory collisions.

Output files under the **exclusive-create private directory**:

- `boolean-predicate-source.private.txt`: candidate Java `static`
  fragment with real original field names/operands; never publish.
- `boolean-predicate-rows.private.json`: private offsets and fields.
- `boolean-predicate-aggregate.json`: aggregate counts/hashes only.

Only generic implementation and synthetic test code are published.
The real original-v309 measurement was obtained independently; running
the new **R51 GitHub Python CLI** against the private original/candidate
JAR pair is a separate unfinished gate. Its private source fragment
must also be compiled against independently reconstructed dependencies
and compared with full JVM initialization order before it can be accepted.

## Limits

Reconstructing expressions for these two stores does **not** recover
the other `<clinit>` operations, enum side effects, six missing dynamic
final fields, other original methods, runtime correctness or original
authorial Java. No canonical owner or member identities are promoted.
