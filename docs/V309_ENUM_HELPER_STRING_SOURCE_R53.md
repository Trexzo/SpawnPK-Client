# R53 — recover two exact enum-helper String initializer source forms

The exact original v309 class has five `static final String` fields
initialized at runtime rather than through a JVM `ConstantValue`.
After R52's direct enum-reference initializer, the remaining five
String values are a separate source-recovery obstacle.

## Two concrete verified JVM operand chains

Read-only, SHA-256-pinned original-v309 `javap` inspection established
**two** contiguous initializers with the exact form:

```text
getstatic owner.finalEnumRef : Lowner$NestedEnum;
invokestatic owner$NestedEnum.helper(Lowner$NestedEnum;)Ljava/lang/String;
putstatic owner.finalString : Ljava/lang/String;
```

Both original helper methods are declared static in the original
nested enum class and consume its exact JVM type. There are no branch
targets entering these producers or stores and no exception-handler
coverage. A corresponding private Java expression form exists for each,
with the exact original source/member names and order; its SHA-256 is
recorded in [R53 aggregate evidence](../research/v309-source-recovery/enum-helper-string-finals-r53.json).

These are **source expression forms**, not complete `<clinit>` code,
method correctness, or source/runtime equivalence. The fourth nested
enum still has a source name collision and unverified classfile metadata.
The R49 private flat workaround's nine normalized method matches do not
override those vetoes.

## Replay in the actual GitHub project

Run on a machine holding the exact original JAR, from your GitHub clone.
These class/hash parameters are placeholders, not accepted mappings.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.enum_helper_string_source `
  'C:\private\original-v309.jar' `
  'example/Owner.class' `
  'C:\private\r53-new-output' `
  --original-sha256 '<complete original SHA256>'
```

The new generic verifier validates both complete original JAR SHA
preflight and postflight, unique relevant classfile entries, original
field metadata, JVM enum superclass and modifier evidence, exact method
signature/static modifier, contiguous instruction chain, branch and
handler exclusions, and unique original initializer assignments.

The tool writes only into a fresh **private directory**:
`enum-helper-strings.private.txt` (real member identifiers/source text)
and `enum-helper-strings.aggregate.json` (counts and SHA-256 only).
Never check private fragments, binaries, literal strings, or original
obfuscated class coordinates into public GitHub.

Hosted synthetic Java 9 tests cover positive two-field recovery,
wrong descriptor, injected incoming branch, duplicate initializer
stores, incorrect full JAR hash and no overwrite.

## What remains

Of the five original runtime-assigned final Strings, **two** now have
verified immediate enum-helper invocation expression forms. Three
remain: two conditional selection + invokedynamic concatenation
initializers, and one external-method + invokedynamic concatenation
initializer. The new GitHub R53 CLI itself has not yet been run on
private original JARs; the original measurements were independent
read-only bytecode analysis. None of the original nested enum's helper
runtime methods, complete class initialization, source equivalence,
runtime equivalence, or canonical identities is certified by R53.
