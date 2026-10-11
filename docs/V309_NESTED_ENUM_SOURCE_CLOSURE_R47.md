# R47 — six missing reference fields depend on four stable nested enums

R46's private Java 9 rebuild reached **115 exact original JVM field declarations out of 126**, with 11 remaining. This R47 investigation narrows the remaining reference-type closure: **six** absent original field declarations use **four distinct nested JVM enum class types** of the configuration owner. Their field dependency multiplicities are **1, 1, 1, 3**. The other five absent declarations are Strings with unresolved final initialization.

## Exact pinned original-client evidence

A read-only comparison of SHA-pinned original v308 and v309 JARs confirms that **all four nested enum classfiles are byte-for-byte identical** across these releases. Their exact SHA-256 fingerprints are stored in the [private-safe aggregate R47 frontier](../research/v309-source-recovery/nested-enum-closure-r47.json). Raw original class names and classfile bytes are never published.

Identical binary classfiles across two releases do not prove an older decompiled Java source is semantically exact, and do not prove their Java source has been recovered.

## JVM/source name collision

One nested enum has the same simple name as its enclosing class. JVM binary class names permit this after obfuscation, but Java source of the shape `class Example { enum Example { X } }` fails with javac because the inner type redeclares the enclosing type's name. Synthetic Java 9 tests prove this negative case. A reviewed, reversible compiler-name/bytecode transformation with exact binary identity proof is needed before source recovery can claim this enum. The helper detects the collision but never invents or accepts a mapping.

## Separate private compiler experiment — parent reached 121 fields

I also compiled a **separate private** revision of the R46 Java source using four top-level Java enum **type-only shells** with dollar signs in their names. These deliberately reproduce the required parent-field JVM reference descriptors, but **do not reconstruct the original nested enum member methods, initialization or InnerClasses attributes**. To avoid the original source-name shadowing issue, the method reference to the parent class was qualified explicitly in this private compiler experiment.

With `javac --release 9 -g:none -proc:none`, the parent compiled to **121 original-matching field declarations out of 121 candidate fields**, leaving only five original String declarations absent. The pre-existing eight reconstructed candidate method opcode/resolved-operand disassemblies were preserved. The initial two-opcode original assignment from an enum constant to the parent static-final field was also reproduced. This is **parent field metadata and a short assignment-site match only**, not source recovery of the four enum implementations.

The aggregate R47 record includes SHA-256 pins for the private revised parent source, compiled parent class and candidate JAR. None of these private files is uploaded. A synthetic Java9 regression proves that a top-level dollar-named enum can supply the exact parent descriptor without claiming to reproduce the original nested JVM class semantics.

## Local exact-private replay

From the cloned repository root, with Python 3.11+ and independently verified complete JAR SHA-256 values:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.nested_enum_source_closure `
  'C:\private\original-v309.jar' `
  'C:\private\original-v308.jar' `
  'C:\private\recompiled-R46-candidate.jar' `
  'example/Configuration.class' `
  --original-sha256 '<actual original v309 full JAR SHA256>' `
  --previous-sha256 '<actual original v308 full JAR SHA256>' `
  --candidate-sha256 '<actual rebuilt R46 full JAR SHA256>' `
  --out 'C:\private\new-nested-closure.json'
```

These are placeholders, **not canonical mappings**. Exact full-JAR hashes, a matching original/candidate class owner, unique class entries, JVM Enum superclass and enum flags, and postflight input hashes are mandatory. An existing output file is never overwritten.

The private report contains only opaque nested IDs, class SHA-256 values, missing-field reference counts and binary/source-name collision checks. Console output contains aggregates only. The separate exact-v309 observations recorded in the R47 JSON were not represented as an execution of the new public GitHub CLI.

## Next source recovery gate

Recover the four original nested enum Java implementations, constants, methods, static initialization, InnerClasses metadata and dependencies; correctly handle the Java source-name collision. The private **type-only shells** have already demonstrated six correct parent field descriptors, but those shell enum implementations are not recovered original source and are not production-ready. The five absent String declarations, original mutable initialization semantics, and three substantive unrecovered methods remain distinct blockers.

**No original nested enum Java source, original classfile, source alias or runtime-equivalence certificate has been produced by this PR.** Original and candidate JARs and detailed private reports stay out of GitHub and hosted CI; tests use synthetic Java only.
