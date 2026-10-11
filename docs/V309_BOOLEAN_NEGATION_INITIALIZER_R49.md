# R49 — recover one branch-defined Boolean initializer exactly

R48 reconstructs only **78 direct literal-producing mutable scalar
stores** from original v309. The other two Boolean initializer stores
are control-flow joins, and it correctly refuses to substitute their
immediately preceding `iconst_0` as if it were the sole reaching value.

R49 independently recovers **one** of these two originally conditional
assignments. The exact original JVM sequence is a logical negation of
another public static mutable Boolean field:

`getstatic boolean → ifne → iconst_1 → goto → iconst_0 → putstatic boolean`

The `ifne` branch must target `iconst_0`; the `goto` must target
the final `putstatic`. Both branch destinations and exact original
source/target field metadata are mandatory for the verification.

## Private Java9 source proof

I inserted the corresponding `target = !source;` expression into a
separate **private** R48/R47 source candidate at the matching relative
initializer position and compiled with
`javac --release 9 -g:none -proc:none`.

The rebuilt class contains **the same six original JVM opcodes, control
flow and field references** after normalization for relocated bytecode
offsets and constant-pool indices. All eight preexisting R24 candidate
method opcode/operand disassemblies remain unchanged.

| Recovered initializer evidence | Private current result |
| --- | ---: |
| Original mutable scalar fields | 80 |
| Exact direct literal/store pairs (R48) | 78 |
| Exact branch-based Boolean negation (R49) | **1** |
| Mutable scalars with individually verified initial assignments | **79/80** |
| Remaining enum-dependent conditional Boolean | **1** |
| Owner declarations structurally matching original | 120/126 |

This private proof's source, compiled class and candidate JAR SHA-256
values are recorded in
[the R49 aggregate](../research/v309-source-recovery/boolean-negation-initializer-r49.json).
No literal values, raw original field names or private source code are
uploaded. The remaining conditional Boolean depends on the original
nested enum whose values/behaviors are not yet recovered.

## Run the narrowly scoped comparator

From a clone of the GitHub repository with private original/candidate
whole-JAR SHA-256 pins:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.boolean_negation_initializer_microparity `
  'C:\private\original-v309.jar' `
  'C:\private\rebuilt-candidate.jar' `
  'example/Owner.class' `
  '<exact private source Boolean field>' `
  '<exact private target Boolean field>' `
  --original-sha256 '<verified original whole JAR SHA256>' `
  --candidate-sha256 '<verified candidate whole JAR SHA256>' `
  --out 'C:\private\new-bool-negation-proof.json'
~~~

Examples are placeholders, not accepted original mappings.

R49 requires exactly one target `putstatic` in each class initializer,
contiguous six JVM instructions, exact `getstatic` source and
`putstatic` target descriptors, identical Boolean field metadata,
and correct `ifne`/`goto` branch destinations. It fails closed on
different source fields, unnegated booleans, wrong modifiers, missing
code and SHA mismatch. No source is generated automatically.

## What remains unverified

Even when this micro-slice matches, **other original `<clinit>` instructions
and side effects are omitted**. Six original dynamic-final fields,
the remaining nested-enum-dependent conditional Boolean, actual nested
enum values/method bodies, subsequent mutable-field mutations and
three substantial original methods remain unrecovered.

This does not certify whole-method StackMapTable parity, source authorship,
complete original class initialization or runtime equivalence.
No canonical v309 class/field/member identity is promoted.
The original-private proof was measured using independent Java source
recompilation and `javap`; the GitHub comparator itself is tested on
synthetic javac classes and is not claimed to have run against the
private original JAR.

No original SpawnPK binaries, private JVM coordinates, recovered Java
or raw literals are committed to GitHub.
