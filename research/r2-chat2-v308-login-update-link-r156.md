# Chat 2 — exact-v308 login update-link mouse handler R156

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R156 is a separate non-canonical class-only review for the input-side handler paired with
R155 `LoginUpdateFetcher`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_A573AD6C6FAF32749506`
- field/method proposals: **0**

## Stable ID

`rs/l/d/d` -> `CLIENT_CLASS_000395` -> `LoginUpdateLinkMouseHandler`

## Exact LoginScreen ownership

R11 already recovers `rs/l/d/c` as `LoginScreen`.

Inside exact-v308 `LoginScreen.run()`:

1. the launcher JFrame is obtained;
2. `new rs/l/d/d(this)` is constructed;
3. that exact instance is installed through `JFrame.addMouseListener`.

The handler therefore belongs to LoginScreen interaction rather than a generic global browser
or launcher utility.

## Complete behavior

`rs/l/d/d` extends `java.awt.event.MouseAdapter`.

Its only overridden input method is `mousePressed(MouseEvent)`.

The method:

- returns if the LoginScreen has no active Client;
- ignores clicks while the relevant login-state flag is set;
- accepts only the fixed screen rectangle:
  - **x 10..132**
  - **y 460..485**
- on a valid click, calls `Client.f(...)` with the exact URL:

`https://spawnpk.net/forums/index.php?/forum/10-updates/`

There are no unrelated actions.

## R155 family join

R155 independently recovers adjacent `rs/l/d/e` as `LoginUpdateFetcher`.

That thread:

- is also directly owned by LoginScreen;
- opens the same exact SpawnPK updates-forum URL;
- parses latest update headlines/links;
- writes the resulting display text back into LoginScreen.

R156 therefore supplies the complementary input-side action for the same exact login update
surface: R155 fetches the update presentation and R156 opens its source page when the user
clicks the Latest Update region.

## Naming boundary

`LoginUpdateLinkMouseHandler` is **0.999**.

The name is deliberately behavioral and narrow. It does not claim an original developer
identifier; it records the exact owner, input mechanism and update-link responsibility proven
by current bytecode.

## Acceptance boundary

Chat 2 does not promote R156. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_A573AD6C6FAF32749506`.
