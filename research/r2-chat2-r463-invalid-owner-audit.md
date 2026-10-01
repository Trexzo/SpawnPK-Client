# Chat 2 — R463 duplicate/invalid-owner audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R463 retains **no semantic proposal**.

The attempted `rs/gui/c` button-shaper proposal was invalid for two independent reasons.

### 1. Stable-ID collision

The attempted R463 fixture assigned:

- `CLIENT_CLASS_000203`

But R9 already owns that canonical stable ID as:

- `rs/gui/a/a`
- `GpuSettingsPanel`
- proposal `SEMPROP_D32EC38E28B9C962D7FA`
- review `SEMREVIEW_F015AA6B979CF43ECBE6`

The repository-wide uniqueness test correctly rejected R463 with:

`duplicate class stable_id CLIENT_CLASS_000203: R9 and R463`

This proves the R463 stable ID was inferred incorrectly and must not be retained.

### 2. Initial semantic-name collision

The first R463 attempt also reused `RuneLiteSquareButtonShaper`, already owned by R177
for a different exact-v308 class. Renaming the proposed class did not repair the invalid
canonical target identity.

## Exact bytecode observation retained only as research

`rs/gui/c` is constructed by a RuneLite/Substance skin path and overrides a button-shaper
corner-radius method to return `0.0f`, producing square corners.

That observation may be useful in future lineage work, but without the correct canonical
stable ID it is not eligible for a semantic proposal in Chat 2.

## Boundary

R463 is a zero-retained audit only.

No candidate JSON, semantic-review JSON or deterministic semantic test remains for R463.
