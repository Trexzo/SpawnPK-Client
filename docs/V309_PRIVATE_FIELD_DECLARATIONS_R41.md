# R41 — stage exact missing JVM field declarations privately

The [R37 source frontier](../research/v309-source-recovery/frontier.json)
documents a class with **126 original field declarations** and only **4**
declarations in the R24/R37 partial Java candidate. R41 addresses the
*declaration* portion of that gap while deliberately **not reconstructing
field initializers or source behavior**.

## Measured private v309 configuration inventory

The [aggregate R41 field gap](../research/v309-source-recovery/field-declaration-gap-r41.json)
is cross-checked against the tracked R37 original/candidate fingerprints:

| Field declaration property | Original v309 | R24/R37 candidate | Missing |
| --- | ---: | ---: | ---: |
| Total fields | 126 | 4 | **122** |
| Static fields | 126 | 4 | **122** |
| Final fields | 41 | 0 | **40** missing, 1 modifier mismatch |
| Mutable static fields | 85 | 4 | **82** |

The 122 missing field types are 97 booleans, 10 integers, 8 strings,
6 project-defined object references and 1 boxed integer. The candidate
already contains the one original integer-array declaration, but its
`final` modifier differs.

**ConstantValue boundary:** 33 of the 40 missing `final` fields have
an exact original JVM `ConstantValue` attribute. The other 7 missing
finals have no such attribute, and the shared array-field `final`
mismatch also has no `ConstantValue`. Across all 41 original final
fields, this divides into **33 with literal constant evidence and 8
without**. R41 counts the evidence but does not emit initializer code.
A later independently reviewed tool could use the 33 exact constant
values; the remaining 8 require initializer/assignment reconstruction. Of the four candidate declarations, three
have exact JVM field metadata, while one is a known mismatch.

## Generate a private field declaration fragment

From a local clone of `Trexzo/SpawnPK-Client` with Python 3.11+:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.private_field_scaffold `
  'C:\private\original-v309.jar' `
  'C:\private\recompiled-candidate.jar' `
  'example/Configuration.class' `
  'C:\private\new-r41-scaffold' `
  --original-sha256 '<actual original complete-JAR SHA256>' `
  --candidate-sha256 '<actual candidate complete-JAR SHA256>'
~~~

Use your *actual* SHA-pinned complete original and candidate JARs, plus the
verified class entry. Placeholder paths and hashes are not accepted class
mappings. If necessary, R33/R34 can produce the candidate JAR from locally
staged reconstructed Java with a fully pinned staged source tree.

The tool rejects unsupported JVM/Java identifiers, malformed descriptors,
unsafe Java field access flags, generic signatures that cannot be faithfully
translated from JVM descriptor alone, different-type name collisions, and
incomplete class/method/field parity evidence.

It exclusively creates:

- `missing-fields.fragment.txt` — **private** declaration-only source
  fragment, with exact JVM name, descriptor-based Java type and modifiers
  from the original class. It is deliberately not a `.java` file and is
  not inserted into the candidate automatically.
- `private-field-scaffold-manifest.json` — aggregate counts, SHA-256 of
  the emitted fragment and input JAR pins, with **no private field names**.

Original binaries and source remain unmodified. Existing files/directories
are not overwritten.

## Critical initializer and source-completeness boundary

The helper intentionally writes **no `= null`**, `= 0`, `= false` or
other manufactured initializer. An original `static final` field can
require a field `ConstantValue` or a particular `<clinit>` assignment.
The 33 missing finals with exact `ConstantValue` metadata can be
treated as literal initializer candidates in a separate, verified recovery
pass. The other 7 missing final declarations—and the shared candidate
array field with a `final` modifier mismatch—still need explicit
initializer/assignment recovery. R41 itself emits no initializers and
requires manual review before attempting to compile the fragment into a
source file. The one original candidate field with a
`final` modifier mismatch also requires independent reconciliation.

The source candidate's other unreconstructed methods and hundreds of
field access sites are not implemented by this tool. **A valid declaration
does not imply recovered initialization, runtime behavior, source
authorship or a certified original client.**

Do not upload the private fragment, original JAR, recompiled candidate
class, raw original member identifiers or decompiled source to public
GitHub or CI. Only generic tooling, synthetic regression tests and the
aggregate numerical frontier belong in this repository.
