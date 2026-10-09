# v309 exact-private five-lane replay — single local command

This is the final research replay convenience gate for issue #877 following merged #882. It runs the existing research builders against the **same exact SHA-pinned local private original JARs** and generates the source reports in memory. The only output is **one compact noncanonical concordance JSON file**—not five separate output files, private class indexes, JARs, CP values, or disassembly.

## One PowerShell command on the original private-JAR machine

Run from a checkout of certified SpawnPK-Client main. Supply the actual private original JAR paths; names below are examples.

    python -m spk_recovery.v309_exact_private_concordance_replay --v308-jar "C:\private\client-v308.jar" --v309-jar "C:\private\client-v309.jar" --out "$env:TEMP\v309-private-concordance-new.json"

No manual archive extraction, temporary full-index exports, or intermediate reports are required. The output path must be **new**, and never a pinned input. To start over, choose a different output name rather than overwriting evidence.

## Strict, ordered authority boundary

1. SHA-256 check original private JARs, tracked class lineage, tracked global-field report, and 143/26 ACCEPTED_INCOMPLETE frontier before parsing.
2. Revalidate canonical class-lineage schema and exact v308/v309 build pins.
3. Run merged #881 pinned structural audit **first**: exact 2,221 old/new entry structural fingerprints and zero drift. Any mismatch stops the run rather than regenerating accepted fingerprints.
4. Build exact in-memory JAR indexes once for global String-literal and method-shape evidence. Require zero class parse errors, 10,472 v308 and 10,502 v309 classes, and unchanged exact JAR SHA.
5. Run merged #875 and #876 unique-literal and whole-archive method-shape research directly from those indexes; never serialize indexes.
6. Run merged #878 CP-referent method comparison and #879 both-archive CP-semantic rival-owner research against the same two private originals.
7. Run merged #882 five-report cryptographic provenance/coverage joiner. It checks each complete source report's content-derived ID, report chain, eight descriptor-blocked class hypotheses, 26 blocked fields, exact client hashes and absence of accepted identity mutations.
8. Write one **new** bounded research concordance JSON and print only aggregate research counts.

Unexpected upstream exceptions may contain private class names, CP strings or paths. The one-shot CLI masks the exception *message* and prints only its class, with no copied private values. A failed stage leaves **no output**.

## Crucial limits

A research bucket named SUPPORTED_SUBSET_ONLY_NEEDS_EXPLICIT_REVIEW is **not** permission to edit class, field, member or Source M1 lineage. Full semantic identity may depend on methods not supported by the present CP decoder, renamed external owners, correlated String literals, rival classes outside the supported subset, and independent manual review. A future, separately reviewed acceptance proposal is required.

The canonical state remains **143 unresolved v309 fields**, including 26 descriptor-blocked relationships. The last separately measured Source M1 compilation frontier remains 98 errors; this tool edits neither frontier.

The original private JARs are never sent to GitHub or CI. Hosted Ubuntu and Windows tests use synthetic fixtures and mocks; **hosted green is not evidence that a private full replay succeeded**.
