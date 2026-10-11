# R49 — real v309 nested-enum source candidates with verified JVM method slices

R47 established four original nested enum classfiles, byte-identical
between exact original v308 and v309. The private partial owner source
needs those enum types to reconstruct original field declarations.
R47's type-only shells are **not** source recovery.

## Real private Java 9 source experiment

I independently reconstructed three of those original enum types as
private Java `enum` declarations. Using read-only exact original-v309
bytecode, I reproduced each constant's semantic JVM runtime name,
ordinal and constructor data. One enum also has a case-insensitive
lookup method; its Java implementation reproduced the original compiled
instruction sequence.

The source was compiled under `javac --release 9 -g:none -proc:none`,
without using the original client binary as a classpath fallback.

| Measured category | Private R49 result |
| --- | ---: |
| Original owner-nested enum classes | 4 |
| Independently compiled Java enum source candidates | **3** |
| Exact original enum constant name/ordinal/argument records represented | **14** |
| Original enum method bodies compared | **16** |
| Instruction bodies matching after *explicit* generated-name aliases | **16/16** |
| Source-name collision still blocking fourth enum | **1** |

Per-enum original/candidate JVM classfile and common private source
SHA-256 values, method counts and the exact bounded normalization
policy are recorded in
[the R49 aggregate evidence](../research/v309-source-recovery/nested-enum-source-parity-r49.json).

**Crucial identity limitation:** The original client obfuscates the JVM
static enum-constant field identifiers and private compiler-generated
array/helper names. Java `enum` source necessarily uses constant identifiers
that agree with runtime `Enum.name()`, not those obfuscated JVM field
identifiers. So **16/16 instruction matches require three explicitly
reviewed name-alias categories**: constant fields by ordinal/declaration
order, generated values-array field and generated values-helper method.
Constant strings, integer constructor values and other JVM operations
were *not* replaced or guessed. This is **not** exact binary parity and
does not accept the obfuscated-to-recovered class/field mapping.

The fourth enum has the same simple source-level name as its enclosing
owner. Java rejects declaring that nested enum verbatim, as R47's
compiler test demonstrates; it remains unrecovered in valid original
source form. No fabricated workaround is promoted.

**Separate fourth-enum flat-dollar prototype:** I independently wrote a
private top-level Java `enum` whose legal identifier contains a dollar
sign so its compiled JVM *internal class name* equals the original
nested enum's binary owner. It reconstructed the original two runtime
constant records and **9/9 normalized method instruction sequences**.

This is a **source prototype, not exact nested source**. The flattened
Java declaration omits the original `InnerClasses` attribute for the
nested enum, and two hand-written static accessor methods have different
`ACC_SYNTHETIC` access bits from the original compiler-generated
accessors. Furthermore, enum constant field identifiers remain
semantically named rather than the original obfuscated JVM identifiers.
The separate [R49 collision proof](../research/v309-source-recovery/flat-enum-collision-r49.json)
pins private source/class hashes, records the two concrete metadata
vetoes, and **explicitly forbids** source/runtime identity acceptance.

Across the three strictly nested Java candidates plus this **flat
collision workaround**, all four original enum classes have private
Java source prototypes and **25/25 instruction bodies** matched after
documented name normalization. This does **not** mean 25 complete
method/class equivalence certifications; the fourth remains rejected
by the stricter R49 comparison gate.

## GitHub replay for an independently compiled candidate

The R49 comparator validates exact-original and candidate **whole-JAR
SHA-256** pins and the original class entry on each of the three enum
types; verifies JVM enum superclass, class flags, field access and
declaration types, unique enum values and compiler helper fields, then
compares **every method** with normalized JVM instruction sequences,
branch targets and frame/handler metadata.

From the repository root:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.nested_enum_source_parity `
  'C:\private\original-v309.jar' `
  'C:\private\candidate-with-reconstructed-enums.jar' `
  '<actual original enum class entry 1>' `
  '<actual original enum class entry 2>' `
  '<actual original enum class entry 3>' `
  --original-sha256 '<actual original full-JAR SHA256>' `
  --candidate-sha256 '<actual candidate full-JAR SHA256>' `
  --out 'C:\private\new-r49-enum-parity.json'
~~~

The command has no invented original class coordinates. Insert your
locally verified paths, entries and SHA pins. Only **aggregate** Boolean
results and counts are output, with no obfuscated class/field names or
private constructor literal values. The private report is
exclusive-create and must stay outside the public repository.

The independent original-vs-recompiled 16/16 observation above used
private normalized `javap` comparisons. The new GitHub R49 parser
and its hosted tests constitute an additional check; **do not**
claim the parser was executed against the private original unless
that exact replay has actually completed and passed.

## What remains

Recover the fourth collision-affected enum, establish reviewed
obfuscated JVM alias mappings for actual client source linkage,
reconstruct original enum `InnerClasses` metadata and preserve
correct outer-class initialization wiring.

The parent configuration source still lacks five original dynamic-final
String declarations/initialization expressions, and the original
`<clinit>` and three substantive method bodies have not been fully
reconstructed. R48's 78 direct scalar initializer pairs are
independent work; they do not certify complete source or runtime behavior.

No proprietary original JAR, decompiled source, compiler output,
literal enum values, raw JVM member paths or private source is committed.
No canonical mappings are automatically accepted.
