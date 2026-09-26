# Chat 2 — exact-v308 RuneLite color-picker source recovery R179

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

External source corroboration:

`runelite/runelite@7e6d9ac8138be3aa165f88da527ad5a5e6a5d21b`

R179 is a separate non-canonical class-only review for the named RuneLite color-picker
classes embedded in exact v308.

The upstream source is used only to recover original component names after exact structural
matching. It does not replace the pinned v308 JAR as runtime authority.

## Deterministic review result

- candidate classes: **8**
- resolved proposals: **8**
- unresolved: **0**
- review ID: `SEMREVIEW_EDB429AA6A1DC45523CF`
- field/method proposals: **0**

## Exact class map

| Raw v308 class | Stable ID | Recovered source name | Exact role |
| --- | --- | --- | --- |
| `rs/ui/components/a/a` | `CLIENT_CLASS_001038` | `ColorPanel` | tone/saturation-brightness color surface |
| `rs/ui/components/a/d` | `CLIENT_CLASS_001041` | `ColorPickerManager` | color-picker lifecycle manager |
| `rs/ui/components/a/e` | `CLIENT_CLASS_001042` | `ColorValuePanel` | numeric color-channel panel |
| `rs/ui/components/a/h` | `CLIENT_CLASS_001045` | `ColorValueSlider` | horizontal numeric color slider |
| `rs/ui/components/a/k` | `CLIENT_CLASS_001048` | `HuePanel` | vertical hue selector |
| `rs/ui/components/a/n` | `CLIENT_CLASS_001051` | `PreviewPanel` | selected-color preview panel |
| `rs/ui/components/a/o` | `CLIENT_CLASS_001052` | `RecentColors` | recent-color persistence/palette |
| `rs/ui/components/a/q` | `CLIENT_CLASS_001054` | `RuneliteColorPicker` | RuneLite color-picker dialog |

## Structural match

The exact v308 package `rs/ui/components/a` contains the same named source-class graph as
RuneLite's `net.runelite.client.ui.components.colorpicker` package.

Highlights:

- `rs/ui/components/a/q` is a `JDialog` with exact color-picker UI strings, four numeric
  channel panels, hue panel, color panel, preview, hex input and change/close callbacks;
- `rs/ui/components/a/d` owns the current picker and creates that dialog;
- `rs/ui/components/a/o` persists `recentColors` under the exact `colorpicker` group;
- `a`, `e`, `h`, `k`, and `n` match the upstream panel/slider/preview field and
  method responsibilities one-for-one.

Exact v308 also preserves the dialog strings:

- `Color Picker - `
- `Red`
- `Green`
- `Blue`
- `Opacity`
- `Hex color`
- `Previous`
- ` Current`
- `#000`

## Anonymous helper boundary

The remaining obfuscated siblings in `rs/ui/components/a` are mouse/focus/document-filter
helper classes corresponding to anonymous/nested implementation details in the upstream
source.

R179 deliberately does **not** invent standalone semantic names for those helpers. The goal is
to recover source-visible named classes, not inflate coverage by naming compiler artifacts.

## Provenance boundary

These eight names are stronger than ordinary descriptive inference because matching public
RuneLite source exists. The semantic proposal still remains non-canonical until explicit
acceptance.

The exact-v308 binary remains the authority for behavior and identity; the RuneLite source
commit is corroborating name provenance only.

## Acceptance boundary

Chat 2 does not promote R179. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_EDB429AA6A1DC45523CF`.
