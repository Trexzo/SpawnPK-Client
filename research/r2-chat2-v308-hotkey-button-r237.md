# Chat 2 — exact-v308 RuneLite HotkeyButton source recovery R237

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_4CD0295E3AAEF38D97C5`
- field/method proposals: **0**

## Stable ID

- `rs/s/b/i` -> `CLIENT_CLASS_000869` -> `HotkeyButton`

## Exact source identity

Exact v308 extends `JButton`, owns one `Keybind`, and reproduces RuneLite's
`HotkeyButton` behavior:

- disable focus traversal keys so Tab can be bound;
- use the client default font at 12pt;
- normalize null to `Keybind.NOT_SET`;
- update button text from the keybind's `toString()`;
- left-mouse release resets the binding to `NOT_SET`;
- key press constructs `ModifierlessKeybind` when configured modifierless,
  otherwise ordinary `Keybind`.

The anonymous listener classes `rs/s/b/j` and `rs/s/b/k` are compiler artifacts of this
button behavior and remain unnamed.

## Acceptance boundary

Chat 2 does not promote R237. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_4CD0295E3AAEF38D97C5`.
