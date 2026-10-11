# R48 — recover exact original static scalar initializers from JVM bytecode

R46 recovered mutable Java **field declarations**, but left their runtime
initial values unknown. R47 added type-only support for five original
nested-enum reference declarations. R48 moves to an actual, independently
recompiled piece of original **initializer behavior**: constant-producing
`<clinit>` instruction pairs that immediately store into original
mutable static scalar fields.

## Private exact-v309 proof

I independently reproduced the original R24 candidate from its archived
private Java and confirmed the exact R24 class SHA-256. I then compiled
a separate Java 9 candidate containing the 120 original field declaration
shapes from R42–R47, including **three explicitly unverified nested enum
type shells**. Using the exact-original v309 constant-pool and
`<clinit>` disassembly, I staged the original scalar assignments in the
original bytecode store order.

| Original mutable scalar field type | Verified literal-to-store pairs |
| --- | ---: |
| Booleans | **72** (31 true, 41 false) |
| Integers | **6** |
| Strings | **2** |
| **Total** | **80 / 80** |

The generated private Java was compiled with
`javac --release 9 -g:none -proc:none`. Direct original-vs-candidate
JVM disassembly comparison verified **80/80 matching immediate literal
producer opcodes, values and target `putstatic` field descriptors**,
without relying on matching original bytecode offsets or constant-pool
indices.

All 120 candidate field declarations still match original metadata,
and the original eight R24 method opcode/resolved-operand sequences
remain unchanged. Source, class and whole candidate JAR fingerprints
are in [the R48 aggregate evidence](../research/v309-source-recovery/mutable-scalar-initializers-r48.json).
No original private values, field names, JVM disassembly, Java source or
candidate binaries have been uploaded.

**Important:** 80 exact individual initial assignments do not reconstruct
the full `<clinit>`. Other field writes, nested-enum initialization,
dynamic-final expressions, invokedynamic calls and their relative
side effects remain unresolved. Later writes to the same mutable
fields in other methods are not included in this proof.

## GitHub-first private replay

From the GitHub clone root using verified local original and rebuilt
candidate **complete JAR** SHA-256 pins:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.mutable_scalar_initializer_source `
  'C:\private\original-v309.jar' `
  'C:\private\source-candidate-before-r48.jar' `
  'example/Owner.class' `
  'C:\private\new-r48-output' `
  --original-sha256 '<measured original whole-JAR SHA256>' `
  --candidate-sha256 '<measured candidate whole-JAR SHA256>'
~~~

Paths/class entries/hashes are placeholders, **not accepted mappings**.
The tool verifies both whole-JAR SHA-256 inputs, strict class method/field
matrix, original and candidate owner identity, and exact public/static
boolean/int/String field declarations. It then checks, **for every**
matching scalar field:

1. Original `<clinit>` has **exactly one** own-field `putstatic`.
2. The instruction immediately before the store is an adjacent
   supported JVM integer/boolean or String literal producer.
3. JVM integer ranges, boolean 0/1 encoding and String CP tag are valid.
4. The candidate does not already assign the target field in its
   own `<clinit>`.

Unsupported producers, missing assignments, duplicate writes,
non-printable/non-ASCII literal strings, modified field metadata or
input drift fail closed. The output is an exclusive-create
`mutable-scalars-clinit.fragment.txt` and an aggregate manifest
with SHA-256 of the private fragment. It is **not** merged into any
source automatically. The terminal prints no field names or literal
values.

## Verification and remaining blockers

Hosted CI uses synthetic independently compiled Java9 classes; it
proves exact literal/store-sequence replay, wrong-pin rejection,
no overwrite, duplicate-assignment refusal and honest behavior claims.

The private original-v309 evidence independently supports the 80/80
result, but **running the GitHub R48 CLI itself against private
original-v309 input is still a separate verification step**.

R47's nested enum shells remain non-equivalent to the original enum
source. Six original dynamic-final declarations/assignments are
still missing; three substantive original method bodies, original
initializer side-effect order and later field mutations are not
reconstructed. Strict StackMap, class and runtime equivalence
are not certified. No canonical class/member identities are accepted.

Never publish the private fragment, original client JAR, recovered
Java source, classfiles or raw obfuscated original identifiers.
