# Chat 2 — exact-v308 lottery interface R454

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/ao` -> `CLIENT_CLASS_000616` -> `LotteryInterface`
- proposal: `SEMPROP_DDF905EA91C5F5920817`
- review: `SEMREVIEW_CDD6AB67AA1813803C7C`

## Exact identity

Exact surviving presentation includes:

- `Enter lottery`
- `Buy-entry`
- `Lottery title`
- participant-count text
- `The winning pot is currently..`
- `Time until the winner is announced..`
- a formatted hours/minutes/seconds countdown
- `Latest Raffle Winners`

The class is a live CustomInterfaceBuilder constructed by the central custom-interface
registry and has no second domain.

## Boundary

This recovers client presentation only. Entry pricing, ticket consumption, winner
selection, pot computation and rewards remain server authority.

R454 remains non-canonical Chat 2 research only.
