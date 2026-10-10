# R33 — isolated private-source compilation and class-wide parity

This GitHub-owned workflow composes R31 (resolved JVM StackMapTable),
R32 (whole-class method inventory) and an isolated `javac --release 9`
build of a privately reconstructed Java source slice.

It is designed to make *recovered source* work measurable. It does not
claim that private candidate source is a complete v309 implementation.

## Use

From a local clone of `Trexzo/SpawnPK-Client` with Python 3.11+ and
JDK 21 available:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.source_candidate_replay `
  'C:\private\exact-v309-client.jar' `
  'C:\private\source-candidate-root' `
  'C:\private\source-candidate-root\example\Config.java' `
  'example/Config.class' `
  'C:\private\r33-new-output' `
  --original-sha256 '<actual original JAR SHA-256>' `
  --source-sha256 '<actual Config.java SHA-256>' `
  --timeout-seconds 180
~~~

Replace all paths and hashes with *measured local values*. The output root
must not already exist. It contains the newly built private candidate JAR,
compiled JVM classes, and a JSON method-parity report. A second run with
the same inputs and a new output directory should reproduce the same
candidate-JAR bytes and aggregate matrix.

## Isolation and verification

- Pins original full-client JAR and the entry Java source with SHA-256
  before creating outputs, then verifies the same exact bytes afterwards.
- Compiles with `--release 9 -g:none -proc:none`, with a fresh **empty
  classpath**, and an explicit source path. The original client JAR is
  **not** used as a compiler dependency.
- Does not run candidate Java. It only compiles it and profiles classfiles.
- Refuses missing target class, wrong input hash, compiler timeout,
  invalid output path or compilation failure. Compiler stdout/stderr is
  not echoed into errors because it can disclose proprietary source.
- Records original and compiled-JAR fingerprints, class counts, and the
  strict per-method parity matrix from R32 using the now-merged R31
  frame parser. All detailed output remains private and local.
- Will not publish a success report after failed compilation or matrix
  validation. Partial output may remain locally for diagnosis.

Only the entry source file is directly SHA-pinned. Other .java files
loaded implicitly through `-sourcepath` must be treated as additional
**private candidate dependencies**; a complete provenance/closed-input
proof for them is an independent future gate. This is therefore a bounded
development aid, NOT final build reproducibility authority.

## Status and safety

The private seven-method configuration candidate from R24 has only partial
method-body correspondence to original v309. R33 can compile and measure
it in one command, but it is **not a client replacement** and has three
substantive unreconstructed methods plus many missing original fields.
A compiling Java method can also depend on runtime behavior unavailable
in this source slice.

No original JARs, candidate Java, compiled proprietary classfiles, or
private report files should be committed or uploaded to public GitHub.
Zero canonical class/member/field acceptances occur here. Source milestone
publication still requires independent review, source completeness and
explicit authority promotion.
