# R66 — compiled large-method JVM control-flow and exception-table parity gate

R62 measures private original JVM basic-block, exception-region and write-atlas evidence. R63–R65 identify original local producer/write patterns for all 78 static stores in the 697-instruction method. **R66 adds the missing independent original-versus-compiled-candidate acceptance gate** for method shape and exception behavior boundaries.

## Grounded exact-original acceptance frontier

| JVM method | Original instructions | Original static writes | Original branches | Original exception-table entries |
| --- | ---: | ---: | ---: | ---: |
| Larger v309 owner method | 697 | 78 | 120 | 44 |
| Other complex owner method | 364 | 0 | 9 | 1 |

These are counts measured read-only from the SHA-256-pinned original v309 client. **No actual recompiled version of either complete method exists in this R66 acceptance run.** The evidence file `research/v309-source-recovery/large-method-cfg-acceptance-r66.json` explicitly retains false certification flags.

## Exact structural checks

`spk_recovery.large_method_cfg_parity` reads two complete SHA-256-pinned JARs (original and private compiled candidate) and exact private method identifiers. It checks both whole-JAR SHA values before and after and requires:

- Unique original and candidate class entries with the same classfile major version and selected JVM method access flags.
- Entire method instruction coverage and an identical count of JVM opcode positions. Every opcode must match except **LDC versus LDC_W width**; this is not a claim that constant-pool values match.
- All original and candidate explicit branch edges targeting the same **instruction ordinals**, even if bytecode offsets shift.
- All original and candidate typed exception-handler entries in **exact order**. Each handler's start/end/handler offsets must match JVM instruction boundaries, with matching catch class or catch-all type and identical normalized protected intervals.
- Exact ordered `putstatic` targets, with an explicit injective **private** original-field-to-candidate-field alias map covering every stored owner field. External field coordinates must already match exactly.

It writes an aggregate-only JSON report into a fresh private directory. Original obfuscated identities and the alias map never appear in stdout or public artifacts. Synthetic Java 9 tests cover a real try/catch method with named fields, matching renamed candidate fields, changed exception type and branch destination, missing field alias and wrong original whole-JAR SHA.

## Private replay example

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.large_method_cfg_parity `
  'C:\private\original-v309.jar' 'example/Owner.class' `
  'privateOriginalMethod' '(Z)V' `
  'C:\private\candidate.jar' 'example/CandidateOwner.class' `
  'candidateMethod' '(Z)V' `
  'C:\private\owner-field-aliases.json' 'C:\private\r66-new-output' `
  --original-sha256 '<whole original-JAR SHA256>' `
  --candidate-sha256 '<whole candidate-JAR SHA256>'
```

Method/class coordinates above are illustrative placeholders. The alias file uses `{ "schema_version":1, "aliases":[ { "original":{ "name":"fieldA", "descriptor":"Z" }, "candidate":{ "name":"fieldB", "descriptor":"Z" } } ] }`; replace example identities only in your **private** file. Do not commit original binaries, method identities, private aliases or recovered source.

## Mandatory limitations

Even a passing R66 result proves **structural CFG and exception-table alignment only**. It does not verify all constant-pool values, invokedynamic recipes, method/field reads, dataflow, helper implementations, binary source provenance, runtime side effects or behavior. Those require separate original/candidate operand and runtime tests. In particular, having R62–R65 source *site* proofs does NOT mean the 697-instruction original Java method has been reconstructed or compiled. Both actual v309 complex-method candidate comparisons remain **unperformed**.
