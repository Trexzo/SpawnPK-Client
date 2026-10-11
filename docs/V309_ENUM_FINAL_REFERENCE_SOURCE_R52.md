# R52 — independently witnessed original nested-enum static-final source form

R43 measured eight original v309 static-final declarations whose initial
values are assigned by `<clinit>`, rather than encoded as JVM `ConstantValue`.
R44/R45 recovered one integer-array initializer and one boxed integer.
The **six** outstanding final declarations are five Strings and one
reference to an owner-nested enum.

## Concrete exact-original v309 finding

On the SHA-256-pinned v309 JAR, the remaining enum-typed final field's
initializer is an **immediately adjacent** JVM `getstatic` of a
nested enum constant, followed by a `putstatic` into the owner field,
at the start of the original `<clinit>`. The referenced enum type has
the exact expected descriptor. Independent read-only JVM inspection
identified one such pair. The complete private source-form fragment,
including original identifiers, was reconstructed and SHA-256 hashed
locally, **not published**. Only
[aggregate original evidence](../research/v309-source-recovery/enum-final-reference-source-r52.json)
is tracked.

This is a **single exact source-expression form**, not reconstruction of
the fourth enum's source/runtime behavior. The original obfuscated enum
has the real Java source naming collision identified by R47/R49, and
its independently reconstructed flat-dollar candidate still lacks exact
InnerClasses/synthetic method parity. No runtime behavior is certified.

## Reusable GitHub verifier

`spk_recovery.enum_final_reference_source` verifies:

- Original whole JAR fingerprint before and after parsing.
- Unique original owner class entry and exact nested enum class entry.
- Original nested field has static/final flags and no ConstantValue.
- Nested class is a JVM enum with `java/lang/Enum` superclass.
- Referenced enum constant is marked JVM enum/static/final.
- Original `getstatic` + `putstatic` pair is contiguous, with the same
  exact referenced enum descriptor, and the original target is written
  exactly once.
- No incoming branch target or exception-handler coverage can skip the
  producer/store pair.

It creates a **new private directory only** and returns an aggregate
report without leaking identifiers, original literals or bytecode.
An unsupported or unproven enum reference is omitted from recovered
source forms. Bad input/hash, duplicate/missing stores, wrong enum
structural evidence or existing output directories fail closed.

From a GitHub checkout with the private original v309 JAR:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.enum_final_reference_source `
  'C:\private\original-v309.jar' `
  'example/Owner.class' `
  'C:\private\r52-new-output' `
  --original-sha256 '<exact measured whole-JAR SHA256>'
```

The example class name and hash marker are **not** accepted canonical
identities. R52's generic tool has not yet been run on the original
private client JAR; its original proof was independently measured.

Hosted regression tests use synthetic Java 9 `enum` source with a
`static final` enum reference, plus negative reference-descriptor,
wrong nested class, duplicate store, injected branch edge, wrong pin,
and output collision cases.

## Remaining blockers

The one original static-final enum **reference assignment** has a
verified JVM source form, but its source-level enum class remains
unverified and does not automatically compile as the original nested
type. The five String dynamic-final expressions involve conditional
selection, invokedynamic concatenation and external methods and remain
outstanding. Full `<clinit>` ordering/side effects, complete recovered
source, authoritative identifiers and runtime equivalence are separate
unmet gates. Never commit the private fragment or original client.
