# Chat 2 — exact-v308 legacy sequence / spot-animation config loaders R62

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R62 is a separate non-canonical class-only semantic review batch for two explicit legacy
definition override loaders.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_142F0F9C2756A947D982`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/y` -> `CLIENT_CLASS_001121`
- `rs/z` -> `CLIENT_CLASS_001125`

R28 already recovers:

- `rs/d/a` -> `SequenceDefinition`
- `rs/d/x` -> `SpotAnimationDefinition`

## `rs/y` -> `LegacySequenceConfigLoader`

The class accepts a `SequenceDefinition[]`, clones the array, then reads the hard-coded
legacy file:

`configs/old_a.dat`

The text format uses `anim` sections plus `arr1:`, `arr2:` and `other:` records.
Those values are written directly into fields on the selected SequenceDefinition.

The semantic role is therefore an explicit legacy sequence-definition override loader.

## `rs/z` -> `LegacySpotAnimationConfigLoader`

This class accepts `SpotAnimationDefinition[]` and reads:

`configs/old_g.dat`

The text format uses `graphic`, `data:`, `arr1:` and `arr2:` records. Parsed values
overwrite the selected spot-animation definition's model/sequence/render metadata and
array fields; the linked SequenceDefinition is rebound from the decoded sequence id.

The semantic role is therefore an explicit legacy spot-animation / graphic-definition
override loader.

## Naming boundary

These are semantic recovery names. The file names and exact target definition types are
primary evidence; R62 does not claim additional original-source identifiers.

## Acceptance boundary

Chat 2 does not promote R62. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_142F0F9C2756A947D982`.
