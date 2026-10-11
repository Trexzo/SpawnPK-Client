# R57 — complete ordered original v309 initializer source

R56 provided a private original-versus-compiled-candidate acceptance gate. R57 supplies the missing source-generation stage: one Java static initializer fragment assembled from ALL original static-field writes in exact JVM order.

## Independently measured original JVM partition

| Original assignment form | Stores | Instructions each |
| --- | ---: | ---: |
| Direct literal/null/static-field read and store | 84 | 2 |
| Enum comparison, conditional String and concatenation | 2 | 8 |
| Enum static String helper | 2 | 3 |
| Reference-identity boolean comparison | 1 | 7 |
| Boolean negation | 1 | 6 |
| New integer array | 1 | 3 |
| External static String helper and concat | 1 | 3 |
| Boxed Integer | 1 | 3 |
| **Assignments** | **93** | **212 instructions total** |
| Trailing return | — | 1 |
| **Complete original initializer** | — | **213 total** |

These counts originate from a separate read-only inspection of the SHA-pinned v309 client. They do not depend on R57 generator output. Only aggregate counts and truthful vetoes are tracked in research/v309-source-recovery/full-clinit-expression-partition-r57.json.

## Private source assembler

The module spk_recovery.ordered_complete_clinit_source validates whole-JAR SHA-256 pre/post, exact unique class entries for the owner and referenced dependency classes, original declared static-field metadata, contiguous JVM instructions, unsupported opcode/handler rejection, precise conditional/jump targets, and strict accounting for every instruction and every branch edge.

It accepts original JVM literal and static-field-read pairs, actual nested enum helper methods, precise StringConcatFactory recipes, boolean predicates, integer-array creation and Integer boxing. No fallback source is invented for unsupported expressions. It returns one private Java static initializer in the original write order and emits public-safe aggregate counts with the private fragment SHA-256.

Run from your GitHub checkout against private original v309 input:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.ordered_complete_clinit_source `
  'C:\private\client-v309.jar' `
  'example/private-owner.class' `
  'C:\private\r57-new-output' `
  --sha256 '<exact original whole-JAR SHA256>'
```

The class entry above is a placeholder, not a canonical alias. Output files are complete-clinit.private.java.txt (contains original identifiers/literals, never publish) and complete-clinit.aggregate.json (counts/hash only). Destination must not exist. Synthetic Java9 regression tests include positive multi-pattern staging and adversarial bytecode/branch and wrong-SHA cases.

## Exact limitations

The original nested enum has a known Java source/binary-name collision. Therefore a JVM-backed source expression may NOT yet compile against a recovered Java source tree. R57 is NOT a complete reconstructed Java class and has NOT yet executed its new CLI against the private original JAR. A candidate built with this fragment must still satisfy the separate R56 ordered-write/opcode branch gate, exact invokedynamic and constant-pool operands, nested enum/helper source and runtime verification. Do not commit proprietary original client binaries, private aliases or private generated source.
