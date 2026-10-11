# R64 — original v309 null-guarded boolean static write source forms

The 697-instruction original method has 78 static assignments. Independent SHA-256-pinned original-v309 disassembly measured 30 conditional boolean assignments, with this contiguous JVM sequence:

```text
aload_1
ldc original-private-String-key
invokevirtual(String)->reference
ifnonnull AFTER_STATIC_STORE
iconst_0 or iconst_1
putstatic OriginalOwner.boolean
```

The original branch destination is beyond the write, and no unexpected branch or exception-handler targets enter the six-instruction window. This is a bounded **null-guard conditional assignment shape**, not proof of the surrounding 44 exception regions, original local variable type, or source/runtime equivalence.

The exact original breakdown is **14 assignments of true, 16 assignments of false**, with 29 original post-store `goto`s and one `getstatic` instead. Paired with R63's 37 typed getter/conversion chains, these account for 67 of 78 local JVM write patterns; **11 original static writes remain different**. Source counts and noncertification flags appear in [R64 aggregate evidence](../research/v309-source-recovery/null-guard-boolean-stores-r64.json) without original literals or member coordinates.

## GitHub private source tool

`spk_recovery.null_guard_boolean_source` checks the exact whole original-JAR SHA before/after reading, unique original owner class, exact private method identity, contiguous six-op JVM windows, original String LDC kind, declared original static boolean field, exact method descriptor returning a reference, `ifnonnull` target beyond the write, and no branch/handler entry into the expression interior.

For accepted windows it emits one **private-only local Java expression form** conceptually equivalent to:

```java
if (originalLocalSlot1.lookup("private original key") == null) {
    originalBooleanField = true;
}
```

`originalLocalSlot1` is a **placeholder** whose original Java type has not been proven. The real original field and lookup method names and keys are taken from bytecode only in the private fragment. This is NOT a compilable original method or proof of its exception side effects.

### Private replay

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.null_guard_boolean_source `
  'C:\private\original-v309.jar' `
  'example/OriginalOwner.class' `
  'privateOriginalMethodName' '()V' `
  'C:\private\r64-new-output' `
  --sha256 '<complete original client SHA256>'
```

Class/method names are illustrative placeholders only. It writes a new private site graph (`null-boolean-sites.private.json`), the exact private local source shapes (`null-boolean-source.private.java.txt`), and public-safe aggregate counts/fingerprints (`null-boolean-source.aggregate.json`). Never publish private outputs, original client binaries, literal keys or source.

Synthetic Java9 tests cover two exact nullable-boolean stores, modified original method descriptor, invalid branch target entering a store, incorrect complete-JAR SHA and existing-output preservation.

## Unmet gates

The new R64 GitHub CLI has **not yet been privately replayed against the exact original v309 JAR**, though the 30 original local windows and safe entry boundaries were independently measured. The original Java local variable type, full exception nesting, neighboring `goto`s, the remaining 11 static writes, helper semantics, original method compilation and runtime equivalence remain unverified. Do not treat 67 JVM producer forms as a recovered complete original method.
