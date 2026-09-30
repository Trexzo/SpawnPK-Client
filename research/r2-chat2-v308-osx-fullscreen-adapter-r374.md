# Chat 2 — R374 duplicate OSXFullScreenAdapter audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R374 retains **no semantic proposal**.

The attempted R374 recovery:

- `rs/A/n`
- `CLIENT_CLASS_000017`
- `OSXFullScreenAdapter`

is an exact duplicate of the already-authoritative R21 proposal:

- proposal: `SEMPROP_DFCFE84222B5E2FC5D19`
- review: `SEMREVIEW_A9CC34F7D0E7034AAAE4`

R21 already records the same exact-v308 superclass, Frame ownership, fullscreen enter/exit
state transitions, registration helper, log strings and historical RuneLite source identity.

The former R374 candidate/review/test are therefore removed. This file preserves the later
source corroboration only and must not participate in semantic ownership or proposal counts.

R374 remains a correction/audit batch only. Chat 2 performs no acceptance or rewrite.
