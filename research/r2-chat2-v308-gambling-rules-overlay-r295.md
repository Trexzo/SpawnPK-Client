# Chat 2 — exact-v308 gambling rules-switched overlay R295

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/X` -> `CLIENT_CLASS_000570` -> `GamblingRulesSwitchedOverlay`
- review: `SEMREVIEW_8ED4761D93BFEC9D10C4`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 overlay contract

`rs/n/c/X` extends the already-reviewed `ClientOverlay` base.

Its visibility predicate requires active interface **59835** and the gambling-interface rule-switched state. In the HIGH render pass it draws the exact message:

- **The rules**
- **have been**
- **switched!**

and animates the sprite owned by the same gambling interface. The timing logic uses the gambling interface's shared timestamp for the 500 ms/1000 ms notification animation/reset cycle.

## Boundary

R295 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
