# v309 two-lane private evidence replay

The accepted GitHub frontier is **143 unresolved fields**. Its two largest
independently researched classes of residual are:

- **68 `empty_both` field relations** — no canonical method/whole-JAR usage
  witness. The existing `empty_field_declaration_evidence` prover requires
  exact JARs, verified class/member lineage, paired canonical declaration
  boundaries and two-sided interval evidence. No candidate is auto-accepted.
- **26 descriptor-identity vetoes** across **8 missing new class identities**.
  The `descriptor_class_verified_replay` prover recomputes the grouped
  dependency inventory, then requires independent unique class-index matches.
  It produces candidates only.

A *single* local private-JAR command runs both proofs with one in-memory
indexing pass per client. It verifies the accepted `frontier.json`, tracked
class lineage, member lineage and global report SHA-256 against that frontier
**before indexing either JAR**, then independently runs both proven research
generators with the **same** indexes.

From an installed checkout at the repository root:

```powershell
python -m spk_recovery.v309_private_dual_proof_replay `
  --v308-jar "C:\private\exact-v308-client.jar" `
  --v309-jar "C:\private\exact-v309-client.jar" `
  --out-dir "$env:TEMP\v309-dual-proof-new"
```

Replace both example JAR paths with the actual local exact builds. Use a
**nonexistent** output directory for each run. The output is entirely local,
exclusive/non-overwriting, and contains only:

```text
BUNDLE.json
descriptor-class-research.json
empty-field-declaration-research.json
```

The output `BUNDLE.json` binds both reports by deterministic SHA-256 and exact
client fingerprints. The two full class indexes are **never serialized** by the
command, and no client JAR is copied. If any proof fails, no output directory
is created; a failed write to a newly-created directory rolls it back.

Both reports contain class/field identifiers and fingerprints: **treat them
as private evidence**, never automatically commit them. GitHub unit tests
use only synthetic JAR bytes and tracked accepted metadata and cannot
measure the real candidate yield without the proprietary clients.

This **does not promote** any class, field, member lineage, or
`authority/v309.json`. Candidates remain review-only; the accepted 143-field
frontier is not reduced until an independently justified review acceptance and
fresh recomputation of all dependent reports passes the existing fail-closed
authority gates. The other **49** residual fields (48 topology and 1 raw-source)
remain separate proof lanes; this command does not claim to resolve them.
