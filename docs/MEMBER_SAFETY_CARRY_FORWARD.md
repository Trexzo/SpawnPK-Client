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
