# Chat 2 — exact-v308 overlay utility and drag hotkey R215

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R215 is a separate non-canonical class-only review for two remaining non-synthetic
overlay-framework helpers.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_48B9458A7F27AEBC8AD9`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/j` -> `CLIENT_CLASS_000491` -> `OverlayDragHotkeyListener`
- `rs/l/f/m` -> `CLIENT_CLASS_000494` -> `OverlayUtil`

## OverlayDragHotkeyListener

R20 already fixes `rs/A/i` as `HotkeyListener`.

`rs/l/f/j` extends that exact class and is constructed only by R213
`OverlayRenderer`.

The constructor receives the keybind supplier from R17 `RuneLiteConfig.x()`.
That exact config method carries:

- key: `dragHotkey`;
- name: `Drag Hotkey`;
- description: `Configures the hotkey used to drag UI elements around`.

On press, the listener sets the renderer's drag-hotkey state true.

On release, it clears the flag and invokes the renderer's drag-state reconciliation path.

The owner, config metadata and state mutation all independently agree on the drag-hotkey
listener identity.

## OverlayUtil

`rs/l/f/m` is stateless apart from shared static drawing constants.

It provides static helpers for:

- drawing a Shape with the standard overlay border stroke;
- drawing/filling Shapes with outline + fill colors;
- a reduced-alpha fill variant;
- rendering outlined text at a RuneLite point;
- selecting the standard border Stroke;
- adjusting a stacking rectangle according to R160 `OverlayPosition`;
- calculating position anchor offsets from `OverlayPosition` and `Dimension`.

Exact-v308 references to the class are confined to:

- R213 `Overlay`;
- R213 `OverlayRenderer`;
- itself.

Overlay delegates shared shape/text helpers to it. OverlayRenderer delegates fixed-position
layout calculations to it.

That makes it a framework utility rather than a feature renderer.

## Withheld remainder

The other still-unreviewed top-level `rs/l/f/*` classes in this immediate seam are
compiler-generated enum-switch helpers. They remain unnamed.

R215 therefore adds only the two non-synthetic helpers with independent semantic evidence.

## Naming boundary

Both names are descriptive exact-behavior recovery at confidence **0.999**.

R215 adds no field or method proposals and performs no semantic acceptance.

## Acceptance boundary

Chat 2 does not promote R215. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_48B9458A7F27AEBC8AD9`.
