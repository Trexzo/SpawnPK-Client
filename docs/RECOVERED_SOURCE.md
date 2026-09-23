# R4C — recovered source workspace

R4C consumes only a **complete, independently verified R4B readable-client build**.

It does not rename symbols and does not accept semantic candidates.

## Command

```powershell
spk-source-workspace `
  .\generated\readable-v308\readable-client-manifest.json `
  .\generated\readable-v308\readable-client.jar `
  .\tools\cfr.jar `
  --decompiler-sha256 <PINNED_SHA256> `
  --engine cfr `
  --out-dir .\generated\source-v308
```

Vineflower and Procyon are also supported via `--engine vineflower` and `--engine procyon`. All engines remain bound to the explicitly supplied decompiler JAR SHA-256.

## Required authority pins

Before decompilation, R4C verifies:

- readable build status is `complete`
- independent R4B verification passed
- readable JAR SHA-256 matches the R4B manifest
- semantic namespace ID exists
- class remap-plan digest exists
- member remap-plan digest exists
- decompiler binary SHA-256 matches the explicitly supplied pin

## Workspace

```text
src/                              # generated Java source tree
decompiler-result.json
recovered-source-manifest.json
```

The recovered-source manifest records:

- exact source authority SHA-256
- readable transformed JAR SHA-256
- semantic namespace ID
- exact class/member plan digests
- decompiler engine + decompiler SHA-256
- Java source file count
- total generated source bytes
- deterministic source-tree SHA-256

The source-tree digest is computed over sorted relative Java paths plus exact file bytes.
It lets later stages prove they are analyzing the same decompiler output without storing the
source tree in Git.

Generated Java remains an artifact, not authoritative source and not recovered original
identifier metadata.


## Project-scoped Procyon mode

For archives that bundle large dependency trees, R4C can explicitly recover source only for
project-owned classes while keeping the **entire verified readable JAR** as the binary
authority:

```powershell
spk-source-workspace `
  .\\generated\\readable-v308\\readable-client-manifest.json `
  .\\generated\\readable-v308\\readable-client.jar `
  .\\tools\\procyon-decompiler-0.6.0.jar `
  --decompiler-sha256 <PINNED_SHA256> `
  --engine procyon `
  --project-only `
  --out-dir .\\generated\\source-v308
```

Project selection is taken only from the verified R4B manifest's
`project_source_prefixes`. The readable JAR SHA-256 remains the authority pin; dependency
classfiles are extracted only as decompiler resolution context and are not requested as
recovered source.

The recovered-source manifest additionally records `source_scope = project_classes`, the
normalized project prefixes, exact selected project class count, and a deterministic digest
over the sorted selected class entry names.

Procyon class-file inputs are split into deterministic command-length-safe batches so the
same mode works on Windows and POSIX. This scope change does not weaken R5: clean rebuild
still compiles project sources with zero project-binary fallback and independently verifies
the complete expected project class set, while bundled non-project classes remain in the
exact dependency capsule.

Whole-archive decompilation remains the default. Project-only mode is currently supported
only by Procyon and fails closed for other engines.


## Procyon source normalization

R8I applies a narrow source-safety normalization after Procyon finishes and before the
recovered source tree is hash-pinned.

This is **not** semantic naming or manual source repair.

The normalizer currently handles only two exact, proven Procyon output defects:

- a top-level `synthetic class X` pseudo-declaration is rewritten only when the matching
  readable classfile proves the compiler-generated helper shape: package-private
  `ACC_SYNTHETIC`, `java/lang/Object`, no interfaces, only synthetic static-final
  `int[]` fields, and at most one static `<clinit>`. Omitted exact fields are restored
  as Java-representable `static final int[]` declarations;
- a standalone string-concatenation expression such as `"value=" + call();` is captured
  into a deterministic unused `String` local only when it is lexically inside executable
  brace depth. This preserves evaluation, including any method-call side effects, while
  making the statement legal Java.

Any synthetic-class shape outside that proof boundary fails closed instead of being
rewritten.

For Procyon workspaces, R4C writes:

```text
source-normalization.json
```

The normalization report records the exact readable JAR SHA, before/after source-tree
hashes, deterministic action provenance, and a `SRCNORM_*` ID. That normalization ID is
included in the recovered-source workspace ID material, so R5 consumes the normalized tree
as the explicit source authority.

CFR and Vineflower source workspaces are unchanged by this stage.
