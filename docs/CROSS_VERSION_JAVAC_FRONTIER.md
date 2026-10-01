# Cross-version javac frontier

`spk-cross-version-javac-frontier` compares two **private**
`spk-javac-diagnostics` reports generated with
`--include-identifiers`.

The comparison is intentionally separate from Source M1 repair. It answers a
narrow question: which compiler failures are reproduced across independently
recovered client versions, and which failures are build-specific?

## Matching

Each private diagnostic is normalized to the Java path below its final
`src/` boundary, then compared as a multiset using:

- normalized source path;
- javac category and raw message;
- symbol kind/value and symbol shape;
- location kind/value.

Line numbers are intentionally excluded so harmless decompiler line movement
does not split an otherwise identical failure family.

The report records exact shared, old-only and new-only counts and category
distributions. By default, raw identifiers and source paths are removed from
the output and replaced by report-local ordinal IDs. Use
`--include-identifiers` only for a private diagnostic artifact.

The report also binds the exact private diagnostic inputs by their
`JAVACDIAG_*` report IDs and raw javac-log SHA-256 values. Each input's
frontier and diagnostic report identities are rederived from its authority
fields before comparison, so stale or internally inconsistent diagnostic JSON
is refused without exposing its raw identifiers.

## Build binding

`spk-javac-build-binding` closes the separate build-identity boundary. It
binds one private diagnostic report to the exact
`clean_project_rebuild_report` that produced it and fails closed unless:

- the binding carries the exact lowercase 40-hex recovery-tooling commit;
- the clean rebuild has the expected build ID;
- its source-authority SHA-256 matches the expected exact client;
- its public diagnostic report ID, frontier ID, raw-input SHA-256 and complete
  aggregate summary exactly match the private diagnostic;
- the recovered workspace and source-tree authority are present;
- project-binary fallback is exactly zero.

The emitted `JAVACBIND_*` report contains the recovery-tooling commit plus
build/source authority IDs, hashes and aggregate state. It never emits source paths, symbols, locations or
raw diagnostic messages.

## Boundary

A high overlap is evidence that a Source M1 defect family generalizes across
versions. It is **not** evidence that either recovered source tree is
release-ready, and this tool does not weaken clean-rebuild, round-trip or
publication gates.

Example:

```powershell
spk-cross-version-javac-frontier `
  .\v307\javac-diagnostic-private.json `
  .\v308\javac-diagnostic-private.json `
  --out .\cross-version-javac-frontier.json
```

## One-command historical/current comparison

After both private Source-M1 runs have produced their identifier-bearing javac
diagnostics, companion clean-rebuild reports, and runner-emitted
`javac-build-binding.json` files:

```powershell
& .\scripts\Invoke-CrossVersionJavacFrontier.ps1
```

The wrapper requires a clean checkout at exact `origin/main`. Each Source-M1
runner emits its own `javac-build-binding.json` at the moment the clean
rebuild frontier is measured. That binding records the exact-main recovery
tooling commit used for that run.

The comparator first requires the v307 and v308 bindings to carry the **same
recovery-tooling commit**. It then independently regenerates both bindings
from the private diagnostics + clean-rebuild reports and requires the
regenerated `JAVACBIND_*` identities to equal the recorded bindings.

The two build authorities remain pinned to:

- exact v307
  `6232bae206846a4ba8d09766a2dee886b69016066a3f50f83b201bf705f93662`;
- exact v308
  `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`.

Only after the same-tooling gate and both binding verifications pass does the
wrapper produce the redacted cross-version frontier report. It then rechecks
that each verified binding's diagnostic report ID, raw-input SHA-256 and
frontier ID are exactly the comparator inputs.

This prevents a newer Source-M1 tooling improvement from being misreported as
a v307/v308 client-version delta. The wrapper's `v307` and `v308` labels
are therefore build-authority-backed **and** same-tooling-bound rather than
inferred from filenames or directory names. The comparison still does not
claim either source tree is release-ready.

## Measured exact v307/v308 checkpoint

The first successful frozen equivalent-tooling private comparison is recorded in:

`fixtures/v307-v308-source-m1-exact-javac-parity-07ed6f9.json`

It is bound to recovery-tooling commit
`07ed6f961fd9ab67439b1d9428446f914bafeabf` and records only redacted
IDs, hashes, and aggregate counts.

Measured result:

- exact v307 and exact v308 both reached
  `JAVACFRONTIER_D028FE33F2F3EC395B94`;
- 350 errors on each build;
- 75 affected files on each build;
- 350 shared errors;
- 0 v307-only errors;
- 0 v308-only errors;
- 100% overlap in both directions;
- `EXACT_FRONTIER_EQUAL=True`;
- redacted comparator report
  `XJAVACFRONTIER_3029D957ED98E41FC96D`.

The raw javac input hashes, recovered source-tree hashes, diagnostic report IDs,
and build-binding IDs remain distinct across the two builds. Exact frontier
equality therefore means equality of the normalized private diagnostic
multisets used by the comparator, not byte identity of the raw logs or source
trees.

The older
`fixtures/v307-v308-source-m1-public-frontier-parity.json` fixture remains
preserved as the historical 405/405 public-only anchor from before the private
comparator had run. It must not be rewritten to impersonate the later 350/350
measurement.

Both recovery releases were still blocked at clean rebuild during the 350/350
measurement. This checkpoint proves cross-version compiler parity at that
tooling authority; it does not satisfy the final release-ready cross-version
gate.

## Deterministic public-safe checkpoint export

A successful `Invoke-CrossVersionJavacFrontier.ps1` run now also invokes
`spk-cross-version-javac-checkpoint` and writes:

`v307-v308-javac-checkpoint.json`

The checkpoint builder does **not** consume either private diagnostic report.
It accepts only:

- the already-redacted `XJAVACFRONTIER_*` comparison report;
- the independently regenerated redacted old/new `JAVACBIND_*` reports;
- the optional `XVERBIN_*` authority for the compared build pair.

Before emitting a checkpoint it independently rederives both `JAVACBIND_*`
identities and the `XJAVACFRONTIER_*` identity from their public authority
fields, requires both bindings to use the same recovery-tooling commit, and
requires each binding's diagnostic report ID, raw-input SHA-256 and frontier
ID to match the side of the comparator it claims to bind.

The exporter also refuses any comparator family containing `source_path`,
`message`, `symbol`, or `location`, even if the input incorrectly claims
`identifiers_included=false`.

The emitted `XJAVACCHECKPOINT_*` artifact contains only build/source authority
hashes and IDs, compiler aggregate state, and the redacted comparator summary.
It does not declare either recovery release ready. Its purpose is to eliminate
manual transcription when promoting an exact-local measurement into a reviewed
public checkpoint.
