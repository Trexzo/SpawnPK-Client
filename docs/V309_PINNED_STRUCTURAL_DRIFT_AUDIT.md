# Exact-private v309 pinned class structural drift audit

Research follow-up to merged #880 (lossless JVM Modified UTF-8), within issue #877. The two pinned original client JARs contained 16 third-party dependency classes per build with special Modified UTF-8 String literals. Changed parser semantics can change the structural fingerprints of these classes. No canonical class or member mapping should be silently regenerated.

## Canonical guard

This command checks the exact v308/v309 class lineage **as it exists**, without editing it.

- Verify tracked class-lineage file SHA-256 against the accepted v309 frontier, plus exact SHA-256 for both original private JARs.
- Revalidate complete canonical class-lineage schema and both build declarations.
- Require all 1,129 accepted v308 and 1,092 accepted v309 class entries to be present. Check their raw entry SHA-256 and internal names against the original pinned lineage.
- Require complete archive entry counts of 10,472 classes in v308 and 10,502 classes in v309; reject duplicated ZIP paths and missing pinned classes.
- Parse each pinned entry using the **lossless** classfile decoder from #880 and recompute the structural SHA-256. Count exact matches and any mismatches **without rewriting pinned hashes**.
- A structural mismatch gives the report state `STRUCTURAL_FINGERPRINT_DRIFT_REVIEW_VETO` and command exit code 2, never an accepted or silently updated identity.
- The compact research report contains only aggregate per-build counts, already published exact-JAR hashes and a deterministic report ID. No private class names, actual entry hashes, strings, Code, method identities or recovered source appear in output.

## Local private invocation

Run in the repository checkout, using only the exact, privately held v308 and v309 JARs:

```powershell
python -m spk_recovery.v309_pinned_structural_audit `
  --v308-jar "C:\private\exact-v308-client.jar" `
  --v309-jar "C:\private\exact-v309-client.jar" `
  --out "$env:TEMP\v309-pinned-structural-audit-new.json"
```

The report path must be a **new** file: outputs and protected inputs cannot be overwritten. Never upload the proprietary JARs or raw computed class hashes to GitHub.

## Boundaries

This does not authenticate any *unaccepted* changed class in the eight descriptor-blocked v309 hypotheses; it only checks the **previously pinned** class fingerprints for regression after parser hardening. An entirely green result is evidence that pinned SHA-based identity proof still agrees with the new lossless parser; it does not reduce the current v309 frontier of **143 unresolved field relationships**.

Hosted CI covers synthetic classfiles, wrong archive SHA, missing and duplicate ZIP entries, canonical raw SHA mismatch, structural mismatch as explicit veto, unexpected lineage count and privacy of emitted report. **Actual private JAR replay is separately required**; never claim it from synthetic hosted checks.

Tracks #877 and parent #828. No canonical acceptance or client source export in this PR.
