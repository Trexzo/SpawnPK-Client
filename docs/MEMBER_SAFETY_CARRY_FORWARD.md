# Member-safety acceptance carry-forward

`spk-member-safety-carry-forward` transfers an already reviewed member-safety
acceptance to another exact build only when the risk semantics are unchanged.

This exists for cross-version recovery cases such as historical v307 -> v308
where the exact client SHA changes but the reviewed member rename surface may
remain identical.

## Required inputs

- previous member remap plan;
- previous member-safety report;
- previous explicit acceptance;
- target member remap plan;
- freshly generated target member-safety report.

Both reports are validated against their exact plans. The previous acceptance
must validate before any transfer is considered.

## Equivalence rule

Build-specific fields are expected to change:

- source SHA-256;
- member-plan digest;
- report ID;
- risk IDs.

Those fields are not used as semantic equality.

For every stable `CLIENT_FIELD_*` / `CLIENT_METHOD_*` member, the following
must remain exactly equal:

- member identity;
- kind;
- owner internal name;
- source name;
- descriptor;
- target name;
- access flags;
- complete hazard payload;
- final risk level.

The member sets must also be identical. Transfer is all-or-nothing: one changed,
missing or newly introduced member blocks the target acceptance entirely.

## Output

On full equivalence the command emits:

- `member_safety_carryforward_report` provenance;
- a normal schema-valid `member_safety_acceptance` bound to the target report.

The carried reason retains the previous explicit review reason and identifies
the previous report authority.

On any mismatch, the command emits only the carry-forward report and exits
blocked. The affected member must receive fresh review.

This does not claim that two client binaries are equivalent in general. It
proves only that the exact member-name safety review surface supplied to this
gate is unchanged.

## Historical v307 preparation wrapper

`scripts/Prepare-HistoricalV307MemberSafety.ps1` composes this gate for the exact historical v307 -> v308 fixture. It SHA-verifies both client JARs, deterministically regenerates the v307 index, checks canonical coverage for both builds, builds the exact source-safe semantic namespace/member plans for v307 and v308, rescans both member-safety surfaces, and first revalidates the archived reviewed v308 acceptance against the freshly reproduced v308 report.

Only after that reproduction succeeds does it invoke `spk-member-safety-carry-forward`. The resulting v307 acceptance is independently validated again and its path is printed for `scripts/Invoke-HistoricalV307RecoveryRelease.ps1`.

If v307 lineage is absent, the build-specific coverage/semantic namespace stages fail closed; identity must then be restored through the existing R3 migration authority rather than fabricated in this wrapper.
