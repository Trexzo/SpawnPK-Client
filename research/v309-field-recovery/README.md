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

## Current accepted frontier

The GitHub-first handoff was completed by PR #857 and is now on `main`.
The tracked accepted member lineage remains at **143 unresolved**, with SHA-256
`21D590B6C27BFD3DE5E17B664A61FE430F02BF5129638D6FDD678D81AF387070`.
The next research evidence generators (#858/#859 and follow-ups) do **not**
automatically reduce that count: their review specs require exact private-JAR
measurement and explicit `member-accept-review` promotion.

## Descriptor-class dependency gate

Use the tracked `global-field-usage.json` and run:

```sh
python -m spk_recovery.descriptor_class_dependencies \
  research/v309-field-recovery/global-field-usage.json \
  --out descriptor-class-dependencies.review.json
```

This read-only research report groups **26 descriptor identity vetoes** by
**8 missing new-build class identities**. The largest dependency is the
old canonical `CLIENT_CLASS_000029` (`rs/Client` descriptor), blocking
14 field identities. Five field descriptors and nine field owners changed
their raw names across v308/v309.

The output is **not** class-lineage or member-lineage authority. Resolving a
descriptor gate requires an independently proven new class identity, an exact
recomputation of dependent field evidence, and an explicit reviewed acceptance
step. Matching raw strings is insufficient; no veto may be bypassed merely
because a raw descriptor appears unchanged.

## Single current descriptor-class replay (merged GitHub chain)

The authoritative tooling chain on `main` is:

- PR #862: `descriptor_class_dependencies` (26 vetoes, 8 class dependencies).
- PR #863: `descriptor_class_index_witness` (unique exact/structural
  class-index witnesses; research-only).
- PR #864: `descriptor_class_verified_replay` (rebuild from original global
  report; recompute class/index evidence; research-only).
- PR #865: `descriptor_class_private_jar_replay` (pinned local exact-JAR
  entry point; full indexes remain in memory; outputs never overwrite inputs).

For measurement with the two exact private JARs, use the command documented in
[the root README](../../README.md#v309-active-recovery-frontier-october-2026).
Do not run the old index/diff/authority recipe in place of this current proof
lane. Never commit the private client JARs or full reconstructed indexes.

The exact pinned hashes remain:

- v308: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`
- v309: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`

The command stops if either JAR mismatches, a tracked frontier file has
changed, any class cannot be parsed, or the 26/8 group accounting drifts.
A successful command produces **research candidates only**. Even a candidate
for `CLIENT_CLASS_000029` does **not** automatically remove any of the
143 unresolved fields. A separately reviewed class relationship, recomputed
field evidence and explicit canonical acceptance are still required.

## Continue-here contract

`research/v309-field-recovery/frontier.json` remains the source of truth for
the accepted-but-incomplete handoff; `authority/v309.json` must not be
invented or promoted for convenience. Follow GitHub `main` for tooling, keep
new unmeasured work in draft PRs, and require hosted CI before merge.
The current proof lane needs local private JARs only for the exact replay;
GitHub-only changes should not pretend that they measured private bytes.
