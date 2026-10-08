# v309 GitHub-first recovery frontier

This directory is the tracked handoff point for **accepted but not yet fully promoted**
v309 recovery state.

It is intentionally separate from `authority/`.

`authority/v309.json` remains reserved for the eventual fail-closed
`EXACT_CURRENT_CLIENT` promotion after the normal authority-candidate gate reports the
build ready. An unresolved recovery frontier must never be represented as that final
authority snapshot.

## Tracked frontier files

The handoff branch should contain:

- `class-lineage.json` — canonical class lineage used by the accepted v309 recovery state.
- `member-lineage.json` — latest validated member lineage after explicit reviewed identity
  acceptance.
- `global-field-usage.json` — exact-JAR global field frontier recomputed from that member
  lineage.
- `canonical-method-field-context.json` — exact canonical-method context frontier
  recomputed from the same member lineage/global report.
- `frontier.json` — compact provenance manifest binding all tracked files to exact client
  hashes and the GitHub base used to create the frontier.

Client JARs remain untracked.

## Rules

1. Never edit a lineage relation by hand to make the unresolved count decrease.
2. New member relations enter the frontier only through an explicit reviewed acceptance
   spec and the existing fail-closed `member-accept-review` command.
3. Recompute dependent reports after every accepted batch.
4. Every `frontier.json` update must pin file SHA-256 values, exact v308/v309 client
   SHA-256 values, unresolved count, and the proof batch that produced the change.
5. Keep the previous accepted frontier in Git history; do not rewrite it in place.
6. GitHub CI/review is the normal workflow after this handoff. Local exact-JAR execution is
   only required when a new proof lane genuinely needs the proprietary client bytes.

## Current handoff

The branch was created from:

`b56e2b9d76c71141264d79f0350c4a6470d5eaaf`

The local source frontier before final handoff has:

- member lineage SHA-256
  `F3B3E0C9522C7C4719223DBE1B3F34AF0C36F816E0A4C265201030DBD3446BD0`
- 149 unresolved members
- six additional reviewed method-context/boundary-block identities from
  `METHODBOUNDARY_3D5AF61BCEDF9BD1687C`
- review spec SHA-256
  `FA39804B9E6BA589EDA013F86B8B69EB9D17941F3F0152D9801C984EE2096640`

The final local handoff step must accept exactly those six reviewed IDs, validate the
expected 143 unresolved frontier, recompute its reports, write the tracked files above,
and push them to this branch.
