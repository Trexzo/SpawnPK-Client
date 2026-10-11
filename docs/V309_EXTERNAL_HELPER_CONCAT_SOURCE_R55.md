# R55 — original v309 external String-helper + concat initializer

The final remaining `static final String` expression in the measured
v309 configuration owner starts with a **no-argument external static
String-returning helper**, runs `invokedynamic`
`StringConcatFactory.makeConcatWithConstants`, and stores the resulting
String into the original owner field.

Read-only analysis of the whole SHA-256-pinned original-v309 JAR
independently verified exactly one immediate instruction chain:

```text
invokestatic ExternalOwner.helper():Ljava/lang/String;
invokedynamic StringConcatFactory.makeConcatWithConstants:
    (Ljava/lang/String;)Ljava/lang/String;
putstatic OriginalOwner.finalString:Ljava/lang/String;
```

The external method is declared static with that exact JVM signature
in a unique original classfile. Its **method body and side effects
are not recovered**. The single invokedynamic bootstrap recipe has
one dynamic String marker and zero constant-argument markers. The
private candidate Java expression is reconstructed from that exact
source method and recipe, but the real original class/member names
and literal segments are not published. Its SHA-256 appears in the
[bounded R55 aggregate evidence](../research/v309-source-recovery/external-helper-concat-final-r55.json).

## Original-source progress interpretation

| Dynamic static-final String form | Independently measured |
| --- | ---: |
| R53: enum-helper-backed String | 2 |
| R54: conditional enum comparison + concat | 2 |
| R55: external static String helper + concat | 1 |
| **Total original String source forms accounted for** | **5 / 5** |

This covers the **local JVM expression shapes** of five runtime-assigned
String finals, not source/runtime equivalence. Compiling each generated
private expression against its independently recovered dependencies and
checking complete original JVM initializer ordering is still required.
R52's direct enum-final reference is a separate sixth final-field
source form and the R44/R45 int-array/boxed-int forms are separate still.

## Private replay from GitHub

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.external_helper_concat_source `
  'C:\private\original-v309.jar' `
  'example/Owner.class' `
  'C:\private\r55-new-output' `
  --original-sha256 '<exact complete original JAR SHA256>'
```

Paths/class coordinates above are **placeholders**. The generic module
checks complete original-JAR hashes pre/post, unique original owner and
external method classfile entries, exact no-arg static String helper
declaration, contiguous invocation/concat/store sequence, authenticated
StringConcatFactory method handle and one-marker recipe, incoming
branch/exception-handler veto, original final String field metadata,
and unique original stores.

Two exclusive-create outputs are private:
`external-helper-concat.private.txt` with original identifier/literal
source text and `external-helper-concat.aggregate.json` with only
counts and fingerprints. Existing output is never overwritten.

Hosted synthetic Java9 tests cover the exact external call+concat form,
nonstatic method rejection, incorrect bootstrap identity, incoming
branch, duplicate original store, wrong SHA and no-overwrite.

The exact GitHub R55 CLI is **not yet privately replayed against the
original JAR**; the original measurement is independent read-only
JVM evidence. Full external helper behavior, runtime side effects,
complete `<clinit>`, original authorial Java, and canonical class/member
identities remain unverified. Never publish original client binaries or
the private generated fragment.
