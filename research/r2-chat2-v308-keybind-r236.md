# Chat 2 — exact-v308 RuneLite keybind source recovery R236

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_909D55E99BED7DFC5582`
- field/method proposals: **0**

## Stable IDs

- `rs/s/b/l` -> `CLIENT_CLASS_000872` -> `Keybind`
- `rs/s/b/m` -> `CLIENT_CLASS_000873` -> `ModifierlessKeybind`

## Exact source identity

Exact v308 `rs/s/b/l` preserves the complete RuneLite `Keybind` value type:

- modifier-to-key-code BiMap and combined modifier mask;
- `NOT_SET`, `CTRL`, `ALT`, `SHIFT`;
- keyCode/modifiers fields;
- integer and KeyEvent constructors;
- modifier-key normalization;
- press/release matching;
- `toString`, `equals`, `hashCode`;
- modifier lookup helper.

Exact v308 `rs/s/b/m` extends it and preserves RuneLite
`ModifierlessKeybind` exactly: the same constructors and
`matches(KeyEvent)` delegation to the protected matcher with modifier ignoring enabled.

## Acceptance boundary

Chat 2 does not promote R236. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_909D55E99BED7DFC5582`.
