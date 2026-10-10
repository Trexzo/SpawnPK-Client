# R42 — exact JVM ConstantValue literals in private recovered Java

R41 stages missing field *declarations* without guessing initializers.
R42 adds **opt-in** source literals only where the SHA-pinned original
JVM class has an actual `ConstantValue` attribute, and where its
descriptor can be represented without changing the value.

## Original v309 source-recovery opportunity

The exact-private [R42 evidence record](../research/v309-source-recovery/exact-constantvalue-r42.json)
builds on the R37/R41 configuration class inventory:

| Missing final field category | Declarations |
| --- | ---: |
| Exact JVM literal constant attributes | **33** |
| No JVM ConstantValue; initializer still unknown | **7** |
| Shared existing field with different final modifier (no ConstantValue) | **1** |

The 33 literal attributes belong to **28 boolean fields, 4 integer fields
and 1 String field**. The JVM ConstantValue attribute records 32
integer-backed constants (including all booleans) and one String. No
raw original values or field names appear in the public repository.

## Local private staging

After obtaining separately SHA-256-verified original and compiled candidate
JARs, run this command from the GitHub clone root (Python 3.11+):

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.private_field_scaffold `
  'C:\private\original-v309.jar' `
  'C:\private\compiled-recovery-candidate.jar' `
  'example/Configuration.class' `
  'C:\private\new-r42-output' `
  --original-sha256 '<actual original complete-JAR SHA256>' `
  --candidate-sha256 '<actual candidate complete-JAR SHA256>' `
  --emit-verified-constants
~~~

Replace all placeholders with **locally verified** paths, class entry,
and complete-JAR SHA-256 values. The tool still applies the strict
original-versus-recompiled JVM class method, field and header checks,
and exclusively creates a private output root. It writes a text fragment,
not an automatically merged Java source file.

In this mode, a declaration whose **original field** is static final
and has exact JVM ConstantValue metadata may receive an explicitly
checked Java `= literal` initializer. Primitive integral, boolean,
and simple printable-ASCII String encodings are supported. The tool
fails closed on invalid values or ambiguous floating-point payloads.
Other declarations **remain without initializers**.

Without `--emit-verified-constants`, the R41 default remains
**declaration-only**, unchanged.

## Evidence requirements and limits

Synthetic Java regression tests separately compile original classes,
generate candidate fragments, recompile the generated literal declarations
and compare JVM field flags, descriptors and exact ConstantValue metadata.
The tests also cover boolean 0/1 validation, signed integral ranges,
string quoting/backslashes, rejected non-ASCII/control strings and
unsupported float/double values.

**Independent private real-v309 replay:** the 33 actual original JVM
ConstantValue-bearing declarations were emitted into an isolated *private*
Java class (not an original-client class replacement), compiled using
`javac --release 9 -g:none -proc:none`, and compared against the original
field descriptor and ConstantValue attributes. **33/33 fields matched**:
28 booleans, 4 integers and 1 String. Only the SHA-256 fingerprints of
the private source and compiled isolated proof class are stored in the
aggregate R42 record; the Java, original values and names are not
published. That independent replay used private JVM field observation,
not the R42 GitHub CLI; running the R42 CLI against the private original
is an additional separate verification step.

The exact literals have **not** been staged into a full original client
source class or claimed to pass full-source parity. The other seven final
assignments require separate reconstruction of JVM class-initialization
semantics, and the shared array-field final modifier mismatch remains
unresolved. Three substantive methods are still unrecovered.

No original client JAR, original constants, raw private field names,
generated Java fragment or compiled proprietary class is committed to
GitHub. Neither this process nor any amount of literal metadata parity
accepts canonical class identities or certifies runtime/source equivalence.
