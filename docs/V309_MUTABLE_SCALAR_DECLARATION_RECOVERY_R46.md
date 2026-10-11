# R46 — reconstruct mutable scalar Java declarations without guessed initializers

R42 recovered exact JVM ConstantValue literal declarations. R44/R45
independently verified two non-ConstantValue static-final initializer
expressions. R46 recovers the **declaration syntax only** of additional
mutable static scalar fields directly from the exact original JVM
field inventory. Unlike source initialization reconstruction, the
declarations themselves can be recompiled without project-defined
reference types or invented assignment values.

## Independently compiled private v309 source

Using the exact original v309 class and a private copy of the combined
R45 Java9 source candidate, I staged **77 missing mutable static field
declarations**: 69 booleans, 6 integers, and 2 Strings. The four staged
R24 support-source files were compiled with
`javac --release 9 -g:none -proc:none`, without classpath access to the
original client binary.

| JVM field declaration evidence | Previous R45 | R46 |
| --- | ---: | ---: |
| Candidate field declarations | 38 | **115** |
| Candidate fields exactly matching original JVM metadata | 38 | **115** |
| Original field declarations still missing | 88 | **11** |
| Existing candidate method disassemblies preserved | 8/8 | **8/8** |

The remaining 11 declarations comprise five original String fields
and six project-defined reference fields; **six** of these are original
non-ConstantValue final fields whose initialization semantics are
unrecovered.

**Critical:** field declaration parity is *not* field-value or runtime
initialization parity. Many of the 77 added original mutable fields
receive assignments in the original `<clinit>`; the R46 source has
**not** reconstructed those assignments. It would be incorrect to
claim equivalent runtime configuration, a functional v309 source client
or source/runtime equivalence based on the 115/126 field count.

The private Java source, classfile, deterministic candidate JAR and
SHA-256 fingerprints were independently verified; only the hashes
and aggregate counts are recorded in
[the R46 evidence record](../research/v309-source-recovery/mutable-scalar-declarations-r46.json).
No original field names or source code are published.

## Reproduce declaration-only staging

On the local machine, with a clone of this repository and separately
verified original and private candidate whole-JAR SHA-256 values:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.private_field_scaffold `
  'C:\private\original-v309.jar' `
  'C:\private\private-candidate.jar' `
  'example/Configuration.class' `
  'C:\private\new-r46-scalar-fragment' `
  --original-sha256 '<actual original complete-JAR SHA256>' `
  --candidate-sha256 '<actual candidate complete-JAR SHA256>' `
  --scalar-declarations-only
~~~

The paths, hashes and class entry are placeholders. The tool uses the
strict original/candidate JVM class method+field matrix and exact
SHA-256 input pins, then emits **only** missing `public static`
boolean, int and String fields with the exact JVM access mask and
no ConstantValue attribute. All other fields are counted as excluded;
the output is a private, non-`.java` text fragment with declarations
only and an aggregate JSON manifest. No existing files are overwritten.

This flag is mutually exclusive with R42's
`--emit-verified-constants` to avoid mixing literal and
declaration-only proof scopes. Omitted flags retain the existing
R41/R42 behavior.

## Next source-level blockers

1. Recover the remaining project-defined field types and the six
   non-ConstantValue final-field assignment expressions with exact
   type and dependency evidence, without an original binary classpath.
2. Reconstruct the original `<clinit>` runtime values and assignment
   order for the 77 mutable scalar declarations and other fields.
3. Recover the three missing substantive method bodies and all
   referenced source dependencies.
4. Run strict JVM StackMapTable, class, method and field parity gates
   from R31/R32/R35/R36, and independent runtime behavior tests.

No canonical class/member/field identity is accepted by this change.
Hosted CI tests use synthetic Java fixtures only; a private exact-v309
run of the GitHub CLI is distinct from the independent R46 compiled
source demonstration and is not falsely claimed.
