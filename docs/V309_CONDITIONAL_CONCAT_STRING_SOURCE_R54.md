# R54 — exact original v309 conditional StringConcatFactory source forms

The exact original v309 class has **five** nonconstant `static final
String` initializers. R53 independently identified two final Strings
assigned from enum static helper calls. R54 measures a different
two-String category: **enum comparison → conditional String literal →
JVM invokedynamic concatenation → final String store**.

## Independently observed original-v309 behavior

Both original instruction windows have this contiguous JVM pattern:

```text
getstatic owner.enumReference
getstatic owner$NestedEnum.enumConstant
if_acmpne Lelse
ldc "<private String true operand>"
goto Ljoin
Lelse: ldc "<private String false operand>"
Ljoin: invokedynamic makeConcatWithConstants:(String)String
putstatic owner.finalString
```

The two sites use the exact same `StringConcatFactory` bootstrap recipe,
which has **one** dynamic String marker and zero constant-argument
substitution markers. The original pre/post concat literal segments and
conditional String operands were extracted and reconstructed into **private
candidate Java expressions**, then independently SHA-256 hashed. The
[aggregate evidence](../research/v309-source-recovery/conditional-concat-string-source-r54.json)
contains no raw original literal contents, source/member names or network
endpoints.

The supported candidate expression form is conceptually:

```java
finalString = "private prefix" +
    (enumReference == enumConstant ? "first" : "second")
    + "private suffix";
```

Those words are illustrative placeholders, **not** the original
values. The original Java language syntax and complete JVM source/runtime
equivalence have not been established.

## GitHub private replay

Run from the actual GitHub checkout against the SHA-256-pinned private
original v309 JAR. Example coordinates are placeholders.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.conditional_concat_string_source `
  'C:\private\original-v309.jar' `
  'example/Owner.class' `
  'C:\private\new-r54-output' `
  --original-sha256 '<exact complete original v309 JAR SHA256>'
```

The new tool enforces original JAR SHA pre/post, unique class entry
identity, original dynamic final field store uniqueness, JVM exact nested
enum constant metadata, precise conditional and goto edges, bytecode
adjacency, valid `ldc` String operands, authenticated
`java/lang/invoke/StringConcatFactory.makeConcatWithConstants` bootstrap
method handle, exact one-argument String descriptor, one literal recipe
marker, no external incoming branch or exception-handler entry, and
safe private-only output.

It never downloads binaries or executes the original client. It writes
only into a new output directory:
`conditional-concat-source.private.txt` with original identifiers/literals,
and `conditional-concat-aggregate.json` with counts and hashes only.
Do not commit the private fragment or original JAR.

Hosted synthetic Java 9 tests confirm two exact source forms and rejection
of changed bootstrap origin, unexpected branch targets, altered enum
descriptors, duplicate target stores, wrong complete JAR hash and occupied
output directories. The actual R54 GitHub CLI itself has not yet been
replayed against the private client; original evidence was collected
independently via read-only `javap`.

## Unresolved source frontier

Combining the separate R53 (2) and R54 (2) operand-pattern measurements
provides source forms for **four of the five** dynamic-final Strings.
The remaining fifth involves an external static String-returning method
followed by a different invokedynamic concatenation recipe.

Even for the four described sites, the original nested enum source
collision, complete class initialization ordering, other side effects,
runtime equivalence and canonical member identities all remain
unaccepted. No generated Java or original binary is published.
