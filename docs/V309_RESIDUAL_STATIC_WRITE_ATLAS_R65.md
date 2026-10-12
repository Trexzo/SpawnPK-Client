# R65 — all 78 original static-write locations partitioned by exact JVM shapes

The earlier R62–R64 merges added independent proofs for the 697-instruction original-v309 method's JVM control flow, 37 typed lookup/conversion value producer chains, and 30 nullable-boolean write windows. The **11 remaining `putstatic` instructions** were re-inspected directly in the SHA-256-pinned original client.

## Original binary observations (no original names or literal strings published)

| Original JVM local producer/assignment form | Residual sites |
| --- | ---: |
| Two string keys followed by virtual lookup and static Boolean conversion | 1 |
| Single string lookup followed by static reference conversion | 1 |
| Nullable integer default assigned from immediate | 1 |
| Nullable Boolean default with an additional static side-effecting call | 1 |
| Boolean extraction, local caching and a static notification call | 1 |
| Direct Boolean literal assignment | 1 |
| Nullable String literal default | 1 |
| Direct String-returning lookup assignment | 1 |
| Direct null reference assignment | 1 |
| Indexed local reference passed to static factory and stored | 1 |
| Direct static reference copy | 1 |
| **Total residual** | **11** |

Four residual fields are Boolean, one integer and six reference typed. Combining the 11 with R63's 37 typed chains and R64's 30 null-guarded Boolean writes accounts for **all 78 original `putstatic` instructions by JVM-local opcode shapes**. These are source-shape **classifications**, not original Java reconstruction, nor verification of the 44 original exception-table regions or call side effects.

[R65 public evidence](../research/v309-source-recovery/residual-static-write-shapes-r65.json) tracks counts and exact-original JAR provenance without original field/method identities, asset/network strings or proprietary classfile contents.

## GitHub verifier

`spk_recovery.residual_static_write_atlas` uses a complete SHA-256-pinned original JAR and privately selected original class/method. It integrates the actual R63 and R64 planners, requires their accepted write-site offsets to be disjoint, validates every original static field assignment against a declared owner field, and records each *remaining* original write's strict trailing JVM opcode window and original exception region indices. It refuses unsupported local shapes rather than fabricating source. It verifies each accepted suffix is contiguous with no branch or handler jump into the interior, and keeps actual member descriptors/literals in a private-only JSON site atlas.

Output report includes only total write counts, partition counts, names of opcode-shape categories, and a SHA-256 of the private atlas. **No recovered complete Java method or original runtime behavior is claimed.**

### Private replay

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.residual_static_write_atlas `
  'C:\private\original-v309.jar' `
  'example/PrivateOwner.class' `
  'originalPrivateMethodName' '(Ljava/lang/Object;)V' `
  'C:\private\r65-new-output' `
  --original-sha256 '<whole original-v309 JAR SHA256>'
```

The class/method descriptors above are **placeholders only**. Outputs are `residual-static-write-sites.private.json` (private original field names, literal and full JVM windows) and `residual-static-write-atlas.aggregate.json` (safe counts/hashes). The directory must be new. The tool never patches or executes the original client.

Synthetic Java9 regression tests combine two typed R63 chains, one null-guarded R64 assignment, and three R65 residual direct assignments; require exact disjoint six-write coverage, reject an unknown value opcode and undeclared target field, and verify full-JAR SHA and no-overwrite.

## Unmet parity gates

The R65 GitHub CLI has not yet been executed on the private actual v309 client. Eleven opcode-shape categories were independently measured with read-only disassembly. Their exact per-site handler/branch admissibility still must be replayed with the new CLI. Reconstruction of each residual source expression, full local type dataflow, all 44 exception handlers, helper calls and side effects, verified 697-instruction method compilation, and runtime equivalence are **not** complete.

The next high-value step is joining R62's private CFG with R63/R64/R65 private site data, then recovering the remaining local expressions under exact handler boundaries. Do not infer original source author intent from opcode suffixes.
