# R60 — exact original-v309 short method source forms

R57–R59 established a private Java9 source shell for all 126 owner fields and the 93 ordered initializer writes. R60 tackles the next gap: **original method bodies**. SHA-pinned read-only original bytecode identifies six short, exact JVM source-form patterns in the 10-method original owner (9 ordinary methods + class initializer):

| Method form | Count | Original JVM instructions each |
| --- | ---: | ---: |
| Default public Object constructor | 1 | 3 |
| Static boolean method returning false | 2 | 2 |
| Static boolean method delegating to a declared no-arg boolean method | 1 | 2 |
| Two-branch boolean flag setter | 1 | 20 |
| Ten-element indexed int-array writer | 1 | 41 |
| **Bounded method source forms** | **6** | **70 total** |

Three method bodies remain **unreconstructed**: one four-instruction invokedynamic/lambda invocation, and two substantial methods of **364** and **697** instructions. These are not replaced with stubs or claimed as recovered. The class initializer's separate 213 instructions are the R57–R59 scope.

## GitHub implementation

`spk_recovery.small_owner_method_source` validates the SHA-256-pinned original JAR and referenced original external field-owner classes. It stages only: the exact Object super-constructor call; two `iconst_0; ireturn` boolean methods; a same-owner declared static no-arg boolean delegator; a real `iload_0; ifeq ... goto` branch diamond with all eight declared static boolean flag writes including the one external original static-field write; and ten contiguous getstatic-array/index/int-literal/iastore groups with monotonically ordered indices 0–9. Each supported method must have no exception handlers, every branch must match, and field/method descriptors and modifiers must be original metadata.

Unknown methods are **omitted**, never given fabricated bodies. The tool creates only a fresh private `short-owner-methods.private.java.txt` and `short-owner-methods.aggregate.json` (counts and private-fragment SHA, no private names/literals). The generated snippet is for private integration into the recovered owner source shell; the resulting compiled class and original runtime equivalence are not certified.

### Example private PowerShell replay

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.small_owner_method_source `
  'C:\private\original-v309.jar' `
  'example/OriginalOwner.class' `
  'C:\private\r60-new-output' `
  --original-sha256 '<complete original-v309 JAR SHA256>'
```

These inputs are placeholders, NOT asserted canonical original Java identities. The actual original JAR and source fragments must stay private.

## Tests and limits

Hosted synthetic Java9 tests cover six positive short methods, unsupported complex method omission, changed constant-return opcode, corrupted array writer, SHA mismatch and existing output preservation. Public aggregate original evidence is retained in `research/v309-source-recovery/small-owner-methods-r60.json`. New GitHub R60 CLI has not yet been replayed against the actual private JAR; the source forms are based on independent read-only exact-v309 JVM examination.

Remaining method sources, complex invokedynamic/lambda call-site semantics, original nested-enum classfile sources, full compilation against recovered dependencies, original method/runtime side effects and complete client behavior remain unresolved. **Six JVM source forms is not six original runtime-parity certifications.**
