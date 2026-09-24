# Chat 2 — exact-v308 interface arrow overlay / ScriptPacket 24 R138

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R138 resolves the previously withheld ScriptPacket 24 family without inventing a tutorial,
onboarding or coach-mark domain that does not survive in exact v308.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_53E67568D36705B68452`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/a/i/b` -> `CLIENT_CLASS_000470` -> `InterfaceArrowOverlay`
- `rs/l/f/a/i/d` -> `CLIENT_CLASS_000472` -> `InterfaceArrowPacketHandler`
- `rs/l/f/a/i/e` -> `CLIENT_CLASS_000473` -> `InterfaceArrowDirection`
- `rs/l/f/a/i/g` -> `CLIENT_CLASS_000475` -> `InterfaceArrowSection`

## Exact arrow identity

The direction enum survives exactly as:

- `LEFT`;
- `RIGHT`;
- `UP`;
- `DOWN`.

Each direction returns one exact Client sprite.

Client initialization loads those four sprites from:

- `orbs/arrow`;
- `orbs/arrow 2`;
- `orbs/arrow 3`;
- `orbs/arrow 4`.

The overlay renders the selected arrow intermittently from the live Client frame counter,
giving a blinking pointer presentation.

## Widget anchoring

The overlay can be created in two exact ways.

The first accepts:

- overlay/layer integer;
- direction;
- x offset;
- y offset.

The second accepts one exact interface widget ID.

That helper reads `rs/n/e.H[widgetId]`, inspects the widget sprite dimensions and derives an
offset before creating the arrow overlay against that widget.

This is the evidence that fixes `Interface` in the readable name: the system is explicitly
able to point at the client's interface widget graph rather than only arbitrary world
coordinates.

## Exact section enum

The paired enum survives exactly as:

- `ACHIEVEMENT`;
- `EQUIPMENT`;
- `INVENTORY`;
- `MAGIC`;
- `MISC`;
- `SETTINGS`.

These are stored as live state on the same arrow subsystem.

R138 deliberately calls this `InterfaceArrowSection`, not TutorialSection or GuideSection,
because the binary proves the interface-section tags but not the higher-level feature that
requests them.

## ScriptPacket 24

R115 registers `rs/l/f/a/i/d` as exact ScriptPacket **24**.

Its implemented selectors are completely coherent:

- selector **0** clears/removes the current arrow overlay;
- selector **1** creates the arrow with packet layer, direction and x/y offsets, plus one
  boolean presentation mode;
- selector **3** changes only the exact interface-section enum;
- selector **4** anchors the current arrow to one packet-specified interface widget ID.

No implemented selector mutates unrelated gameplay or Client state.

## Naming boundary

All four names are **0.999**.

The exact nouns available in v308 are arrow resources, direction constants, interface-widget
anchoring and interface-section constants. R138 stays at that descriptive boundary and does
not infer a tutorial/onboarding feature name.

R138 remains class-only.

## Residual ScriptPacket boundary

After R138, the deliberately unnamed ScriptPacket frontier is reduced from six IDs to five:

- **8** — combat-stat-like overlay, higher-level feature noun still not proven;
- **23** — timed three-string notification queue with no domain noun;
- **27** — twelve-string HUD/overlay with no self-identifying domain;
- **32** — mixed handler with no honest single subsystem noun;
- **33** — 30700-series interface controller whose owning feature remains unidentified.

## Acceptance boundary

Chat 2 does not promote R138. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_53E67568D36705B68452`.
