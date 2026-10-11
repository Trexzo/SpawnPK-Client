# R58 — JVM initializer operand parity with exact LDC-width normalization

R57 reconstructs the original v309 93-write initializer as a private ordered Java source fragment. In a private Java 9 compile-only skeleton of 126 fields, we independently reproduced the original 213-instruction, 93-write sequence, but R56's strict byte-for-byte opcode requirement rejects two constant-pool indexing differences: original `ldc` compiled as `ldc_w`.

R58 provides a **separate** verifier. It NEVER changes or weakens R56. It accepts only these two opcode widths as interchangeable, and only after comparing the original and candidate constant pool *types and literal values* exactly. Every other opcode and checked operand must agree.

## Independently measured exact-v309 private skeleton result

| Feature | Original | Compiled skeleton |
| --- | ---: | ---: |
| JVM `<clinit>` instructions | 213 | 213 |
| Ordered `putstatic` writes | 93 | 93, same members/order |
| `getstatic` operands | 14 | 14, exact same field member refs |
| `invokestatic` operands | 4 | 4, exact same static method refs |
| LDC literal values | 7 | 7, exact same JVM literals |
| `invokedynamic` StringConcatFactory recipes | 3 | 3, exact recipe contents |
| Branch destinations by instruction ordinal | 8 | 8, same graph |
| Opcode width changes | — | 2 `ldc` → `ldc_w` |
| Other opcode positions | 211 | 211 identical |

The private compile used `javac --release 9 -g:none -proc:none` and privately staged a Java class with the original 126 field *declarations* and 93 reconstructed assignments. The nested enums and external helper bodies were **compile-only substitutes**, and original static-final ConstantValue field metadata was **not preserved**. This result is structural/operand parity of the initializer, NOT class metadata/source/runtime equivalence. Aggregate evidence, including private JAR hashes but no original class names or values, is in `research/v309-source-recovery/clinit-operand-private-skeleton-r58.json`.

## Independent GitHub verifier

`spk_recovery.clinit_operand_semantic_witness` compares two SHA-pinned original/candidate JVM classes using an explicit **private** original-field-to-candidate-field alias map. It requires:

- Full original and candidate JAR SHA-256 preflight/postflight, unique class entries, identical JVM classfile major version, and explicit injective aliases covering every original/candidate initializer field write.
- Identical mapped `putstatic` member-write order and full instruction count.
- Exact branch targets normalized by JVM instruction ordinal, even when code offsets shift because an LDC instruction becomes wider.
- Exact referenced static fields and methods (unmapped external member coordinates must remain identical), `newarray` primitive type and immediate values.
- Exact LDC constant-pool *kind* (String versus Integer) and exact literal value; no unproven CP classes, condy, floating-point NaN or unknown constant kinds.
- Exact invokedynamic callsite name/signature, bootstrap method-handle kind/owner/name/signature and semantic bootstrap arguments/recipes.
- No exception handlers or unsupported instructions, and no existing-output overwrite.

Private usage from a GitHub checkout (placeholder class names and locations):

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.clinit_operand_semantic_witness `
  'C:\private\original-v309.jar' 'example/Owner.class' `
  'C:\private\candidate.jar' 'example/Owner.class' `
  'C:\private\aliases.json' 'C:\private\r58-new-output' `
  --original-sha256 '<original whole-JAR SHA256>' `
  --candidate-sha256 '<compiled whole-JAR SHA256>'
```

The checker reports aggregate counts and flags only; never a private class/member name, binary, string literal or source fragment. Synthetic Java9 regression tests cover success, exact width-normalization, altered LDC contents, changed invokedynamic bootstrap recipe, changed helper method, swapped writes, alias gaps, SHA mismatch, and output-path preservation.

## Remaining gates

The new GitHub R58 verifier has **not yet been run on the private original/candidate pair**; the published aggregate observation originates from an independent read-only javap comparison. Original nested-enum InnerClasses attributes/source, helper bodies and side effects, all static-final ConstantValue field metadata, original class/source parity and runtime behavior remain unverified. R56's strict byte-level opcode gate still **fails** on the two width differences. No proprietary original client or generated source is published.
