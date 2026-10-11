# R45 — second verified non-ConstantValue JVM source initializer

The original v309 configuration class has 41 static-final fields.
R42 recovered the exact literal ConstantValue-backed 33. R44 privately
reconstructed one final integer-array allocation. R45 targets one
more final-field initializer whose original JVM expression is an
integer constant loaded with `ldc`, converted through
`java.lang.Integer.valueOf(int)`, and stored in the static field.

No raw original integer value or obfuscated field identifier is
published.

## Real private combined Java source proof

The already verified R42+R44 private Java candidate (37 declarations,
all exact) was copied into another **private** source directory. I added
the original expression as a static-final boxed-integer field, compiled
with `javac --release 9 -g:none -proc:none`, then inspected the
resulting JVM class against the pinned original v309 class.

| Measurement | R42+R44 | R45 private combined |
| --- | ---: | ---: |
| Declared fields | 37 | **38** |
| Declarations with exact original JVM metadata | 37 | **38** |
| Missing original fields | 89 | **88** |
| Non-ConstantValue final initialization expressions recovered | 1 | **2** |
| Existing candidate method declarations | 8 | 8 |
| Existing method opcode/resolved-operand sequences retained | 8/8 | **8/8** |

The boxed-integer initializer matches **three consecutive original JVM
instructions**: `ldc` of an integer, `Integer.valueOf(int)`, and
`putstatic` of the corresponding field. The R44 array initializer
also remains a three-instruction match in the R45 candidate.

The detailed original/client bytecode, private Java source, exact field
name and original integer value stay private. The public
[aggregate R45 record](../research/v309-source-recovery/boxed-integer-initializer-r45.json)
contains only SHA-256 fingerprints, counts and explicit certification
vetoes.

## Reproduce private initializer micro-parity

From a local clone of `Trexzo/SpawnPK-Client`, using actual measured
complete original/candidate JAR SHA-256 values:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.boxed_integer_microparity `
  'C:\private\original-v309.jar' `
  'C:\private\recompiled-candidate.jar' `
  'example/Configuration.class' `
  '<exact private boxed-Integer field name>' `
  --original-sha256 '<actual original complete JAR SHA256>' `
  --candidate-sha256 '<actual rebuilt complete JAR SHA256>' `
  --out 'C:\private\new-boxed-integer-proof.json'
~~~

These are placeholders, **not** mappings. The helper requires the field
to be static-final `java.lang.Integer` with no ConstantValue attribute;
locates an exact `ldc` of a JVM integer, `invokestatic
Integer.valueOf(I)`, and `putstatic` sequence in each class initializer;
compares the original raw integer constant bits, exact opcodes and
field metadata. It permits different bytecode offsets/constant-pool
indices but refuses unverified or differently compiled source paths.

Only a private report contains an opaque field ID and a digest of
the integer bits; public terminal output contains aggregate Boolean
checks, not original Java or raw names.

## Remaining gates

**Six original final-field initializer expressions remain unrecovered:**
five Strings and one project-defined reference. In addition, **88
original field declarations** and **three substantive original methods**
are missing from the R45 candidate.

Full class-initializer instruction/StackMap parity, side-effect order,
external dependencies, source equivalence and runtime behavior have
**not** been certified. Passing a three-opcode micro-gate does not
certify any other original bytecode or original class lineage.

The exact private v309 expression was independently measured via
local `javap` and private Java recompilation; the new GitHub verifier
has synthetic javac regression coverage but has **not** been claimed
to run against the private original JAR. Never upload the original
client, private Java, classfiles, literal value, original obfuscated
field path or detailed evidence report to public CI.
