# R452 — Acyclic JVM forward-branch resource argument evidence

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R451 draft PR #1248 (after correcting the R450 callback's `literal` name shadowing)  
**State:** DRAFT / UNMERGED / NOT DEPLOYED. This is offline static inspection only.

## Why R452 matters

R450 reports possible resource-looking string constants near known `Class.getResource*` / `ClassLoader.getResource*` calls in the same reconstructed Java 11 method. R451 improves precision by tracking the actual `String` parameter on a straight-line symbolic operand stack, rejecting all branched methods. A significant set of real Java methods use conditional or unconditional branches, and treating all of them as entirely unknown leaves genuine static reconstruction leads unavailable.

R452 implements **selected, strictly forward-only, acyclic JVM control flow**. It explores both successors of `ifeq/ifne/iflt/ifge/ifgt/ifle`, integer/reference equality comparisons, `ifnull/ifnonnull`, and forward `goto/goto_w`, with fixed worklist, stack and branching budgets. It does **not evaluate branch predicates**, so all syntactically reachable paths are conservatively possible. It refuses backward/zero-offset branches (loops), unaligned or out-of-bounds destinations, `jsr/ret`, switch instructions, exception handlers, unmodeled opcodes, long/double category-two values, missing return, operand underflow, invalid locals, and unbounded abstract-state expansion.

At every allowlisted resource API **callsite**, the analyzer records the symbolically tracked argument from each analyzed path that reaches that site. A candidate is credited only if **every path has the same allowed resource-like `CONSTANT_String` argument**. If any path has a different literal or a dynamic/unknown value, that callsite is marked ambiguous and no name is attributed. A conditional call that is skipped on some branches can still be described as a known argument *if that call instruction executes*; the audit does not claim the call always executes.

This is bounded **static abstract interpretation**, not original game execution, verified JVM bytecode behavior, proof of successful resource loading, full control-flow/dataflow, or a source code reconstruction.

## Implementation

- `tools/r452/forward_branch_resource_operands.py`: pure JVM bytecode control-flow analysis. It consumes R450's instruction boundaries and R451's method-descriptor semantics, propagates known literal `String` values through a narrow subset of `ldc/ldc_w`, `aload/astore`, selected primitive instructions, stack `pop/dup/swap`, `checkcast`, and modeled method calls. It explores a DAG of instruction boundaries, deduplicates symbolic (PC, stack, local) states, and refuses any unsupported reachable path. Branch-target boundaries are checked independently of execution paths. The maximum worklist is 4,096 abstract states per method, up to 96 branch instructions, and 256 stack entries. No Java class is loaded, interpreted dynamically, or executed.
- `tools/r452/audit_forward_branch_resource.py`: owner-private gated CLI. It calls R451→R450→R449→R448→R447→R446, verifying the exact original v309 JAR SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38` (10,502 class files and 419 original resources) and exact isolated R421 current source/class and two dependency JAR inventories (1,277 Java files, 1,394 compiled classes, original Store Java/class SHA pins). It independently rechecks per-file compiled bytes and full owner-TEMP current evidence, and calculates the **incremental class+method+resource signals not already attributed by R451**. The original resource companion is optional and read-only; comparing its bytes is not proof of an assembled playable JAR.
- Default console output is strictly **aggregate counts**, not private class/method/resource names, source paths, files or SHA values. It reports number of supported acyclic methods, skipped methods, graph states explored, resource callsites, ambiguous callsites, same-literal all-path candidate sites, unique matching original-JAR resource names, and new class+method+resource signals beyond R451.
- `--save-private-unapproved-worklist` explicitly opts in to producing one new **private OS TEMP quarantine**. The complete audit is run twice, and the full currently observed owner source/class/dependency SHA inventory must match across passes. The resulting new exclusive file `R452-UNAPPROVED-BRANCH-RESOURCE-WORKLIST.json` contains only names and candidate referencers; no original client source or JAR bytes are copied, and no prior output file is overwritten. The report cannot act as R442's independently approved historical R421 full reference.

### Owner-only commands (once connected and isolated originals are present)

Read-only default:

```powershell
python -B tools\r452\audit_forward_branch_resource.py --original-v309-jar '<owner-local exact original v309 JAR>'
```

Optional private-only worklist:

```powershell
python -B tools\r452\audit_forward_branch_resource.py --original-v309-jar '<owner-local original v309 JAR>' --save-private-unapproved-worklist
```

Optional `--resource-companion-root` accepts only a previously preserved, separately isolated private resource companion; none is extracted or installed.

## Public verification

The matrix uses Windows/Ubuntu × Python 3.11/3.13 and an installed JDK21, but the **36 new tests are entirely synthetic**, using invented Java11 bytecode, fake ZIPs and TEMP directories. They exercise same-literal diamonds, conflicting/dynamic branches, malformed/misaligned jumps, loops, switches, exception handling, stack underflow, state/branch budgets, local String propagation, overlapping R451/R452 evidence, full owner SHA rechecks, no-write defaults and explicit no-overwrite private quarantine. Inherited R451/R450/R449/R448/R447/R446/R445/R442/R426 public suites also run. **Neither GitHub CI nor this draft PR can establish real owner-private client functionality.**

The authorized desktop `DESKTOP-LTXXO4K` remained offline at R452 intake. No real R421 classes or SHA-pinned v309 JAR/resources were read in this development session. Original `LootHistoryStore`/Plugin integration, async deletion receipts, installed v312 compatibility, resource packaging, GUI startup, login, gameplay and performance are not verified. The independently approved **historical R421 full inventory** is still missing; present-day R446 observation is not an independent historical approval.

**Keep draft and unmerged. No client launch, installation, source export, persistent loot-history writes, R415/R417 deletion-intent cleanup, write unlock, or production release.**
