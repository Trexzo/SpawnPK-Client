# v309 CP-referent whole-archive rival scan — research only

**Purpose:** continue [issue #877](https://github.com/Trexzo/SpawnPK-Client/issues/877) after the merged pairwise CP-aware tool (#878). A proposed class may have method fingerprints matching between versions yet still collide with a *different* class elsewhere in either client JAR. This research command checks the rival-class problem without pretending that absence of a rival proves semantic identity.

## Authority and preflight

- Require the exact SHA-pinned private v308 and v309 client archives, the tracked frontier and unchanged canonical v308 class lineage. Reuse `build_v309_cp_method_research` for the existing eight-class/26-field candidate and old-fingerprint checks.
- Build complete independent indexes of **all 10,472 v308 and 10,502 v309 classes**, with zero class parse errors; reject incomplete archives.
- For each proposed old/new class, compute a fingerprint of **only completely resolved CP-bearing methods** using the existing `_method_semantics` parser and exact CP operands. Normalize only the class's own JVM type to a private in-memory sentinel. Unrelated member, owner, descriptor, literal and float bit meaning must remain unchanged.
- Use a necessary coarse whole-archive prefilter: method access, erased descriptor shape and **exact Code length**. It cannot exclude any class sharing three or more fully matching CP-bearing methods; unlike the earlier class-shape lane, it does not require matching field counts or field shapes. Evaluate every passing class in both archive directions.
- A rival class with at least three individually unique, exact CP-referent semantic method fingerprints is an explicit veto. A plausible rival that cannot be decoded, an overbroad prefilter (more than 500 classes), an inadequate candidate witness count, or an incomplete input **cannot become a uniqueness claim**.
- If all coarse-viable competitors decode and none match, classify at most `MUTUAL_WHOLE_ARCHIVE_SUPPORTED_SUBSET_RESEARCH_ONLY`. This is a statement about the subset of methods the strict parser supports—not a canonical class identity.

## How to run against private originals

Run from the pinned checkout with original private client JARs:

```powershell
python -m spk_recovery.v309_cp_whole_archive_rival_research `
  --v308-jar "C:\private\exact-v308-client.jar" `
  --v309-jar "C:\private\exact-v309-client.jar" `
  --out "$env:TEMP\v309-cp-rival-new.json"
```

The paths above are examples. Output is **new-file-only**, and no private JAR, bytecode, class-index dump, resolved CP entry, member descriptor, actual method signature, or raw literal may be published. Research output contains only known canonical class IDs, aggregate per-class counts, categorical vetoes, pinned hashes, and source report IDs.

## What remains unproven

This tool is **not** a complete code equivalence proof. Unsupported control-flow instructions, unproven member/class renames outside the proposed self owner, CP-free code, new/removed methods, ambiguous duplicate method fingerprints, and arbitrary source-selection hypotheses remain unresolved. A clean result is not automatic acceptance, and cannot authorize accepting any of the 26 descriptor-blocked field identities.

Issue #877 remains open until independent private exact-JAR replay, an explicit review of all conflicts/alternatives, and a separate canonical acceptance proposal. The tracked v309 frontier stays **143 unresolved**, `ACCEPTED_INCOMPLETE`; Source M1's local compiler frontier is unrelated to this task.
