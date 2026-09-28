# Chat 2 — exact-v308 SyncMode correction note

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

This note records a correction discovered while preparing a would-be R93 GPU enum batch.

## Why no R93 semantic review is retained

R15 already owns all three exact-v308 GPU enum coordinates:

- `rs/k/a/a` -> `CLIENT_CLASS_000315` -> `AntiAliasingMode`
- `rs/k/a/b` -> `CLIENT_CLASS_000316` -> `ColorBlindMode`
- `rs/k/a/c` -> `CLIENT_CLASS_000317` -> `VsyncMode`

A second semantic review for the same owners would duplicate existing Chat 2 evidence and
break the deliberate no-overlap gate used by later review batches.

The temporary R93 candidate/review/test files were therefore removed rather than weakening
that invariant.

## New evidence: `VsyncMode` -> upstream-exact `SyncMode`

The first two R15 names remain strongly corroborated.

For `rs/k/a/c`, exact v308 preserves the enum constants:

- `OFF`
- `ON`
- `ADAPTIVE`

R15 correctly identified the role as the GPU configuration's vsync mode, but used the
descriptive semantic name `VsyncMode`.

Current RuneLite source preserves this exact enum as the nested
`GpuPluginConfig.SyncMode`, with the identical `OFF`, `ON`, `ADAPTIVE` values and
the GPU config method `vsyncMode()`.

Therefore the stronger historical/source-name candidate for
`CLIENT_CLASS_000317` is **`SyncMode`**, not `VsyncMode`.

## Boundary

This correction is now folded directly into R15 on the Chat 2 branch: `CLIENT_CLASS_000317` remains the same stable owner, while its reviewed semantic name is `SyncMode`. The corrected R15 review ID is `SEMREVIEW_9F64F82DCFBF8C7A97EF`.

No duplicate semantic batch was created and Chat 2 still performs no canonical acceptance.
