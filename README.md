<img width="246" height="449" alt="image" src="https://github.com/user-attachments/assets/543ea4c9-38ac-44f1-8af8-98045a8d315d" />

<img width="500" height="449" alt="image" src="https://github.com/user-attachments/assets/835f4622-855b-4ff5-a9ad-64c3ea46814f" />

# SpawnPK Client Recovery

Version-aware recovery tooling for the obfuscated SpawnPK JVM client.

The project is built around **stable logical identities**, not whatever short names
ProGuard emits in one release. It fingerprints every build, transfers proven identities
across updates, deep-analyzes only real deltas, and keeps exact client binaries outside Git.

## Current authority

Exact v308 authority:

- SHA-256: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`
- Main class: `rs.gui.Launcher`
- Build/config value: `308`
- Outer protocol revision: `317`

The known v307 -> v308 update changed one archive entry (`rs/f/a.class`) and one
meaningful build constant (`307 -> 308`).

## v309 active recovery frontier (October 2026)

**v308 is the last exact historical build used as the pinned baseline**, not a
claim that the current post-v308 client is still v308. Exact v309 has SHA-256
`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

The GitHub-first v309 handoff in
[`research/v309-field-recovery/`](research/v309-field-recovery/README.md) is
**ACCEPTED_INCOMPLETE** with **143 unresolved fields**. It is **not**
`EXACT_CURRENT_CLIENT`; do not hand-edit lineages, change old authority or
claim v309 release readiness to remove these blockers.

The **current descriptor-class evidence lane** is implemented on `main`:

1. `descriptor_class_dependencies` groups the 26 field descriptor vetoes by
   8 old canonical class IDs (largest: `CLIENT_CLASS_000029`, 14 fields).
2. `descriptor_class_index_witness` requires independently unique cross-build
   class-index hashes before proposing a research candidate.
3. `descriptor_class_verified_replay` regenerates that inventory from the
   original global report rather than trusting a hand-edited queue.
4. `descriptor_class_private_jar_replay` verifies the accepted GitHub frontier,
   both **exact private JARs**, and all source-file hashes, builds indexes only
   in memory, then writes a **new research-only report**.

The **preferred two-lane command** now also measures the 68 `empty_both` fields using the same exact class indexes, while preserving its independent proof requirements. See [`docs/V309_PRIVATE_DUAL_PROOF_REPLAY.md`](docs/V309_PRIVATE_DUAL_PROOF_REPLAY.md).

On a local, installed checkout containing the *exact private v308 and v309 JARs*:

```powershell
python -m spk_recovery.v309_private_dual_proof_replay `
  --v308-jar "C:\private\exact-v308-client.jar" `
  --v309-jar "C:\private\exact-v309-client.jar" `
  --out-dir "$env:TEMP\spk-v309-dual-proof-new"
```

The JAR paths above are **examples, not known files**; replace both with the
real private paths. Use a **new, nonexistent output directory** each run: existing
reports and pinned inputs are never overwritten. The output contains only the
two research reports and one SHA-pinned manifest, not the two full class indexes. This command cannot accept a class or field
identity, modify `authority/`, or certify v309. After measuring exact witnesses,
use separate reviewed canonical acceptance and regenerate all dependent evidence.
**Do not commit JARs, complete indexes, or raw private outputs** to Git.

### Current v309 source-recovery workflow in GitHub

For bounded method and class reconstruction, use this supported **research-only**
chain instead of accumulating separate private R24/R25/R26 scripts:

1. [R26 exact-class slice](docs/V309_EXACT_CLASS_SLICE_R26.md) uses the
   checksum-pinned original JAR to preserve the requested classfile bytes.
2. [R27 dual-decompiler execution](docs/V309_DUAL_DECOMPILER_R27.md) feeds that
   same private slice independently to pinned CFR and Vineflower executables,
   generating private Java plus an aggregate, deterministic manifest.
3. [R33 isolated private source compilation](docs/V309_PRIVATE_SOURCE_COMPILE_REPLAY_R33.md)
   compiles staged candidate Java with no original-client binary fallback,
   checks SHA-256 input pins, and produces a private candidate class archive.
4. [R31/R25 strict JVM method parity](docs/V309_SOURCE_METHOD_PARITY_R25.md)
   compares decoded instructions, resolved references, handlers, stack/local
   limits, and normalized StackMapTable metadata.
5. [R32 class-wide method matrix](docs/V309_CLASS_METHOD_MATRIX_R32.md)
   measures matching, changed, missing and extra methods in one pass.
   R33 invokes this matrix after isolated compilation.

These are **separate steps**: decompiler output is not equivalent reconstructed
source by default, and instruction parity does not authorize canonical
identity acceptance or release publication. Third-party decompiler executables
must be independently supplied and hash-pinned; none is committed or silently
downloaded. Never upload proprietary class slices or generated Java to CI.

Older R0/R1 examples below intentionally document the historical v308 baseline.
For new v309 work, start with the linked accepted frontier, not those examples.

## Current v309 recovered-Java source status

The [R37 verified private-source frontier](research/v309-source-recovery/frontier.json)
records an exact-original v309 configuration class study: a recompiled
seven-method instruction-level research slice, **four candidate fields
against 126 original fields**, and explicit unresolved method, field and
StackMapTable gaps. The research candidate is **not** a certified or
published source tree. [Review the bounded evidence and next source
blockers](docs/V309_PRIVATE_SOURCE_FRONTIER_R37.md).

## Recovered source in this repository

The layout below is the **intended publication target** for certified Java source, versioned by exact client build; it is not a claim that the files exist today:

```text
recovered-source/
  v308/
    SOURCE-MILESTONE.json
    BUNDLE.json
    src/**/*.java
    provenance/*.json
```

`recovered-source/v308/src/` becomes canonical only after Source Milestone 1 reports `publishable=true` and the publication bundle independently verifies. Raw/intermediate decompiler output is not committed. The current `recovered-source/` folder contains a README, not a published/certified v308 or v309 Java source tree; do not describe the uncommitted local candidate as a GitHub source release.

## What exists today

The repository now has a complete core recovery/update pipeline:

```text
exact client JAR
  -> complete index + structural fingerprints
  -> cross-build class matching
  -> stable CLIENT_CLASS identities
  -> stable CLIENT_FIELD / CLIENT_METHOD identities
  -> semantic candidate review + explicit acceptance
  -> verified class/member remap plans
  -> ASM whole-JAR rewrite
  -> deterministic repackaging
  -> independent transformed-JAR verification
  -> readable client JAR
  -> hash-pinned recovered source
  -> source readiness + rebuild toolchain authority
  -> zero-project-binary-fallback clean rebuild
  -> round-trip verification
  -> stable SRC_* parameter/local identities
  -> explicit inferred source-name review + semantic AST rewrite
  -> clean rebuild + round-trip acceptance of rewritten source
  -> safe inferred source-name carry-forward
  -> deterministic recovery release manifest
  -> one-command existing-authority/future-update release
  -> independent release reproducibility verification
```

For future releases:

```text
previous authority + new client.jar
  -> update-migrate
  -> exact hash/index/diff
  -> trusted class-lineage transfer
  -> trusted member-lineage transfer
  -> semantic-name carry-forward only where identity survives
  -> focused unresolved/new/changed analysis queue
  -> authority-candidate completion gate
```

Unmatched or ambiguous entities remain unresolved. The tool does not invent identity just
to complete an update.

## Important naming rule

Original local-variable, parameter, source-file and line-number metadata was stripped from
v308. Readable names produced by this project are therefore either:

- supported by surviving exact evidence, or
- explicitly labeled inference/candidate names.

They are not presented as lost original source identifiers.

## Setup

Requirements:

- Python 3.11+
- JDK 21 for bytecode remapping / integration tests

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

CI runs on both Windows and Linux and includes:

- unit/integration tests
- Python compile checks
- CLI registration checks
- repository hygiene checks
- real Java/ASM remap fixtures

## R0 — exact indexing and diffing

```powershell
spk-recovery index C:\path\to\client-v308.jar `
  --expect-sha256 854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6 `
  --out .\evidence\indexes\v308.json
```

The index contains exact entry hashes, parsed class metadata, constants, strings, member
shapes and name-insensitive structural fingerprints.

## R1 — stable class identities

```powershell
spk-recovery lineage-seed .\evidence\indexes\v308.json `
  --build-id v308 `
  --build-number 308 `
  --authority EXACT_CURRENT_CLIENT `
  --out .\generated\v308.lineage.json

spk-recovery lineage-validate .\generated\v308.lineage.json
```

Canonical IDs look like:

```text
CLIENT_CLASS_000001
CLIENT_CLASS_000002
...
```

A class can retain the same logical ID even if its obfuscated path changes in a later build.

## R2 — semantic review and verified rewriting

Fields and non-constructor methods get their own stable identities:

```text
CLIENT_FIELD_000001
CLIENT_METHOD_000001
```

Semantic names remain separate from identity and require explicit review/acceptance.

Core R2 commands include:

```text
semantic-resolve
semantic-accept
remap-plan
remap-risk-scan
member-remap-plan
member-safety-scan
member-safety-validate
class-remap
jar-remap
verify-remap
decompile
```

The remapper uses ASM and rewrites JVM references consistently. Class entry paths,
manifest `Main-Class`, and `META-INF/services` entries are handled explicitly.

Member remapping has a separate name-sensitivity/reflection safety gate.

The output JAR is deterministic and is independently re-indexed/verified after rewriting.

## R3 — incremental future-update migration

The one-command migration entry point is:

```powershell
spk-recovery update-migrate `
  .\authority\previous-index.json `
  .\client-new.jar `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  --old-build-id v308 `
  --new-build-id v309 `
  --new-build-number 309 `
  --member-candidates .\research\v308-to-v309.members.json `
  --out-dir .\generated\migration-v309
```

It composes the safe automatic stages and writes a deterministic migration workspace.

Changed-class field transfer is intentionally stricter than method transfer. Canonical
promotion does not trust a research strategy label by itself: `spk-field-proof-transfer`
recomputes JAR-bound field-position evidence from the exact old/new bytecode and canonical
method lineage before a changed-class field can enter authority.

A clean update can finish with:

```text
ready_for_authority=true
```

A nontrivial update can validly finish blocked with a focused review queue instead. This
is expected behavior; it prevents ambiguous/new code from silently entering canonical state.

The workspace contains:

```text
new-index.json
migration-report.json
analysis-queue.json
class-lineage.json
member-lineage.json
class-transfer-summary.json
member-transfer-summary.json
authority-candidate.json
focused-analysis-queue.json
migration-workspace.json
```

The previous authority is never modified in place.

## R4 — accepted semantics to readable client/source

R4 turns one accepted authority state into reproducible readable artifacts without
weakening the review boundaries established in R1-R3.

### Readable client build

```powershell
spk-readable-build `
  .\client-v308.jar `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\authority\v308-index.json `
  --build-id v308 `
  --out-dir .\generated\readable-v308
```

This composes the accepted semantic namespace, class/member remap plans, class/member
safety gates, deterministic ASM rewrite and independent verification into one workspace.

### Recovered source workspace

```powershell
spk-source-workspace `
  .\generated\readable-v308\readable-client-manifest.json `
  .\generated\readable-v308\readable-client.jar `
  .\tools\cfr.jar `
  --decompiler-sha256 <PINNED_SHA256> `
  --engine cfr `
  --out-dir .\generated\source-v308
```

The source manifest pins the original authority SHA, transformed JAR SHA, semantic namespace,
class/member plan digests, exact decompiler SHA and a deterministic generated source-tree SHA.

### Coverage

```powershell
spk-coverage `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  --build-id v308 `
  --out .\generated\v308-coverage.json
```

Coverage keeps `ACCEPTED`, `CANDIDATE` and `UNKNOWN` separate. Only accepted names count
as remap-ready semantic coverage.

### Future-build semantic carry-forward

After a new build is promoted to exact authority:

```powershell
spk-semantic-carry-forward `
  .\authority\v308.snapshot.json `
  .\authority\v309.snapshot.json `
  .\authority\class-lineage.json `
  .\authority\member-lineage.json `
  .\authority\v309-index.json `
  --out-dir .\generated\v309-semantic-carry
```

Accepted names carry forward only when the same stable class/member ID has proven identity
in both authority builds. Missing new identity blocks carry-forward rather than guessing.


## R5 — buildable recovered source

R5 strengthens recovered source from a static decompile into a rebuildable project without
claiming that compiler output must be byte-identical to the original client.

- `spk-source-readiness` verifies the recovered source-tree authority and audits layout,
  imports and decompiler-failure surfaces.
- `spk-build-authority` records exact bytecode/build metadata plus the actual rebuild
  `java`/`javac` toolchain.
- `spk-progressive-compile` measures compile coverage with the readable client only as an
  explicit temporary fallback.
- `spk-clean-rebuild` removes every SpawnPK project-class binary fallback. Only bundled
  non-project dependency bytecode may remain in the dependency capsule.
- `spk-roundtrip-verify` compares rebuilt project classes with readable authority and
  separates `byte_identical`, `structural_equivalent`, `codegen_variance_only` and
  `semantic_surface_drift`.

A clean project rebuild requires `clean_project_build=true` and
`project_binary_fallback_count=0`. Compiler/decompiler codegen variance is recorded, not
misrepresented as byte identity or runtime equivalence.

## R6 — inferred parameter/local naming

Exact v308 has no surviving original local-variable or parameter-name metadata. R6 therefore
adds a separate inferred source-name layer with explicit review and binary regression gates.

- `spk-source-symbols` uses `com.sun.source.*` to create deterministic `SRC_METHOD_*`,
  `SRC_PARAM_*`, `SRC_LOCAL_*`, `SRC_CATCH_*`, `SRC_RESOURCE_*`, `SRC_ENHFOR_*` and
  `SRC_LAMBDA_PARAM_*` identities.
- `spk-source-name-review` validates evidence-backed candidate names against exact
  `source_symbol_id` targets. Candidate confidence 1.0 is forbidden.
- `spk-source-name-plan` consumes only explicitly accepted `SRCPROP_*` proposals.
- `spk-source-rewrite` rewrites a copied workspace through javac semantic `Element`
  resolution; it never performs global text replacement.
- `spk-source-rewrite-accept` requires the rewritten source to survive R5A/R5B, a zero-
  fallback R5D rebuild and R5E round-trip verification.
- `spk-source-name-carry-forward` reuses previously accepted inferred names only when
  canonical method identity and whole-method source-symbol shape remain trustworthy.

These names remain inferred readable replacements, never recovered original developer names.

## R7 — release, update and reproducibility authority

R7 turns the proven R4-R6 stages into deterministic release workflows:

- `spk-release-manifest` binds the verified recovery chain into one deterministic R7A
  release authority manifest.
- `spk-release-build` runs the existing-authority readable/source/rebuild/round-trip release
  chain in one command.
- `spk-update-release` connects conservative R3 update migration to a new exact authority
  and then the R7 release path.
- `spk-release-verify` independently re-verifies the R7A manifest and can additionally
  verify authority/readable/decompiler JAR hashes, final source-tree hash and rebuild javac
  toolchain.

R6 inferred parameter/local carry-forward is intentionally post-source and never contaminates
exact binary/class/member authority. A reproducibility PASS is provenance/rebuild evidence,
not proof that inferred names are original identifiers.

## Repository rules

- Do not commit client JARs or cache binaries.
- Do not commit raw or intermediate generated/decompiled client output. The only exception is a verified Source-Milestone publication under `recovered-source/<build>/`.
- Preserve exact SHA-256 provenance for authority builds.
- Do not claim inferred names are original developer names.
- Do not automatically promote unmatched-new classes or members.
- Do not transfer semantic names unless stable identity is proven.
- Prefer deterministic mappings over hand-editing decompiled Java.

## Documentation

Useful starting points:

- `docs/ARCHITECTURE.md`
- `docs/AUTHORITY.md`
- `docs/LINEAGE.md`
- `docs/MEMBER_LINEAGE.md`
- `docs/SEMANTIC_REVIEW.md`
- `docs/REMAP_PLAN.md`
- `docs/CLASS_REMAP.md`
- `docs/MEMBER_REMAP.md`
- `docs/MEMBER_SAFETY.md`
- `docs/FIELD_POSITION_PROOF.md`
- `docs/VERIFY_DECOMPILE.md`
- `docs/UPDATE_INTAKE.md`
- `docs/UPDATE_TRANSFER.md`
- `docs/UPDATE_MEMBER_TRANSFER.md`
- `docs/UPDATE_FINALIZE.md`
- `docs/UPDATE_ORCHESTRATION.md`

- `docs/SEMANTIC_NAMESPACE.md`
- `docs/READABLE_BUILD.md`
- `docs/RECOVERED_SOURCE.md`
- `docs/COVERAGE.md`
- `docs/SEMANTIC_CARRY_FORWARD.md`
- `docs/SOURCE_READINESS.md`
- `docs/BUILD_AUTHORITY.md`
- `docs/PROGRESSIVE_COMPILE.md`
- `docs/CLEAN_REBUILD.md`
- `docs/ROUNDTRIP_VERIFICATION.md`
- `docs/SOURCE_SYMBOLS.md`
- `docs/SOURCE_NAME_REVIEW.md`
- `docs/SOURCE_REWRITE.md`
- `docs/SOURCE_REWRITE_ACCEPTANCE.md`
- `docs/SOURCE_NAME_CARRY_FORWARD.md`
- `docs/RECOVERY_RELEASE.md`
- `docs/EXISTING_AUTHORITY_RELEASE.md`
- `docs/UPDATE_TO_RELEASE.md`
- `docs/RELEASE_VERIFICATION.md`
- `docs/CROSS_VERSION_BACKTEST.md`
- `docs/CROSS_VERSION_SOURCE_DELTA.md`
- `docs/CROSS_VERSION_JAVAC_FRONTIER.md`

### R50 — strict boolean initializer branch witnesses

[R50's private v309 conditional-boolean join probe](docs/V309_CONDITIONAL_BOOLEAN_JOIN_R50.md) checks local control-flow diamonds for the two R48-excluded boolean stores without fabricating original predicates or claiming complete Java/runtime equivalence. The actual original-v309 replay remains outstanding; hosted tests use synthetic Java only.

### R51 — bounded boolean predicate source forms

The [R51 v309 predicate source-form research](docs/V309_BOOLEAN_PREDICATE_SOURCE_R51.md) stages private Java expression candidates for exactly two independently observed JVM patterns: static-reference identity equality and static-boolean negation. The full original dependencies, class initializer and source/runtime equivalence remain unverified; no private source is in GitHub.

### R52 — original nested-enum final reference source form

[R52's exact JVM enum-final initializer witness](docs/V309_ENUM_FINAL_REFERENCE_SOURCE_R52.md) documents a directly verified `getstatic`/`putstatic` source form for one original v309 owner field. The referenced enum's source naming collision and runtime parity remain unresolved; five dynamic-final String initializer expressions are still outstanding.

### R53 — enum-helper-backed v309 String finals

[R53's pinned original-v309 two-String helper operand-chain recovery](docs/V309_ENUM_HELPER_STRING_SOURCE_R53.md) stages private JVM source forms for two runtime-assigned String finals, leaving three String initializer expressions unresolved. Original nested-enum helper/runtime parity and full class initializer order remain separate vetoes.

### R54 — exact conditional StringConcatFactory final-source forms

[R54's original-v309 conditional String concat study](docs/V309_CONDITIONAL_CONCAT_STRING_SOURCE_R54.md) verifies two private enum-comparison/branch/StringConcatFactory source forms against exact bytecode and bootstrap recipes. Together with R53's separate two enum-helper forms, one dynamically initialized final String remains without a bounded source form; no original runtime or full initializer equivalence is claimed.

### R55 — original v309 external String-helper concat form

[R55's bounded external-helper String initializer research](docs/V309_EXTERNAL_HELPER_CONCAT_SOURCE_R55.md) accounts for the fifth original dynamic-final String local expression form, after the independent R53/R54 measurements. Neither the external helper body nor complete source/runtime/JVM initializer parity is certified; source fragments remain private.

### R56 — exact full-v309 JVM initializer order gate

[R56's private original/recompiled Java acceptance verifier](docs/V309_COMPLETE_CLINIT_ORDER_R56.md) measures **all 93 original static-field writes and the 213-instruction initializer**, not just the eight dynamic-final expression forms. A private explicit field-alias map and compiled candidate are required; neither full opcode/store parity nor runtime equivalence is yet certified.

### R57 — assemble all 93 original JVM initializer assignments in order

[R57 whole ordered-initializer source reconstruction](docs/V309_COMPLETE_ORDERED_CLINIT_SOURCE_R57.md) builds a **private-only Java initializer fragment** by exhaustively accounting for all 213 original-v309 `<clinit>` instructions (84 two-op stores, nine complex stores, one `return`). It does not claim successful private compilation, original source authorship, or runtime equivalence; R56 and separate constant-pool/helper parity gates remain mandatory.

### R58 — complete-v309 initializer operand parity with conservative LDC normalization

[R58's exact JVM operand checker](docs/V309_CLINIT_OPERAND_SEMANTIC_PARITY_R58.md) documents a private Java9 skeleton matching 93 static writes, 14 static-field reads, four helper calls, seven loaded constants and three StringConcatFactory recipes against the original v309 bytecode. Two literal loads compiled as `ldc_w` rather than `ldc`; the new checker permits only equal-valued constant-pool width differences, leaving strict R56 and all source/runtime equivalence gates unchanged.

### R59 — full v309 owner field metadata source shell

[R59's private original-owner Java shell](docs/V309_COMPLETE_OWNER_SOURCE_SHELL_R59.md) combines all **126 original field declarations** (including **33 exact JVM ConstantValue fields** and eight blank dynamic finals) with the R57 93-write initializer. An independently compiled Java9 private skeleton matched all 126 original field access/descriptor/ConstantValue/Signature tuples, while methods, nested enums, `InnerClasses` and runtime parity remain unverified.

### R60 — six original v309 owner method source forms

[R60's exact short-method source recovery](docs/V309_SHORT_OWNER_METHOD_SOURCE_R60.md) stages private Java source forms for the original constructor, two constant-false boolean methods, one boolean delegator, an eight-write two-branch flag toggle, and a ten-element integer-array writer. **Three original method bodies (4, 364, and 697 JVM instructions) remain unrecovered**, and runtime equivalence is not claimed.

### R61 — original LambdaMetafactory invocation boundary

[R61's exact v309 four-op LambdaMetafactory witness](docs/V309_LAMBDA_BOUNDARY_R61.md) proves the original String literal, functional-interface factory and static consumer invocation shape without fabricating the lambda implementation. After R60's six short source forms, **two substantial owner methods (364 and 697 JVM instructions) remain unrecovered**; all runtime equivalence claims remain false.

### R62 — original 697-instruction method CFG and exception/write atlas

[R62's private large-method JVM CFG atlas](docs/V309_LARGE_METHOD_CFG_R62.md) inventories the original v309 owner method's **78 static writes, 44 exception handlers and 120 explicit branches** without guessing source-level try/catch or value expressions. The separate 364-instruction method has 46 invokedynamic sites. Both remain unreconstructed, with original private identifiers/bytecode retained only in private outputs.

### R63 — typed original static field value producer chains

[R63's exact original-v309 primitive field-write operand witnesses](docs/V309_TYPED_STATIC_WRITE_CHAINS_R63.md) identify **37 typed six-op producer chains** among the 697-instruction method's 78 static writes: 32 boolean and five integer stores. This is private JVM dataflow evidence, not recovered original Java or runtime behavior; branch/handler admission and helper side effects remain separate gates.

### R64 — 30 original null-guard boolean field sources

[R64's v309 conditional-null boolean source study](docs/V309_NULL_GUARD_BOOLEAN_SOURCE_R64.md) verifies 30 JVM `ifnonnull`-guarded static Boolean assignments (14 true, 16 false) with no incoming branch/handler entries into their windows. Alongside R63's 37 typed producers, **67 of 78** local static-write shapes are bounded; 11 others and complete source/runtime/exception parity are not recovered.

### R65 — exact original residual static-write site inventory

[R65's disjoint 78-site original JVM static-write atlas](docs/V309_RESIDUAL_STATIC_WRITE_ATLAS_R65.md) joins R63's 37 typed producer windows, R64's 30 null-guarded Boolean windows, and **11 independently measured remaining opcode shapes**. Each remaining write is tracked privately with original JVM operands and exception-region indices; no complete original Java source or runtime behavior is certified.

### R66 — strict original/candidate JVM exception and control-flow acceptance gate

[R66's compiled large-method comparison](docs/V309_LARGE_METHOD_CFG_PARITY_R66.md) requires exact instruction-ordinal branch topology, exact **ordered typed exception tables** and all explicitly mapped original static-field writes when comparing whole-SHA-pinned original and recovered-candidate JARs. The 697-instruction/44-handler and 364-instruction/1-handler original methods have **no certified compiled private candidate yet**; runtime and operand parity remain separate gates.

### R67 — 29 original v309 empty-catch conditional primitive Java source blocks

[R67's original protected-source reconstruction](docs/V309_EMPTY_EXCEPTION_PRIMITIVE_SOURCE_R67.md) stages **29 private Java `try/catch(Exception)` primitive assignment blocks** (26 Boolean, three integer). Their branches reuse exact original key/method/target identities while preserving repeated non-null lookup calls. All 42 original local `Exception` handlers have empty bodies; **13 other local protected ranges and both outer I/O handlers** remain unreconstructed. Synthetic Java9 recompilation is compared using the R66 CFG gate; full original method/runtime parity is not claimed.

### R68 — two direct v309 protected Boolean sources

[R68's private direct typed source reconstruction](docs/V309_DIRECT_EMPTY_EXCEPTION_SOURCE_R68.md) adds two exact original six-JVM-instruction Boolean assignment statements with empty local `Exception` catches. Combined with R67's 29 conditional primitive regions, this accounts for **31/42 local protected Java source forms**. Eleven other local regions, the outer I/O flow, original method compilation and runtime parity remain open.

### R69 — exact v309 Properties initialization type and FileInputStream loading prefix

[R69's original 24-instruction Properties load source recovery](docs/V309_PROPERTIES_LOAD_PREFIX_R69.md) proves that the original settings method constructs one `java.util.Properties` in JVM local slot 1, loads it via a `FileInputStream`, closes the stream, and makes 82 unary plus one two-argument `getProperty` calls. This resolves R67/R68's source receiver type, while outer `IOException` catch structure and whole-method/runtime equivalence remain unverified.

### R70 — original v309 outer IOException Java source envelope

[R70's exact original two-range IOException source recovery](docs/V309_OUTER_IO_EXCEPTION_SOURCE_R70.md) preserves the R69 File/Properties prefix and original `IOException.printStackTrace()` catch behavior. Java9 recompilation reproduces **both original protected-range split boundaries around the early return** without a bytecode patch. The 697-instruction method's middle, remaining 11 local source regions and runtime parity are still unrecovered.

### R71 — five additional original v309 protected List/int/String Java source forms

[R71's exact other empty-catch source recovery](docs/V309_OTHER_PROTECTED_SOURCE_R71.md) adds three original guarded `List.add` regions, one nullable Integer conversion and one String default/second-lookup block. This brings **36 of the original 42 local Exception-protected source regions** into bounded Java source form. Six complex regions, full original method compilation and runtime equivalence remain unresolved.

### R72 — original v309 dual reference/Boolean protected source

[R72's exact original two-static-write empty-catch source recovery](docs/V309_DUAL_REFERENCE_BOOLEAN_SOURCE_R72.md) reconstructs one 11-instruction protected region that assigns an original nested-reference field and then a Boolean field from two separate `Properties` lookups. This brings bounded local JVM-backed Java source forms to **37/42**; five more complex local regions and original whole-method/runtime parity remain unresolved.
