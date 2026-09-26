# Chat 2 — exact-v308 GameState enum R159

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R159 is a separate non-canonical class-only review for the client/RuneLite game-state enum.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_3BB4E2A255F6BCA26229`
- field/method proposals: **0**

## Stable ID

`rs/runelite/a/c` -> `CLIENT_CLASS_000811` -> `GameState`

The stable ID is derived directly from Core's baseline rule: exact-v308 `rs/` classes are
sorted by internal name before deterministic CLIENT_CLASS IDs are assigned.

## Exact enum surface

The enum preserves these exact constants and numeric ids:

- `UNKNOWN` -> **-1**
- `STARTING` -> **0**
- `LOGIN_SCREEN` -> **10**
- `LOGIN_SCREEN_AUTHENTICATOR` -> **11**
- `LOGGING_IN` -> **20**
- `LOADING` -> **25**
- `LOGGED_IN` -> **30**
- `CONNECTION_LOST` -> **40**
- `HOPPING` -> **45**

It exposes deterministic id -> enum lookup and enum -> id access.

## Exact surviving semantic noun

The strongest evidence is not merely the state constants.

Exact-v308 `rs/runelite/events/GameStateChanged` contains:

- field `gameState` of type `rs/runelite/a/c`;
- `getGameState()`;
- `setGameState(rs/runelite/a/c)`.

That surviving API fixes the noun directly as **GameState**.

## Runtime transition evidence

`Client` constructs and posts `GameStateChanged` events using this enum during real
client lifecycle transitions.

Exact examples include events for:

- `LOADING`;
- `LOGIN_SCREEN`;
- `LOGGING_IN`.

The same enum is consumed across Client, login and plugin/UI runtime code, so it is a shared
top-level client state contract rather than a local plugin status enum.

## Naming boundary

`GameState` is **0.999**.

The name is effectively preserved by the exact public event field/accessor names plus the
canonical state constant set. Chat 2 still records it as a non-canonical proposal rather than
claiming source recovery beyond the surviving evidence.

## Acceptance boundary

Chat 2 does not promote R159. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_3BB4E2A255F6BCA26229`.
