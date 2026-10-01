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

- the clean rebuild has the expected build ID;
- its source-authority SHA-256 matches the expected exact client;
- its public diagnostic report ID, frontier ID, raw-input SHA-256 and complete
  aggregate summary exactly match the private diagnostic;
- the recovered workspace and source-tree authority are present;
- project-binary fallback is exactly zero.

The emitted `JAVACBIND_*` report contains only build/source authority IDs,
hashes and aggregate state. It never emits source paths, symbols, locations or
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
diagnostics and companion clean-rebuild reports:

```powershell
& .\scripts\Invoke-CrossVersionJavacFrontier.ps1
```

The wrapper requires a clean checkout at exact `origin/main`. Before
comparison it independently creates:

- `v307-javac-build-binding.json`, pinned to exact v307
  `6232bae206846a4ba8d09766a2dee886b69016066a3f50f83b201bf705f93662`;
- `v308-javac-build-binding.json`, pinned to exact v308
  `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`.

Only after both bindings pass does it produce the redacted cross-version
frontier report. It then rechecks that each binding's diagnostic report ID,
raw-input SHA-256 and frontier ID are exactly the comparator inputs.

This means the wrapper's `v307` and `v308` labels are authority-backed
rather than inferred from filenames or directory names. The comparison still
does not claim either source tree is release-ready.
