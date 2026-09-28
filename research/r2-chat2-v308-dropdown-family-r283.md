# Chat 2 — exact-v308 dropdown component family R283

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/a/a/a` -> `CLIENT_CLASS_000527` -> `DropDownComponent`
- `rs/n/a/a/b` -> `CLIENT_CLASS_000528` -> `DropDownMenuPanel`
- `rs/n/a/a/c` -> `CLIENT_CLASS_000529` -> `DropDownManager`
- `rs/n/a/a/e` -> `CLIENT_CLASS_000531` -> `DropDownOptionWidget`
- existing R19 authority: `rs/n/a/a/d` -> `CLIENT_CLASS_000530` -> `DropDownOption`
- review: `SEMREVIEW_2CC55EC1F08E1BC9A757`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 identity

The subsystem is fixed by surviving exact literals and live joins rather than package adjacency.

`DropDownComponent` owns a list of the already-reviewed `DropDownOption` value type. Its factory converts string options into `DropDownOption(text, "Select")`, initializes the displayed value to the first option, and selection updates map the exact option opcode range beginning at 32432 back to the selected index.

The shared helper emits the explicit exact-v308 diagnostic:

`The interface ID … is not a drop down component`

when an open request targets anything other than `rs/n/a/a/a`.

`DropDownManager` owns the common dropdown popup state. Its initialization loads `misc/dd1` and `misc/dd2`; opening binds the target component into the singleton popup panel and records the active interface id in `Client.cI`; closing resets `Client.cI` to -1 and hides the popup.

`DropDownMenuPanel` owns a fixed 25-element array of option-row widgets, the active dropdown component and popup rendering/layout state. `DropDownOptionWidget` is the row widget type consumed by that panel and renders itself relative to the active dropdown.

## Boundary

These are descriptive semantic names derived from exact-v308 behavior. R283 does not claim stripped developer identifiers, does not rename fields/methods and performs no semantic acceptance or source rewrite.
