# R61 — original v309 LambdaMetafactory invocation boundary

R60 established six bounded original owner-method source forms but kept three method bodies unsupported: one four-instruction method and two substantial methods with 364 and 697 instructions. The exact original-v309 JAR's four-instruction method is a **JVM invocation boundary**, not yet recoverable lambda or consumer source.

## Read-only original-v309 measurement

SHA-pinned original JVM disassembly confirms exactly one no-argument static void method with the contiguous opcode sequence:

```text
ldc           <original private String>
invokedynamic <LambdaMetafactory functional-interface factory>
invokestatic  <declared static consumer accepting String and that interface>
return
```

The `invokedynamic` bootstrap refers to `java/lang/invoke/LambdaMetafactory.metafactory` through a static method handle. Its returned functional-interface descriptor matches the interface parameter of the consumer's static JVM descriptor, alongside the String argument. These are structural facts from the original JAR, not permissions to invent Java lambda contents.

The public aggregate [R61 evidence](../research/v309-source-recovery/lambda-boundary-r61.json) records opcode types, counts and noncertification flags without leaking original member names, literal values, consumer endpoints or the original binary.

## Implementation

`spk_recovery.lambda_boundary_witness` verifies complete original JAR SHA-256 before and after reading, a unique owner and external consumer classfile, a single supported four-instruction method, the String LDC constant-pool kind, exact functional-interface return shape, exact original consumer method JVM descriptor/static modifier, and the LambdaMetafactory bootstrap method handle and three argument types (method type, implementation method handle, method type). Unsupported patterns or multiple matches are rejected. The original implementation method handle is hashed as **private evidence** and never returned raw.

From an actual GitHub checkout, with the exact private original v309 JAR and privately resolved owner entry:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.lambda_boundary_witness `
  'C:\private\original-v309.jar' `
  'example/OriginalOwner.class' `
  'C:\private\r61-new-output' `
  --sha256 '<exact whole original SHA-256>'
```

Class entry is an illustrative placeholder, not a promoted canonical owner alias. Only `lambda-boundary.aggregate.json` is emitted into a fresh output directory. The witnessed private method/literal details are never published. Java 9 synthetic positive/negative tests cover consumer descriptor changes, forged bootstrap method, wrong String constant kind, wrong original SHA and output-path preservation.

## Unmet gates

The original LambdaMetafactory's implementation body, consumer implementation side effects and runtime behavior remain unproven. The two large owner methods, with 364 and 697 instructions, remain unreconstructed. This R61 GitHub CLI has not yet been replayed against the private original-JAR environment; original observations were independently verified with read-only disassembly. Full Java source, classfile, source-name collision, and runtime parity remain unaccepted. Do not publish original client binaries, strings, original private identifiers or generated Java.
