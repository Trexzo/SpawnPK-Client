# R38 — exact-input private source-frontier replay

The versioned [R37 v309 recovered-source frontier](../research/v309-source-recovery/frontier.json)
is an aggregate report, not a source release. R38 adds an executable
cross-check: regenerate the measurable class, method, field and JVM-header
evidence from **both original and rebuilt JAR bytes**. The output never
accepts identities or claims that the original Java is fully recovered.

## Replay from a local GitHub checkout

Prepare an original-client JAR and an independently compiled candidate JAR.
Use R33/R34 for the source compilation, with its complete staged-Java tree
SHA pin. Then run R38 from a local checkout using the exact measured complete
JAR SHA-256 values:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.source_frontier_replay `
  'C:\private\original-v309.jar' `
  'C:\private\compiled-candidate.jar' `
  'example/Configuration.class' `
  --original-sha256 '<64-character original-JAR SHA256>' `
  --candidate-sha256 '<64-character candidate-JAR SHA256>' `
  --frontier 'research/v309-source-recovery/frontier.json' `
  --out 'C:\private\new-source-frontier-proof.json'
~~~

The class entry and hashes above are **placeholders**; use your exact
measured values, never copy made-up or guessed coordinates. The tool
rejects JAR fingerprint drift, missing/duplicate class entries, unsupported
JVM evidence, previously unaccepted authority claims, and changes in the
recorded field/method/header counts. It creates a private report with
exclusive-create mode, so previous runs are not overwritten.

Without `--frontier`, R38 reports the measured class inventory and strict
R31/R32/R35/R36 method/field/header evidence without comparing a recorded
historical snapshot. This is useful for a **new** Java candidate that does
not match R37's old compiled fingerprint.

## Interpretation and remaining vetoes

R38 strictly measures classfile major versions, declared field/method counts,
JVM field modifiers and ConstantValue metadata, class header flags,
superclass/interfaces, and *current* R31 strict method-body classification.
It also confirms original/candidate classfile SHA-256 independent of whole
JAR ZIP offsets or compression choices.

A method previously called an 'instruction-level match' by R24 can **fail**
the stricter R31 StackMapTable parity gate, so R38 explicitly reports
`historical_R24_seven_method_claims_recertified=false`.
The R37 historic six-of-seven matching stack maps is not silently replaced
by a 'seven fully certified methods' claim.

Even if all *remeasurable* R37 snapshot dimensions agree, that is
a consistency proof only. Class and field identity acceptance, complete
JVM Code attributes, runtime behavior, external dependencies and authorial
source identity remain independently unverified.

**Never commit** original JARs, generated class slices, recovered Java,
full private reports, or original obfuscated class/member coordinates
to the public repository. Hosted tests compile only synthetic Java.
