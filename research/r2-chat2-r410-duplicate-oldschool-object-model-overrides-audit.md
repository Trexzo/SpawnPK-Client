# Chat 2 — R410 duplicate OldSchool override correction

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R410 retains **no semantic proposal**.

The attempted proposal:

- `rs/c/a/a`
- `CLIENT_CLASS_000080`
- attempted name: `OldSchoolItemDefinitionOverrides`

was rejected after reconciling the current live semantic corpus.

R350 already owns the exact coordinate and stable ID:

- `rs/c/a/a`
- `CLIENT_CLASS_000080`
- `OldSchoolObjectModelOverrides`
- proposal: `SEMPROP_AA02B66A159291F2A957`
- review: `SEMREVIEW_CDE25DFEBEFB618396DD`

## Why R350 is authoritative

Direct reinspection confirms the R350 interpretation:

- the target is the R28 `ObjectDefinition` type;
- the call is gated by the exact `OLDSCHOOL` definition mode;
- the override table mutates the object definition model-id array;
- the large ID switch does not establish item-definition behavior.

The R410 item-definition interpretation was therefore a target-type misclassification.

## Cleanup boundary

The attempted R410 candidate JSON, review JSON and deterministic test are removed.

R410 is a correction note only and creates no acceptance/rewrite authority.
