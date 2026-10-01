# Chat 2 — residual custom-interface builders R405

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R397 already fixes the shared base/bootstrap as:

- `rs/n/c` -> `CustomInterfaceBuilder`
- `rs/n/d` -> `CustomInterfaceBootstrap`

R405 recovers three previously-unowned live builders while deliberately leaving their
unknown product domains unresolved.

## ToggleOptionSelectorInterface

`rs/n/c/aA` / `CLIENT_CLASS_000576`

Builds two roots, 53500 and 53519, around the same eighteen interactive option widgets.
Each entry has exact hover text `Select option` and generated display text
`Selecting this option Toggle N`.

The two roots use different deterministic layouts, but no surviving text identifies the
feature controlled by those toggles.

## TwoOptionSelectionDialogInterface

`rs/n/c/aT` / `CLIENT_CLASS_000595`

Adds two exact choices:

- widget 30583 -> `1`
- widget 30584 -> `2`

Both use hover text `Select option`.

It also supplies the dialog close control `Close Window` / `Close` and rewrites root
6960's six-child geometry around those controls. The feature using choices 1/2 is not
preserved.

## GameframeInfoSpriteInjector

`rs/n/c/aV` / `CLIENT_CLASS_000597`

Injects:

- `gameframe/info/sprite 2` -> child 65747 under root 29998
- `gameframe/info/sprite 3` -> child 65746 under root 29997
- `gameframe/info/sprite 4` -> child 65745 under root 29994

All are positioned at 18,12. The exact resources are proven; a higher-level feature noun
is not.

## Boundary

All three classes are constructed only by the live R397 CustomInterfaceBootstrap. Names
are deliberately behavioral rather than invented product labels.

R405 remains non-canonical semantic research only.
