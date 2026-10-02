# Chat 2 — R492 duplicate Material Tabs audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R492 retains **no semantic proposal**.

The exact-v308/source audit independently recovered:

- `rs/ui/components/b/a` -> `MaterialTab`
- `rs/ui/components/b/e` -> `MaterialTabGroup`

However, R230 already owns both exact classes with the same proposal identities and the same
review ID:

- `MaterialTab`: `SEMPROP_6D79F389F40FB65CC55F`
- `MaterialTabGroup`: `SEMPROP_E484B991F3F329953FBC`
- R230 review: `SEMREVIEW_5789FBA171B6FB2F21B5`

The R492 candidate/review/test artifacts are therefore removed. The later source
corroboration is retained only as this audit note.

R492 is a correction-only batch.
