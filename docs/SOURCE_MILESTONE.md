# Source Milestone 1

Source Milestone 1 is the publication gate for the recovered v308 Java source repository.

The target publication repository is:

`Trexzo/SpawnPK-Client-Source`

That repository MUST NOT be created or populated until a source milestone manifest reports:

```json
"publishable": true
```

## Hard gates

A milestone is publishable only when all of the following hold:

1. The milestone is bound to one exact lowercase 40-hex `SpawnPK-Client` authority commit.
2. The recovery authority is exactly build `v308`.
3. The exact client authority SHA-256 links across readable, recovered-source, clean-rebuild, and release authority.
4. Accepted class/member semantic naming intelligence is carried by the canonical lineage and its semantic provenance.
5. The semantic namespace ID and class/member plan digests agree across the readable and recovered-source authorities.
6. Deterministic source-safe fallback naming is enabled with a non-empty fallback prefix.
7. The recovery release is ready and its reproducibility verification passes.
8. The canonical Java source-tree SHA-256 matches the release authority.
9. Clean project compilation completes.
10. Project binary fallback count is exactly zero.
11. Generated project classes exactly equal the expected project class set: no missing and no unexpected classes.

A failed gate is recorded in `blockers`; it never gets silently downgraded.

## Manifest

The deterministic milestone manifest has:

- kind: `source_milestone_manifest`
- ID prefix: `SRCMILESTONE_`
- source tree SHA-256, Java file count and source byte count
- exact authority commit and exact client SHA-256
- semantic namespace and class/member plan digests
- accepted semantic review IDs recovered from canonical class/member provenance
- fallback policy
- recovered workspace, build authority, clean rebuild, release and release-verification IDs
- collision-derived provenance when present
- exact project class-set equality
- publication target and deterministic export layout

Semantic names are evidence-backed recovery names. The milestone does not claim inferred semantic identifiers are original developer identifiers.

## Verification

`spk-source-milestone verify` rebuilds the milestone manifest from its authority inputs and requires exact reproduction.

Verification reports use:

- kind: `source_milestone_verification`
- ID prefix: `SRCMILEVERIFY_`

Source-tree drift, authority drift, gate drift or provenance drift changes the recomputed manifest and fails exact verification.

## Provenance document

Every publication bundle generates:

`provenance/SOURCE-PROVENANCE.json`

This document is derived directly from the accepted milestone manifest. Callers cannot override it.

It records:

- exact authority repository, commit and client SHA-256
- exact v308 build ID
- semantic namespace, class/member plan digests and review IDs
- deterministic fallback policy
- recovered workspace, build authority, clean rebuild, release and release-verification IDs
- collision provenance when present
- canonical source-tree authority
- exact project class-set status

Provenance IDs use the prefix `SRCPROV_`.

## Source-only publication bundle

`spk-source-milestone bundle` refuses any manifest where `publishable` is false.

The deterministic bundle contains only:

```text
SOURCE-MILESTONE.json
BUNDLE.json
src/**/*.java
provenance/SOURCE-PROVENANCE.json
provenance/*.json
```

Only `.java` files are copied from the source authority. Classfiles, JARs and unrelated workspace files are not copied.

Bundle IDs use the prefix `SRCBUNDLE_`.

## Publication boundary

Framework code may be merged before an exact v308 milestone is publishable.

Publication itself is a separate action and remains forbidden until:

1. an exact v308 milestone manifest exists;
2. `publishable=true`;
3. exact milestone verification reports `verified=true` and `publishable=true`;
4. the source-only bundle is built from that exact source authority.

Until those conditions are satisfied, do not create or populate `Trexzo/SpawnPK-Client-Source`.

## GitHub Actions publication gate

The manual workflow `.github/workflows/source-milestone-1.yml` consumes one exact authority artifact from a prior GitHub Actions run. The artifact contract is:

```text
authority/
  class-lineage.json
  member-lineage.json
  readable-client-manifest.json
  recovered-source-manifest.json
  clean-rebuild.json
  recovery-release.json
  release-verification.json
  src/**/*.java
```

The workflow refuses a non-40-hex authority commit, requires that commit to be an ancestor of the workflow revision, rejects non-Java files inside the source authority root, builds the milestone manifest, exactly reproduces it, builds the source-only publication bundle, verifies every indexed file/provenance hash and exported source-tree authority, and uploads the verified result as an Actions artifact.

The uploaded artifact layout is:

```text
source-m1/
  SOURCE-MILESTONE.json
  publication/
    SOURCE-MILESTONE.json
    BUNDLE.json
    src/**/*.java
    provenance/*.json
  verification/
    SOURCE-MILESTONE-VERIFICATION.json
    SOURCE-BUNDLE-VERIFICATION.json
```

The workflow does **not** create, push to, or otherwise populate `Trexzo/SpawnPK-Client-Source`. Publication remains a separate action that is forbidden until the milestone and bundle verification both pass.

## Bundle verification

`spk-source-milestone verify-bundle` independently verifies an already-built publication bundle. It recomputes the canonical Java source-tree authority, requires the indexed file set to match exactly, verifies every indexed file SHA-256, verifies the provenance index, regenerates `SOURCE-PROVENANCE.json` from the embedded milestone, rejects unindexed or binary files, and optionally requires an external milestone manifest to match the embedded manifest exactly.

Bundle verification reports use:

- kind: `source_publication_bundle_verification`
- ID prefix: `SRCBUNDLEVERIFY_`

Publication bundle source files are emitted with canonical LF line endings and JSON metadata is emitted as deterministic UTF-8/LF bytes so the exported authority is stable across Windows and Linux.
