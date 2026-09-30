# Chat 2 — exact-v308 Player IP / UID Matcher interface R439

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/U` -> `CLIENT_CLASS_000567` -> `PlayerIpUidMatcherInterface`
- proposal: `SEMPROP_B3F6742C1CD5AC29C3BD`
- review: `SEMREVIEW_C279A940BDF04AF0CC6B`

## Exact screen identity

The builder extends R436 `CustomInterfaceBuilder` and creates root widget **51200**.

Its own title is:

`Player IP / UID Matcher`

## Exact match/moderation surface

The interface builds:

- a 100-row match result list;
- online / online-non-match state presentation;
- per-row `Action` controls;
- `IP Address: ...` ban state;
- `UID: ...` ban state;
- geolocation state;
- `Ban all`;
- `Ban this IP/UID`;
- ordering by total matches;
- ordering by most recent;
- `Search new name`;
- back navigation.

## Reverse references

Outside this class, exact v308 references `rs/n/c/U` only from R436
`CustomInterfaceRegistry`.

## Boundary

This names only the client-side interface. It does not claim details of server-side
identity correlation, geolocation, moderation policy or enforcement behavior.

R439 remains non-canonical semantic research only.
