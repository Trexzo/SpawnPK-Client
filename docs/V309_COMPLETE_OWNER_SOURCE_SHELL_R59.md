# R59 — exact v309 field declaration metadata plus complete ordered initializer source shell

R57 assembles one 93-assignment initializer. R58 checks full original/candidate instruction operand semantics while allowing only identical LDC literal values in either one- or two-byte constant-pool reference form. R59 adds the next missing private source component: **every original field declaration, including compile-time ConstantValue metadata and blank dynamic finals**, merged with the R57 initializer into a single private Java source shell.

## Independently compiled exact-original evidence

The pinned original v309 owner (stable logical ID CLIENT_CLASS_000167) has **126 fields**: 41 public static final (33 encoded as JVM ConstantValue and 8 assigned by `<clinit>`), plus 85 mutable public static. The 33 ConstantValue fields comprise **28 boolean, four int and one String**. All fields have no generic Signature attribute. Owner class version is Java 9 (major 53), class access 0x0031.

I independently rebuilt a private Java9 owner with all 126 original field declarations and one ordered initializer, compiled with `javac --release 9 -g:none -proc:none`, and read both classfiles rather than trusting a text diff. **126/126** field name, descriptor, JVM access, ConstantValue and Signature tuples are identical. The compiled skeleton also has 213 initializer instructions, all 93 writes in exact order and all eight branch target ordinals equal. The sole original-vs-candidate opcode differences remain **two `ldc` versus `ldc_w` constant-pool widths**.

The candidate's nested enum and helper definitions are **synthetic compile-only substitutes**. Original method bodies and InnerClasses metadata are not restored, and full source/runtime equivalence is false. Evidence is aggregate-only at `research/v309-source-recovery/complete-owner-field-shell-r59.json`; original class/member names, original String values, whole binaries and generated private Java are never committed.

## Reproducible private GitHub generator

`spk_recovery.complete_owner_source_shell` verifies whole original JAR SHA256 pre/post, unique owner and dependency class entries, original major/access flags, precise declaration order, public static/final metadata, JVM field descriptors, the exact ConstantValue type/range and printable String evidence. It requires every blank final field to receive exactly one original initializer write. It then delegates to R57's complete original `<clinit>` source partitioner, joins all declarations and 93 ordered assignments into one *private* Java class shell, and writes aggregate counts and source SHA only.

Example PowerShell from your GitHub checkout (private class entry is a placeholder):

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.complete_owner_source_shell `
  'C:\private\original-v309.jar' 'example/Owner.class' `
  'C:\private\r59-new-output' `
  --sha256 '<exact original whole-JAR SHA256>'
```

Private output: `original-owner-shell.private.java.txt`, and `original-owner-shell.aggregate.json`. Existing output is preserved. Synthetic Java9 tests compile a source shell, reparse both classfiles and verify field flags, ConstantValues, blank dynamic finals and initializer writes, and reject wrong pins, generic signatures, impossible mutable ConstantValue combinations and occupied outputs.

## Remaining acceptance gates

The **new generic R59 CLI has not yet been executed on the private original JAR**. The independently compiled private candidate proves exact owner field declaration metadata and strong initializer structural parity, not actual whole-client recovery. The real nested enum source-name/InnerClasses collision, original methods and helper side effects, all original binary members and runtime behavior still require separate restoration and verification. R56 strict raw opcode parity remains false on the two LDC width changes; R58 deliberately checks operand semantics separately. No canonical alias/whole-client correctness is promoted.
