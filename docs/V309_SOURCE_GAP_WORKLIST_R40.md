# R40 — prioritized reconstruction gaps from exact JVM evidence

R37 and R38 measure the original-v309 recovered-source frontier. R40 adds
a **direct reconstruction worklist**, derived on demand from the same
SHA-256-pinned original and recompiled Java candidate archives.

Instead of ranking work from guessed names or hand-edited notes, the
worklist measures which original method bodies are missing or changed,
which missing original fields those methods reference, and how many
other original methods call each method within the same class.

## Local command

From the GitHub repository root with Python 3.11+:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.source_gap_worklist `
  'C:\private\original-v309.jar' `
  'C:\private\compiled-source-candidate.jar' `
  'example/Configuration.class' `
  --original-sha256 '<original whole-JAR SHA256>' `
  --candidate-sha256 '<compiled candidate whole-JAR SHA256>' `
  --out 'C:\private\gap-worklist-new.json'
~~~

Supply your **actual** original and candidate class entries and measured
SHA-256 pins. Paths and coordinates above are placeholders, not accepted
class mappings. The output file is created exclusively, without overwrite.

## What is measured

- All original methods classified by R31/R32 as matching, changed,
  missing or without an executable Code body. Only missing/changed
  methods with original bodies are included in the review worklist.
- For each open method: original bytecode size, number of incoming
  same-class JVM callsites, references to *missing* original fields,
  and count of distinct missing-field dependencies.
- For each absent or metadata-changed original field: original get/put
  reference counts and number of distinct referencing original methods.
- Deterministic suggested review order: first unique missing-field
  dependencies, then same-class incoming callsites, then original
  Code length. This ordering is a **heuristic only**; it does not claim
  semantic importance, a decompilation, or reliable runtime behavior.
- One-way opaque method/field IDs instead of raw JVM names, method
  descriptors, class paths, source text or private disassembly.

The underlying R31/R32/R35/R36 verifier enforces original/candidate
class path equality, pinned complete JAR hashes, decoded instructions,
StackMapTable frames, field declaration metadata and class headers.
Any unsupported strict evidence aborts the worklist rather than
presenting a partial report as a complete class recovery plan.

## Exact-private v309 gap dependency measurement

The repository now also records
[the R40 original-field dependency aggregate](../research/v309-source-recovery/gap-priority-r40.json),
measured read-only against the exact v309 class and the reproducible
R24/R37 private Java candidate. Original client full-JAR and candidate
class SHA pins are included in that record.

| Unrecovered role | Original Code bytes | Original instruction count | Original own-field access sites | Access sites targeting missing candidate fields | Distinct missing field dependencies |
| --- | ---: | ---: | ---: | ---: | ---: |
| Class initializer | 473 | 213 | 100 | 95 | **89** |
| Other unreconstructed public method | 1,614 | 697 | 78 | 73 | **42** |
| Save-dispatch target, compile-only placeholder | 929 | 364 | 49 | 44 | **41** |

The class initializer has the most distinct missing-field dependencies.
However the public method has substantially more bytecode and the save
target has behaviorally important callback wiring, so the table is
**not** an implementation priority judgment independent of other evidence.

The aggregate was measured using a separate strict private read-only
constant-pool field-reference scan. It **has not** been labeled as a
successful execution of the newly introduced R40 class-wide worklist
or as fully recovered current-R31 Java method parity. No raw client
identifiers or original classfile bytes are stored here.

## Interpretation for the v309 configuration candidate

R37 measured 126 original fields against 4 candidate fields and 10
original method declarations against 8 candidate declarations, with
three substantive original methods still unrecovered. Running R40
locally can identify the **relative dependencies** of the missing method
bodies on original class fields without uploading those private names.
It must not change R37's historic method-count evidence unless the
new exact-input replay is independently checked.

This is **not** a source generator or automatic identity promotion.
A method ranked first does not become equivalent until recompiled Java
has passed the appropriate strict method and class gates. Missing fields
that are not referenced by currently decoded methods still remain missing;
low usage counts are not evidence that they can be removed.

Never commit original client JARs, generated source, reconstructed
classfiles, or detailed private worklist JSON to public GitHub.
Hosted CI uses independently compiled synthetic Java only.
