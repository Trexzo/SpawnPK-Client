# Chat 2 — exact-v308 RuneLite UI component source recovery R228

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R228 adds seven exact RuneLite UI source identities and atomically corrects the older R166
progress component noun.

## Deterministic review result

- candidate classes: **7**
- resolved proposals: **7**
- unresolved: **0**
- review ID: `SEMREVIEW_C1EFA86377CACA7467C3`
- field/method proposals: **0**

## Stable IDs

- `rs/ui/a/d` -> `CLIENT_CLASS_001020` -> `InfoBoxComponent`
- `rs/ui/components/b` -> `CLIENT_CLASS_001059` -> `ColorJButton`
- `rs/ui/components/f` -> `CLIENT_CLASS_001068` -> `DimmableJPanel`
- `rs/ui/components/i` -> `CLIENT_CLASS_001074` -> `FlatTextField`
- `rs/ui/components/r` -> `CLIENT_CLASS_001084` -> `MouseDragEventForwarder`
- `rs/ui/components/u` -> `CLIENT_CLASS_001089` -> `PluginErrorPanel`
- `rs/ui/components/v` -> `CLIENT_CLASS_001090` -> `ProgressBar`

All seven match RuneLite source at `67496933120316f33bfc480f1a1c67c897cb82b9` through distinctive class hierarchy, field
layout, constants and method bodies.

## R166 source-name correction

The wider source audit proves that RuneLite contains two distinct components:

- exact `rs/ui/components/v` is `ProgressBar`;
- exact `rs/ui/components/y` is `ThinProgressBar`.

R166 had previously assigned the descriptive name `ProgressBar` to the latter before the
source pair was recovered. This commit atomically rewrites R166 to `ThinProgressBar` with
corrected proposal `SEMPROP_8C18220DA038113C69E2` and review
`SEMREVIEW_9C381CF759C8D9528363`, then assigns `ProgressBar` to its actual source owner
through R228.

No retained proposal count changes from the R166 correction.

## Acceptance boundary

Chat 2 does not promote R228 or corrected R166. Main/Core may accept only through explicit
semantic acceptance bound to the corresponding corrected review IDs.
