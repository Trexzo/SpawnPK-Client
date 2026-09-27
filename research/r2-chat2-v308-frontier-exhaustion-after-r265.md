# Chat 2 — exact-v308 semantic frontier exhaustion after R265

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

This note records negative semantic findings from a direct exact-v308 bytecode audit after the
retained R244-R265 frontier. Its purpose is to prevent later Chat 2 continuations from repeatedly
rediscovering compiler artifacts and empty shells as if they were new semantic targets.

## rs/ui/components

Every substantive class owner in `rs/ui/components/**` is already represented by a retained
Chat 2 semantic review.

The only owners with no retained review are:

- `rs/ui/components/h`
- `rs/ui/components/t`

Exact bytecode:

- `rs/ui/components/h` is an empty package-private shell with no fields, methods, strings, or
  behavior.
- `rs/ui/components/t` contains only a synthetic `int[]` enum switch map over
  `rs/ui/components/e`, populated in `<clinit>` behind `NoSuchFieldError` guards.

Neither receives a semantic proposal.

## rs/runelite/a

The geometry/coordinate package is also semantically exhausted under the current review set.

Only these exact owners lack retained reviews:

- `rs/runelite/a/k`
- `rs/runelite/a/n`

Both are empty package-private shells with no fields, methods, strings, or executable behavior.

Neither receives a semantic proposal.

## rs/l/f top-level overlay/render package

Among top-level `rs/l/f/{a..n}` owners, the only unreviewed exact classes are:

- `rs/l/f/d`
- `rs/l/f/h`
- `rs/l/f/k`
- `rs/l/f/n`

All four are compiler-generated enum switch-map helpers over reviewed `rs/l/f/l`.
They contain only synthetic `int[]` tables populated in `<clinit>` with
`NoSuchFieldError` guards.

None receives a semantic proposal.

## Self-identifying literal pass

A whole-`rs/**` exact-v308 scan found 41 classes with generated/self-identifying
`toString`-style literals. Every one of those exact owners is already represented in the
current Chat 2 review corpus.

The audit deliberately used decoded classfile constants / `javap -v` for final identity checks.
Raw `strings` output must not be treated as exact Java string text because printable classfile
UTF-8 length bytes can appear as false prefixes (for example raw bytes can display
`kNavigationButton` while the decoded BootstrapMethods constant is exactly
`NavigationButton(...)`).

## Boundary

This is research-only negative evidence.

- no semantic candidate batch is created;
- no class is accepted or renamed;
- no canonical state is changed;
- future work should widen to a different exact-v308 package or source-fingerprint family rather
  than revisit the exclusions above without new evidence.
