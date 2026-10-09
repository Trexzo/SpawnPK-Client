# v309 exact-private CP witness coverage accounting (research only)

## Why this milestone exists

Merged #884 added strict JVM switch and array operand meanings to the existing CP-aware method comparator. Synthetic CI plus an independent private-JAR opcode scan verified the newly supported forms, but **the number of additional *identity witnesses* remains unknown until the official exact-private replay**.

The one-shot exact-private replay (#883) already produces the merged five-lane concordance report. This milestone makes its final JSON output actionable without emitting any additional private evidence artifacts.

## New aggregate evidence fields

Every one of the eight already-public canonical class-group rows now includes:

- Supported CP-bearing methods in v308 and v309.
- Unsupported Code methods in each build (not counted as proof).
- CP-free methods deliberately excluded in each build.
- Count of independent, unique pairwise CP-semantic method witnesses.
- Count of ambiguous duplicate CP-method fingerprint groups.
- The whole-archive mutual rival state and existing research-only review bucket.

The summary also includes totals for those categories across all eight class groups, while retaining **26 descriptor-blocked fields, 143 unresolved field relationships, zero canonical class/member acceptance**.

## Fail-closed validation

- Reject missing, negative, noninteger or boolean counts, and any unique witness count greater than the eligible method count in either build.
- Reject a pairwise report whose aggregate matched-method count disagrees with the sum of its eight class rows.
- For any positive bidirectional whole-archive supported-subset uniqueness state, require the reported rival-scan method witness cardinality to match the pairwise method witness cardinality **exactly** and to be at least three.
- Independently validate every source report's content-derived report ID as already required by #882. Invalid counts cannot be repaired by the joiner.
- Preserve current exception, per-source SHA, canonical 8-group/26-field coverage and overwrite protection.

This is bounded **evidence accounting**, not a confidence score or proof of semantic class equivalence. No private JARs, method names, disassembled Code, constant-pool strings, raw identities or member fingerprints are emitted. The final report is a fresh local output; previous reports are never overwritten or silently upgraded.

## Remaining acceptance boundary

Hosted CI uses synthetic fixtures. The official SHA-pinned original v308/v309 JARs must still be replayed locally with the one-shot tool, and any positive research bucket requires separate review and field/member topology proof before canonical acceptance. The authoritative v309 frontier remains ACCEPTED_INCOMPLETE / **143 unresolved**, including **26 descriptor-blocked** field relationships.
