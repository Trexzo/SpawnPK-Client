# Chat 2 — exact-v308 BankInterface R269

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/n/c/h` -> `CLIENT_CLASS_000661` -> `BankInterface`
- review: `SEMREVIEW_8BECE6D2B37DF2C71AB2`
- unresolved: **0**
- field/method proposals: **0**

## Exact-v308 identity

The class extends the interface-builder base and constructs the UI headed:

`The Bank of SpawnPK`

Its complete live surface is bank-specific:

- nine bank tabs plus create/collapse/select behavior;
- item search;
- repairs;
- potion decanting;
- placeholders;
- insert/swap modes;
- item/note withdrawal modes;
- deposit carried items;
- deposit worn items;
- deposit pet;
- Withdraw 1 / 5 / 10 / 14 / X / All / All But One;
- bank content/currency filtering controls.

The exact resource family is equally specific:

- `bank/BANK`
- `bank/TAB`
- `bank/SEP`

The class also owns the shared bank-tab sprite objects and live bank widget-id mutation paths.

## Naming boundary

`BankInterface` is a descriptive exact-behavior name, not a claim that the original
developer identifier survived obfuscation.

A full prior-review scan before commit found no existing class owner or semantic-name
collision.

## Acceptance boundary

R269 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
