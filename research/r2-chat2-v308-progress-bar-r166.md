# Chat 2 — exact-v308 ThinProgressBar source recovery R166

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R166 remains a one-class non-canonical review. R228 corrects its earlier descriptive
`ProgressBar` name after the wider RuneLite UI source audit identified both upstream
`ProgressBar` and `ThinProgressBar` as separate classes.

## Corrected deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- corrected review ID: `SEMREVIEW_9C381CF759C8D9528363`
- corrected proposal ID: `SEMPROP_8C18220DA038113C69E2`
- field/method proposals: **0**

## Stable ID

`rs/ui/components/y` -> `CLIENT_CLASS_001093` -> `ThinProgressBar`

RuneLite source at `67496933120316f33bfc480f1a1c67c897cb82b9` matches exact v308 field-for-field and behavior-for-behavior:
two integer progress values, maximum clamped to at least one, a fixed four-pixel component
height, percentage calculation and the same filled/unfilled paint routine.

The original R166 behavioral analysis was correct; only the source noun was too broad.
Old proposal `SEMPROP_1253E4C2811A59A9407C` / review
`SEMREVIEW_DD66FE413150F4F4C6A4` are superseded by this corrected review.

R228 assigns the distinct upstream `ProgressBar` source name to its actual exact-v308
owner `rs/ui/components/v`.

## Acceptance boundary

Chat 2 does not promote corrected R166. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_9C381CF759C8D9528363`.
