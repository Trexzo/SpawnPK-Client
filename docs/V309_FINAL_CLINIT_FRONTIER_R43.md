# R43 — exact original JVM static-final initializer writes

R41 introduced a declaration-only private Java scaffold; R42 stages exact
JVM ConstantValue-backed literal expressions. The remaining eight original
static-final fields lack ConstantValue. Their initializer expressions
cannot be guessed or replaced with Java defaults.

## What was observed in exact original v309

The read-only private original client disassembly was inspected against the
R24/R37 recovered-Java candidate. The resulting
[aggregate R43 frontier](../research/v309-source-recovery/final-clinit-assignment-frontier-r43.json)
records:

| Property | Exact-original measurement |
| --- | ---: |
| Final fields total | 41 |
| Final fields with ConstantValue | 33 |
| Final fields without ConstantValue | **8** |
| Original class-initializer Code length | 473 bytes |
| Exact own-field putstatic sites for these finals | **8** |
| Original store sites per final | 1 |
| Candidate missing declarations | 7 |
| Existing candidate field with mismatched modifier | 1 |

The eight required field types are **five Strings, one int array,
one boxed Integer, and one project-defined reference**. Neither the
field names nor their original assignment expressions are committed.

## Reproduce the private store inventory

Using original and separately compiled candidate JARs with measured
complete-JAR SHA-256 pins, from the GitHub clone root:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.final_initializer_frontier `
  'C:\private\original-v309.jar' `
  'C:\private\recompiled-candidate.jar' `
  'example/Configuration.class' `
  --original-sha256 '<actual original JAR SHA256>' `
  --candidate-sha256 '<actual candidate JAR SHA256>' `
  --out 'C:\private\new-final-init-frontier.json'
~~~

Use actual pinned inputs and original class entry; placeholders are not
accepted mappings. The output file must not already exist. The CLI emits
**only aggregate counts**, while the local private report contains opaque
field IDs and exact write bytecode offsets.

R43 validates that each original static-final field lacking ConstantValue
has exactly one `putstatic` in the original `<clinit>`, and refuses
undocumented writes of those final fields outside the initializer.
It records the opcode immediately before the store as provenance.
**That opcode is not asserted to be the value producer.** Real stack
dataflow may involve branches, calls, aliases, temporary locals and
earlier instructions, so no Java initializer expression is generated.

## Next reconstruction gate

The remaining assignments must be recovered with exact producer and
dependency evidence, one field at a time. In particular, the original
initializer includes method calls and invokedynamic concatenations.
Writing a superficially similar Java expression without verifying its
compiled JVM operands, StackMapTable and initialization order could
change actual client behavior.

Before promoting any reconstructed initialization, require an independent
private compiled-source parity replay using the existing R31/R32/R35/R36
class and method gates. R43 neither modifies original classfiles nor
certifies source/runtime equivalence or canonical identities.

Original JARs, private Java fragments, literal values, raw JVM names,
full private reports and bytecode dumps must not be added to GitHub or
its hosted CI artifacts. Tests use synthetic javac classes only.
