# Chat 2 — exact-v308 MaterialTab helper family R258

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/ui/components/b/b` -> `CLIENT_CLASS_001061` -> `MaterialTabSelectionListener`
- `rs/ui/components/b/c` -> `CLIENT_CLASS_001062` -> `MaterialTabTextHoverListener`
- `rs/ui/components/b/d` -> `CLIENT_CLASS_001063` -> `MaterialTabIconHoverListener`
- review: `SEMREVIEW_07B73AE1DA45D496F046`
- unresolved: **0**
- field/method proposals: **0**

## Exact behavior

The reviewed `MaterialTab` installs these exact adapters:

- selection listener: on press, asks the reviewed `MaterialTabGroup` to select this tab;
- text hover listener: WHITE on enter, GRAY on exit only when not selected;
- icon hover listener: swaps the exact themed background colors on enter/exit.

They have no unrelated exact-v308 consumers.

## Deliberately unnamed

The remaining unowned `rs/ui/components/h` is an empty class and
`rs/ui/components/t` is a compiler-generated switch-map helper. R258 does not assign
semantic names to either artifact.

## Acceptance boundary

R258 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
