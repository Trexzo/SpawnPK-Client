# R50 — original JVM conditional-boolean join witnesses

R48 verified **78 of 80** direct literal-to-store pairs in the private
v309 `<clinit>` and deliberately withheld **two branch-joined booleans**.
R50 adds a bounded, fail-closed way to inspect whether either excluded
store matches one specific JVM instruction/control-flow pattern.

## What a successful witness proves

Only this contiguous, local JVM diamond is supported:

```text
  if<cond> L2
  iconst_0 or iconst_1
  goto Lstore
L2:
  iconst_1 or iconst_0
Lstore:
  putstatic owner.boolean_field
```

The conditional may use any supported conditional JVM branch opcode,
but its **predicate-producing code is not reconstructed**.

A valid witness requires distinct exact 0/1 values; correctly aligned
instructions; the conditional branch into the second constant; a goto
to the common store; no other incoming explicit branch/switch edges into
the five-instruction window; and no exception-handler coverage or
landing point inside the window. Any violation leaves that store
**unresolved**, without guessing a constant or Java expression.

## Local replay from GitHub

Use exact local input SHA-256 fingerprints and the original classfile
entry. These are placeholders, not accepted obfuscated names.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.boolean_join_witness `
  'C:\private\original-v309.jar' `
  'C:\private\candidate-before-join.jar' `
  'example/Owner.class' `
  'C:\private\new-r50-replay' `
  --original-sha256 '<measured complete original JAR SHA256>' `
  --candidate-sha256 '<measured complete candidate JAR SHA256>'
```

The tool validates both entire JAR hashes before and after use, JVM
field metadata, owner identity, and the pre-existing strict method/field
matrix. It creates only a new **private** output directory:

- `original-boolean-join-private.json` — field names and offsets,
  local condition opcode, and both exact boolean values. Never commit.
- `boolean-join-aggregate.json` — counts, pins and non-acceptance flags,
  with no private field names or condition literals.

A separate **read-only, original-binary** analysis now confirms that
**both** of the R48-excluded original-v309 boolean stores do match this
narrow five-instruction diamond. This was observed directly using
SHA-256-pinned v309 bytecode and `javap -c -p`, with complete incoming
branch-edge enumeration, no exception-table coverage, and unique original
owner identification from JVM structural counts. One uses an
`if_acmpne` comparison of two static references; the other uses
`ifne` after reading a static boolean. Both have the original
fallthrough value `true` and branch-taken value `false`.
See the [bounded aggregate original-v309 measurement](../research/v309-source-recovery/boolean-join-shape-r50.json).

**This original-binary measurement is distinct from the new R50 GitHub
CLI**: that exact CLI has **not** yet been replayed on the private original
and candidate JAR pair. Hosted CI still tests synthetic Java only. Even a real matching witness would recover **possible stored
boolean values and immediate local branch structure only**, not the
predicate, exact Java initializer expression, full `<clinit>` side-effect
order, later runtime writes, complete class source, or canonical identity.

## Tests and further proof

Hosted CI synthetic Java 9 tests check javac-generated ternary store
patterns, an extra incoming edge, an exception handler, duplicate stores,
wrong input JAR SHA, existing-output preservation and refusal to mistake
a direct constant store for a conditional join.

Next: execute this exact GitHub CLI on the private original and
candidate JARs, then independently reconstruct and test each original
**predicate producer** before staging a Java source expression.
Do not count the two withheld booleans as recovered until that work.
