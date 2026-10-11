# R47 — exact nested-enum reference field declarations (private source bridge)

R46 independently compiled a partial v309 Java source candidate with
**115 of 126 original JVM field declarations**. The remaining source
declaration frontier included five mutable fields referencing original
nested enum types, plus six static-final fields needing actual
class-initializer reconstruction.

R47 adds a deliberately **source-shape-only** bridge for the five
mutable nested-enum reference fields. It **does not recover enum values,
constructors, method bodies or runtime behavior**.

## Measured private source-rebuild result

I independently recompiled the exact R24 four-file candidate from its
archived private source and reproduced its classfile SHA-256. Against the
SHA-256-pinned original v309 JAR, I then assembled the independently
observed R42 literal declarations, R44 array allocation, R45 boxed-integer
assignment, R46 mutable scalar declarations, and the five missing
mutable nested-enum declarations.

The original nested type dependencies were checked against **three
distinct actual v309 enum classfiles**. To compile the owner without
using the original binary as a javac classpath, this proof used three
**empty, explicitly unverified nested enum shells**. Those shells have
the required Java type names but **none of the original enum constants
or initialization semantics**.

| Evidence | Previous R46 | Independent R47 private replay |
| --- | ---: | ---: |
| JVM owner fields represented | 115 | **120** |
| Fields matching original JVM declarations | 115 | **120** |
| Original fields still missing | 11 | **6** |
| New mutable nested-enum reference fields | — | 5 |
| Distinct enum type-shell placeholders | — | 3 |
| Existing R24 method opcode/operand sequences retained | 8/8 | **8/8** |

The six missing fields are **five dynamic-final Strings and one
dynamic-final nested-enum reference**. Their initializer semantics
remain unreconstructed. The new 120-field proof is an *independent*
R24-derived private rebuild and does not assert the exact R46 private
Java file fingerprint was reproduced.

The [R47 aggregate evidence](../research/v309-source-recovery/nested-enum-references-r47.json)
contains SHA-256 of the private Java, compiled owner class and candidate
JAR, input original-JAR pin and non-equivalence vetoes. The private
source, enum shells, original JVM field names and classfiles stay off
public GitHub.

## Generate a private reference-field and type-shell fragment

Run from a cloned repository using **actual** original and candidate
whole-JAR SHA-256 values, plus the exact original owner class entry:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.enum_reference_source_bridge `
  'C:\private\original-v309.jar' `
  'C:\private\candidate-before-reference-bridge.jar' `
  'example/Owner.class' `
  'C:\private\new-r47-bridge' `
  --original-sha256 '<verified original whole-JAR SHA256>' `
  --candidate-sha256 '<verified candidate whole-JAR SHA256>'
~~~

All paths and class coordinates above are **placeholders**, not
accepted v309 mappings. R47 checks both complete JAR pins, the existing
strict class method/field/header matrix, exact original nested enum
class headers and original owner field descriptors. It then creates a
new private folder containing:

- `owner-enum-reference-fields.fragment.txt`: exact missing mutable
  public/static nested-enum field declarations, without assignments
- `unverified-enum-type-shells.fragment.txt`: empty nested Java enum
  type shells, explicitly marked **NOT recovered enum source**
- `aggregate-private-source-bridge.json`: SHA-256 fingerprints and
  aggregate counts; no raw field names

The `.txt` fragments are not silently inserted into a candidate Java
file or published. The CLI never attempts to generate the original
nested enums' constants/constructors or initialize the six remaining
final fields.

## Source authority and next step

Compiling a Java field of type `Owner.NestedEnum` with an empty
placeholder enum proves only that the **field descriptor shape** is
representable in Java. The resulting enum classfile is *not* a match
for the original: enum constants, instance data, initialization order,
generated values()/valueOf methods and any custom bodies remain
unverified.

To go beyond the 120-field milestone, recover the actual source for
the nested enums and the six dynamic-final field assignments from
exact v309 evidence. The original owner `<clinit>`, mutable field
initializations and three substantive missing methods also remain
unrecovered. Full R31/R32/R35/R36 class/method/StackMap and runtime
acceptance is **not** achieved or implied by this proof.

Hosted regression tests compile **synthetic** nested Java enums,
exercise field-metadata equivalence, check original enum header
validation and enforce no output overwrite. No proprietary binary,
source or original obfuscated coordinates are committed.
