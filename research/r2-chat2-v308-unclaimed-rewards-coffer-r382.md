# Chat 2 — unclaimed rewards coffer interface R382

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/u` -> `CLIENT_CLASS_000674` -> `UnclaimedRewardsCofferInterface`
- proposal: `SEMPROP_1B7AC87DA5272CB44932`
- review: `SEMREVIEW_07F093E57DC3684C9E66`

## Exact identity

The class builds root **42100** and preserves:

`<img=131> Coffer of Unclaimed Rewards & Prizes <img=131>`

The interface owns:

- Remove 1 / Remove 5 / Remove 10 / Remove All;
- bank-style inventory storage;
- deposit-to-inventory / deposit-to-bank controls;
- `This coffer usually holds contest prizes, event rewards, etc.`;
- `(Especially if you were offline when you received them)`.

The specific name keeps this interface distinct from R113 `CofferClaimOverlay` and the
mail/coffer action-prompt transport.

## Boundary

R382 names the exact client presentation surface only. Reward-delivery/storage authority
remains server-side and is not inferred.

R382 remains non-canonical.
