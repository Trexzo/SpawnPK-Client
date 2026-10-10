# R11 — external canonical-method field witnesses (research only)

Existing R3M field_proof.py is unchanged: its strict canonical acceptance still counts own-field accesses in methods inside the declaring owner. R11 is a separate opt-in research-only evaluator; it does not generate an R3M proof or apply any mapping.

## Checks

- SHA-256 of original client JARs must match both build records and original indexes.
- CLI requires exact byte SHA-256 pins for both class-lineage and member-lineage JSON.
- Class and member lineage must validate; each profiled accepted class entry must match the recorded entry SHA-256.
- Only unresolved seeded fields in an accepted owner class are considered; target field declarations and access flags must exist and not already belong to another canonical member.
- Witness methods must have a genuine paired CLIENT_METHOD identity and consistent two-sided CLIENT_CLASS owner.
- Entire JVM instruction layouts **and all non-symbolic-CP decoded operands** must align, including local indexes, branch/switch targets, integer constants and increments. Symbolic CP referent identity outside the candidate field is not established by this research. Accessed field operation, offset, target-owner field ordinal and descriptor must align under only accepted class aliases. **Any rs/ object type in a field descriptor without an accepted class alias vetoes the witness**; it is never normalized to an untrusted wildcard, even when the raw obfuscated name is the same in both builds.
- At least two distinct accepted method IDs are required. Repeat accesses inside one method cannot satisfy the threshold.
- Divergent field accesses are retained as negative vetoes on **both sides** of each provisional class/member pair, including old-only and new-only accesses; swapping equally typed candidate fields must not produce accepted evidence.
- The result always has canonical=false, mapping_mutation=false and accepted_identities=0. Output files cannot be overwritten.

## Usage (private Windows checkout)

Set PYTHONPATH to the src directory and run python -m spk_recovery.external_field_witness_research_cli with --class-lineage, --class-lineage-sha256, --member-lineage, --member-lineage-sha256, --old-index, --new-index, --old-jar, --new-jar, --old-build-id v308, --new-build-id v309, --class-id CLIENT_CLASS_000141 and --out pointing to a new private JSON path. Read --help for argument syntax.

Original JARs, the generated report, obfuscated class/member coordinates, the R10/R11 private research evidence and recovered proprietary source must remain outside the public repository.

## R12 authoritative frontier reconciliation (2026-10-10)

**Important correction:** The R10/R11 exact-private investigation used an older pre-promotion member-lineage snapshot with **303 unresolved entries**, not the tracked GitHub-first accepted v309 frontier. The later `research/v309-field-recovery/member-lineage.json` already records **both `CLIENT_FIELD_002107` and `CLIENT_FIELD_002108` as accepted in v309**, each with an explicit reviewed `MANUAL` relation. They are **not** among the 143 remaining unresolved items. The fact that the old private R10/R11 prototype called them pending must never cause a second promotion.

The matching canonical class lineage is also tracked under `research/v309-field-recovery/class-lineage.json`; `research/v309-field-recovery/frontier.json` pins the complete files' SHA-256 values and both exact client JAR hashes. This is the **ACCEPTED_INCOMPLETE** frontier, *not* an `authority/v309.json` final promotion.

The hosted `tests/test_v309_tracked_frontier_reconciliation.py` checks the pinned frontier file hashes, both accepted field relationships and the explicit rejection of an attempted duplicate research proposal. For any further private work, use the current tracked frontier, not the old member-lineage. A replay of the R11 evaluator against current authority should **not** try to recreate either accepted relationship; only genuinely unresolved members are eligible.

### What R11 still proves

The earlier R10/R11 bytecode research measured three previously canonical-method witnesses per field using a deliberately minimal private class-lineage projection. That was useful to test the fail-closed evaluator, but **not** a formal full-lineage replay or independent justification to replace the existing accepted reviewed proofs. R11 itself has `canonical=false`, `mapping_mutation=false`, and `accepted_identities=0`. This research tool does not claim reflection, native linkage, initialization, exception or whole-program equivalence.

Additional v309 gaps still require fresh private-JAR measurement with *current* accepted lineage, appropriate formal proof and explicit review. The tracked 143 unresolved entries and 26 descriptor blockers are frontier figures rather than counts newly recalculated by R11/R12.