# Chat 2 — login hover sprite control R351

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/g` -> `CLIENT_CLASS_000496` -> `LoginHoverSpriteControl`
- proposal: `SEMPROP_66072B4F63BA997B2DC2`
- review: `SEMREVIEW_091E1BB8883267E83A45`

## Parent ownership

The only exact-v308 external class reference is R11 `LoginScreen` (`rs/l/d/c`).

LoginScreen constructs many instances of `rs/l/g` with visual pairs including:

- `textbox` / `textbox 2`
- `button` / `button 2`
- `box` / `box 2` / `box 3`

That proves this is a reusable login presentation primitive rather than a control dedicated
to one particular action.

## Exact behavior

The class owns:

- live `Client`;
- base `rs/l/F` sprite;
- hover/overlay `rs/l/F` sprite;
- current alpha;
- maximum alpha;
- alpha step;
- optional frame-delay counter;
- hover/animation booleans.

Its hit-test compares `Client.hP/hQ` with the supplied draw coordinate plus the base
sprite width/height.

Rendering:

1. draws the base sprite;
2. stores current hover state;
3. advances or reverses alpha in fixed steps;
4. draws the secondary sprite using that alpha.

LoginScreen also queries the hit-test/current-alpha state for interaction decisions.

## Naming boundary

The name intentionally uses `Control`, not `Button`, because the same exact class is
used for textbox, button and box assets.

R351 remains non-canonical semantic research only.
