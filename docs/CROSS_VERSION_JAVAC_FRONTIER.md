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

## Boundary

A high overlap is evidence that a Source M1 defect family generalizes across
versions. It is **not** evidence that either recovered source tree is
release-ready, and this tool does not weaken clean-rebuild, round-trip or
publication gates.

Example:

```powershell
spk-cross-version-javac-frontier `
  .\\v307\\javac-diagnostic-private.json `
  .\\v308\\javac-diagnostic-private.json `
  --out .\\cross-version-javac-frontier.json
```

## One-command historical/current comparison

After both private Source-M1 runs have produced their identifier-bearing javac
diagnostic reports, the repository wrapper keeps the final output redacted:

```powershell
& .\scripts\Invoke-CrossVersionJavacFrontier.ps1
```

Its defaults consume the historical v307 backtest diagnostic and the current
v308 Source-M1 exact-local diagnostic from their standard desktop output
locations. The wrapper requires a clean checkout at exact `origin/main` and
refuses any final report with `identifiers_included=true`.

The wrapper only compares the two supplied compiler frontiers. It does not
claim that either input was produced at the same repository commit; provenance
for each underlying Source-M1 run remains the responsibility of that run's
own authority/release artifacts.
