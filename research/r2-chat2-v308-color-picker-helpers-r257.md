# Chat 2 — exact-v308 color-picker helper family R257

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/ui/components/a/b` -> `CLIENT_CLASS_001039` -> `ColorPanelDragListener`
- `rs/ui/components/a/c` -> `CLIENT_CLASS_001040` -> `ColorPanelMouseListener`
- `rs/ui/components/a/f` -> `CLIENT_CLASS_001043` -> `ColorValueDocumentFilter`
- `rs/ui/components/a/g` -> `CLIENT_CLASS_001044` -> `ColorValueFocusListener`
- `rs/ui/components/a/i` -> `CLIENT_CLASS_001046` -> `ColorValueSliderDragListener`
- `rs/ui/components/a/j` -> `CLIENT_CLASS_001047` -> `ColorValueSliderMouseListener`
- `rs/ui/components/a/l` -> `CLIENT_CLASS_001049` -> `HuePanelDragListener`
- `rs/ui/components/a/m` -> `CLIENT_CLASS_001050` -> `HuePanelMouseListener`
- `rs/ui/components/a/p` -> `CLIENT_CLASS_001053` -> `RecentColorClickListener`
- `rs/ui/components/a/r` -> `CLIENT_CLASS_001055` -> `PreviewColorSelectListener`
- `rs/ui/components/a/s` -> `CLIENT_CLASS_001056` -> `HexColorDocumentFilter`
- `rs/ui/components/a/t` -> `CLIENT_CLASS_001057` -> `ColorPickerFocusListener`
- `rs/ui/components/a/u` -> `CLIENT_CLASS_001058` -> `ColorPickerWindowCloseListener`
- review: `SEMREVIEW_B852479D96D12B5DCBE2`
- unresolved: **0**
- field/method proposals: **0**

## Exact family boundary

R179 already recovered the principal RuneLite-derived color-picker components:
`ColorPanel`, `ColorPickerManager`, `ColorValuePanel`, `ColorValueSlider`,
`HuePanel`, `PreviewPanel`, `RecentColors`, and `RuneliteColorPicker`.

R257 names only their still-obfuscated live UI adapters.

- ColorPanel helpers forward X/Y drag/press/release coordinates into color selection.
- ColorValuePanel's document filter enforces the exact 0..255 component range; its focus listener commits the edited value.
- ColorValueSlider helpers forward X drag/press/release positions into slider updates.
- HuePanel helpers forward Y drag/press/release positions into hue updates.
- RecentColorClickListener forwards one stored Color to its Consumer.
- PreviewColorSelectListener applies one PreviewPanel color into RuneliteColorPicker and optionally copies alpha.
- HexColorDocumentFilter strips `#`/`0x`, validates exact hex-color text and refuses invalid edits.
- ColorPickerFocusListener commits picker text/color state on focus loss.
- ColorPickerWindowCloseListener commits final state, calls the optional consumer, stores changed recent colors, and clears the active picker in ColorPickerManager.

## Naming boundary

R257 uses descriptive exact-behavior names for helper/adaptor classes. No anonymous/helper
original identifier is claimed.

## Acceptance boundary

R257 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
