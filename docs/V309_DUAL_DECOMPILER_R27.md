# R27 — targeted dual-decompiler replay in SpawnPK-Client

R27 composes the repository's R26 exact-class slice builder with the existing
CFR/Vineflower runner. It is a **real GitHub project capability** rather than
a private ZIP research script. Original client bytes and generated sources
remain strictly local and untracked.

## Execution contract

1. Verify SHA-256 of the **complete original JAR** and each executable
   **CFR** and **Vineflower** JAR before creating an output directory.
2. Refuse any pre-existing output directory.
3. Create one deterministic private class slice containing the exact
   requested class and its nested classes.
4. Run CFR and Vineflower **separately** on that same exact byte input.
   Each receives a distinct private output directory.
5. Verify both runs generated at least one Java file, fingerprint each
   generated source tree, and re-hash all three input JARs plus the slice.
6. Only then write `private-research-manifest.json`. The manifest contains
   SHA-256 evidence and aggregate counts, not original class coordinates,
   recovered Java, decompiler console text or proprietary member names.

The existing `spk_recovery.decompiler` runner requires runnable decompiler
JARs. R27 does **not** supply or download third-party binaries. Users must
obtain independently verified CFR/Vineflower executables themselves and pin
the exact actual SHA-256 of each, not merely assume a version string proves
the contents. Failure leaves the partial **private** output tree for diagnosis
but does not publish a success manifest.

## One-command replay

From a local clone of `Trexzo/SpawnPK-Client`, set `PYTHONPATH` to `src`
(or install the Python package), and supply the three exact JAR pins:

~~~powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m spk_recovery.dual_decompiler_slice `
  'C:\private\client-v309.jar' `
  'C:\private\cfr.jar' `
  'C:\private\vineflower.jar' `
  'C:\private\dual-output-new' `
  --class-entry 'example/Config.class' `
  --original-sha256 '<64-character original-JAR SHA256>' `
  --cfr-sha256 '<64-character CFR-JAR SHA256>' `
  --vineflower-sha256 '<64-character Vineflower-JAR SHA256>'
~~~

Replace example paths and hashes with verified local values. The v309
original JAR fingerprint is already pinned in
`research/v309-field-recovery/frontier.json`; do not edit that accepted
incomplete frontier or guess raw class identities based on filenames.

## Evidence limitations

A dual-decompiler run proves **only** that the tools executed against the
same SHA-pinned input. It does **not** prove recovered Java correctness,
equivalent compilation, runtime behavior, original authorship, accepted
class/member lineage, or a complete source tree. Use the separately merged
R25 `spk_recovery.source_method_parity` gate and existing formal review
requirements for any proposed method parity; the R25 gate itself does
not prove StackMapTable or all Code-subattribute equality.

The original JAR, executable tool JARs, private slice, generated Java and
full logs must **not** be uploaded to public GitHub issues, PRs, workflows
or artifacts. Synthetic-JAR CI exercises the orchestration paths without
sharing actual SpawnPK source. The current blocked configuration owner and
its three field candidates remain unaccepted.
