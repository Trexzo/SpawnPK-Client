# R32 — class-wide source-method parity matrix

R25/R30 validate one Java method at a time. R32 summarizes an entire
**separately compiled** class against the exact original class, without
requiring a manual list of every method descriptor.

## Usage from this GitHub repository

Run locally with Python 3.11+ installed, original and candidate **JAR**
files, and their independently measured SHA-256 values:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.source_class_method_matrix `
  'C:\private\exact-original-v309.jar' `
  'C:\private\rebuilt-source-candidate.jar' `
  'example/Config.class' `
  --original-sha256 '<64-character original-JAR SHA256>' `
  --candidate-sha256 '<64-character candidate-JAR SHA256>' `
  --out 'C:\private\class-method-matrix-new.json'
~~~

Example paths and hashes are placeholders; never assume your local candidate
is a faithful build. The output path uses exclusive-create mode and will not
overwrite a previous report. Without `--out`, only aggregate counts print.

## What the matrix means

The tool verifies exact complete JAR SHA-256 fingerprints and unique
classfile ZIP entries. It compares identical JVM owner paths and groups
declared methods by exact name+descriptor. The underlying merged method
verifier compares JVM instructions, resolved constant-pool/indy references,
exception metadata, Code lengths, and stack/local maxima. Later added
bytecode gates may strengthen this without accepting mappings.

Counts are classified as:

- `instruction_parity`: shared method body passes the bounded parity gate
- `body_difference`: shared method body differs
- `missing_method` / `extra_method`: only one compiled class declares it
- `no_original_code`: original abstract/native or otherwise lacks Code
- `candidate_has_no_code`: compiled candidate lacks expected Code

**Field-inventory parity is a separate mandatory witness.** R35 now reports
original and candidate field totals plus shared exact declarations, shared
declarations with changed access/signature/ConstantValue metadata, missing
fields and extra fields. Class generic signatures are compared independently.
A method-complete candidate with missing or altered JVM fields remains
**incomplete** and cannot be mistaken for a reconstructed class.

Field metadata is compared by exact JVM name+descriptor; no auto-aliasing
or inferred source field rename is performed. Signed-zero constants remain
distinct, while potentially ambiguous NaN ConstantValue evidence fails
closed. Private per-field IDs are opaque; raw names are not printed.

An unsupported or incomplete method-body comparison fails the **whole**
matrix rather than creating an apparent success. Method identifiers in the
private output are one-way derived IDs: no raw obfuscated names/descriptors
are printed. Even when all measured method bodies match, the report **never**
claims source equivalence, accepted owner lineage, whole-class equivalence,
field correctness, runtime correctness or source publication eligibility.

## Application to the v309 frontier

The existing private seven-method configuration reconstruction has several
unreconstructed methods. R32 can measure its method inventory and deviations
in one deterministic pass, *once it is compiled as a separate candidate
archive*. Its field counts can now expose the known structural incompleteness
of the private configuration source candidate even when individual methods
match. It does not accept `CLIENT_CLASS_000167` or the three unresolved
field candidates, nor does it modify `authority/` or canonical lineages.

Original JARs, source candidate Java, generated classfiles and private
method-matrix JSON remain **outside the GitHub repository and CI**.
Hosted tests use independently compiled synthetic Java fixtures only.
