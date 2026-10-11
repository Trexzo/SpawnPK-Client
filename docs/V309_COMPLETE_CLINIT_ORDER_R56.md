# R56 — original v309 complete initializer order is the next acceptance gate

R44–R55 identified source expression forms for all eight original dynamic
static-final initializers: one int array, one boxed int, one nested enum
reference, two static enum-helper Strings, two enum-conditional concat Strings,
and one external static String helper concat.

That **does not** establish parity for the full static initializer.

## Independently measured original v309 JVM initializer

From the exact SHA-256 pinned original v309 classfile
`CLIENT_CLASS_000167` (private original class coordinates withheld):

| Original JVM observation | Measured |
| --- | ---: |
| Declared fields | 126 |
| Classfile major | 53 (Java 9) |
| `<clinit>` instructions | 213 |
| `putstatic` writes | 93 |
| `getstatic` reads | 14 |
| `invokestatic` calls | 4 |
| `invokedynamic` calls | 3 |
| Explicit branch edges | 8 |
| Non-ConstantValue final initializations | 8 |

The opcode + bytecode-offset order projection is SHA-256 hashed in
[aggregate-only original evidence](../research/v309-source-recovery/clinit-store-order-r56.json);
neither proprietary class names nor original literals are committed.

The other **85 static writes** and their precise interleaving matter.
Knowing the eight final expression shapes is not enough to reconstitute
their complete initializer.

## New private verifier

`spk_recovery.clinit_store_order_witness` reads **two complete SHA-pinned
JARs**: the exact original and a separately **compiled Java candidate**.
Its private JSON alias map must explicitly cover every field written by
the original `<clinit>` and by the candidate. The verifier never guesses
the relationship between obfuscated field names.

It fail-closes unless all of these hold:

1. Both JARs have correct whole-file SHA-256 values before and after
   profiling, unique class entries, and parseable initializers.
2. Every class-local `putstatic` refers to a declared field.
3. The alias map is explicit, injective and complete for all stored fields
   in both classes; duplicate or missing entries are rejected.
4. The ordered sequence of mapped original and candidate `putstatic`
   targets matches **exactly**.
5. The complete JVM instruction opcode sequence matches and explicit
   branch destinations, normalized to instruction ordinals, match.

Only aggregate counts and truthful non-equivalence flags are written.
No original field identities, private alias rows, original literals or
classfile bytes are emitted to stdout or report artifacts. No input
is mutated; outputs are exclusive-create and existing paths are
preserved. The checker is intentionally **stricter than semantic
equivalence**; Java source can be behaviorally equivalent but compile
to different opcode layouts.

### Private replay

From a GitHub checkout holding a private original JAR, candidate JAR,
and accepted private alias file:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.clinit_store_order_witness `
  'C:\private\original-v309.jar' 'example/Original.class' `
  'C:\private\recompiled-source.jar' 'example/Recompiled.class' `
  'C:\private\field-aliases.json' 'C:\private\r56-new-output' `
  --original-sha256 '<whole-original-JAR-SHA256>' `
  --candidate-sha256 '<whole-candidate-JAR-SHA256>'
```

The private JSON must use this structural schema; field identifiers below
are illustrative, not recovered authority:

```json
{
  "schema_version": 1,
  "aliases": [
    {
      "original": {"name": "originalField", "descriptor": "I"},
      "candidate": {"name": "candidateField", "descriptor": "I"}
    }
  ]
}
```

Synthetic Java 9 test classes exercise matching mapped order, duplicate
and missing aliases, swapped assignment order, opcode mismatch, bad
descriptors, wrong JAR pins and output-collision preservation.

## Honest certification boundary

**No compiled private source candidate or 93-entry alias map has been
supplied to this R56 verifier.** The measured original 213-instruction,
93-write target is a grounded acceptance frontier, **not a passing
parity result**. Even a successful future R56 check does **not** prove
matching constant-pool operands, invokedynamic bootstrap recipes,
helper implementation side effects, original authorial Java or runtime
equivalence. Those need separate verification.

Do not commit private aliases, source fragments, original binaries,
or obfuscated original class coordinates to public GitHub.
