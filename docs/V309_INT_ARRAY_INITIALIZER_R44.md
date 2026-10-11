# R44 — first exact original non-literal array initialization recovery

R42 recovered exact JVM ConstantValue-backed Java expressions in private
source. For fields without ConstantValue, source initialization requires
separate bytecode evidence. R44 demonstrates this on one concrete,
bounded original-v309 array field and adds a reusable fail-closed
three-instruction micro-parity checker.

## Private R24 source reconstruction experiment

The original v309 configuration class declares a static final integer
array. Its original JVM class initializer allocates an array with
**10 elements**, using the consecutive instructions:

`bipush 10` → `newarray int` → `putstatic` for that field.

In a **private copy** of the R24 partial Java source, I changed the
existing mutable array declaration into a final field initialized by
the exact `new int[10]` expression, and recompiled the four private R24
Java files using `javac --release 9 -g:none -proc:none`.

| Verification | Result |
| --- | --- |
| Original and compiled candidate field metadata | Exact static/final match |
| Recompiled allocation instruction sequence | **3/3 matches**, modulo offset and CP index |
| Existing candidate method declarations | 8/8 preserved |
| Existing method opcode + resolved operand disassemblies | 8/8 unchanged |
| Previously matching candidate fields | 3 |
| Candidate fields matching original metadata after change | **4** |
| Entire original class initializer equivalent | **No** |

The original client remains unchanged. Both private baseline and updated
candidate class SHA-256 values, plus a source SHA-256, are recorded in
[the aggregate R44 proof](../research/v309-source-recovery/int-array-initializer-r44.json).

**Scope distinction:** This is a standalone R24 four-field candidate
with one field repaired. The R42 33-literal/37-field expanded source
was not additionally merged into this exact private R44 prototype.
Do not claim a measured 37-of-37 combined source rebuild yet.

## Run the verifier locally

From the GitHub clone root, with Python 3.11+ and the original/candidate
**complete JAR SHA-256** values measured independently:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.array_initializer_microparity `
  'C:\private\original-v309.jar' `
  'C:\private\r24-array-initialized-candidate.jar' `
  'example/Configuration.class' `
  '<exact private field name>' `
  --original-sha256 '<actual original JAR SHA256>' `
  --candidate-sha256 '<actual candidate JAR SHA256>' `
  --out 'C:\private\new-array-microparity.json'
~~~

The example paths/class/field identifiers are placeholders and **not**
accepted mappings. The tool requires both classfile fields to be
static-final `int[]`; verifies each has a single directly consecutive
integer-size instruction, `newarray int` and `putstatic` in
`<clinit>`; compares field modifiers, exact array length/type, and
opcode sequence. A different constant-pool index or earlier
initializer instructions may shift bytecode offsets without breaking
the narrowly defined match. A non-final field or a complex
allocation-expression suffix fails closed.

## Remaining recovery gates

Micro-parity validates **only this allocation fragment**, not the full
class-initialization method, missing dependencies, stack-map verifier
behavior, method call graph or runtime semantics. The private R24 source
still lacks 122 original field declarations and three substantive
method bodies. R42 addresses 33 literal fields independently; the next
step is to combine exact R42 literal declarations and R44 array
initialization into a single private Java source revision, then
measure it against the original with R31/R32/R35/R36.

Public GitHub includes generic tooling, synthetic javac tests and
aggregate cryptographic evidence only. No original client JAR, raw
obfuscated field identifier, private Java source, classfile or recovered
constant value is published.
