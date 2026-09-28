# Chat 2 — exact-v308 LoginScreen state enum R157

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R157 is a separate non-canonical class-only review for the exact two-state enum owned by
the recovered LoginScreen.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_2FFAECB55B981427C7BA`
- field/method proposals: **0**

## Stable ID

`rs/l/d/c$a` -> `CLIENT_CLASS_000394` -> `LoginScreenState`

## Exact enum identity

The class is a Java enum with exactly two surviving values:

- `LOADING_ASSETS`
- `LOGIN_PROMPT`

These are not inferred labels; they survive directly in exact-v308 bytecode.

## LoginScreen ownership

R11 already reviews enclosing `rs/l/d/c` as `LoginScreen`.

LoginScreen stores one `rs/l/d/c$a` field as its active state. The constructor initializes
that field to `LOADING_ASSETS`, and a dedicated setter replaces it with another enum value.

No unrelated class owns the state.

## Behavioral partition

Exact LoginScreen rendering/input code branches directly on the enum.

When state is `LOADING_ASSETS`:

- the asset-loading/progress presentation is rendered;
- the loading-frame/progress graphics are updated;
- login-prompt interaction is not used.

When state is `LOGIN_PROMPT`:

- LoginScreen enables prompt-region interaction checks;
- login-input hover/cursor state is updated;
- the normal interactive login prompt path is active.

The enum therefore represents the high-level state of LoginScreen rather than a generic
loading flag or cosmetic mode.

## Naming boundary

`LoginScreenState` is **0.999**.

The name is descriptive but directly constrained by exact surviving enum values and exclusive
ownership by the already-reviewed LoginScreen.

## Acceptance boundary

Chat 2 does not promote R157. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_2FFAECB55B981427C7BA`.
